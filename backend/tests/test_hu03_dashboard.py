"""Pruebas de aceptacion de HU-03 (Dashboard de supervision remota del propietario) y RF-013/RF-014.

Cada clase cita, en su docstring, el criterio de
`HistoriasDeUsuario_PinateriaDemo_v1_0.docx` que cubre. El criterio de
"carga en menos de 10 s desde una red movil" se cubre con una cota de latencia
del endpoint en la prueba de rendimiento; la parte de red (Cloudflare Tunnel)
se verifica manualmente segun `DEPLOY.md`.
"""

import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.compra import Compra, EstadoCompra
from app.models.proveedor import Proveedor
from app.models.venta import MetodoPago
from tests.conftest import obtener_token
from tests.test_historial_ventas import _crear_venta
from tests.test_hu01_venta import _crear_producto


def _auth(client: TestClient, usuario) -> dict[str, str]:
    """Devuelve el header Authorization para el usuario dado."""
    return {"Authorization": f"Bearer {obtener_token(client, usuario.username)}"}


class TestAccesoSoloLectura:
    """HU-03: el Dashboard es de solo lectura para el propietario; el vendedor no accede."""

    @pytest.mark.parametrize("ruta", ["/dashboard/resumen", "/dashboard/alertas-stock"])
    def test_propietario_y_administrador_pueden_consultar(
        self, client, usuario_propietario, usuario_administrador, ruta
    ):
        assert client.get(ruta, headers=_auth(client, usuario_propietario)).status_code == 200
        assert client.get(ruta, headers=_auth(client, usuario_administrador)).status_code == 200

    @pytest.mark.parametrize("ruta", ["/dashboard/resumen", "/dashboard/alertas-stock"])
    def test_vendedor_recibe_403(self, client, usuario_vendedor, ruta):
        assert client.get(ruta, headers=_auth(client, usuario_vendedor)).status_code == 403

    @pytest.mark.parametrize("ruta", ["/dashboard/resumen", "/dashboard/alertas-stock"])
    def test_sin_token_recibe_401(self, client, ruta):
        assert client.get(ruta).status_code == 401


class TestVentasTotalesDelDia:
    """HU-03: "ventas totales del dia actual, con actualizacion automatica"."""

    def test_dia_sin_ventas_devuelve_ceros(self, client, usuario_propietario):
        cuerpo = client.get("/dashboard/resumen", headers=_auth(client, usuario_propietario)).json()
        assert Decimal(cuerpo["total_vendido"]) == 0
        assert cuerpo["cantidad_ventas"] == 0
        assert Decimal(cuerpo["ticket_promedio"]) == 0
        assert cuerpo["total_por_metodo"] == {}
        assert cuerpo["top_productos"] == []

    def test_suma_ventas_de_todos_los_vendedores_con_desglose_y_promedio(
        self, client, db_session: Session, categoria_prueba, usuario_propietario, usuario_vendedor, usuario_administrador
    ):
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata Mickey", "25000", 50)
        _crear_venta(db_session, usuario_vendedor, producto.id, 2, "25000", MetodoPago.EFECTIVO)
        _crear_venta(db_session, usuario_administrador, producto.id, 1, "25000", MetodoPago.TARJETA)

        cuerpo = client.get("/dashboard/resumen", headers=_auth(client, usuario_propietario)).json()

        assert Decimal(cuerpo["total_vendido"]) == 75000
        assert cuerpo["cantidad_ventas"] == 2
        assert Decimal(cuerpo["ticket_promedio"]) == 37500
        assert {k: Decimal(v) for k, v in cuerpo["total_por_metodo"].items()} == {
            "efectivo": Decimal(50000),
            "tarjeta": Decimal(25000),
        }

    def test_el_dia_se_calcula_en_hora_de_bogota_no_utc(
        self, client, db_session: Session, categoria_prueba, usuario_propietario, usuario_vendedor
    ):
        """Una venta de ayer a las 11 pm en Bogota (ya "hoy" en UTC) no cuenta como hoy."""
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "1000", 50)
        zona = ZoneInfo("America/Bogota")
        ayer_23h = datetime.now(zona).replace(hour=23, minute=0, second=0, microsecond=0) - timedelta(days=1)
        _crear_venta(db_session, usuario_vendedor, producto.id, 1, "1000", fecha=ayer_23h)
        _crear_venta(db_session, usuario_vendedor, producto.id, 1, "1000", fecha=datetime.now(timezone.utc))

        cuerpo = client.get("/dashboard/resumen", headers=_auth(client, usuario_propietario)).json()

        assert cuerpo["cantidad_ventas"] == 1
        assert Decimal(cuerpo["total_vendido"]) == 1000

    def test_top_productos_ordenado_por_unidades_y_limitado_a_cinco(
        self, client, db_session: Session, categoria_prueba, usuario_propietario, usuario_vendedor
    ):
        for indice in range(1, 7):
            producto = _crear_producto(db_session, categoria_prueba.id, f"Producto {indice}", "1000", 100)
            _crear_venta(db_session, usuario_vendedor, producto.id, indice, "1000")

        top = client.get("/dashboard/resumen", headers=_auth(client, usuario_propietario)).json()["top_productos"]

        assert [p["nombre"] for p in top] == ["Producto 6", "Producto 5", "Producto 4", "Producto 3", "Producto 2"]
        assert top[0]["unidades"] == 6
        assert Decimal(top[0]["total"]) == 6000


class TestComprasDelDia:
    """RF-014: el propietario supervisa a distancia tambien el abastecimiento del dia."""

    def test_cuenta_compras_recibidas_y_pendientes_de_hoy(
        self, client, db_session: Session, usuario_propietario, usuario_administrador
    ):
        proveedor = Proveedor(nombre_empresa="Papeles del Valle SAS", nombre_contacto="Marta", telefono="3001112233")
        db_session.add(proveedor)
        db_session.commit()
        for estado, total in ((EstadoCompra.RECIBIDA, "50000"), (EstadoCompra.RECIBIDA, "30000"), (EstadoCompra.PENDIENTE, "9000"), (EstadoCompra.CANCELADA, "1000")):
            db_session.add(
                Compra(proveedor_id=proveedor.id, usuario_id=usuario_administrador.id, estado=estado, total=Decimal(total))
            )
        db_session.commit()

        compras = client.get("/dashboard/resumen", headers=_auth(client, usuario_propietario)).json()["compras"]

        assert compras["recibidas"] == 2
        assert compras["pendientes"] == 1
        assert Decimal(compras["total_recibido"]) == 80000


class TestAlertasDeStockBajo:
    """HU-03: "alertas de stock bajo cuando stock_actual <= stock_minimo" (RF-013)."""

    def test_lista_solo_productos_activos_en_o_bajo_el_minimo(
        self, client, db_session: Session, categoria_prueba, usuario_propietario
    ):
        bajo = _crear_producto(db_session, categoria_prueba.id, "Bajo", "1000", 2)
        igual = _crear_producto(db_session, categoria_prueba.id, "Igual", "1000", 5)
        sobrado = _crear_producto(db_session, categoria_prueba.id, "Sobrado", "1000", 50)
        inactivo = _crear_producto(db_session, categoria_prueba.id, "Inactivo", "1000", 0)
        inactivo.activo = False
        db_session.commit()

        headers = _auth(client, usuario_propietario)
        alertas = client.get("/dashboard/alertas-stock", headers=headers).json()

        assert [a["nombre"] for a in alertas] == ["Bajo", "Igual"]
        assert alertas[0] == {
            "id": bajo.id,
            "nombre": "Bajo",
            "categoria": categoria_prueba.nombre,
            "stock_actual": 2,
            "stock_minimo": 5,
        }
        assert {igual.id, bajo.id}.isdisjoint({sobrado.id, inactivo.id})
        assert client.get("/dashboard/resumen", headers=headers).json()["alertas_stock_bajo"] == 2

    def test_las_mas_criticas_aparecen_primero(
        self, client, db_session: Session, categoria_prueba, usuario_propietario
    ):
        _crear_producto(db_session, categoria_prueba.id, "Casi", "1000", 5)
        _crear_producto(db_session, categoria_prueba.id, "Agotado", "1000", 0)

        alertas = client.get("/dashboard/alertas-stock", headers=_auth(client, usuario_propietario)).json()

        assert [a["nombre"] for a in alertas] == ["Agotado", "Casi"]


class TestTiempoDeCarga:
    """HU-03: "el Dashboard carga en menos de 10 s desde una red movil externa"."""

    def test_el_resumen_responde_muy_por_debajo_del_presupuesto_de_10_s(
        self, client, db_session: Session, categoria_prueba, usuario_propietario, usuario_vendedor
    ):
        producto = _crear_producto(db_session, categoria_prueba.id, "Producto", "1000", 500)
        for _ in range(30):
            _crear_venta(db_session, usuario_vendedor, producto.id, 1, "1000")
        headers = _auth(client, usuario_propietario)

        inicio = time.perf_counter()
        respuesta = client.get("/dashboard/resumen", headers=headers)
        transcurrido = time.perf_counter() - inicio

        assert respuesta.status_code == 200
        assert transcurrido < 2.0


def _dia_bogota(dias_atras: int, hora: int = 12) -> datetime:
    """Devuelve un instante de hace `dias_atras` dias a la `hora` de Bogota."""
    zona = ZoneInfo("America/Bogota")
    return datetime.now(zona).replace(hour=hora, minute=0, second=0, microsecond=0) - timedelta(days=dias_atras)


class TestRangosDeFechas:
    """HU-03 ampliada: el propietario consulta hoy, ayer, semana, mes, ... o un rango personalizado."""

    @pytest.fixture
    def con_ventas(self, db_session: Session, categoria_prueba, usuario_vendedor):
        """Una venta de $1.000 hoy, ayer, hace 5, hace 20 y hace 100 dias."""
        producto = _crear_producto(db_session, categoria_prueba.id, "Producto", "1000", 500)
        for dias in (0, 1, 5, 20, 100):
            _crear_venta(db_session, usuario_vendedor, producto.id, 1, "1000", fecha=_dia_bogota(dias))

    def _resumen(self, client, usuario, **parametros):
        return client.get("/dashboard/resumen", params=parametros, headers=_auth(client, usuario))

    def test_sin_parametros_es_solo_hoy(self, client, con_ventas, usuario_propietario):
        cuerpo = self._resumen(client, usuario_propietario).json()
        assert cuerpo["desde"] == cuerpo["hasta"]
        assert cuerpo["cantidad_ventas"] == 1
        assert len(cuerpo["ventas_por_dia"]) == 1

    def test_ayer(self, client, con_ventas, usuario_propietario):
        ayer = _dia_bogota(1).date().isoformat()
        cuerpo = self._resumen(client, usuario_propietario, desde=ayer, hasta=ayer).json()
        assert cuerpo["cantidad_ventas"] == 1
        assert Decimal(cuerpo["total_vendido"]) == 1000

    def test_ultimos_7_dias_incluye_hoy_y_deja_fuera_lo_anterior(self, client, con_ventas, usuario_propietario):
        cuerpo = self._resumen(
            client, usuario_propietario, desde=_dia_bogota(6).date().isoformat(), hasta=_dia_bogota(0).date().isoformat()
        ).json()
        assert cuerpo["cantidad_ventas"] == 3  # hoy, ayer y hace 5 dias
        assert Decimal(cuerpo["total_vendido"]) == 3000

    def test_rango_largo_suma_todo_lo_que_cae_dentro(self, client, con_ventas, usuario_propietario):
        cuerpo = self._resumen(
            client, usuario_propietario, desde=_dia_bogota(179).date().isoformat(), hasta=_dia_bogota(0).date().isoformat()
        ).json()
        assert cuerpo["cantidad_ventas"] == 5

    def test_la_serie_trae_un_elemento_por_dia_con_ceros(self, client, con_ventas, usuario_propietario):
        cuerpo = self._resumen(
            client, usuario_propietario, desde=_dia_bogota(6).date().isoformat(), hasta=_dia_bogota(0).date().isoformat()
        ).json()
        serie = cuerpo["ventas_por_dia"]
        assert len(serie) == 7
        assert [d["fecha"] for d in serie] == sorted(d["fecha"] for d in serie)
        assert [Decimal(d["total"]) for d in serie] == [0, 1000, 0, 0, 0, 1000, 1000]
        assert sum(Decimal(d["total"]) for d in serie) == Decimal(cuerpo["total_vendido"])
        assert sum(d["cantidad"] for d in serie) == cuerpo["cantidad_ventas"]

    def test_hasta_sin_desde_consulta_un_solo_dia(self, client, con_ventas, usuario_propietario):
        cuerpo = self._resumen(client, usuario_propietario, hasta=_dia_bogota(1).date().isoformat()).json()
        assert cuerpo["desde"] == cuerpo["hasta"] == _dia_bogota(1).date().isoformat()
        assert cuerpo["cantidad_ventas"] == 1

    @pytest.mark.parametrize(
        "parametros",
        [
            {"desde": "2099-01-01", "hasta": "2099-01-02"},  # futuro
            {"desde": "2026-01-10", "hasta": "2026-01-01"},  # invertido
            {"desde": "2020-01-01", "hasta": "2026-01-01"},  # mas de 366 dias
            {"desde": "no-es-fecha"},
        ],
    )
    def test_rangos_invalidos_responden_422(self, client, usuario_propietario, parametros):
        assert self._resumen(client, usuario_propietario, **parametros).status_code == 422

    def test_las_compras_respetan_el_rango(self, client, db_session: Session, usuario_propietario, usuario_administrador):
        proveedor = Proveedor(nombre_empresa="Proveedor", nombre_contacto="Ana", telefono="3001112233")
        db_session.add(proveedor)
        db_session.commit()
        for dias in (0, 10):
            db_session.add(
                Compra(
                    proveedor_id=proveedor.id,
                    usuario_id=usuario_administrador.id,
                    estado=EstadoCompra.RECIBIDA,
                    total=Decimal("1000"),
                    fecha=_dia_bogota(dias),
                )
            )
        db_session.commit()

        solo_hoy = self._resumen(client, usuario_propietario).json()["compras"]
        mes = self._resumen(
            client, usuario_propietario, desde=_dia_bogota(29).date().isoformat(), hasta=_dia_bogota(0).date().isoformat()
        ).json()["compras"]

        assert solo_hoy["recibidas"] == 1
        assert mes["recibidas"] == 2
