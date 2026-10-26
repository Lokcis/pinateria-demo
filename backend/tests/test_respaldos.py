"""Pruebas del respaldo automatico de PostgreSQL (sin base de datos real)."""

import copy
import os
import stat
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml
from sqlalchemy.engine import make_url

from app.core.celery_app import celery
from app.core.config import settings
from app.tasks import respaldos

DIA = 86400


def test_el_comando_no_expone_la_contrasena_en_los_argumentos(tmp_path):
    url = make_url("postgresql://admin:s3cr3t%40x@db:5433/pinateria_demo")

    comando, entorno = respaldos.construir_comando_pg_dump(url, tmp_path / "r.dump")

    assert "s3cr3t" not in " ".join(comando)
    assert entorno["PGPASSWORD"] == "s3cr3t@x"  # make_url decodifica el %40
    assert comando[:2] == ["pg_dump", "--format=custom"]
    assert comando[comando.index("--host") + 1] == "db"
    assert comando[comando.index("--port") + 1] == "5433"
    assert comando[-1] == "pinateria_demo"


def test_poda_solo_los_dump_mas_viejos_que_la_retencion(tmp_path):
    ahora = time.time()
    viejo, reciente, ajeno = tmp_path / "a.dump", tmp_path / "b.dump", tmp_path / "notas.txt"
    for archivo, antiguedad_dias in ((viejo, 20), (reciente, 3), (ajeno, 99)):
        archivo.write_text("x")
        os.utime(archivo, (ahora - antiguedad_dias * DIA, ahora - antiguedad_dias * DIA))

    borrados = respaldos.podar_respaldos_antiguos(tmp_path, dias=14, ahora=ahora)

    assert borrados == [viejo]
    assert not viejo.exists() and reciente.exists() and ajeno.exists()


def _completado(returncode=0, stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout="", stderr=stderr)


@pytest.fixture
def carpeta_respaldos(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "respaldos_carpeta", str(tmp_path))
    monkeypatch.setattr(settings, "database_url", "postgresql://u:p@db:5432/pinateria_demo")
    return tmp_path


def test_respaldo_exitoso_deja_un_dump_y_rota_los_viejos(carpeta_respaldos, monkeypatch):
    viejo = carpeta_respaldos / "pinateria_demo_viejo.dump"
    viejo.write_text("x")
    os.utime(viejo, (time.time() - 30 * DIA,) * 2)

    def falso_run(comando, **_):
        if comando[0] == "pg_dump":
            Path(comando[comando.index("--file") + 1]).write_bytes(b"PGDMP-contenido")
        return _completado()

    monkeypatch.setattr(respaldos.subprocess, "run", falso_run)

    ruta = Path(respaldos.respaldar_base_de_datos())

    assert ruta.exists() and ruta.suffix == ".dump"
    assert not list(carpeta_respaldos.glob("*.tmp"))
    assert not viejo.exists()


def test_si_pg_dump_falla_no_queda_archivo_y_no_se_rota(carpeta_respaldos, monkeypatch):
    viejo = carpeta_respaldos / "pinateria_demo_viejo.dump"
    viejo.write_text("x")
    os.utime(viejo, (time.time() - 30 * DIA,) * 2)
    monkeypatch.setattr(respaldos.subprocess, "run", lambda *a, **k: _completado(1, "conexion rechazada"))

    with pytest.raises(RuntimeError, match="conexion rechazada"):
        respaldos.respaldar_base_de_datos()

    assert viejo.exists()  # un respaldo fallido nunca borra los buenos
    assert not list(carpeta_respaldos.glob("*.tmp"))


def test_un_dump_ilegible_se_descarta(carpeta_respaldos, monkeypatch):
    def falso_run(comando, **_):
        if comando[0] == "pg_dump":
            Path(comando[comando.index("--file") + 1]).write_bytes(b"basura")
            return _completado()
        return _completado(1, "no es un archivo valido")

    monkeypatch.setattr(respaldos.subprocess, "run", falso_run)

    with pytest.raises(RuntimeError, match="no es valido"):
        respaldos.respaldar_base_de_datos()

    assert not list(carpeta_respaldos.iterdir())


def test_el_respaldo_esta_programado_a_diario():
    from app.core.celery_app import celery

    programa = celery.conf.beat_schedule["respaldo-diario"]
    assert programa["task"] == "respaldos.respaldar_base_de_datos"
    assert "respaldos.respaldar_base_de_datos" in celery.tasks


@pytest.mark.skipif(os.name == "nt", reason="los permisos POSIX no existen en Windows")
def test_el_dump_queda_legible_para_el_usuario_del_servidor(carpeta_respaldos, monkeypatch):
    """pg_dump lo crea en 0600 y el worker corre como root: sin chmod nadie mas podria copiarlo."""

    def falso_run(comando, **_):
        if comando[0] == "pg_dump":
            destino = Path(comando[comando.index("--file") + 1])
            destino.write_bytes(b"PGDMP-contenido")
            destino.chmod(0o600)
        return _completado()

    monkeypatch.setattr(respaldos.subprocess, "run", falso_run)

    ruta = Path(respaldos.respaldar_base_de_datos())

    assert stat.S_IMODE(ruta.stat().st_mode) == 0o644


# --- Programacion del respaldo diario (Celery Beat) --------------------------------


def _debida(ahora_utc: datetime, ultima_ejecucion_utc: datetime) -> bool:
    """Dice si Beat consideraria vencido el respaldo diario en `ahora_utc`."""
    horario = copy.copy(celery.conf.beat_schedule["respaldo-diario"]["schedule"])
    horario.nowfun = lambda: ahora_utc
    return horario.is_due(ultima_ejecucion_utc).is_due


def test_beat_sin_estado_se_salta_el_respaldo_del_dia_y_con_estado_lo_recupera():
    """Por que el estado de Beat debe persistir: tras recrear el contenedor despues de las 2:30 (7:30 UTC)."""
    ahora = datetime(2026, 10, 12, 9, 0, tzinfo=timezone.utc)  # 4:00 a. m. en Bogota
    ayer_a_las_730 = datetime(2026, 10, 11, 7, 30, tzinfo=timezone.utc)
    hoy_a_las_730 = datetime(2026, 10, 12, 7, 30, 5, tzinfo=timezone.utc)

    assert not _debida(ahora, ahora)  # arranque sin archivo de estado: "ultima vez" = ahora
    assert _debida(ahora, ayer_a_las_730)  # con el estado guardado, recupera el de hoy
    assert not _debida(ahora, hoy_a_las_730)  # y no lo repite si ya corrio


def test_el_estado_de_beat_esta_en_un_volumen_de_docker():
    compose = yaml.safe_load((Path(__file__).resolve().parents[2] / "docker-compose.yml").read_text(encoding="utf8"))
    beat = compose["services"]["celery_beat"]

    argumentos = beat["command"].split()
    archivo = Path(argumentos[argumentos.index("--schedule") + 1])
    montajes = [m.split(":") for m in beat.get("volumes", [])]
    volumen = next((origen for origen, destino, *_ in montajes if Path(destino) in archivo.parents), None)

    assert volumen is not None, f"{archivo} no esta dentro de un volumen: se pierde al recrear el contenedor"
    assert volumen in compose["volumes"], "debe ser un volumen con nombre, no una ruta del contenedor"
