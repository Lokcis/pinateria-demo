"""Configuracion de la conexion a base de datos con SQLAlchemy.

Expone el engine, la fabrica de sesiones (SessionLocal), la clase base
declarativa (Base) que heredan todos los modelos ORM, y la dependencia
get_db para inyectar sesiones en los endpoints de FastAPI.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Provee una sesion de base de datos por request (dependencia FastAPI).

    Garantiza que la sesion se cierre siempre, incluso si el endpoint
    lanza una excepcion, para evitar fugas de conexiones del pool.

    Yields:
        Session: Una sesion de SQLAlchemy vinculada al engine configurado.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
