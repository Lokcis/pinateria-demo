"""Configuracion centralizada de la aplicacion.

Carga la configuracion desde variables de entorno (o un archivo .env en
desarrollo local) usando pydantic-settings. Ninguna credencial tiene un
valor por defecto: si falta una variable de entorno requerida, la
aplicacion debe fallar al arrancar en lugar de usar un secreto de
respaldo hardcodeado.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuracion de la aplicacion cargada desde el entorno.

    Attributes:
        database_url: Cadena de conexion a PostgreSQL. Requerida, sin
            valor por defecto (nunca debe contener credenciales de
            respaldo hardcodeadas en el codigo fuente).
        redis_url: Cadena de conexion a Redis, usada como broker/backend
            de Celery.
        secret_key: Clave secreta usada para firmar los tokens JWT.
            Requerida, sin valor por defecto.
        jwt_algorithm: Algoritmo de firma para los tokens JWT.
        access_token_expire_minutes: Minutos de vigencia de un access
            token antes de expirar.
        environment: Nombre del entorno de ejecucion (development,
            staging, production). Util para condicionar comportamiento
            no critico (por ejemplo, nivel de logging).
        cors_origins: Origenes permitidos por CORS, separados por comas
            (por defecto, el servidor de desarrollo de Vite).
        zona_horaria: Zona horaria del negocio; define cuando empieza y
            termina "el dia" en el historial de ventas.
        respaldos_carpeta: Carpeta (dentro del contenedor) donde se guardan
            los respaldos de PostgreSQL; docker-compose la mapea a `./backups`.
        respaldos_dias_retencion: Dias que se conservan los respaldos; los
            mas antiguos se borran despues de cada respaldo exitoso.
        ventas_sin_conexion_dias_max: Antiguedad maxima, en dias, de una venta hecha sin conexion
            que el servidor acepta al recibirla (Fase 9).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str
    redis_url: str
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8
    environment: str = "production"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    zona_horaria: str = "America/Bogota"
    respaldos_carpeta: str = "/app/backups"
    respaldos_dias_retencion: int = 14
    ventas_sin_conexion_dias_max: int = 7


@lru_cache
def get_settings() -> Settings:
    """Retorna una instancia cacheada de Settings.

    Usa lru_cache para que Settings se instancie (y valide contra el
    entorno) una unica vez por proceso, evitando relecturas repetidas
    de variables de entorno en cada request.

    Returns:
        Settings: La configuracion validada de la aplicacion.

    Raises:
        pydantic.ValidationError: Si falta una variable de entorno
            requerida (por ejemplo, DATABASE_URL o SECRET_KEY), la
            aplicacion no debe arrancar.
    """
    return Settings()


settings = get_settings()
