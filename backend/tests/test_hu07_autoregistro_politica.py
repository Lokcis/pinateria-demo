"""Pruebas de aceptacion de HU-07: politica de datos, promociones aparte y autorregistro por enlace (RF-046 a RF-049).

Cada clase cita el criterio de `docs/02-historias-de-usuario.md` (seccion 3.7) que cubre.
"""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.models.cliente import Cliente, MedioAutorizacion, OrigenRegistro
from app.models.configuracion_negocio import ConfiguracionNegocio
from app.services import limite_envios
from app.services.politica_datos import PENDIENTE, DatosNegocio, construir_politica, faltantes, version_vigente
from tests.conftest import obtener_token, pagos_en_efectivo
from tests.test_hu01_venta import _crear_producto
from tests.test_hu07_hu08_clientes_vendedor import _crear_cliente, _cuerpo_cliente, _vender

DATOS_NEGOCIO = {
    "nombre": "Piñatería Demo de Prueba",
    "documento": "900.123.456-7",
    "direccion": "Calle 123 # 45-67, Bogotá",
    "telefono": "3000000000",
    "correo_datos": "datos@ejemplo.com",
    "politica_fecha": "12-10-2026",
}


@pytest.fixture(autouse=True)
def _limpiar_limite():
    """Cada prueba arranca sin intentos previos en el limite de envios."""
    limite_envios.reiniciar()
    yield
    limite_envios.reiniciar()


@pytest.fixture
def negocio_completo(db_session):
    """Deja guardados todos los datos del negocio que exige la politica."""
    db_session.add(ConfiguracionNegocio(id=1, politica_version="1.0", **DATOS_NEGOCIO))
    db_session.commit()


@pytest.fixture
def negocio_sin_datos():
    """Sin datos del negocio guardados (como en un servidor recien instalado): la base de prueba arranca asi."""


def _cambiar_negocio(db_session, **campos):
    """Cambia datos del negocio ya guardados (por ejemplo, para dejar uno vacio)."""
    fila = db_session.get(ConfiguracionNegocio, 1)
    for campo, valor in campos.items():
        setattr(fila, campo, valor)
    db_session.commit()


def _auth(client, usuario):
    return {"Authorization": f"Bearer {obtener_token(client, usuario.username)}"}


@pytest.fixture
def h_vendedor(client, usuario_vendedor):
    return _auth(client, usuario_vendedor)


@pytest.fixture
def h_admin(client, usuario_administrador):
    return _auth(client, usuario_administrador)


def _generar_enlace(client, h_admin) -> str:
    respuesta = client.post("/autoregistro/enlace", headers=h_admin)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["token"]


def _cuerpo_publico(**extra) -> dict:
    cuerpo = {
        "nombre": "Lucía Mora",
        "documento": "5050606070",
        "telefono": "3112223344",
        "email": "lucia@example.com",
        "acepta_politica": True,
    }
    cuerpo.update(extra)
    return cuerpo


# ---------------------------------------------------------------------------
# Politica de datos
# ---------------------------------------------------------------------------


class TestPoliticaVigente:
    """HU-07: el POS y el formulario publico muestran el aviso de privacidad y la politica vigente."""

    def test_con_los_datos_del_negocio_es_la_version_oficial(self, client, h_vendedor, negocio_completo):
        politica = client.get("/clientes/politica", headers=h_vendedor).json()

        assert politica["version"] == "1.0"
        assert politica["datos_completos"] is True and politica["faltantes"] == []
        assert "Piñatería Demo de Prueba" in politica["aviso"]
        assert "datos@ejemplo.com" in politica["aviso"]
        assert PENDIENTE not in politica["aviso"]
        titulos = [s["titulo"] for s in politica["secciones"]]
        assert any("Derechos del titular" in t for t in titulos) and any("Cómo ejercer" in t for t in titulos)
        assert all(PENDIENTE not in p for s in politica["secciones"] for p in s["parrafos"])
        assert "promociones" in politica["texto_promociones"]

    def test_sin_los_datos_del_negocio_queda_como_borrador_y_marca_lo_que_falta(self, client, h_vendedor, negocio_sin_datos):
        politica = client.get("/clientes/politica", headers=h_vendedor).json()

        assert politica["version"] == "borrador"
        assert politica["datos_completos"] is False
        assert "Correo para solicitudes de datos" in politica["faltantes"]
        assert "Fecha desde la que rige la política" in politica["faltantes"]
        assert PENDIENTE in politica["aviso"]

    def test_el_alta_guarda_la_version_que_se_mostro(self, client, db_session, h_vendedor, negocio_completo):
        oficial = _crear_cliente(client, h_vendedor, documento="1")
        _cambiar_negocio(db_session, correo_datos="")
        borrador = _crear_cliente(client, h_vendedor, documento="2", nombre="Otro")

        assert db_session.get(Cliente, oficial["id"]).autorizacion_version == "1.0"
        assert db_session.get(Cliente, borrador["id"]).autorizacion_version == "borrador"

    def test_quien_atiende_las_solicitudes_por_defecto_es_el_negocio(self):
        datos = DatosNegocio(nombre="Piñatería de Prueba", politica_fecha="12-10-2026")
        assert "Persona que atiende las solicitudes: Piñatería de Prueba" in str(construir_politica(datos)["secciones"])
        con_persona = DatosNegocio(nombre="Piñatería de Prueba", responsable_datos="Doña Rosa")
        assert "Persona que atiende las solicitudes: Doña Rosa" in str(construir_politica(con_persona)["secciones"])

    def test_faltantes_y_version(self):
        assert len(faltantes(DatosNegocio())) == 6
        assert version_vigente(DatosNegocio()) == "borrador"
        completos = DatosNegocio(
            nombre="n", documento="d", direccion="a", telefono="t", correo_datos="c@x.co", politica_fecha="f", politica_version="2.1"
        )
        assert version_vigente(completos) == "2.1"


# ---------------------------------------------------------------------------
# Promociones: autorizacion aparte
# ---------------------------------------------------------------------------


class TestPromocionesAparte:
    """Autorizacion separada y expresa para ofrecer promociones: casilla distinta, desmarcada por defecto."""

    def test_por_defecto_no_acepta(self, client, h_vendedor):
        cliente = _crear_cliente(client, h_vendedor)
        assert cliente["acepta_publicidad"] is False and cliente["publicidad_fecha"] is None

    def test_se_guarda_con_su_fecha_cuando_la_dan(self, client, h_vendedor):
        cliente = _crear_cliente(client, h_vendedor, acepta_publicidad=True)
        assert cliente["acepta_publicidad"] is True and cliente["publicidad_fecha"] is not None

    def test_se_da_y_se_retira_despues(self, client, h_vendedor):
        cliente = _crear_cliente(client, h_vendedor)
        dado = client.patch(f"/clientes/{cliente['id']}", json={"acepta_publicidad": True}, headers=h_vendedor).json()
        assert dado["acepta_publicidad"] is True and dado["publicidad_fecha"] is not None
        retirado = client.patch(f"/clientes/{cliente['id']}", json={"acepta_publicidad": False}, headers=h_vendedor).json()
        assert retirado["acepta_publicidad"] is False and retirado["publicidad_fecha"] is not None  # queda la fecha del retiro

    def test_no_se_puede_activar_en_un_cliente_desactivado(self, client, h_vendedor):
        cliente = _crear_cliente(client, h_vendedor)
        client.patch(f"/clientes/{cliente['id']}", json={"activo": False}, headers=h_vendedor)
        respuesta = client.patch(f"/clientes/{cliente['id']}", json={"acepta_publicidad": True}, headers=h_vendedor)
        assert respuesta.status_code == 409

    def test_el_listado_filtra_a_quienes_aceptan(self, client, h_vendedor):
        _crear_cliente(client, h_vendedor, nombre="Sí", documento="1", acepta_publicidad=True)
        _crear_cliente(client, h_vendedor, nombre="No", documento="2")
        quienes = lambda **p: [c["nombre"] for c in client.get("/clientes", params=p, headers=h_vendedor).json()]
        assert quienes(acepta_publicidad=True) == ["Sí"]
        assert quienes(acepta_publicidad=False) == ["No"]
        assert quienes() == ["No", "Sí"]

    def test_revocar_o_suprimir_retira_las_promociones(self, client, db_session, h_vendedor, h_admin):
        revocado = _crear_cliente(client, h_vendedor, nombre="A", documento="1", acepta_publicidad=True)
        suprimido = _crear_cliente(client, h_vendedor, nombre="B", documento="2", acepta_publicidad=True)
        for cliente, tipo in ((revocado, "revocatoria"), (suprimido, "supresion")):
            solicitud = client.post(
                "/solicitudes-titular", json={"cliente_id": cliente["id"], "tipo": tipo}, headers=h_admin
            ).json()
            client.patch(f"/solicitudes-titular/{solicitud['id']}", json={"estado": "resuelta", "respuesta": "ok"}, headers=h_admin)
        db_session.expire_all()
        assert db_session.get(Cliente, revocado["id"]).acepta_publicidad is False
        anonimo = db_session.get(Cliente, suprimido["id"])
        assert anonimo.acepta_publicidad is False and anonimo.publicidad_fecha is None


# ---------------------------------------------------------------------------
# Administracion del enlace
# ---------------------------------------------------------------------------


class TestAdministrarElEnlace:
    """HU-07: "el administrador pueda consultar, copiar, desactivar y regenerar el enlace, y que un enlace
    desactivado o regenerado deje de funcionar con un mensaje claro"."""

    def test_el_vendedor_recibe_403(self, client, h_vendedor):
        assert client.get("/autoregistro/enlace", headers=h_vendedor).status_code == 403
        assert client.post("/autoregistro/enlace", headers=h_vendedor).status_code == 403
        assert client.patch("/autoregistro/enlace", json={"activo": False}, headers=h_vendedor).status_code == 403

    def test_al_inicio_no_hay_enlace(self, client, h_admin, negocio_completo):
        enlace = client.get("/autoregistro/enlace", headers=h_admin).json()
        assert enlace["existe"] is False and enlace["token"] is None and enlace["activo"] is False

    def test_no_se_genera_sin_los_datos_del_negocio(self, client, h_admin, negocio_sin_datos):
        respuesta = client.post("/autoregistro/enlace", headers=h_admin)
        assert respuesta.status_code == 409
        assert "Correo para solicitudes de datos" in respuesta.json()["detail"]
        assert "Datos del negocio" in respuesta.json()["detail"]

    def test_genera_un_codigo_largo_y_aleatorio(self, client, h_admin, negocio_completo):
        primero = _generar_enlace(client, h_admin)
        assert len(primero) >= 30
        assert client.get("/autoregistro/enlace", headers=h_admin).json()["activo"] is True

    def test_regenerar_deja_sin_efecto_el_anterior(self, client, h_admin, negocio_completo):
        viejo = _generar_enlace(client, h_admin)
        nuevo = _generar_enlace(client, h_admin)
        assert viejo != nuevo
        assert client.get(f"/publico/autoregistro/{viejo}").status_code == 404
        assert client.get(f"/publico/autoregistro/{nuevo}").status_code == 200

    def test_desactivar_y_reactivar_conserva_el_codigo(self, client, h_admin, negocio_completo):
        token = _generar_enlace(client, h_admin)
        apagado = client.patch("/autoregistro/enlace", json={"activo": False}, headers=h_admin).json()
        assert apagado["activo"] is False and apagado["token"] == token
        assert client.get(f"/publico/autoregistro/{token}").status_code == 404
        assert client.patch("/autoregistro/enlace", json={"activo": True}, headers=h_admin).json()["activo"] is True
        assert client.get(f"/publico/autoregistro/{token}").status_code == 200

    def test_cambiar_el_estado_sin_enlace_es_404(self, client, h_admin, negocio_completo):
        assert client.patch("/autoregistro/enlace", json={"activo": True}, headers=h_admin).status_code == 404

    def test_no_se_reactiva_si_faltan_datos(self, client, db_session, h_admin, negocio_completo):
        _generar_enlace(client, h_admin)
        client.patch("/autoregistro/enlace", json={"activo": False}, headers=h_admin)
        _cambiar_negocio(db_session, telefono="")
        assert client.patch("/autoregistro/enlace", json={"activo": True}, headers=h_admin).status_code == 409


# ---------------------------------------------------------------------------
# Formulario publico
# ---------------------------------------------------------------------------


class TestFormularioPublico:
    """HU-07: el enlace abre un formulario sin pedir sesion, con el aviso y la politica vigentes, y no
    permite enviar sin marcar la aceptacion."""

    @pytest.fixture
    def token(self, client, h_admin, negocio_completo):
        return _generar_enlace(client, h_admin)

    def test_se_abre_sin_sesion_y_muestra_el_aviso_y_la_politica(self, client, token):
        respuesta = client.get(f"/publico/autoregistro/{token}")  # sin Authorization
        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert cuerpo["version"] == "1.0" and "datos@ejemplo.com" in cuerpo["aviso"] and cuerpo["secciones"]

    @pytest.mark.parametrize("token_falso", ["no-existe", "x" * 300, "a"])
    def test_un_codigo_equivocado_responde_con_mensaje_claro(self, client, token, token_falso):
        respuesta = client.get(f"/publico/autoregistro/{token_falso}")
        assert respuesta.status_code == 404
        assert "no está disponible" in respuesta.json()["detail"]

    def test_sin_datos_del_negocio_no_se_ofrece_el_formulario(self, client, db_session, token):
        _cambiar_negocio(db_session, documento="")
        assert client.get(f"/publico/autoregistro/{token}").status_code == 404
        assert client.post(f"/publico/autoregistro/{token}", json=_cuerpo_publico()).status_code == 404

    def test_no_se_envia_sin_aceptar(self, client, db_session, token):
        sin_marcar = client.post(f"/publico/autoregistro/{token}", json=_cuerpo_publico(acepta_politica=False))
        assert sin_marcar.status_code == 422
        sin_campo = _cuerpo_publico()
        del sin_campo["acepta_politica"]
        assert client.post(f"/publico/autoregistro/{token}", json=sin_campo).status_code == 422
        assert db_session.query(Cliente).count() == 0

    @pytest.mark.parametrize("cambio", [{"telefono": "123"}, {"email": "no-es-correo"}, {"nombre": "   "}])
    def test_datos_invalidos_422(self, client, token, cambio):
        assert client.post(f"/publico/autoregistro/{token}", json=_cuerpo_publico(**cambio)).status_code == 422

    def test_enlace_desactivado_o_regenerado_no_recibe_envios(self, client, h_admin, db_session, token):
        client.patch("/autoregistro/enlace", json={"activo": False}, headers=h_admin)
        respuesta = client.post(f"/publico/autoregistro/{token}", json=_cuerpo_publico())
        assert respuesta.status_code == 404 and "no está disponible" in respuesta.json()["detail"]
        assert db_session.query(Cliente).count() == 0


class TestEnvioDelAutoregistro:
    """HU-07: el cliente queda con origen autorregistro, medio electronico, fecha y version de la politica,
    sin descuento propio, y se puede asociar a una venta como cualquier otro."""

    @pytest.fixture
    def token(self, client, h_admin, negocio_completo):
        return _generar_enlace(client, h_admin)

    def test_guarda_al_cliente_con_la_evidencia(self, client, db_session, token):
        antes = datetime.now(timezone.utc)
        respuesta = client.post(f"/publico/autoregistro/{token}", json=_cuerpo_publico())
        assert respuesta.status_code == 201
        assert "Gracias" in respuesta.json()["mensaje"]

        cliente = db_session.query(Cliente).one()
        assert cliente.nombre == "Lucía mora" and cliente.documento == "5050606070"
        assert cliente.origen_registro == OrigenRegistro.AUTOREGISTRO
        assert cliente.autorizacion_medio == MedioAutorizacion.ELECTRONICO
        assert cliente.autorizacion_version == "1.0"
        assert cliente.autorizacion_fecha >= antes
        assert cliente.autorizacion_registrada_por is None
        assert (cliente.descuento_tipo, cliente.descuento_valor) == (None, None)
        assert cliente.activo is True and cliente.utilizable is True
        assert cliente.acepta_publicidad is False

    def test_no_se_guarda_la_direccion_ip(self, client, db_session, token):
        client.post(
            f"/publico/autoregistro/{token}", json=_cuerpo_publico(), headers={"cf-connecting-ip": "203.0.113.9"}
        )
        valores = [str(v) for v in vars(db_session.query(Cliente).one()).values()]
        assert not any("203.0.113.9" in v for v in valores)
        assert not [c for c in Cliente.__table__.columns.keys() if "ip" in c.split("_")]

    def test_la_casilla_de_promociones_es_aparte(self, client, db_session, token):
        client.post(f"/publico/autoregistro/{token}", json=_cuerpo_publico(acepta_publicidad=True))
        cliente = db_session.query(Cliente).one()
        assert cliente.acepta_publicidad is True and cliente.publicidad_fecha is not None

    def test_el_cliente_autorregistrado_se_puede_asociar_a_una_venta(
        self, client, db_session, categoria_prueba, h_vendedor, token
    ):
        client.post(f"/publico/autoregistro/{token}", json=_cuerpo_publico())
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata", "20000.00", 5)
        encontrado = client.get("/clientes", params={"q": "Lucía", "solo_utilizables": True}, headers=h_vendedor).json()
        assert [c["origen_registro"] for c in encontrado] == ["autoregistro"]
        venta = _vender(client, h_vendedor, producto.id, pagos=pagos_en_efectivo("20000"), cliente_id=encontrado[0]["id"])
        assert venta.status_code == 201

    @pytest.mark.parametrize("repetido", [{"documento": "9999999999"}, {"telefono": "3000000001"}])
    def test_un_duplicado_responde_igual_y_no_toca_nada(self, client, db_session, h_vendedor, token, repetido):
        existente = _crear_cliente(client, h_vendedor, nombre="Original", documento="9999999999", telefono="3000000001")
        respuesta_nueva = client.post(f"/publico/autoregistro/{token}", json=_cuerpo_publico())
        respuesta_repetida = client.post(
            f"/publico/autoregistro/{token}", json=_cuerpo_publico(nombre="Intruso", **repetido)
        )

        assert respuesta_repetida.status_code == respuesta_nueva.status_code == 201
        assert respuesta_repetida.json() == respuesta_nueva.json()  # nada que revele que ya existia
        assert db_session.query(Cliente).count() == 2  # el existente y el nuevo; el intruso no se creó
        assert db_session.get(Cliente, existente["id"]).nombre == "Original"
        assert db_session.query(Cliente).filter(Cliente.nombre == "Intruso").count() == 0

    def test_el_campo_trampa_se_ignora_sin_avisar(self, client, db_session, token):
        respuesta = client.post(f"/publico/autoregistro/{token}", json=_cuerpo_publico(sitio_web="http://spam.example"))
        assert respuesta.status_code == 201
        assert respuesta.json()["mensaje"] == client.post(f"/publico/autoregistro/{token}", json=_cuerpo_publico()).json()["mensaje"]
        assert db_session.query(Cliente).count() == 1  # solo el envío sin trampa

    def test_el_limite_de_envios_bloquea_el_uso_abusivo(self, client, db_session, token):
        cabecera = {"cf-connecting-ip": "198.51.100.7"}
        for i in range(limite_envios.MAX_INTENTOS):
            r = client.post(
                f"/publico/autoregistro/{token}",
                json=_cuerpo_publico(documento=f"700{i}", telefono=f"31100000{i}0"),
                headers=cabecera,
            )
            assert r.status_code == 201
        bloqueado = client.post(f"/publico/autoregistro/{token}", json=_cuerpo_publico(documento="8888"), headers=cabecera)
        assert bloqueado.status_code == 429
        assert db_session.query(Cliente).count() == limite_envios.MAX_INTENTOS
        # Otro visitante no se ve afectado.
        otro = client.post(
            f"/publico/autoregistro/{token}", json=_cuerpo_publico(documento="8888", telefono="3199999999"),
            headers={"cf-connecting-ip": "198.51.100.8"},
        )
        assert otro.status_code == 201


class TestLimiteDeEnvios:
    """RF-049: el limite se cuenta por visitante y vence con la ventana."""

    def test_permite_hasta_el_maximo_y_luego_bloquea(self):
        assert all(limite_envios.registrar_intento("a", ahora=100.0 + i) for i in range(limite_envios.MAX_INTENTOS))
        assert limite_envios.registrar_intento("a", ahora=110.0) is False
        assert limite_envios.registrar_intento("b", ahora=110.0) is True

    def test_vuelve_a_permitir_cuando_vence_la_ventana(self):
        for i in range(limite_envios.MAX_INTENTOS):
            limite_envios.registrar_intento("a", ahora=100.0 + i)
        assert limite_envios.registrar_intento("a", ahora=100.0 + limite_envios.VENTANA_SEGUNDOS + 10) is True

    def test_no_guarda_el_identificador_en_claro(self):
        limite_envios.registrar_intento("203.0.113.9", ahora=1.0)
        assert "203.0.113.9" not in limite_envios._intentos
        assert all("203.0.113.9" not in clave for clave in limite_envios._intentos)

    def test_descarta_a_los_visitantes_vencidos(self):
        limite_envios.registrar_intento("viejo", ahora=1.0)
        limite_envios.registrar_intento("nuevo", ahora=1.0 + limite_envios.VENTANA_SEGUNDOS + 5)
        assert len(limite_envios._intentos) == 1


# ---------------------------------------------------------------------------
# Datos del negocio (configurables desde la aplicacion)
# ---------------------------------------------------------------------------


class TestDatosDelNegocio:
    """Los datos del responsable se editan en la aplicacion ("Datos personales > Datos del negocio"), solo el administrador."""

    def test_el_vendedor_recibe_403(self, client, h_vendedor):
        assert client.get("/negocio", headers=h_vendedor).status_code == 403
        assert client.put("/negocio", json={}, headers=h_vendedor).status_code == 403

    def test_al_inicio_no_hay_nada_y_se_sabe_que_falta(self, client, h_admin):
        negocio = client.get("/negocio", headers=h_admin).json()
        assert negocio["datos_completos"] is False and len(negocio["faltantes"]) == 6
        assert negocio["version_vigente"] == "borrador" and negocio["actualizado_en"] is None

    def test_guardar_los_datos_completa_la_politica(self, client, h_admin, h_vendedor):
        respuesta = client.put("/negocio", json={**DATOS_NEGOCIO, "politica_version": "1.0"}, headers=h_admin)
        assert respuesta.status_code == 200
        negocio = respuesta.json()
        assert negocio["datos_completos"] is True and negocio["faltantes"] == []
        assert negocio["version_vigente"] == "1.0" and negocio["actualizado_en"] is not None
        assert client.get("/negocio", headers=h_admin).json()["nombre"] == DATOS_NEGOCIO["nombre"]
        # El POS ya ve el aviso con esos datos, sin tocar el servidor.
        politica = client.get("/clientes/politica", headers=h_vendedor).json()
        assert politica["version"] == "1.0" and "datos@ejemplo.com" in politica["aviso"]

    def test_recorta_espacios_y_la_version_vacia_vuelve_a_1_0(self, client, h_admin):
        respuesta = client.put(
            "/negocio", json={**DATOS_NEGOCIO, "nombre": "  Mi tienda  ", "politica_version": "   "}, headers=h_admin
        ).json()
        assert respuesta["nombre"] == "Mi tienda" and respuesta["politica_version"] == "1.0"

    def test_un_dato_incompleto_deja_la_politica_en_borrador(self, client, h_admin):
        respuesta = client.put("/negocio", json={**DATOS_NEGOCIO, "telefono": ""}, headers=h_admin).json()
        assert respuesta["datos_completos"] is False and respuesta["faltantes"] == ["Teléfono"]
        assert respuesta["version_vigente"] == "borrador"

    def test_guardar_otra_vez_reemplaza_y_una_version_nueva_queda_en_las_autorizaciones(
        self, client, db_session, h_admin, h_vendedor
    ):
        client.put("/negocio", json={**DATOS_NEGOCIO, "politica_version": "1.0"}, headers=h_admin)
        primero = _crear_cliente(client, h_vendedor, documento="1")
        client.put("/negocio", json={**DATOS_NEGOCIO, "politica_version": "1.1", "correo_datos": "nuevo@ejemplo.com"}, headers=h_admin)
        segundo = _crear_cliente(client, h_vendedor, documento="2")

        assert db_session.get(Cliente, primero["id"]).autorizacion_version == "1.0"
        assert db_session.get(Cliente, segundo["id"]).autorizacion_version == "1.1"
        assert db_session.query(ConfiguracionNegocio).count() == 1  # una sola fila
        assert "nuevo@ejemplo.com" in client.get("/clientes/politica", headers=h_vendedor).json()["aviso"]

    def test_el_correo_vacio_se_acepta_pero_uno_mal_escrito_no(self, client, h_admin):
        assert client.put("/negocio", json={**DATOS_NEGOCIO, "correo_datos": ""}, headers=h_admin).status_code == 200
        assert client.put("/negocio", json={**DATOS_NEGOCIO, "correo_datos": "no-es-correo"}, headers=h_admin).status_code == 422

    def test_registra_quien_lo_guardo(self, client, db_session, h_admin, usuario_administrador):
        client.put("/negocio", json=DATOS_NEGOCIO, headers=h_admin)
        assert db_session.get(ConfiguracionNegocio, 1).actualizado_por == usuario_administrador.id

    def test_el_enlace_de_autorregistro_se_habilita_al_completar_los_datos(self, client, h_admin):
        assert client.post("/autoregistro/enlace", headers=h_admin).status_code == 409
        client.put("/negocio", json=DATOS_NEGOCIO, headers=h_admin)
        assert client.post("/autoregistro/enlace", headers=h_admin).status_code == 200

