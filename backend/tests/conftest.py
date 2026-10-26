"""Fixtures compartidas para las pruebas del backend.

IMPORTANTE — seguridad de datos:
    Estas pruebas requieren una base de datos PostgreSQL de PRUEBA real
    (SQLite no sirve: el esquema usa tipos ENUM nativos de Postgres y el
    operador `%` de `pg_trgm`). NUNCA apuntes `TEST_DATABASE_URL` a la
    base de datos de produccion: el fixture de sesion crea y DESTRUYE
    todas las tablas al terminar la corrida.

Uso tipico (Docker ya tiene un servicio `db` con Postgres):
    export TEST_DATABASE_URL="postgresql://postgres:clave@localhost:5432/pinateria_demo_test"
    pytest
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.models.categoria import Categoria
from app.models.usuario import RolUsuario, Usuario
from main import app

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    pytest.skip(
        "Define TEST_DATABASE_URL (una base de datos Postgres de PRUEBA, nunca "
        "la de produccion) para correr esta suite. Ver docstring de conftest.py.",
        allow_module_level=True,
    )

_engine = create_engine(TEST_DATABASE_URL)
_SessionLocalPrueba = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture(scope="session", autouse=True)
def preparar_base_de_datos_prueba():
    """Crea la extension pg_trgm, todas las tablas y las vistas de alertas, de margen y de clientes antes de la corrida.

    Estas pruebas usan `Base.metadata.create_all` (no las migraciones de
    Alembic) para construir el esquema, asi que los objetos de base de
    datos que las migraciones crean con `op.execute` (la extension
    `pg_trgm`, las vistas `vw_alertas_stock_bajo`, `vw_margen_detalle` y `vw_clientes_resumen`) deben replicarse aqui
    tambien. Ver `alembic/versions/0001_esquema_inicial.py`.

    Yields:
        None
    """
    with _engine.connect() as conexion:
        conexion.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        conexion.commit()

    Base.metadata.create_all(bind=_engine)

    with _engine.connect() as conexion:
        conexion.execute(
            text(
                """
                CREATE VIEW vw_alertas_stock_bajo AS
                SELECT p.id, p.nombre, p.stock_actual, p.stock_minimo, c.nombre AS categoria
                FROM productos p
                JOIN categorias c ON c.id = p.categoria_id
                WHERE p.activo = TRUE
                  AND p.stock_actual <= p.stock_minimo
                """
            )
        )
        # Adendo v2, Fase A3: vista de margen (migracion 0004).
        conexion.execute(
            text(
                """
                CREATE VIEW vw_margen_detalle AS
                SELECT d.id AS detalle_id, d.venta_id, d.producto_id, v.fecha, v.usuario_id,
                       d.cantidad,
                       d.subtotal - d.descuento_prorrateado             AS ingreso_neto,
                       d.costo_unitario * d.cantidad                    AS costo_total,
                       d.subtotal - d.descuento_prorrateado
                           - d.costo_unitario * d.cantidad              AS margen
                FROM detalle_ventas d
                JOIN ventas v ON v.id = d.venta_id
                """
            )
        )
        # Adendo v2, Fase A2: resumen de compras por cliente (migracion 0005).
        conexion.execute(
            text(
                """
                CREATE VIEW vw_clientes_resumen AS
                SELECT c.id AS cliente_id,
                       COUNT(v.id)                    AS numero_ventas,
                       COALESCE(SUM(v.total), 0)      AS total_comprado,
                       MAX(v.fecha)                   AS ultima_compra
                FROM clientes c
                LEFT JOIN ventas v ON v.cliente_id = c.id
                GROUP BY c.id
                """
            )
        )
        # Adendo v3, Fase G1: gastos y compras recibidas unificados (migracion 0009).
        conexion.execute(
            text(
                """
                CREATE VIEW vw_gastos_unificados AS
                SELECT 'gasto'::text AS origen, g.id AS origen_id, g.fecha, g.categoria_id, c.nombre AS categoria,
                       g.descripcion, g.beneficiario, g.monto, g.metodo_pago, g.plataforma, g.registrado_por_id,
                       (g.anulado_en IS NOT NULL) AS anulado, g.creado_en
                FROM gastos g
                JOIN categorias_gasto c ON c.id = g.categoria_id
                UNION ALL
                SELECT 'compra'::text, k.id,
                       (COALESCE(k.recibida_en, k.fecha) AT TIME ZONE 'America/Bogota')::date,
                       s.id, COALESCE(s.nombre, 'Compra de mercancía'),
                       'Compra #' || k.id || ' — ' || p.nombre_empresa, p.nombre_empresa, k.total, k.metodo_pago,
                       k.plataforma, k.usuario_id, FALSE, COALESCE(k.recibida_en, k.fecha)
                FROM compras k
                JOIN proveedores p ON p.id = k.proveedor_id
                LEFT JOIN categorias_gasto s ON s.es_sistema
                WHERE k.estado = 'recibida'
                """
            )
        )
        conexion.commit()

    yield

    with _engine.connect() as conexion:
        conexion.execute(text("DROP VIEW IF EXISTS vw_alertas_stock_bajo"))
        conexion.execute(text("DROP VIEW IF EXISTS vw_margen_detalle"))
        conexion.execute(text("DROP VIEW IF EXISTS vw_clientes_resumen"))
        conexion.execute(text("DROP VIEW IF EXISTS vw_gastos_unificados"))
        conexion.commit()

    Base.metadata.drop_all(bind=_engine)


@pytest.fixture
def db_session():
    """Provee una sesion de base de datos envuelta en una transaccion que se revierte al final.

    Cada prueba corre en su propia transaccion (con SAVEPOINT para el
    `db.commit()` que hacen los endpoints), que se revierte al terminar:
    las pruebas quedan aisladas entre si sin recrear el esquema cada vez.

    Yields:
        Session: La sesion de SQLAlchemy a usar en la prueba.
    """
    conexion = _engine.connect()
    transaccion_externa = conexion.begin()
    # `create_savepoint`: el commit/rollback de la sesion (y los que hacen los
    # endpoints) solo afectan un SAVEPOINT; la transaccion externa sigue intacta
    # hasta el rollback final, incluso si un endpoint hace `db.rollback()`.
    sesion = _SessionLocalPrueba(bind=conexion, join_transaction_mode="create_savepoint")

    try:
        yield sesion
    finally:
        sesion.close()
        transaccion_externa.rollback()
        conexion.close()


@pytest.fixture
def client(db_session):
    """Cliente de pruebas de FastAPI, con `get_db` sobreescrito hacia la sesion de prueba.

    Args:
        db_session: La sesion transaccional de la prueba actual.

    Yields:
        TestClient: Cliente HTTP contra la app FastAPI.
    """

    def _get_db_de_prueba():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_de_prueba
    with TestClient(app) as cliente_prueba:
        yield cliente_prueba
    app.dependency_overrides.clear()


@pytest.fixture
def categoria_prueba(db_session: Session) -> Categoria:
    """Crea una categoria de prueba ("Piñatas Infantiles").

    Args:
        db_session: Sesion de base de datos de la prueba.

    Returns:
        Categoria: La categoria creada.
    """
    categoria = Categoria(nombre="Piñatas Infantiles", descripcion="Piñatas tematicas para niños")
    db_session.add(categoria)
    db_session.commit()
    db_session.refresh(categoria)
    return categoria


def _crear_usuario(db_session: Session, username: str, rol: RolUsuario) -> Usuario:
    """Crea un usuario de prueba con contrasena conocida ("clave-de-prueba-123").

    Args:
        db_session: Sesion de base de datos de la prueba.
        username: Nombre de usuario, unico.
        rol: Rol a asignar.

    Returns:
        Usuario: El usuario creado.
    """
    usuario = Usuario(
        nombre=f"Usuario de prueba ({rol.value})",
        username=username,
        password_hash=hash_password("clave-de-prueba-123"),
        rol=rol,
        activo=True,
    )
    db_session.add(usuario)
    db_session.commit()
    db_session.refresh(usuario)
    return usuario


@pytest.fixture
def usuario_vendedor(db_session: Session) -> Usuario:
    """Crea un usuario con rol VENDEDOR."""
    return _crear_usuario(db_session, "vendedor.prueba", RolUsuario.VENDEDOR)


@pytest.fixture
def usuario_administrador(db_session: Session) -> Usuario:
    """Crea un usuario con rol ADMINISTRADOR."""
    return _crear_usuario(db_session, "admin.prueba", RolUsuario.ADMINISTRADOR)


@pytest.fixture
def usuario_propietario(db_session: Session) -> Usuario:
    """Crea un usuario con rol PROPIETARIO (solo lectura)."""
    return _crear_usuario(db_session, "propietario.prueba", RolUsuario.PROPIETARIO)


def pagos_en_efectivo(total: str) -> list[dict]:
    """Un solo pago en efectivo por el total exacto, sin vueltas (Adendo v2, `POST /ventas`).

    Args:
        total: Total de la venta ya redondeado a $50 (ej. "18000").

    Returns:
        list[dict]: La lista `pagos` del payload.
    """
    return [{"metodo_pago": "efectivo", "monto": total, "monto_recibido": total}]


def obtener_token(client: TestClient, username: str) -> str:
    """Inicia sesion con la contrasena de prueba estandar y retorna el access token.

    Args:
        client: Cliente de pruebas ya configurado.
        username: Nombre de usuario a autenticar.

    Returns:
        str: El access token JWT.
    """
    respuesta = client.post(
        "/login",
        data={"username": username, "password": "clave-de-prueba-123"},
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["access_token"]
