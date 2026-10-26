"""Pruebas del agente de impresion: formato del ticket y endpoints (sin hardware)."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.impresoras import ErrorImpresion
from app.main import app, obtener_impresora
from app.schemas import TicketIn
from app.ticket import a_texto, construir_renglones, formatear_pesos

ANCHO = 48

TICKET_JSON = {
    "venta_id": 7,
    "fecha": "2026-09-25T20:30:00+00:00",
    "metodo_pago": "efectivo",
    "total": "68000.00",
    "lineas": [
        {"nombre_producto": "Piñata Mickey Mouse", "cantidad": 2, "precio_unitario": "25000.00", "subtotal": "50000.00"},
        {
            "nombre_producto": "Bolsa de dulces surtidos de un kilo con relleno especial",
            "cantidad": 1,
            "precio_unitario": "18000.00",
            "subtotal": "18000.00",
        },
    ],
}


def _renglones(ticket_json=TICKET_JSON, **overrides):
    argumentos = {
        "ancho": ANCHO,
        "nombre_negocio": "PIÑATERIA DEMO",
        "nit": "NIT: 900.000.000 - 0",
        "direccion": "CALLE 123 # 45-67 BARRIO DEMO",
        "telefono": "Tel: 3000000000",
        "pie": "¡Gracias!",
        "zona_horaria": "America/Bogota",
        **overrides,
    }
    return construir_renglones(TicketIn(**ticket_json), **argumentos)


class TestFormatoTicket:
    def test_formatea_pesos_colombianos_sin_decimales(self):
        assert formatear_pesos(Decimal("25000.00")) == "$25.000"
        assert formatear_pesos(Decimal("1250000")) == "$1.250.000"
        assert formatear_pesos(Decimal("999.50")) == "$1.000"

    def test_ninguna_linea_excede_el_ancho_del_papel(self):
        for linea in a_texto(_renglones(), ANCHO).splitlines():
            assert len(linea) <= ANCHO, linea

    def test_incluye_venta_fecha_en_hora_de_bogota_y_pago(self):
        texto = a_texto(_renglones(), ANCHO)
        assert "Venta #7" in texto
        assert "25/09/2026 15:30" in texto  # 20:30 UTC = 15:30 Bogota (UTC-5)
        assert "Pago: Efectivo" in texto

    def test_incluye_lineas_y_total(self):
        texto = a_texto(_renglones(), ANCHO)
        assert "Piñata Mickey Mouse" in texto
        assert "2 x $25.000" in texto
        assert "$50.000" in texto
        assert "TOTAL" in texto and "$68.000" in texto

    def test_nombres_largos_se_parten_en_varias_lineas(self):
        texto = a_texto(_renglones(), ANCHO)
        assert "Bolsa de dulces surtidos de un kilo con relleno\n" in texto
        assert "especial\n" in texto

    def test_encabezado_incluye_nombre_nit_y_direccion(self):
        texto = a_texto(_renglones(), ANCHO)
        assert "PIÑATERIA DEMO" in texto
        assert "NIT: 900.000.000 - 0" in texto
        assert "CALLE 123 # 45-67 BARRIO DEMO" in texto
        # En ese orden: nombre antes que NIT, NIT antes que direccion.
        assert texto.index("DEMO") < texto.index("NIT") < texto.index("CALLE 123")

    def test_nit_y_direccion_vacios_no_imprimen_linea(self):
        texto = a_texto(_renglones(nit="", direccion=""), ANCHO)
        assert "NIT" not in texto
        assert "CALLE 123" not in texto

    def test_encabezado_incluye_telefono_despues_de_la_direccion(self):
        texto = a_texto(_renglones(), ANCHO)
        assert "Tel: 3000000000" in texto
        assert texto.index("CALLE 123") < texto.index("Tel: 3000000000")

    def test_telefono_vacio_no_imprime_linea(self):
        assert "Tel:" not in a_texto(_renglones(telefono=""), ANCHO)


class _ImpresoraFalsa:
    def __init__(self, error: Exception | None = None):
        self.error = error
        self.recibidos = []

    def imprimir(self, venta_id, renglones):
        if self.error:
            raise self.error
        self.recibidos.append((venta_id, renglones))


@pytest.fixture
def cliente_con(request):
    """Cliente con una impresora falsa inyectada; devuelve (cliente, impresora)."""

    def _crear(impresora):
        app.dependency_overrides[obtener_impresora] = lambda: impresora
        app.dependency_overrides[get_settings] = lambda: Settings(modo="mock")
        return TestClient(app), impresora

    yield _crear
    app.dependency_overrides.clear()


class TestEndpoints:
    def test_salud(self, cliente_con):
        cliente, _ = cliente_con(_ImpresoraFalsa())
        respuesta = cliente.get("/salud")
        assert respuesta.status_code == 200
        assert respuesta.json() == {"status": "ok", "modo": "mock"}

    def test_imprimir_ok_envia_el_ticket_a_la_impresora(self, cliente_con):
        cliente, impresora = cliente_con(_ImpresoraFalsa())
        respuesta = cliente.post("/imprimir", json=TICKET_JSON)
        assert respuesta.status_code == 200
        assert respuesta.json() == {"status": "ok", "modo": "mock"}
        assert impresora.recibidos[0][0] == 7

    def test_impresora_caida_devuelve_503_con_mensaje_legible(self, cliente_con):
        cliente, _ = cliente_con(_ImpresoraFalsa(ErrorImpresion("Impresora sin papel")))
        respuesta = cliente.post("/imprimir", json=TICKET_JSON)
        assert respuesta.status_code == 503
        assert respuesta.json()["detail"] == "Impresora sin papel"

    def test_ticket_sin_lineas_es_rechazado(self, cliente_con):
        cliente, _ = cliente_con(_ImpresoraFalsa())
        respuesta = cliente.post("/imprimir", json={**TICKET_JSON, "lineas": []})
        assert respuesta.status_code == 422

    def test_cors_permite_al_frontend_de_desarrollo(self, cliente_con):
        cliente, _ = cliente_con(_ImpresoraFalsa())
        respuesta = cliente.options(
            "/imprimir",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
                "Access-Control-Request-Private-Network": "true",
            },
        )
        assert respuesta.status_code == 200
        assert respuesta.headers["access-control-allow-origin"] == "http://localhost:5173"
        assert respuesta.headers["access-control-allow-private-network"] == "true"


def test_modo_mock_escribe_el_ticket_en_un_archivo(tmp_path):
    from app.impresoras import ImpresoraMock

    ImpresoraMock(str(tmp_path), ANCHO).imprimir(7, _renglones())
    contenido = (tmp_path / "venta_7.txt").read_text(encoding="utf-8")
    assert "Venta #7" in contenido and "$68.000" in contenido


class _EscposFalso:
    """Simula la impresora ESC/POS de python-escpos y anota lo que recibe."""

    def __init__(self, falla_imagen: bool = False):
        self.llamadas = []
        self.falla_imagen = falla_imagen

    def set(self, **opciones):
        self.llamadas.append(("set", opciones.get("align")))

    def image(self, ruta, **opciones):
        if self.falla_imagen:
            raise RuntimeError("no se pudo convertir la imagen")
        self.llamadas.append(("image", ruta, opciones))

    def text(self, texto):
        self.llamadas.append(("text", texto))

    def ln(self, n=1):
        self.llamadas.append(("ln", n))

    def cut(self):
        self.llamadas.append(("cut",))

    def close(self):
        self.llamadas.append(("close",))


class TestLogoDelTicket:
    """Aceptacion 1.6: el ticket lleva el logo arriba; si el logo falla, el ticket sale igual."""

    def _impresora(self, monkeypatch, escpos, **ajustes):
        from app.impresoras import ImpresoraEscpos

        impresora = ImpresoraEscpos(Settings(modo="escpos", **ajustes))
        monkeypatch.setattr(impresora, "_abrir", lambda: escpos)
        return impresora

    def test_el_logo_viene_incluido_y_es_un_png_en_blanco_y_negro(self):
        from PIL import Image

        from app.impresoras import ruta_del_logo

        ruta = ruta_del_logo(Settings().logo_ticket)
        assert ruta is not None
        imagen = Image.open(ruta)
        assert imagen.mode == "1" and imagen.width <= 576  # 576 puntos = ancho util del papel de 80 mm

    def test_imprime_el_logo_antes_del_texto_y_corta(self, monkeypatch):
        escpos = _EscposFalso()

        self._impresora(monkeypatch, escpos).imprimir(7, _renglones())

        tipos = [llamada[0] for llamada in escpos.llamadas]
        assert tipos.index("image") < tipos.index("text")
        assert tipos[-2:] == ["cut", "close"]
        imagen = next(llamada for llamada in escpos.llamadas if llamada[0] == "image")
        assert imagen[1].endswith("logo-ticket.png") and imagen[2]["center"] is True

    def test_si_el_logo_falla_el_ticket_se_imprime_igual(self, monkeypatch):
        escpos = _EscposFalso(falla_imagen=True)

        self._impresora(monkeypatch, escpos).imprimir(7, _renglones())

        tipos = [llamada[0] for llamada in escpos.llamadas]
        assert "image" not in tipos and "text" in tipos and "cut" in tipos

    @pytest.mark.parametrize("valor", ["", "   ", "assets/no-existe.png"])
    def test_sin_logo_configurado_o_sin_archivo_no_intenta_imprimirlo(self, monkeypatch, valor):
        escpos = _EscposFalso()

        self._impresora(monkeypatch, escpos, logo_ticket=valor).imprimir(7, _renglones())

        assert "image" not in [llamada[0] for llamada in escpos.llamadas]
        assert "cut" in [llamada[0] for llamada in escpos.llamadas]

    def test_el_modo_mock_anota_el_logo(self, tmp_path):
        from app.impresoras import ImpresoraMock

        ImpresoraMock(str(tmp_path), ANCHO, "assets/logo-ticket.png").imprimir(7, _renglones())

        assert (tmp_path / "venta_7.txt").read_text(encoding="utf-8").startswith("[LOGO logo-ticket.png]")


class TestAjustePorRedondeo:
    """El ticket anota el redondeo a multiplo de 50 solo cuando la venta lo tuvo."""

    @staticmethod
    def _ticket(subtotales, total):
        return {
            **TICKET_JSON,
            "total": total,
            "lineas": [
                {"nombre_producto": f"Item {i}", "cantidad": 1, "precio_unitario": s, "subtotal": s}
                for i, s in enumerate(subtotales)
            ],
        }

    def test_sin_redondeo_no_imprime_ajuste_ni_subtotal(self):
        texto = a_texto(_renglones(), ANCHO)
        assert "redondeo" not in texto
        assert "Subtotal" not in texto

    def test_redondeo_hacia_abajo_se_anota_con_signo_negativo(self):
        texto = a_texto(_renglones(self._ticket(["1020.00"], "1000.00")), ANCHO)
        assert "Subtotal" in texto and "$1.020" in texto
        assert "Ajuste por redondeo" in texto and "-$20" in texto
        assert "TOTAL" in texto and "$1.000" in texto

    def test_redondeo_hacia_arriba_se_anota_con_signo_positivo(self):
        texto = a_texto(_renglones(self._ticket(["1030.00"], "1050.00")), ANCHO)
        assert "Ajuste por redondeo" in texto and "+$20" in texto

    def test_ajuste_va_antes_del_total_y_cabe_en_el_papel(self):
        texto = a_texto(_renglones(self._ticket(["1020.00"], "1000.00")), ANCHO)
        assert texto.index("Ajuste por redondeo") < texto.index("TOTAL")
        assert all(len(linea) <= ANCHO for linea in texto.splitlines())


TICKET_ADENDO_V2 = {
    "venta_id": 9,
    "fecha": "2026-10-08T20:30:00+00:00",
    "subtotal": "30600.00",
    "descuento_tipo": "porcentaje",
    "descuento_valor": "10.00",
    "descuento_monto": "3060.00",
    "ajuste_redondeo": "10.00",
    "total": "27550.00",
    "pagos": [
        {"metodo_pago": "efectivo", "monto": "20000.00", "monto_recibido": "50000.00", "vueltas": "30000.00"},
        {"metodo_pago": "transferencia", "plataforma": "nequi", "monto": "7550.00", "vueltas": "0"},
    ],
    "lineas": [{"nombre_producto": "Piñata", "cantidad": 1, "precio_unitario": "30600.00", "subtotal": "30600.00"}],
}


class TestTicketConPagosYDescuento:
    """Adendo v2, HU-05 y HU-06: "el ticket impreso liste cada pago con su metodo (y plataforma) y,
    en efectivo, el monto recibido y las vueltas"; y muestre subtotal, descuento y total."""

    def test_imprime_subtotal_descuento_ajuste_y_total_en_ese_orden(self):
        texto = a_texto(_renglones(TICKET_ADENDO_V2), ANCHO)
        posiciones = [texto.index(t) for t in ("Subtotal", "Descuento (10 %)", "Ajuste por redondeo", "TOTAL")]
        assert posiciones == sorted(posiciones)
        assert "-$3.060" in texto and "+$10" in texto and "$27.550" in texto

    def test_lista_cada_pago_con_plataforma_recibido_y_vueltas(self):
        texto = a_texto(_renglones(TICKET_ADENDO_V2), ANCHO)
        assert "Pago: Efectivo" in texto and "Recibido" in texto and "$50.000" in texto
        assert "Vueltas" in texto and "$30.000" in texto
        assert "Pago: Transferencia (Nequi)" in texto and "$7.550" in texto
        assert texto.index("TOTAL") < texto.index("Pago: Efectivo")
        assert all(len(linea) <= ANCHO for linea in texto.splitlines())

    def test_tarjeta_no_imprime_recibido_ni_vueltas(self):
        ticket = {
            **TICKET_ADENDO_V2,
            "descuento_tipo": None, "descuento_valor": None, "descuento_monto": "0",
            "subtotal": "30600.00", "ajuste_redondeo": "0", "total": "30600.00",
            "pagos": [{"metodo_pago": "tarjeta", "monto": "30600.00"}],
        }
        texto = a_texto(_renglones(ticket), ANCHO)
        assert "Pago: Tarjeta" in texto
        assert "Recibido" not in texto and "Vueltas" not in texto
        assert "Subtotal" not in texto and "Descuento" not in texto

    def test_descuento_en_pesos_sin_porcentaje(self):
        ticket = {**TICKET_ADENDO_V2, "descuento_tipo": "monto", "descuento_valor": "3060"}
        texto = a_texto(_renglones(ticket), ANCHO)
        assert "Descuento " in texto and "Descuento (" not in texto

    def test_venta_en_cero_sin_pagos_se_imprime(self):
        ticket = {
            **TICKET_ADENDO_V2,
            "descuento_tipo": "porcentaje", "descuento_valor": "100", "descuento_monto": "30600.00",
            "ajuste_redondeo": "0", "total": "0", "pagos": [],
        }
        texto = a_texto(_renglones(ticket), ANCHO)
        assert "Descuento (100 %)" in texto and "Pago:" not in texto

    def test_el_formato_anterior_sigue_imprimiendo(self):
        texto = a_texto(_renglones(), ANCHO)
        assert "Pago: Efectivo" in texto
        assert texto.index("Pago: Efectivo") < texto.index("Piñata Mickey Mouse")

    def test_sin_pagos_ni_metodo_es_rechazado(self, cliente_con):
        cliente, _ = cliente_con(_ImpresoraFalsa())
        ticket = {k: v for k, v in TICKET_ADENDO_V2.items() if k != "pagos"}
        assert cliente.post("/imprimir", json=ticket).status_code == 422

    def test_el_endpoint_acepta_el_formato_nuevo(self, cliente_con):
        cliente, _ = cliente_con(_ImpresoraFalsa())
        assert cliente.post("/imprimir", json=TICKET_ADENDO_V2).status_code == 200


class TestVendedorEnElTicket:
    """Adendo v2, HU-08: "la venta quede asignada al vendedor elegido y que asi aparezca ... en el ticket"."""

    def test_imprime_quien_atendio_despues_de_la_venta(self):
        texto = a_texto(_renglones({**TICKET_JSON, "vendedor": "Laura Gómez"}), ANCHO)
        assert "Atendió: Laura Gómez" in texto
        assert texto.index("Venta #7") < texto.index("Atendió") < texto.index("Piñata Mickey Mouse")

    def test_sin_vendedor_no_imprime_la_linea(self):
        assert "Atendió" not in a_texto(_renglones(), ANCHO)

    def test_un_nombre_largo_se_parte_y_cabe_en_el_papel(self):
        texto = a_texto(_renglones({**TICKET_JSON, "vendedor": "María de los Ángeles Fernández de la Hoz y Sandoval"}), ANCHO)
        assert "Atendió: María" in texto
        assert all(len(linea) <= ANCHO for linea in texto.splitlines())


class TestTicketDeVentaSinConexion:
    """Fase 9: una venta hecha sin conexion se imprime con su referencia local, aun sin numero del servidor."""

    TICKET = {k: v for k, v in TICKET_ADENDO_V2.items() if k != "venta_id"} | {"referencia": "SC-0003"}

    def test_imprime_la_referencia_en_lugar_del_numero_de_venta(self):
        texto = a_texto(_renglones(self.TICKET), ANCHO)
        assert "Venta SC-0003" in texto and "Venta #" not in texto
        assert all(len(linea) <= ANCHO for linea in texto.splitlines())

    def test_el_numero_de_venta_tiene_prioridad_en_el_identificador(self):
        ticket = TicketIn.model_validate(self.TICKET | {"venta_id": 12})
        assert ticket.identificador == 12
        assert "Venta #12" in a_texto(_renglones(self.TICKET | {"venta_id": 12}), ANCHO)

    def test_sin_numero_ni_referencia_se_rechaza(self):
        sin_ninguno = {k: v for k, v in TICKET_ADENDO_V2.items() if k != "venta_id"}
        with pytest.raises(ValueError):
            TicketIn.model_validate(sin_ninguno)

    @pytest.mark.parametrize("referencia", ["../etc", "SC 0003", "", "A" * 31])
    def test_una_referencia_no_apta_para_nombre_de_archivo_se_rechaza(self, referencia):
        with pytest.raises(ValueError):
            TicketIn.model_validate(self.TICKET | {"referencia": referencia})

    def test_el_endpoint_imprime_y_nombra_el_archivo_con_la_referencia(self, tmp_path):
        from app.impresoras import ImpresoraMock

        app.dependency_overrides[obtener_impresora] = lambda: ImpresoraMock(tmp_path, ANCHO)
        try:
            respuesta = TestClient(app).post("/imprimir", json=self.TICKET)
        finally:
            app.dependency_overrides.pop(obtener_impresora, None)
        assert respuesta.status_code == 200, respuesta.text
        assert "Venta SC-0003" in (tmp_path / "venta_SC-0003.txt").read_text(encoding="utf-8")
