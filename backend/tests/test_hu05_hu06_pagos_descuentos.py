"""Pruebas de aceptacion de HU-05 (pagos mixtos y vueltas) y HU-06 (descuentos) — Adendo v2, Fase A1.

Cada clase cita, en su docstring, el criterio de `docs/02-historias-de-usuario.md`
(secciones 3.5 y 3.6) que cubre. El descuento propio del cliente (Fase A2) se prueba
en `test_hu07_hu08_clientes_vendedor.py`; aqui, el general y el manual. La migracion 0002 se
ensaya aparte sobre una base con datos (ver `docs/06`).
"""

import time
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.descuento import DescuentoGeneral, TipoDescuento, TopeDescuento
from app.models.detalle_venta import DetalleVenta
from app.models.venta import MetodoPago
from app.services.calculo_venta import (
    calcular_monto_descuento,
    calcular_totales,
    describir_topes,
    prorratear_descuento,
    validar_pagos,
    validar_topes,
)
from tests.conftest import obtener_token, pagos_en_efectivo
from tests.test_hu01_venta import _crear_producto

D = Decimal


def _auth(client: TestClient, usuario) -> dict[str, str]:
    """Devuelve el header Authorization para el usuario dado."""
    return {"Authorization": f"Bearer {obtener_token(client, usuario.username)}"}


def _configurar(db_session: Session, general=None, topes=None) -> None:
    """Deja configurados el descuento general (tipo, valor, activo) y los topes (porcentaje, monto)."""
    if general is not None:
        tipo, valor, activo = general
        db_session.merge(DescuentoGeneral(id=1, tipo=tipo, valor=D(valor), activo=activo))
    if topes is not None:
        porcentaje, monto = topes
        db_session.merge(
            TopeDescuento(
                id=1,
                tope_porcentaje=D(porcentaje) if porcentaje is not None else None,
                tope_monto=D(monto) if monto is not None else None,
            )
        )
    db_session.commit()


def _vender(client, headers, producto_id, cantidad=1, pagos=None, descuento=None):
    """Hace `POST /ventas` con una sola linea."""
    cuerpo = {"detalles": [{"producto_id": producto_id, "cantidad": cantidad}], "pagos": pagos or []}
    if descuento is not None:
        cuerpo["descuento"] = descuento
    return client.post("/ventas", json=cuerpo, headers=headers)


# ---------------------------------------------------------------------------
# Calculo (funciones puras)
# ---------------------------------------------------------------------------


class TestOrdenDeCalculo:
    """HU-06: "el descuento se calcule sobre el subtotal de la venta, que el total se redondee a
    multiplo de $50 despues de descontar, que un porcentaje no supere 100 y que el descuento no
    pueda ser mayor al subtotal"."""

    def test_descuento_sobre_el_subtotal_y_redondeo_despues(self):
        totales = calcular_totales(D("3060"), calcular_monto_descuento(D("3060"), TipoDescuento.PORCENTAJE, D("10")))
        # 3060 - 306 = 2754 -> 2750: el ajuste (-4) se calcula despues de descontar.
        assert (totales.subtotal, totales.descuento_monto, totales.ajuste_redondeo, totales.total) == (
            D("3060.00"), D("306.00"), D("-4.00"), D("2750.00")
        )

    def test_porcentaje_con_centavos_redondea_al_centavo(self):
        assert calcular_monto_descuento(D("1025"), TipoDescuento.PORCENTAJE, D("7.5")) == D("76.88")

    def test_porcentaje_mayor_a_100_falla(self):
        with pytest.raises(ValueError, match="100"):
            calcular_monto_descuento(D("1000"), TipoDescuento.PORCENTAJE, D("101"))

    def test_monto_mayor_al_subtotal_falla(self):
        with pytest.raises(ValueError, match="no puede ser mayor que el subtotal"):
            calcular_monto_descuento(D("1000"), TipoDescuento.MONTO, D("1500"))

    def test_monto_con_centavos_falla(self):
        with pytest.raises(ValueError, match="entero"):
            calcular_monto_descuento(D("1000"), TipoDescuento.MONTO, D("100.50"))


class TestProrrateo:
    """docs/03, 7.8: el descuento se reparte entre las lineas en proporcion a su subtotal."""

    def test_ejemplo_del_documento(self):
        assert prorratear_descuento([D("60000"), D("40000")], D("10000")) == [D("6000.00"), D("4000.00")]

    def test_los_centavos_sobrantes_van_a_la_ultima_linea_y_la_suma_es_exacta(self):
        partes = prorratear_descuento([D("1000"), D("1000"), D("1000")], D("100"))
        assert partes == [D("33.33"), D("33.33"), D("33.34")]
        assert sum(partes) == D("100")

    def test_una_linea_gratis_no_recibe_descuento(self):
        assert prorratear_descuento([D("5000"), D("0")], D("500")) == [D("500.00"), D("0.00")]

    def test_sin_descuento_todo_en_cero(self):
        assert prorratear_descuento([D("5000"), D("1000")], D("0")) == [D("0.00"), D("0.00")]


class TestTopes:
    """HU-06: "el vendedor no pueda aplicar un descuento que supere cualquiera de los dos y que el
    sistema le indique el limite vigente"."""

    def test_dentro_de_ambos_topes(self):
        validar_topes(D("100000"), D("5000"), D("10"), D("5000"))

    def test_supera_el_porcentaje(self):
        with pytest.raises(ValueError, match=r"hasta 10 % del subtotal y hasta \$20\.000"):
            validar_topes(D("10000"), D("1500"), D("10"), D("20000"))

    def test_supera_el_monto_aunque_el_porcentaje_cumpla(self):
        with pytest.raises(ValueError, match="límite"):
            validar_topes(D("100000"), D("6000"), D("10"), D("5000"))

    def test_sin_topes_no_limita(self):
        validar_topes(D("1000"), D("1000"), None, None)
        assert describir_topes(None, None) == "sin límite"


class TestValidacionDePagos:
    """HU-05: suma de pagos = total (mostrando cuanto falta o sobra), plataforma obligatoria en
    transferencia, monto recibido >= monto en efectivo y vueltas = recibido - monto."""

    def test_pagos_mixtos_con_vueltas(self):
        pagos = validar_pagos(
            [
                (MetodoPago.EFECTIVO, None, D("20000"), D("50000")),
                (MetodoPago.TRANSFERENCIA, "nequi", D("6000"), None),
            ],
            D("26000"),
        )
        assert [(p.metodo_pago, p.monto, p.vueltas) for p in pagos] == [
            (MetodoPago.EFECTIVO, D("20000.00"), D("30000.00")),
            (MetodoPago.TRANSFERENCIA, D("6000.00"), D("0.00")),
        ]

    @pytest.mark.parametrize(
        "pagos, mensaje",
        [
            ([(MetodoPago.TARJETA, None, D("20000"), None)], r"faltan \$6\.000"),
            ([(MetodoPago.TARJETA, None, D("30000"), None)], r"sobran \$4\.000"),
            ([(MetodoPago.TRANSFERENCIA, None, D("26000"), None)], "Nequi o Daviplata"),
            ([(MetodoPago.EFECTIVO, None, D("26000"), D("20000"))], "no puede ser menor"),
            ([(MetodoPago.EFECTIVO, None, D("26000"), None)], "monto recibido"),
            ([(MetodoPago.EFECTIVO, None, D("25990"), D("30000")), (MetodoPago.TARJETA, None, D("10"), None)], "múltiplo de \\$50"),
            ([(MetodoPago.TARJETA, None, D("26000"), D("26000"))], "solo aplica a pagos en efectivo"),
            ([(MetodoPago.TARJETA, "nequi", D("26000"), None)], "solo aplica a pagos por transferencia"),
            ([(MetodoPago.TARJETA, None, D("25999.50"), None)], "entero"),
            ([], "al menos un pago"),
        ],
    )
    def test_pagos_invalidos(self, pagos, mensaje):
        with pytest.raises(ValueError, match=mensaje):
            validar_pagos(pagos, D("26000"))

    def test_venta_en_cero_no_lleva_pagos(self):
        assert validar_pagos([], D("0")) == []
        with pytest.raises(ValueError, match=r"\$0"):
            validar_pagos([(MetodoPago.TARJETA, None, D("100"), None)], D("0"))

    def test_tarjeta_admite_montos_que_no_son_multiplo_de_50(self):
        pagos = validar_pagos(
            [(MetodoPago.EFECTIVO, None, D("20000"), D("20000")), (MetodoPago.TARJETA, None, D("6000"), None)],
            D("26000"),
        )
        assert len(pagos) == 2
        pagos = validar_pagos([(MetodoPago.TARJETA, None, D("3030"), None), (MetodoPago.TRANSFERENCIA, "nequi", D("20"), None)], D("3050"))
        assert sum(p.monto for p in pagos) == D("3050")


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


class TestVentaConPagosMixtos:
    """HU-05: varios pagos en una venta; no se confirma si la suma es distinta del total."""

    def test_efectivo_y_nequi_con_vueltas(self, client, db_session, categoria_prueba, usuario_vendedor):
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata Mickey", "26000.00", 5)

        respuesta = _vender(
            client,
            _auth(client, usuario_vendedor),
            producto.id,
            pagos=[
                {"metodo_pago": "efectivo", "monto": "20000", "monto_recibido": "50000"},
                {"metodo_pago": "transferencia", "plataforma": "nequi", "monto": "6000"},
            ],
        )

        assert respuesta.status_code == 201, respuesta.text
        cuerpo = respuesta.json()
        assert D(cuerpo["total"]) == D("26000")
        assert [(p["metodo_pago"], p["plataforma"], D(p["monto"]), p["monto_recibido"] and D(p["monto_recibido"]), D(p["vueltas"])) for p in cuerpo["pagos"]] == [
            ("efectivo", None, D("20000"), D("50000"), D("30000")),
            ("transferencia", "nequi", D("6000"), None, D("0")),
        ]
        assert cuerpo["descuento_origen"] == "ninguno"

    def test_suma_distinta_del_total_no_confirma_ni_descuenta_stock(
        self, client, db_session, categoria_prueba, usuario_vendedor
    ):
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata Mickey", "26000.00", 5)

        respuesta = _vender(
            client,
            _auth(client, usuario_vendedor),
            producto.id,
            pagos=[{"metodo_pago": "tarjeta", "monto": "20000"}],
        )

        assert respuesta.status_code == 422
        assert "faltan $6.000" in respuesta.json()["detail"]
        db_session.refresh(producto)
        assert producto.stock_actual == 5

    def test_transferencia_sin_plataforma_es_422(self, client, db_session, categoria_prueba, usuario_vendedor):
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "5000.00", 5)

        respuesta = _vender(
            client, _auth(client, usuario_vendedor), producto.id, pagos=[{"metodo_pago": "transferencia", "monto": "5000"}]
        )

        assert respuesta.status_code == 422
        assert "Nequi o Daviplata" in respuesta.json()["detail"]

    def test_responde_en_menos_de_2_segundos(self, client, db_session, categoria_prueba, usuario_vendedor):
        """HU-05: "la venta con pagos mixtos siga confirmandose en menos de 2 segundos" (latencia local)."""
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "5000.00", 5)
        headers = _auth(client, usuario_vendedor)

        inicio = time.perf_counter()
        respuesta = _vender(
            client,
            headers,
            producto.id,
            pagos=[
                {"metodo_pago": "efectivo", "monto": "2000", "monto_recibido": "5000"},
                {"metodo_pago": "transferencia", "plataforma": "daviplata", "monto": "3000"},
            ],
        )
        assert respuesta.status_code == 201
        assert time.perf_counter() - inicio < 2.0


class TestDescuentoGeneralYManual:
    """HU-06: el general es opcional (el vendedor lo aplica a quien corresponda, decision del
    08-10-2026); el manual respeta los topes del vendedor; los topes no limitan al administrador
    ni al descuento general."""

    def test_con_el_general_activo_se_puede_vender_sin_descuento(
        self, client, db_session, categoria_prueba, usuario_vendedor
    ):
        _configurar(db_session, general=(TipoDescuento.PORCENTAJE, "10", True))
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "5000.00", 5)

        respuesta = _vender(client, _auth(client, usuario_vendedor), producto.id, pagos=pagos_en_efectivo("5000"))

        assert respuesta.status_code == 201, respuesta.text
        assert (respuesta.json()["descuento_origen"], D(respuesta.json()["total"])) == ("ninguno", D("5000"))

    def test_aplica_el_general(self, client, db_session, categoria_prueba, usuario_vendedor):
        _configurar(db_session, general=(TipoDescuento.PORCENTAJE, "10", True))
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata", "30600.00", 5)

        respuesta = _vender(
            client, _auth(client, usuario_vendedor), producto.id,
            pagos=pagos_en_efectivo("27550"), descuento={"origen": "general"},
        )

        assert respuesta.status_code == 201, respuesta.text
        cuerpo = respuesta.json()
        assert (cuerpo["descuento_origen"], cuerpo["descuento_tipo"]) == ("general", "porcentaje")
        assert (D(cuerpo["subtotal"]), D(cuerpo["descuento_monto"]), D(cuerpo["ajuste_redondeo"]), D(cuerpo["total"])) == (
            D("30600"), D("3060"), D("10"), D("27550")
        )
        assert D(cuerpo["detalles"][0]["descuento_prorrateado"]) == D("3060")

    def test_el_general_no_lo_limitan_los_topes(self, client, db_session, categoria_prueba, usuario_vendedor):
        _configurar(db_session, general=(TipoDescuento.MONTO, "5000", True), topes=("5", "1000"))
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata", "20000.00", 5)

        respuesta = _vender(
            client, _auth(client, usuario_vendedor), producto.id,
            pagos=pagos_en_efectivo("15000"), descuento={"origen": "general"},
        )

        assert respuesta.status_code == 201, respuesta.text

    def test_general_en_pesos_mayor_al_subtotal_se_limita_al_subtotal(
        self, client, db_session, categoria_prueba, usuario_vendedor
    ):
        _configurar(db_session, general=(TipoDescuento.MONTO, "5000", True))
        producto = _crear_producto(db_session, categoria_prueba.id, "Bolsa", "3000.00", 5)

        respuesta = _vender(client, _auth(client, usuario_vendedor), producto.id, descuento={"origen": "general"})

        assert respuesta.status_code == 201, respuesta.text
        assert D(respuesta.json()["total"]) == 0
        assert respuesta.json()["pagos"] == []

    def test_si_se_pide_el_general_y_ya_no_esta_activo_responde_409(
        self, client, db_session, categoria_prueba, usuario_vendedor
    ):
        _configurar(db_session, general=(TipoDescuento.PORCENTAJE, "10", False))
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "5000.00", 5)

        respuesta = _vender(
            client, _auth(client, usuario_vendedor), producto.id,
            pagos=pagos_en_efectivo("5000"), descuento={"origen": "general"},
        )

        assert respuesta.status_code == 409
        assert "descuento general cambió" in respuesta.json()["detail"]

    def test_quitar_el_descuento_queda_como_manual_en_cero(
        self, client, db_session, categoria_prueba, usuario_vendedor
    ):
        _configurar(db_session, general=(TipoDescuento.PORCENTAJE, "10", True))
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "5000.00", 5)

        respuesta = _vender(
            client, _auth(client, usuario_vendedor), producto.id,
            pagos=pagos_en_efectivo("5000"), descuento={"origen": "manual"},
        )

        assert respuesta.status_code == 201, respuesta.text
        cuerpo = respuesta.json()
        assert (cuerpo["descuento_origen"], cuerpo["descuento_tipo"], D(cuerpo["descuento_monto"])) == ("manual", None, 0)

    def test_manual_del_vendedor_dentro_del_tope(self, client, db_session, categoria_prueba, usuario_vendedor):
        _configurar(db_session, topes=("10", "5000"))
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata", "20000.00", 5)

        respuesta = _vender(
            client, _auth(client, usuario_vendedor), producto.id,
            pagos=pagos_en_efectivo("18000"), descuento={"origen": "manual", "tipo": "monto", "valor": "2000"},
        )

        assert respuesta.status_code == 201, respuesta.text
        assert (respuesta.json()["descuento_origen"], D(respuesta.json()["descuento_monto"])) == ("manual", D("2000"))

    def test_manual_del_vendedor_que_supera_el_tope_es_422_con_el_limite(
        self, client, db_session, categoria_prueba, usuario_vendedor
    ):
        _configurar(db_session, topes=("10", "5000"))
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata", "20000.00", 5)

        respuesta = _vender(
            client, _auth(client, usuario_vendedor), producto.id,
            pagos=pagos_en_efectivo("17000"), descuento={"origen": "manual", "tipo": "porcentaje", "valor": "15"},
        )

        assert respuesta.status_code == 422
        assert respuesta.json()["detail"] == (
            "El descuento supera el límite permitido: hasta 10 % del subtotal y hasta $5.000."
        )
        db_session.refresh(producto)
        assert producto.stock_actual == 5

    def test_los_topes_no_limitan_al_administrador(
        self, client, db_session, categoria_prueba, usuario_administrador
    ):
        _configurar(db_session, topes=("10", "5000"))
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata", "20000.00", 5)

        respuesta = _vender(
            client, _auth(client, usuario_administrador), producto.id,
            pagos=pagos_en_efectivo("10000"), descuento={"origen": "manual", "tipo": "porcentaje", "valor": "50"},
        )

        assert respuesta.status_code == 201, respuesta.text

    def test_descuento_del_100_por_ciento_deja_la_venta_en_cero_sin_pagos(
        self, client, db_session, categoria_prueba, usuario_administrador
    ):
        producto = _crear_producto(db_session, categoria_prueba.id, "Regalo", "8000.00", 5)

        respuesta = _vender(
            client, _auth(client, usuario_administrador), producto.id,
            descuento={"origen": "manual", "tipo": "porcentaje", "valor": "100"},
        )

        assert respuesta.status_code == 201, respuesta.text
        assert (D(respuesta.json()["total"]), respuesta.json()["pagos"]) == (D("0"), [])

    @pytest.mark.parametrize(
        "descuento, mensaje",
        [
            ({"origen": "manual", "tipo": "monto", "valor": "25000"}, "mayor que el subtotal"),
            ({"origen": "manual", "tipo": "porcentaje", "valor": "120"}, "100"),
            ({"origen": "manual", "tipo": "monto"}, "tipo y el valor"),
            ({"origen": "cliente"}, "cliente con descuento propio"),
        ],
    )
    def test_descuentos_invalidos_son_422(
        self, client, db_session, categoria_prueba, usuario_administrador, descuento, mensaje
    ):
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata", "20000.00", 5)

        respuesta = _vender(
            client, _auth(client, usuario_administrador), producto.id,
            pagos=pagos_en_efectivo("20000"), descuento=descuento,
        )

        assert respuesta.status_code == 422
        assert mensaje in respuesta.json()["detail"]

    def test_guarda_el_descuento_repartido_y_el_costo_de_cada_linea(
        self, client, db_session, categoria_prueba, usuario_administrador
    ):
        """HU-06: la venta guarda origen, tipo, valor y monto; docs/03 7.8: prorrateo; HU-09: costo copiado."""
        piñata = _crear_producto(db_session, categoria_prueba.id, "Piñata", "60000.00", 5)
        globo = _crear_producto(db_session, categoria_prueba.id, "Globo", "40000.00", 5)
        piñata.costo_unitario = D("35000")
        db_session.commit()

        respuesta = client.post(
            "/ventas",
            json={
                "detalles": [{"producto_id": piñata.id, "cantidad": 1}, {"producto_id": globo.id, "cantidad": 1}],
                "pagos": [{"metodo_pago": "tarjeta", "monto": "90000"}],
                "descuento": {"origen": "manual", "tipo": "monto", "valor": "10000"},
            },
            headers=_auth(client, usuario_administrador),
        )

        assert respuesta.status_code == 201, respuesta.text
        cuerpo = respuesta.json()
        assert (cuerpo["descuento_tipo"], D(cuerpo["descuento_valor"]), D(cuerpo["descuento_monto"])) == (
            "monto", D("10000"), D("10000")
        )
        assert [D(d["descuento_prorrateado"]) for d in cuerpo["detalles"]] == [D("6000"), D("4000")]
        assert "costo_unitario" not in cuerpo["detalles"][0]
        costos = [
            d.costo_unitario
            for d in db_session.query(DetalleVenta).filter(DetalleVenta.venta_id == cuerpo["id"]).order_by(DetalleVenta.id)
        ]
        assert costos == [D("35000.00"), None]


class TestConfiguracionDeDescuentos:
    """HU-06: "solo el administrador pueda configurar el descuento general ... y los topes; el
    vendedor que lo intente recibe 403"."""

    def test_vendedor_y_administrador_leen_la_configuracion(
        self, client, usuario_vendedor, usuario_administrador
    ):
        for usuario in (usuario_vendedor, usuario_administrador):
            respuesta = client.get("/descuentos/configuracion", headers=_auth(client, usuario))
            assert respuesta.status_code == 200
            assert respuesta.json() == {
                "general": None,
                "topes": {"tope_porcentaje": None, "tope_monto": None, "descripcion": "sin límite"},
            }

    def test_propietario_no_lee_y_sin_token_es_401(self, client, usuario_propietario):
        assert client.get("/descuentos/configuracion", headers=_auth(client, usuario_propietario)).status_code == 403
        assert client.get("/descuentos/configuracion").status_code == 401

    @pytest.mark.parametrize(
        "ruta, cuerpo",
        [
            ("/descuentos/general", {"tipo": "porcentaje", "valor": "5", "activo": True}),
            ("/descuentos/topes", {"tope_porcentaje": "10", "tope_monto": "5000"}),
        ],
    )
    def test_vendedor_no_modifica(self, client, usuario_vendedor, ruta, cuerpo):
        assert client.put(ruta, json=cuerpo, headers=_auth(client, usuario_vendedor)).status_code == 403

    def test_administrador_configura_general_y_topes(self, client, usuario_administrador):
        headers = _auth(client, usuario_administrador)

        general = client.put(
            "/descuentos/general", json={"tipo": "porcentaje", "valor": "5", "activo": True}, headers=headers
        )
        topes = client.put("/descuentos/topes", json={"tope_porcentaje": "10", "tope_monto": "5000"}, headers=headers)

        assert general.status_code == 200 and topes.status_code == 200
        cuerpo = topes.json()
        assert cuerpo["general"] == {"tipo": "porcentaje", "valor": "5.00", "activo": True}
        assert cuerpo["topes"]["descripcion"] == "hasta 10 % del subtotal y hasta $5.000"

        quitar = client.put("/descuentos/topes", json={"tope_porcentaje": None, "tope_monto": None}, headers=headers)
        assert quitar.json()["topes"]["descripcion"] == "sin límite"

    @pytest.mark.parametrize(
        "ruta, cuerpo",
        [
            ("/descuentos/general", {"tipo": "porcentaje", "valor": "150", "activo": True}),
            ("/descuentos/general", {"tipo": "monto", "valor": "0", "activo": True}),
            ("/descuentos/general", {"tipo": "monto", "valor": "100.50", "activo": True}),
            ("/descuentos/topes", {"tope_porcentaje": "0", "tope_monto": None}),
            ("/descuentos/topes", {"tope_porcentaje": "101", "tope_monto": None}),
        ],
    )
    def test_valores_invalidos_son_422(self, client, usuario_administrador, ruta, cuerpo):
        assert client.put(ruta, json=cuerpo, headers=_auth(client, usuario_administrador)).status_code == 422


class TestResumenesPorMontoDePagos:
    """HU-05: "el resumen del dia del Dashboard agrupe el total por metodo de pago usando el monto
    de cada pago (no el numero de ventas)" — RF-041; el historial del dia hace lo mismo."""

    def test_dashboard_e_historial_reparten_una_venta_mixta_por_metodo(
        self, client, db_session, categoria_prueba, usuario_vendedor, usuario_propietario
    ):
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata", "26000.00", 5)
        headers_vendedor = _auth(client, usuario_vendedor)
        _vender(
            client, headers_vendedor, producto.id,
            pagos=[
                {"metodo_pago": "efectivo", "monto": "20000", "monto_recibido": "20000"},
                {"metodo_pago": "transferencia", "plataforma": "daviplata", "monto": "6000"},
            ],
        )

        resumen = client.get("/dashboard/resumen", headers=_auth(client, usuario_propietario)).json()
        historial = client.get("/ventas/hoy", headers=headers_vendedor).json()

        for cuerpo in (resumen, historial):
            assert {k: D(v) for k, v in cuerpo["total_por_metodo"].items()} == {
                "efectivo": D("20000"), "transferencia": D("6000")
            }
            assert D(cuerpo["total_vendido"]) == D("26000")
        venta = historial["ventas"][0]
        assert [p["plataforma"] for p in venta["pagos"]] == [None, "daviplata"]
        assert (D(venta["subtotal"]), D(venta["descuento_monto"]), D(venta["ajuste_redondeo"])) == (D("26000"), 0, 0)
        assert (venta["descuento_origen"], venta["descuento_tipo"], venta["descuento_valor"]) == ("ninguno", None, None)
