"""Pruebas de RF-018: historial de ventas del dia consultable por el empleado."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.detalle_venta import DetalleVenta
from app.models.usuario import Usuario
from app.models.pago_venta import PagoVenta, PlataformaTransferencia
from app.models.venta import MetodoPago, Venta
from tests.conftest import _crear_usuario, obtener_token
from tests.test_hu01_venta import _crear_producto


def _crear_venta(
    db_session: Session,
    usuario: Usuario,
    producto_id: int,
    cantidad: int,
    precio: str,
    metodo: MetodoPago = MetodoPago.EFECTIVO,
    fecha: datetime | None = None,
) -> Venta:
    """Inserta una venta de una sola linea, pagada con un solo metodo, directamente en la base."""
    subtotal = Decimal(precio) * cantidad
    venta = Venta(
        usuario_id=usuario.id,
        subtotal=subtotal,
        total=subtotal,
        pagos=[
            PagoVenta(
                metodo_pago=metodo,
                plataforma=PlataformaTransferencia.NEQUI if metodo == MetodoPago.TRANSFERENCIA else None,
                monto=subtotal,
                monto_recibido=subtotal if metodo == MetodoPago.EFECTIVO else None,
                vueltas=0,
            )
        ],
        fecha=fecha or datetime.now(timezone.utc),
        detalles=[
            DetalleVenta(
                producto_id=producto_id, cantidad=cantidad, precio_unitario=Decimal(precio), subtotal=subtotal
            )
        ],
    )
    db_session.add(venta)
    db_session.commit()
    return venta


def _auth(client: TestClient, usuario: Usuario) -> dict[str, str]:
    return {"Authorization": f"Bearer {obtener_token(client, usuario.username)}"}


class TestHistorialDelDia:
    """RF-018: "historial de ventas del dia consultable por el empleado"."""

    def test_devuelve_las_ventas_de_hoy_con_resumen_y_nombres(
        self, client: TestClient, db_session, categoria_prueba, usuario_vendedor
    ):
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata Mickey", "25000.00", 10)
        _crear_venta(db_session, usuario_vendedor, producto.id, 2, "25000.00", MetodoPago.EFECTIVO)
        _crear_venta(db_session, usuario_vendedor, producto.id, 1, "25000.00", MetodoPago.TARJETA)

        respuesta = client.get("/ventas/hoy", headers=_auth(client, usuario_vendedor))

        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert cuerpo["cantidad_ventas"] == 2
        assert Decimal(cuerpo["total_vendido"]) == Decimal("75000.00")
        assert Decimal(cuerpo["total_por_metodo"]["efectivo"]) == Decimal("50000.00")
        assert Decimal(cuerpo["total_por_metodo"]["tarjeta"]) == Decimal("25000.00")
        assert cuerpo["ventas"][0]["detalles"][0]["nombre_producto"] == "Piñata Mickey"
        assert cuerpo["ventas"][0]["vendedor"] == usuario_vendedor.nombre

    def test_ordena_de_la_mas_reciente_a_la_mas_antigua(
        self, client: TestClient, db_session, categoria_prueba, usuario_vendedor
    ):
        producto = _crear_producto(db_session, categoria_prueba.id, "Globos", "9000.00", 10)
        ahora = datetime.now(timezone.utc)
        antigua = _crear_venta(db_session, usuario_vendedor, producto.id, 1, "9000.00", fecha=ahora - timedelta(minutes=5))
        reciente = _crear_venta(db_session, usuario_vendedor, producto.id, 1, "9000.00", fecha=ahora)

        ids = [v["id"] for v in client.get("/ventas/hoy", headers=_auth(client, usuario_vendedor)).json()["ventas"]]

        assert ids == [reciente.id, antigua.id]

    def test_no_incluye_ventas_de_dias_anteriores(
        self, client: TestClient, db_session, categoria_prueba, usuario_vendedor
    ):
        producto = _crear_producto(db_session, categoria_prueba.id, "Confeti", "3500.00", 10)
        _crear_venta(
            db_session, usuario_vendedor, producto.id, 1, "3500.00", fecha=datetime.now(timezone.utc) - timedelta(days=2)
        )

        cuerpo = client.get("/ventas/hoy", headers=_auth(client, usuario_vendedor)).json()

        assert cuerpo["cantidad_ventas"] == 0
        assert Decimal(cuerpo["total_vendido"]) == Decimal("0")

    def test_vendedor_solo_ve_sus_propias_ventas(
        self, client: TestClient, db_session, categoria_prueba, usuario_vendedor
    ):
        otro_vendedor = _crear_usuario(db_session, "otro.vendedor", usuario_vendedor.rol)
        producto = _crear_producto(db_session, categoria_prueba.id, "Dulces", "18000.00", 10)
        propia = _crear_venta(db_session, usuario_vendedor, producto.id, 1, "18000.00")
        _crear_venta(db_session, otro_vendedor, producto.id, 1, "18000.00")

        ids = [v["id"] for v in client.get("/ventas/hoy", headers=_auth(client, usuario_vendedor)).json()["ventas"]]

        assert ids == [propia.id]

    def test_administrador_ve_las_ventas_de_todos(
        self, client: TestClient, db_session, categoria_prueba, usuario_vendedor, usuario_administrador
    ):
        producto = _crear_producto(db_session, categoria_prueba.id, "Dulces", "18000.00", 10)
        _crear_venta(db_session, usuario_vendedor, producto.id, 1, "18000.00")
        _crear_venta(db_session, usuario_administrador, producto.id, 1, "18000.00")

        cuerpo = client.get("/ventas/hoy", headers=_auth(client, usuario_administrador)).json()

        assert cuerpo["cantidad_ventas"] == 2

    def test_una_venta_creada_por_la_api_aparece_en_el_historial(
        self, client: TestClient, db_session, categoria_prueba, usuario_vendedor
    ):
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata Unicornio", "32000.00", 5)
        cabeceras = _auth(client, usuario_vendedor)
        creada = client.post(
            "/ventas",
            json={
                "pagos": [{"metodo_pago": "transferencia", "plataforma": "nequi", "monto": "32000"}],
                "detalles": [{"producto_id": producto.id, "cantidad": 1}],
            },
            headers=cabeceras,
        )
        assert creada.status_code == 201

        cuerpo = client.get("/ventas/hoy", headers=cabeceras).json()

        assert [v["id"] for v in cuerpo["ventas"]] == [creada.json()["id"]]
        assert "transferencia" in cuerpo["total_por_metodo"]

    def test_propietario_recibe_403(self, client: TestClient, usuario_propietario):
        respuesta = client.get("/ventas/hoy", headers=_auth(client, usuario_propietario))
        assert respuesta.status_code == 403

    def test_sin_token_devuelve_401(self, client: TestClient):
        assert client.get("/ventas/hoy").status_code == 401
