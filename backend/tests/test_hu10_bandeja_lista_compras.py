"""Pruebas de aceptacion de HU-10 (Adendo v2, mejora B1: RF-043 a RF-045).

Bandeja de notificaciones de stock bajo y lista de compras del Dashboard. Cada
clase cita, en su docstring, el criterio de `docs/02-historias-de-usuario.md`
(seccion 3.10) que cubre. El criterio del enlace de WhatsApp (RF-045) se arma
en el frontend y se prueba alli.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.notificacion import Notificacion, TipoNotificacion
from app.models.producto import Producto, TipoProducto
from app.tasks.alertas import revisar_stock_bajo_impl
from tests.conftest import obtener_token
from tests.test_hu01_venta import _crear_producto

_RUTAS_GET = ["/notificaciones", "/dashboard/lista-compras"]
_RUTAS_PATCH = ["/notificaciones/leer-todas", "/notificaciones/1/leida"]


def _auth(client: TestClient, usuario) -> dict[str, str]:
    """Devuelve el header Authorization para el usuario dado."""
    return {"Authorization": f"Bearer {obtener_token(client, usuario.username)}"}


def _crear_notificacion(
    db_session: Session,
    producto: Producto | None,
    hace_minutos: int = 0,
    leida: bool = False,
) -> Notificacion:
    """Crea una notificacion de stock bajo con una fecha de creacion controlada.

    Args:
        db_session: Sesion de base de datos de la prueba.
        producto: Producto que la origina, o None (producto eliminado).
        hace_minutos: Antiguedad de la notificacion.
        leida: Si se crea ya leida.

    Returns:
        Notificacion: La notificacion creada.
    """
    notificacion = Notificacion(
        tipo=TipoNotificacion.STOCK_BAJO,
        producto_id=producto.id if producto is not None else None,
        mensaje=f"Stock bajo: {producto.nombre if producto else 'producto'}.",
        leida=leida,
        creada_en=datetime.now(timezone.utc) - timedelta(minutes=hace_minutos),
    )
    db_session.add(notificacion)
    db_session.commit()
    db_session.refresh(notificacion)
    return notificacion


def _producto(db_session: Session, categoria_id: int, nombre: str, stock: int, minimo: int, **kwargs) -> Producto:
    """Crea un producto con stock y minimo dados."""
    producto = _crear_producto(db_session, categoria_id, nombre, "1000", stock, **kwargs)
    producto.stock_minimo = minimo
    db_session.commit()
    return producto


class TestAcceso:
    """HU-10: "Confirmar que el vendedor reciba 403 al consultar la bandeja y la lista de compras"."""

    @pytest.mark.parametrize("ruta", _RUTAS_GET)
    def test_propietario_y_administrador_pueden_consultar(
        self, client, usuario_propietario, usuario_administrador, ruta
    ):
        assert client.get(ruta, headers=_auth(client, usuario_propietario)).status_code == 200
        assert client.get(ruta, headers=_auth(client, usuario_administrador)).status_code == 200

    @pytest.mark.parametrize("ruta", _RUTAS_GET)
    def test_vendedor_recibe_403_al_consultar(self, client, usuario_vendedor, ruta):
        assert client.get(ruta, headers=_auth(client, usuario_vendedor)).status_code == 403

    @pytest.mark.parametrize("ruta", _RUTAS_PATCH)
    def test_vendedor_recibe_403_al_marcar(self, client, usuario_vendedor, ruta):
        assert client.patch(ruta, headers=_auth(client, usuario_vendedor)).status_code == 403

    @pytest.mark.parametrize("ruta", _RUTAS_GET)
    def test_sin_token_recibe_401_al_consultar(self, client, ruta):
        assert client.get(ruta).status_code == 401

    @pytest.mark.parametrize("ruta", _RUTAS_PATCH)
    def test_sin_token_recibe_401_al_marcar(self, client, ruta):
        assert client.patch(ruta).status_code == 401


class TestBandeja:
    """HU-10: "la bandeja muestre las notificaciones de stock bajo de la mas reciente a la mas
    antigua y que el Dashboard muestre el contador de no leidas"."""

    def test_bandeja_vacia(self, client, usuario_propietario):
        cuerpo = client.get("/notificaciones", headers=_auth(client, usuario_propietario)).json()
        assert cuerpo == {"no_leidas": 0, "notificaciones": []}

    def test_orden_de_la_mas_reciente_a_la_mas_antigua_y_contador(
        self, client, db_session, categoria_prueba, usuario_propietario
    ):
        globos = _producto(db_session, categoria_prueba.id, "Globos", 2, 10)
        velas = _producto(db_session, categoria_prueba.id, "Velas", 1, 5)
        vieja = _crear_notificacion(db_session, globos, hace_minutos=60, leida=True)
        media = _crear_notificacion(db_session, velas, hace_minutos=30)
        nueva = _crear_notificacion(db_session, globos, hace_minutos=1)

        cuerpo = client.get("/notificaciones", headers=_auth(client, usuario_propietario)).json()

        assert cuerpo["no_leidas"] == 2
        assert [n["id"] for n in cuerpo["notificaciones"]] == [nueva.id, media.id, vieja.id]
        primera = cuerpo["notificaciones"][0]
        assert primera["producto_id"] == globos.id
        assert primera["producto_nombre"] == "Globos"
        assert primera["tipo"] == "stock_bajo"
        assert primera["leida"] is False

    def test_filtro_solo_no_leidas_y_limite(self, client, db_session, categoria_prueba, usuario_propietario):
        globos = _producto(db_session, categoria_prueba.id, "Globos", 2, 10)
        _crear_notificacion(db_session, globos, hace_minutos=60, leida=True)
        for minutos in (3, 2, 1):
            _crear_notificacion(db_session, globos, hace_minutos=minutos)

        cuerpo = client.get(
            "/notificaciones",
            params={"solo_no_leidas": True, "limite": 2},
            headers=_auth(client, usuario_propietario),
        ).json()

        assert cuerpo["no_leidas"] == 3  # el contador no depende del filtro ni del limite
        assert len(cuerpo["notificaciones"]) == 2
        assert all(not n["leida"] for n in cuerpo["notificaciones"])

    @pytest.mark.parametrize("limite", [0, 201])
    def test_limite_fuera_de_rango_es_422(self, client, usuario_propietario, limite):
        respuesta = client.get(
            "/notificaciones", params={"limite": limite}, headers=_auth(client, usuario_propietario)
        )
        assert respuesta.status_code == 422

    def test_notificacion_de_producto_eliminado_se_muestra_sin_nombre(
        self, client, db_session, usuario_propietario
    ):
        _crear_notificacion(db_session, None)

        cuerpo = client.get("/notificaciones", headers=_auth(client, usuario_propietario)).json()

        assert cuerpo["notificaciones"][0]["producto_id"] is None
        assert cuerpo["notificaciones"][0]["producto_nombre"] is None


class TestMarcarComoLeidas:
    """HU-10: "se pueda marcar una notificacion como leida o todas a la vez, y que las leidas
    dejen de contar"."""

    def test_marcar_una_la_descuenta_del_contador(
        self, client, db_session, categoria_prueba, usuario_administrador
    ):
        globos = _producto(db_session, categoria_prueba.id, "Globos", 2, 10)
        primera = _crear_notificacion(db_session, globos, hace_minutos=2)
        _crear_notificacion(db_session, globos, hace_minutos=1)
        headers = _auth(client, usuario_administrador)

        respuesta = client.patch(f"/notificaciones/{primera.id}/leida", headers=headers)

        assert respuesta.status_code == 200
        assert respuesta.json()["leida"] is True
        assert respuesta.json()["producto_nombre"] == "Globos"
        assert client.get("/notificaciones", headers=headers).json()["no_leidas"] == 1

    def test_marcar_una_ya_leida_no_falla(self, client, db_session, categoria_prueba, usuario_propietario):
        globos = _producto(db_session, categoria_prueba.id, "Globos", 2, 10)
        leida = _crear_notificacion(db_session, globos, leida=True)

        respuesta = client.patch(f"/notificaciones/{leida.id}/leida", headers=_auth(client, usuario_propietario))

        assert respuesta.status_code == 200
        assert respuesta.json()["leida"] is True

    def test_marcar_una_inexistente_es_404(self, client, usuario_propietario):
        respuesta = client.patch("/notificaciones/999999/leida", headers=_auth(client, usuario_propietario))
        assert respuesta.status_code == 404

    def test_leer_todas_deja_el_contador_en_cero(self, client, db_session, categoria_prueba, usuario_propietario):
        globos = _producto(db_session, categoria_prueba.id, "Globos", 2, 10)
        _crear_notificacion(db_session, globos, leida=True)
        _crear_notificacion(db_session, globos)
        _crear_notificacion(db_session, None)
        headers = _auth(client, usuario_propietario)

        respuesta = client.patch("/notificaciones/leer-todas", headers=headers)

        assert respuesta.status_code == 200
        assert respuesta.json() == {"marcadas": 2}
        assert client.get("/notificaciones", headers=headers).json()["no_leidas"] == 0
        assert client.patch("/notificaciones/leer-todas", headers=headers).json() == {"marcadas": 0}


class TestSinAvisosDuplicados:
    """HU-10: "un producto no genere avisos duplicados mientras tenga una alerta sin leer"; al
    marcarla como leida, la siguiente corrida puede volver a avisar si sigue en stock bajo."""

    def test_tras_marcar_leida_la_tarea_vuelve_a_avisar(
        self, client, db_session, categoria_prueba, usuario_propietario
    ):
        _producto(db_session, categoria_prueba.id, "Globos", 2, 10)
        headers = _auth(client, usuario_propietario)

        assert revisar_stock_bajo_impl(db_session) == 1
        assert revisar_stock_bajo_impl(db_session) == 0
        client.patch("/notificaciones/leer-todas", headers=headers)
        assert revisar_stock_bajo_impl(db_session) == 1

        assert client.get("/notificaciones", headers=headers).json()["no_leidas"] == 1


class TestListaDeCompras:
    """HU-10: "la lista de compras incluya cada producto activo en stock bajo con su stock actual,
    su stock minimo y la cantidad faltante (stock minimo menos stock actual), calculada al abrirla"."""

    def test_lista_vacia(self, client, usuario_propietario):
        cuerpo = client.get("/dashboard/lista-compras", headers=_auth(client, usuario_propietario)).json()
        assert cuerpo["productos"] == []
        assert cuerpo["generado_en"]

    def test_faltante_orden_y_exclusiones(self, client, db_session, categoria_prueba, usuario_propietario):
        _producto(db_session, categoria_prueba.id, "Velas", 1, 5)
        _producto(db_session, categoria_prueba.id, "Globos", 0, 25)
        _producto(db_session, categoria_prueba.id, "Confeti", 6, 5)  # sobre el minimo: no aparece
        inactivo = _producto(db_session, categoria_prueba.id, "Antifaz", 0, 5)
        inactivo.activo = False
        db_session.commit()

        cuerpo = client.get("/dashboard/lista-compras", headers=_auth(client, usuario_propietario)).json()

        assert [(p["nombre"], p["stock_actual"], p["stock_minimo"], p["faltante"]) for p in cuerpo["productos"]] == [
            ("Globos", 0, 25, 25),
            ("Velas", 1, 5, 4),
        ]
        assert cuerpo["productos"][0]["categoria"] == categoria_prueba.nombre

    def test_incluye_productos_justo_en_el_minimo_con_faltante_cero(
        self, client, db_session, categoria_prueba, usuario_propietario
    ):
        _producto(db_session, categoria_prueba.id, "Serpentinas", 5, 5)

        cuerpo = client.get("/dashboard/lista-compras", headers=_auth(client, usuario_propietario)).json()

        assert [(p["nombre"], p["faltante"]) for p in cuerpo["productos"]] == [("Serpentinas", 0)]

    def test_incluye_compuestos_como_cualquier_producto(
        self, client, db_session, categoria_prueba, usuario_propietario
    ):
        _producto(db_session, categoria_prueba.id, "Ancheta cumpleaños", 0, 2, tipo=TipoProducto.ANCHETA)

        cuerpo = client.get("/dashboard/lista-compras", headers=_auth(client, usuario_propietario)).json()

        assert [(p["nombre"], p["faltante"]) for p in cuerpo["productos"]] == [("Ancheta cumpleaños", 2)]

    def test_se_calcula_al_abrirla(self, client, db_session, categoria_prueba, usuario_propietario):
        globos = _producto(db_session, categoria_prueba.id, "Globos", 2, 10)
        headers = _auth(client, usuario_propietario)
        assert client.get("/dashboard/lista-compras", headers=headers).json()["productos"][0]["faltante"] == 8

        globos.stock_actual = 7
        db_session.commit()
        assert client.get("/dashboard/lista-compras", headers=headers).json()["productos"][0]["faltante"] == 3

        globos.stock_actual = 30
        db_session.commit()
        assert client.get("/dashboard/lista-compras", headers=headers).json()["productos"] == []
