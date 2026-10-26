"""Respaldo automatico de PostgreSQL (Celery Beat, diario).

Genera un `pg_dump` en formato custom (`.dump`, restaurable con
`pg_restore`), lo verifica y borra los respaldos mas antiguos que la
retencion configurada. Los archivos se escriben en `RESPALDOS_CARPETA`,
que docker-compose mapea a `./backups` en el servidor.
"""

import logging
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy.engine import URL, make_url

from app.core.celery_app import celery
from app.core.config import settings

logger = logging.getLogger(__name__)

TIMEOUT_SEGUNDOS = 900
SEGUNDOS_POR_DIA = 86400


def construir_comando_pg_dump(url: URL, destino: Path) -> tuple[list[str], dict[str, str]]:
    """Arma el comando `pg_dump` y su entorno, sin poner la contrasena en los argumentos.

    La contrasena viaja en `PGPASSWORD` (no en la linea de comandos) para que
    no aparezca en la lista de procesos ni en los logs.

    Args:
        url: Conexion a la base de datos a respaldar.
        destino: Archivo `.dump` a generar.

    Returns:
        tuple[list[str], dict[str, str]]: Comando y variables de entorno.
    """
    comando = [
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--host", url.host or "localhost",
        "--port", str(url.port or 5432),
        "--username", url.username or "postgres",
        "--file", str(destino),
        url.database or "",
    ]
    entorno = {**os.environ, "PGPASSWORD": url.password or ""}
    return comando, entorno


def podar_respaldos_antiguos(carpeta: Path, dias: int, ahora: float | None = None) -> list[Path]:
    """Borra los `.dump` de `carpeta` con mas de `dias` dias de antiguedad.

    Args:
        carpeta: Carpeta de respaldos.
        dias: Dias de retencion. Los archivos mas nuevos se conservan.
        ahora: Instante de referencia (segundos epoch); por defecto, el actual.

    Returns:
        list[Path]: Los archivos borrados.
    """
    limite = (ahora if ahora is not None else time.time()) - dias * SEGUNDOS_POR_DIA
    borrados = []
    for archivo in carpeta.glob("*.dump"):
        if archivo.stat().st_mtime < limite:
            archivo.unlink()
            borrados.append(archivo)
    return borrados


@celery.task(name="respaldos.respaldar_base_de_datos")
def respaldar_base_de_datos() -> str:
    """Genera, verifica y rota el respaldo de PostgreSQL.

    El archivo se escribe primero con extension `.tmp` y solo se renombra a
    `.dump` si `pg_restore --list` puede leerlo: un respaldo a medias o
    corrupto nunca queda con apariencia de valido ni desplaza a uno bueno
    (la rotacion solo corre despues de un respaldo exitoso).

    Returns:
        str: Ruta del respaldo generado.

    Raises:
        RuntimeError: Si `pg_dump` falla, se pasa del tiempo, o el archivo
            generado no se puede leer.
    """
    carpeta = Path(settings.respaldos_carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)

    url = make_url(settings.database_url)
    marca = datetime.now(ZoneInfo(settings.zona_horaria)).strftime("%Y%m%d_%H%M%S")
    final = carpeta / f"{url.database}_{marca}.dump"
    temporal = final.with_suffix(".dump.tmp")

    comando, entorno = construir_comando_pg_dump(url, temporal)
    try:
        resultado = subprocess.run(
            comando, env=entorno, capture_output=True, text=True, timeout=TIMEOUT_SEGUNDOS, check=False
        )
        if resultado.returncode != 0:
            raise RuntimeError(f"pg_dump fallo (codigo {resultado.returncode}): {resultado.stderr.strip()}")

        verificacion = subprocess.run(
            ["pg_restore", "--list", str(temporal)], capture_output=True, text=True, timeout=60, check=False
        )
        if verificacion.returncode != 0 or not temporal.stat().st_size:
            raise RuntimeError(f"El respaldo generado no es valido: {verificacion.stderr.strip()}")
        # pg_dump lo crea con permisos 0600 y el contenedor corre como root: sin esto el usuario del
        # servidor no podria leerlo (copiarlo fuera del servidor). El acceso lo limita la carpeta ./backups.
        temporal.chmod(0o644)
    except (RuntimeError, subprocess.TimeoutExpired, OSError) as error:
        temporal.unlink(missing_ok=True)
        logger.error("Respaldo de PostgreSQL fallido: %s", error)
        raise RuntimeError(f"Respaldo de PostgreSQL fallido: {error}") from error

    temporal.rename(final)
    borrados = podar_respaldos_antiguos(carpeta, settings.respaldos_dias_retencion)
    logger.info(
        "Respaldo creado: %s (%.1f MB). Respaldos antiguos eliminados: %d",
        final.name,
        final.stat().st_size / 1_048_576,
        len(borrados),
    )
    return str(final)
