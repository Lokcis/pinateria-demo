"""Pruebas de la Fase 9 (modo sin conexion): envio idempotente y ventas hechas sin conexion.

Cubren lo que el servidor garantiza cuando el POS envia una venta que quedo en su cola local:
reenviarla no la duplica ni vuelve a descontar stock, conserva la hora y los precios que vio el
cliente y respeta las mismas reglas de stock, pagos y topes de una venta normal. La cola y la
sincronizacion del navegador se prueban en el frontend (`frontend/src/offline/`).
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.descuento import DescuentoGeneral, TipoDescuento, TopeDescuento
from app.models.detalle_venta import DetalleVenta
from app.models.producto import Producto
from app.models.venta import Venta
from tests.conftest import obtener_token, pagos_en_efectivo
from tests.test_hu01_venta import _crear_producto

D = Decimal


def _auth(client, usuario) -> dict[str, str]:
    """Devuelve el header Authorization para el usuario dado."""
    return {"Authorization": f"Bearer {obtener_token(client, usuario.username)}"}


def _cuerpo(producto_id: int, total: str, *, cantidad: int = 1, uuid_cliente=None, sin_conexion=None, **extra) -> dict:
    """Arma el payload de una venta de una linea pagada en efectivo."""
    cuerpo = {
        "detalles": [{"producto_id": producto_id, "cantidad": cantidad}],
        "pagos": pagos_en_efectivo(total),
        **extra,
    }
    if uuid_cliente is not None:
        cuerpo["uuid_cliente"] = str(uuid_cliente)
    if sin_conexion is not None:
        cuerpo["sin_conexion"] = {"fecha": sin_conexion.isoformat()}
    return cuerpo


def _hace(horas: float) -> datetime:
    """Momento de hace `horas` horas, con zona horaria."""
    return datetime.now(timezone.utc) - timedelta(hours=horas)


class TestEnvioIdempotente:
    """Reenviar la misma venta (mismo `uuid_cliente`) no la duplica ni vuelve a descontar stock."""

    def test_el_reenvio_devuelve_la_misma_venta_con_200_y_el_stock_baja_una_vez(
        self, client, db_session: Session, categoria_prueba, usuario_vendedor
    ):
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "10000.00", 5)
        identificador = uuid.uuid4()
        headers = _auth(client, usuario_vendedor)

        primera = client.post("/ventas", json=_cuerpo(producto.id, "20000", cantidad=2, uuid_cliente=identificador), headers=headers)
        segunda = client.post("/ventas", json=_cuerpo(producto.id, "20000", cantidad=2, uuid_cliente=identificador), headers=headers)

        assert primera.status_code == 201, primera.text
        assert segunda.status_code == 200, segunda.text
        assert segunda.json()["id"] == primera.json()["id"]
        assert db_session.query(Venta).filter(Venta.uuid_cliente == identificador).count() == 1
        db_session.refresh(producto)
        assert producto.stock_actual == 3

    def test_el_reenvio_no_vuelve_a_validar_nada(self, client, db_session: Session, categoria_prueba, usuario_vendedor):
        """Aunque ya no alcance el stock, el reenvio de una venta ya registrada responde 200."""
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "10000.00", 1)
        identificador = uuid.uuid4()
        headers = _auth(client, usuario_vendedor)

        assert client.post("/ventas", json=_cuerpo(producto.id, "10000", uuid_cliente=identificador), headers=headers).status_code == 201
        segunda = client.post("/ventas", json=_cuerpo(producto.id, "10000", uuid_cliente=identificador), headers=headers)

        assert segunda.status_code == 200

    def test_dos_ventas_con_distinto_uuid_son_dos_ventas(self, client, db_session: Session, categoria_prueba, usuario_vendedor):
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "10000.00", 5)
        headers = _auth(client, usuario_vendedor)

        a = client.post("/ventas", json=_cuerpo(producto.id, "10000", uuid_cliente=uuid.uuid4()), headers=headers)
        b = client.post("/ventas", json=_cuerpo(producto.id, "10000", uuid_cliente=uuid.uuid4()), headers=headers)

        assert a.status_code == b.status_code == 201
        assert a.json()["id"] != b.json()["id"]

    def test_sin_uuid_todo_sigue_igual(self, client, db_session: Session, categoria_prueba, usuario_vendedor):
        """Quien no envia `uuid_cliente` (por ejemplo, un cliente viejo) vende como siempre."""
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "10000.00", 5)
        headers = _auth(client, usuario_vendedor)

        a = client.post("/ventas", json=_cuerpo(producto.id, "10000"), headers=headers)
        b = client.post("/ventas", json=_cuerpo(producto.id, "10000"), headers=headers)

        assert a.status_code == b.status_code == 201
        venta = db_session.get(Venta, a.json()["id"])
        assert venta.uuid_cliente is None and venta.sin_conexion is False and venta.sincronizada_en is None

    def test_un_uuid_mal_formado_se_rechaza(self, client, db_session: Session, categoria_prueba, usuario_vendedor):
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "10000.00", 5)
        cuerpo = _cuerpo(producto.id, "10000")
        cuerpo["uuid_cliente"] = "no-es-un-uuid"

        respuesta = client.post("/ventas", json=cuerpo, headers=_auth(client, usuario_vendedor))

        assert respuesta.status_code == 422


class TestVentaHechaSinConexion:
    """Una venta enviada con `sin_conexion` conserva su hora y lo que vio el cliente."""

    def test_se_guarda_con_la_hora_de_la_tienda_y_marcada(self, client, db_session: Session, categoria_prueba, usuario_vendedor):
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "10000.00", 5)
        hora = _hace(2)

        respuesta = client.post(
            "/ventas",
            json=_cuerpo(producto.id, "10000", uuid_cliente=uuid.uuid4(), sin_conexion=hora),
            headers=_auth(client, usuario_vendedor),
        )

        assert respuesta.status_code == 201, respuesta.text
        cuerpo = respuesta.json()
        assert cuerpo["sin_conexion"] is True
        assert datetime.fromisoformat(cuerpo["fecha"]) == hora
        venta = db_session.get(Venta, cuerpo["id"])
        assert venta.sin_conexion is True
        assert venta.sincronizada_en is not None and venta.sincronizada_en > venta.fecha

    def test_exige_el_uuid(self, client, db_session: Session, categoria_prueba, usuario_vendedor):
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "10000.00", 5)

        respuesta = client.post(
            "/ventas",
            json=_cuerpo(producto.id, "10000", sin_conexion=_hace(1)),
            headers=_auth(client, usuario_vendedor),
        )

        assert respuesta.status_code == 422

    def test_rechaza_una_fecha_en_el_futuro(self, client, db_session: Session, categoria_prueba, usuario_vendedor):
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "10000.00", 5)

        respuesta = client.post(
            "/ventas",
            json=_cuerpo(producto.id, "10000", uuid_cliente=uuid.uuid4(), sin_conexion=_hace(-1)),
            headers=_auth(client, usuario_vendedor),
        )

        assert respuesta.status_code == 422
        assert "futuro" in respuesta.json()["detail"]
        db_session.refresh(producto)
        assert producto.stock_actual == 5

    def test_tolera_unos_minutos_de_reloj_adelantado(self, client, db_session: Session, categoria_prueba, usuario_vendedor):
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "10000.00", 5)

        respuesta = client.post(
            "/ventas",
            json=_cuerpo(producto.id, "10000", uuid_cliente=uuid.uuid4(), sin_conexion=_hace(-0.03)),
            headers=_auth(client, usuario_vendedor),
        )

        assert respuesta.status_code == 201, respuesta.text

    def test_rechaza_una_venta_demasiado_antigua(self, client, db_session: Session, categoria_prueba, usuario_vendedor):
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "10000.00", 5)

        respuesta = client.post(
            "/ventas",
            json=_cuerpo(producto.id, "10000", uuid_cliente=uuid.uuid4(), sin_conexion=_hace(24 * 8)),
            headers=_auth(client, usuario_vendedor),
        )

        assert respuesta.status_code == 422
        assert "administrador" in respuesta.json()["detail"]

    def test_rechaza_una_fecha_sin_zona_horaria(self, client, db_session: Session, categoria_prueba, usuario_vendedor):
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "10000.00", 5)
        cuerpo = _cuerpo(producto.id, "10000", uuid_cliente=uuid.uuid4())
        cuerpo["sin_conexion"] = {"fecha": "2026-10-13T20:00:00"}

        respuesta = client.post("/ventas", json=cuerpo, headers=_auth(client, usuario_vendedor))

        assert respuesta.status_code == 422

    def test_respeta_el_precio_que_vio_el_cliente(self, client, db_session: Session, categoria_prueba, usuario_vendedor):
        """El precio del catalogo subio mientras no habia conexion: se cobra lo que se le dijo al cliente."""
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "12000.00", 5)
        cuerpo = _cuerpo(producto.id, "20000", cantidad=2, uuid_cliente=uuid.uuid4(), sin_conexion=_hace(1))
        cuerpo["detalles"][0]["precio_unitario"] = "10000"

        respuesta = client.post("/ventas", json=cuerpo, headers=_auth(client, usuario_vendedor))

        assert respuesta.status_code == 201, respuesta.text
        assert D(respuesta.json()["total"]) == D("20000")
        linea = db_session.query(DetalleVenta).filter(DetalleVenta.venta_id == respuesta.json()["id"]).one()
        assert linea.precio_unitario == D("10000.00")
        assert linea.subtotal == D("20000.00")

    def test_el_precio_propio_no_se_acepta_en_una_venta_normal(self, client, db_session: Session, categoria_prueba, usuario_vendedor):
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "12000.00", 5)
        cuerpo = _cuerpo(producto.id, "1000")
        cuerpo["detalles"][0]["precio_unitario"] = "1000"

        respuesta = client.post("/ventas", json=cuerpo, headers=_auth(client, usuario_vendedor))

        assert respuesta.status_code == 422
        db_session.refresh(producto)
        assert producto.stock_actual == 5

    def test_sin_precio_propio_usa_el_vigente(self, client, db_session: Session, categoria_prueba, usuario_vendedor):
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "12000.00", 5)

        respuesta = client.post(
            "/ventas",
            json=_cuerpo(producto.id, "12000", uuid_cliente=uuid.uuid4(), sin_conexion=_hace(1)),
            headers=_auth(client, usuario_vendedor),
        )

        assert respuesta.status_code == 201, respuesta.text

    def test_la_venta_cae_en_el_dia_en_que_se_hizo(self, client, db_session: Session, categoria_prueba, usuario_vendedor):
        """El historial de hoy no cuenta una venta que se hizo ayer y se envio hoy."""
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "10000.00", 5)
        headers = _auth(client, usuario_vendedor)

        ayer = client.post("/ventas", json=_cuerpo(producto.id, "10000", uuid_cliente=uuid.uuid4(), sin_conexion=_hace(30)), headers=headers)
        hoy = client.post("/ventas", json=_cuerpo(producto.id, "10000", uuid_cliente=uuid.uuid4(), sin_conexion=_hace(0.1)), headers=headers)

        assert ayer.status_code == hoy.status_code == 201
        historial = client.get("/ventas/hoy", headers=headers).json()
        ids = [venta["id"] for venta in historial["ventas"]]
        assert hoy.json()["id"] in ids
        assert ayer.json()["id"] not in ids

    def test_el_historial_marca_las_ventas_sin_conexion(self, client, db_session: Session, categoria_prueba, usuario_vendedor):
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "10000.00", 5)
        headers = _auth(client, usuario_vendedor)
        offline = client.post("/ventas", json=_cuerpo(producto.id, "10000", uuid_cliente=uuid.uuid4(), sin_conexion=_hace(0.1)), headers=headers)
        normal = client.post("/ventas", json=_cuerpo(producto.id, "10000"), headers=headers)

        ventas = {v["id"]: v for v in client.get("/ventas/hoy", headers=headers).json()["ventas"]}

        assert ventas[offline.json()["id"]]["sin_conexion"] is True
        assert ventas[normal.json()["id"]]["sin_conexion"] is False

    def test_queda_a_nombre_del_vendedor_elegido(self, client, db_session: Session, categoria_prueba, usuario_vendedor, usuario_administrador):
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "10000.00", 5)
        cuerpo = _cuerpo(producto.id, "10000", uuid_cliente=uuid.uuid4(), sin_conexion=_hace(1), vendedor_id=usuario_vendedor.id)

        respuesta = client.post("/ventas", json=cuerpo, headers=_auth(client, usuario_administrador))

        assert respuesta.status_code == 201, respuesta.text
        venta = db_session.get(Venta, respuesta.json()["id"])
        assert venta.usuario_id == usuario_vendedor.id
        assert venta.registrada_por_id == usuario_administrador.id


class TestReglasDeNegocioSiguenIgual:
    """Una venta hecha sin conexion no se salta el stock, los pagos ni los topes."""

    def test_sin_stock_responde_409_y_no_guarda_nada(self, client, db_session: Session, categoria_prueba, usuario_vendedor):
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "10000.00", 1)
        identificador = uuid.uuid4()

        respuesta = client.post(
            "/ventas",
            json=_cuerpo(producto.id, "20000", cantidad=2, uuid_cliente=identificador, sin_conexion=_hace(1)),
            headers=_auth(client, usuario_vendedor),
        )

        assert respuesta.status_code == 409
        assert db_session.query(Venta).filter(Venta.uuid_cliente == identificador).count() == 0
        db_session.refresh(producto)
        assert producto.stock_actual == 1

    def test_tras_reponer_el_stock_el_reintento_funciona(self, client, db_session: Session, categoria_prueba, usuario_vendedor):
        """Es el camino del conflicto: el administrador repone el stock y el vendedor reintenta la misma venta."""
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "10000.00", 0)
        cuerpo = _cuerpo(producto.id, "10000", uuid_cliente=uuid.uuid4(), sin_conexion=_hace(1))
        headers = _auth(client, usuario_vendedor)
        assert client.post("/ventas", json=cuerpo, headers=headers).status_code == 409

        producto.stock_actual = 3
        db_session.commit()
        reintento = client.post("/ventas", json=cuerpo, headers=headers)

        assert reintento.status_code == 201, reintento.text
        db_session.refresh(producto)
        assert producto.stock_actual == 2

    def test_los_pagos_deben_sumar_el_total(self, client, db_session: Session, categoria_prueba, usuario_vendedor):
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "10000.00", 5)
        cuerpo = _cuerpo(producto.id, "5000", uuid_cliente=uuid.uuid4(), sin_conexion=_hace(1))

        respuesta = client.post("/ventas", json=cuerpo, headers=_auth(client, usuario_vendedor))

        assert respuesta.status_code == 422

    def test_los_topes_siguen_aplicando_al_descuento_manual_del_vendedor(
        self, client, db_session: Session, categoria_prueba, usuario_vendedor
    ):
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "10000.00", 5)
        db_session.merge(TopeDescuento(id=1, tope_porcentaje=D("10"), tope_monto=None))
        db_session.commit()
        cuerpo = _cuerpo(
            producto.id, "7000", uuid_cliente=uuid.uuid4(), sin_conexion=_hace(1),
            descuento={"origen": "manual", "tipo": "porcentaje", "valor": "30"},
        )

        respuesta = client.post("/ventas", json=cuerpo, headers=_auth(client, usuario_vendedor))

        assert respuesta.status_code == 422

    def test_el_propietario_no_puede_enviar_ventas(self, client, db_session: Session, categoria_prueba, usuario_propietario):
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "10000.00", 5)

        respuesta = client.post(
            "/ventas",
            json=_cuerpo(producto.id, "10000", uuid_cliente=uuid.uuid4(), sin_conexion=_hace(1)),
            headers=_auth(client, usuario_propietario),
        )

        assert respuesta.status_code == 403


class TestDescuentoGeneralSinConexion:
    """El descuento general se respeta tal como lo vio el cliente, aunque haya cambiado o se haya apagado."""

    def test_se_respeta_aunque_el_general_ya_no_este_activo(self, client, db_session: Session, categoria_prueba, usuario_vendedor):
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "10000.00", 5)
        db_session.merge(DescuentoGeneral(id=1, tipo=TipoDescuento.PORCENTAJE, valor=D("5"), activo=False))
        db_session.commit()
        cuerpo = _cuerpo(
            producto.id, "9000", uuid_cliente=uuid.uuid4(), sin_conexion=_hace(1),
            descuento={"origen": "general", "tipo": "porcentaje", "valor": "10"},
        )

        respuesta = client.post("/ventas", json=cuerpo, headers=_auth(client, usuario_vendedor))

        assert respuesta.status_code == 201, respuesta.text
        venta = respuesta.json()
        assert venta["descuento_origen"] == "general"
        assert D(venta["descuento_monto"]) == D("1000")
        assert D(venta["total"]) == D("9000")

    def test_sin_tipo_ni_valor_se_rechaza(self, client, db_session: Session, categoria_prueba, usuario_vendedor):
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "10000.00", 5)
        cuerpo = _cuerpo(
            producto.id, "9000", uuid_cliente=uuid.uuid4(), sin_conexion=_hace(1), descuento={"origen": "general"}
        )

        respuesta = client.post("/ventas", json=cuerpo, headers=_auth(client, usuario_vendedor))

        assert respuesta.status_code == 422

    def test_una_venta_normal_sigue_usando_la_configuracion_vigente(self, client, db_session: Session, categoria_prueba, usuario_vendedor):
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "10000.00", 5)
        db_session.merge(DescuentoGeneral(id=1, tipo=TipoDescuento.PORCENTAJE, valor=D("5"), activo=False))
        db_session.commit()
        cuerpo = _cuerpo(producto.id, "9000", descuento={"origen": "general", "tipo": "porcentaje", "valor": "10"})

        respuesta = client.post("/ventas", json=cuerpo, headers=_auth(client, usuario_vendedor))

        assert respuesta.status_code == 409


class TestEnviosSimultaneos:
    """Dos envios de la misma venta a la vez: el indice unico deja pasar uno solo."""

    def test_el_que_pierde_la_carrera_recibe_la_venta_ya_registrada(
        self, client, db_session: Session, categoria_prueba, usuario_vendedor, monkeypatch
    ):
        from app.routers import ventas as router_ventas

        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "10000.00", 5)
        identificador = uuid.uuid4()
        headers = _auth(client, usuario_vendedor)
        primera = client.post("/ventas", json=_cuerpo(producto.id, "10000", uuid_cliente=identificador), headers=headers)
        assert primera.status_code == 201

        # La segunda peticion no ve la venta de la primera al comprobar (aun no estaba confirmada)
        # y choca contra el indice unico al confirmar.
        real = router_ventas._buscar_por_uuid
        llamadas = []

        def buscar_con_retraso(db, uuid_cliente):
            llamadas.append(uuid_cliente)
            return None if len(llamadas) == 1 else real(db, uuid_cliente)

        monkeypatch.setattr(router_ventas, "_buscar_por_uuid", buscar_con_retraso)

        segunda = client.post("/ventas", json=_cuerpo(producto.id, "10000", uuid_cliente=identificador), headers=headers)

        assert segunda.status_code == 200, segunda.text
        assert segunda.json()["id"] == primera.json()["id"]
        db_session.refresh(producto)
        assert producto.stock_actual == 4
