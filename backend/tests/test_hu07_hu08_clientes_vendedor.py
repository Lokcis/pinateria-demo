"""Pruebas de aceptacion de HU-07 (clientes y Habeas Data), HU-08 (vendedor por venta) y el descuento por cliente (HU-06) — Adendo v2, Fase A2.

Cada clase cita, en su docstring, el criterio de `docs/02-historias-de-usuario.md`
(secciones 3.6 a 3.8) que cubre. El formulario publico de autorregistro
(RF-046 a RF-049) no esta en esta entrega: espera la politica de datos.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.cliente import Cliente, MedioAutorizacion, OrigenRegistro, TipoSolicitudTitular
from app.models.descuento import TipoDescuento, TopeDescuento
from app.models.usuario import RolUsuario
from app.models.venta import Venta
from app.services.politica_datos import cargar_datos_negocio, version_vigente
from app.services.habeas_data import (
    NOMBRE_ANONIMIZADO,
    fecha_limite_solicitud,
    sumar_dias_habiles,
)
from tests.conftest import _crear_usuario, obtener_token, pagos_en_efectivo
from tests.test_hu01_venta import _crear_producto

D = Decimal


def _hoy_en_bogota() -> date:
    """Hoy en la zona horaria del negocio (el servidor y el CI corren en UTC: a ciertas horas el dia difiere)."""
    return datetime.now(ZoneInfo(settings.zona_horaria)).date()


def _auth(client: TestClient, usuario) -> dict[str, str]:
    """Devuelve el header Authorization para el usuario dado."""
    return {"Authorization": f"Bearer {obtener_token(client, usuario.username)}"}


@pytest.fixture
def h_vendedor(client, usuario_vendedor):
    """Headers de un vendedor."""
    return _auth(client, usuario_vendedor)


@pytest.fixture
def h_admin(client, usuario_administrador):
    """Headers de un administrador."""
    return _auth(client, usuario_administrador)


def _cuerpo_cliente(**extra) -> dict:
    """Payload valido para `POST /clientes`; `extra` pisa los campos."""
    cuerpo = {
        "nombre": "María Pérez",
        "documento": "1010202030",
        "telefono": "3001234567",
        "email": "maria@example.com",
        "autorizacion_aceptada": True,
        "autorizacion_medio": "verbal",
    }
    cuerpo.update(extra)
    return cuerpo


def _crear_cliente(client, headers, **extra) -> dict:
    """Crea un cliente por la API y devuelve su JSON."""
    respuesta = client.post("/clientes", json=_cuerpo_cliente(**extra), headers=headers)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _vender(client, headers, producto_id, cantidad=1, pagos=None, **extra):
    """Hace `POST /ventas` con una sola linea; `extra` agrega cliente_id, vendedor_id o descuento."""
    cuerpo = {"detalles": [{"producto_id": producto_id, "cantidad": cantidad}], "pagos": pagos or [], **extra}
    return client.post("/ventas", json=cuerpo, headers=headers)


# ---------------------------------------------------------------------------
# Plazos (funciones puras)
# ---------------------------------------------------------------------------


class TestPlazosLegales:
    """HU-07: "solicitudes ... con su fecha limite legal" (consultas 10 dias habiles, reclamos 15)."""

    def test_los_dias_habiles_saltan_el_fin_de_semana(self):
        viernes = date(2026, 10, 9)
        assert viernes.weekday() == 4
        assert sumar_dias_habiles(viernes, 1) == date(2026, 10, 12)  # lunes
        assert sumar_dias_habiles(viernes, 5) == date(2026, 10, 16)

    def test_consulta_10_dias_y_reclamo_15(self):
        lunes = date(2026, 10, 12)
        assert fecha_limite_solicitud(TipoSolicitudTitular.CONSULTA, lunes) == date(2026, 10, 26)
        for tipo in (TipoSolicitudTitular.ACTUALIZACION, TipoSolicitudTitular.SUPRESION, TipoSolicitudTitular.REVOCATORIA):
            assert fecha_limite_solicitud(tipo, lunes) == date(2026, 11, 2)


# ---------------------------------------------------------------------------
# Registro y edicion de clientes
# ---------------------------------------------------------------------------


class TestRegistroConAutorizacion:
    """HU-07: "no se pueda guardar un cliente sin marcar la autorizacion ... y que se registren la fecha,
    el medio, la version de la politica y el empleado que la recogio"."""

    def test_sin_autorizacion_no_se_guarda(self, client, db_session, h_vendedor):
        respuesta = client.post("/clientes", json=_cuerpo_cliente(autorizacion_aceptada=False), headers=h_vendedor)
        assert respuesta.status_code == 422
        assert db_session.query(Cliente).count() == 0

    def test_sin_el_campo_de_autorizacion_tampoco(self, client, h_vendedor):
        cuerpo = _cuerpo_cliente()
        del cuerpo["autorizacion_aceptada"]
        assert client.post("/clientes", json=cuerpo, headers=h_vendedor).status_code == 422

    def test_registra_la_evidencia(self, client, db_session, usuario_vendedor, h_vendedor):
        antes = datetime.now(timezone.utc) - timedelta(seconds=5)
        creado = _crear_cliente(client, h_vendedor, autorizacion_medio="escrito")

        cliente = db_session.get(Cliente, creado["id"])
        assert cliente.autorizacion_medio == MedioAutorizacion.ESCRITO
        assert cliente.autorizacion_version == version_vigente(cargar_datos_negocio(db_session))
        assert cliente.autorizacion_fecha >= antes
        assert cliente.origen_registro == OrigenRegistro.EMPLEADO
        assert cliente.autorizacion_registrada_por == usuario_vendedor.id
        assert cliente.descuento_tipo is None  # nace sin descuento propio
        assert creado["utilizable"] is True

    def test_la_base_rechaza_un_cliente_sin_registrador(self, db_session):
        """El CHECK de la base protege aunque la aplicacion falle: empleado exige registrador."""
        db_session.add(
            Cliente(
                nombre="X",
                autorizacion_fecha=datetime.now(timezone.utc),
                autorizacion_medio=MedioAutorizacion.VERBAL,
                autorizacion_version="1",
                origen_registro=OrigenRegistro.EMPLEADO,
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_propietario_no_accede(self, client, usuario_propietario):
        h = _auth(client, usuario_propietario)
        assert client.get("/clientes", headers=h).status_code == 403
        assert client.post("/clientes", json=_cuerpo_cliente(), headers=h).status_code == 403

    def test_politica_vigente(self, client, h_vendedor):
        respuesta = client.get("/clientes/politica", headers=h_vendedor)
        assert respuesta.status_code == 200
        assert respuesta.json()["version"] == "borrador"  # sin datos del negocio guardados
        assert respuesta.json()["aviso"] and respuesta.json()["secciones"]


class TestDatosDelCliente:
    """HU-07: "crear, editar y desactivar clientes ..., que el documento no se repita, que el telefono
    tenga solo digitos (7 a 15) y que un cliente con ventas nunca se elimine"."""

    def test_documento_repetido_es_409(self, client, h_vendedor):
        _crear_cliente(client, h_vendedor)
        repetido = client.post("/clientes", json=_cuerpo_cliente(nombre="Otra"), headers=h_vendedor)
        assert repetido.status_code == 409

    def test_clientes_sin_documento_pueden_ser_varios(self, client, h_vendedor):
        _crear_cliente(client, h_vendedor, documento=None, nombre="Ana")
        _crear_cliente(client, h_vendedor, documento="  ", nombre="Beto")

    @pytest.mark.parametrize("telefono", ["12345", "abc1234567", "3001234567890123", "300-123-4567"])
    def test_telefono_invalido(self, client, h_vendedor, telefono):
        respuesta = client.post("/clientes", json=_cuerpo_cliente(telefono=telefono), headers=h_vendedor)
        assert respuesta.status_code == 422

    def test_correo_invalido(self, client, h_vendedor):
        assert client.post("/clientes", json=_cuerpo_cliente(email="no-es-correo"), headers=h_vendedor).status_code == 422

    def test_editar_y_desactivar(self, client, h_vendedor):
        creado = _crear_cliente(client, h_vendedor)
        editado = client.patch(
            f"/clientes/{creado['id']}", json={"nombre": " María P. ", "telefono": "3109998877"}, headers=h_vendedor
        )
        assert editado.status_code == 200
        assert editado.json()["nombre"] == "María p."
        assert editado.json()["telefono"] == "3109998877"

        baja = client.patch(f"/clientes/{creado['id']}", json={"activo": False}, headers=h_vendedor)
        assert baja.json()["activo"] is False
        assert baja.json()["utilizable"] is False

    def test_editar_a_un_documento_ajeno_es_409(self, client, h_vendedor):
        _crear_cliente(client, h_vendedor, documento="111")
        otro = _crear_cliente(client, h_vendedor, documento="222", nombre="Otro")
        assert client.patch(f"/clientes/{otro['id']}", json={"documento": "111"}, headers=h_vendedor).status_code == 409
        # Conservar el propio documento no es conflicto.
        assert client.patch(f"/clientes/{otro['id']}", json={"documento": "222"}, headers=h_vendedor).status_code == 200

    def test_nombre_nulo_es_422(self, client, h_vendedor):
        creado = _crear_cliente(client, h_vendedor)
        assert client.patch(f"/clientes/{creado['id']}", json={"nombre": None}, headers=h_vendedor).status_code == 422

    def test_cliente_inexistente_404(self, client, h_vendedor):
        assert client.get("/clientes/9999", headers=h_vendedor).status_code == 404
        assert client.patch("/clientes/9999", json={"activo": False}, headers=h_vendedor).status_code == 404

    def test_no_existe_endpoint_para_borrar(self, client, h_admin):
        creado = _crear_cliente(client, h_admin)
        assert client.delete(f"/clientes/{creado['id']}", headers=h_admin).status_code == 405

    def test_la_base_impide_borrar_un_cliente_con_ventas(
        self, client, db_session, categoria_prueba, h_vendedor
    ):
        creado = _crear_cliente(client, h_vendedor)
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata", "10000.00", 5)
        assert _vender(client, h_vendedor, producto.id, pagos=pagos_en_efectivo("10000"), cliente_id=creado["id"]).status_code == 201
        with pytest.raises(IntegrityError):
            db_session.execute(text("DELETE FROM clientes WHERE id = :id"), {"id": creado["id"]})
        db_session.rollback()


class TestDescuentoPropio:
    """HU-06: "solo el administrador pueda ... asignar el descuento propio de un cliente; el vendedor
    que lo intente recibe 403"."""

    def test_vendedor_recibe_403(self, client, h_vendedor):
        creado = _crear_cliente(client, h_vendedor)
        respuesta = client.put(
            f"/clientes/{creado['id']}/descuento", json={"tipo": "porcentaje", "valor": "10"}, headers=h_vendedor
        )
        assert respuesta.status_code == 403

    def test_el_vendedor_no_lo_cambia_por_el_patch(self, client, h_vendedor):
        creado = _crear_cliente(client, h_vendedor)
        client.patch(f"/clientes/{creado['id']}", json={"descuento_tipo": "porcentaje", "descuento_valor": "50"}, headers=h_vendedor)
        assert client.get(f"/clientes/{creado['id']}", headers=h_vendedor).json()["descuento_tipo"] is None

    def test_administrador_asigna_y_quita(self, client, h_vendedor, h_admin):
        creado = _crear_cliente(client, h_vendedor)
        asignado = client.put(
            f"/clientes/{creado['id']}/descuento", json={"tipo": "porcentaje", "valor": "12.5"}, headers=h_admin
        )
        assert asignado.status_code == 200
        assert (asignado.json()["descuento_tipo"], Decimal(asignado.json()["descuento_valor"])) == ("porcentaje", D("12.5"))

        quitado = client.put(f"/clientes/{creado['id']}/descuento", json={}, headers=h_admin)
        assert quitado.json()["descuento_tipo"] is None
        assert quitado.json()["descuento_valor"] is None

    @pytest.mark.parametrize(
        "cuerpo",
        [
            {"tipo": "porcentaje", "valor": "101"},
            {"tipo": "porcentaje", "valor": "0"},
            {"tipo": "monto", "valor": "-5"},
            {"tipo": "monto"},
            {"valor": "10"},
        ],
    )
    def test_descuentos_invalidos(self, client, h_vendedor, h_admin, cuerpo):
        creado = _crear_cliente(client, h_vendedor)
        assert client.put(f"/clientes/{creado['id']}/descuento", json=cuerpo, headers=h_admin).status_code == 422


# ---------------------------------------------------------------------------
# Busqueda, rangos y ficha
# ---------------------------------------------------------------------------


class TestBusqueda:
    """HU-07: "la busqueda por nombre (coincidencia parcial), documento o telefono"."""

    @pytest.fixture(autouse=True)
    def _clientes(self, client, h_vendedor):
        _crear_cliente(client, h_vendedor, nombre="María fernanda gómez", documento="1001", telefono="3001111111")
        _crear_cliente(client, h_vendedor, nombre="Carlos ruiz", documento="2002", telefono="3102222222")
        _crear_cliente(client, h_vendedor, nombre="Marta ruiz", documento=None, telefono=None)

    def _buscar(self, client, headers, **params):
        respuesta = client.get("/clientes", params=params, headers=headers)
        assert respuesta.status_code == 200, respuesta.text
        return [c["nombre"] for c in respuesta.json()]

    def test_por_nombre_parcial_sin_distinguir_mayusculas(self, client, h_vendedor):
        # El orden con tildes depende de la colacion de Postgres: se compara sin importar el orden.
        assert sorted(self._buscar(client, h_vendedor, q="mar")) == sorted(["María fernanda gómez", "Marta ruiz"])
        assert self._buscar(client, h_vendedor, q="RUIZ") == ["Carlos ruiz", "Marta ruiz"]

    def test_por_documento_y_por_telefono(self, client, h_vendedor):
        assert self._buscar(client, h_vendedor, q="2002") == ["Carlos ruiz"]
        assert self._buscar(client, h_vendedor, q="31022") == ["Carlos ruiz"]

    def test_los_comodines_se_buscan_literalmente(self, client, h_vendedor):
        assert self._buscar(client, h_vendedor, q="%") == []

    def test_sin_filtro_lista_todos_por_nombre(self, client, h_vendedor):
        assert sorted(self._buscar(client, h_vendedor)) == sorted(["Carlos ruiz", "María fernanda gómez", "Marta ruiz"])
        assert self._buscar(client, h_vendedor)[0] == "Carlos ruiz"  # sin tildes el orden alfabetico es estable

    def test_filtro_por_activo_y_solo_utilizables(self, client, h_vendedor):
        cliente = client.get("/clientes", params={"q": "Carlos"}, headers=h_vendedor).json()[0]
        client.patch(f"/clientes/{cliente['id']}", json={"activo": False}, headers=h_vendedor)
        assert "Carlos ruiz" not in self._buscar(client, h_vendedor, solo_utilizables=True)
        assert self._buscar(client, h_vendedor, activo=False) == ["Carlos ruiz"]
        assert "Carlos ruiz" in self._buscar(client, h_vendedor)


class TestFichaYRangos:
    """HU-07: "la ficha del cliente muestre su historial de ventas (fecha, total, vendedor y pagos) y el
    total comprado, y que el listado se pueda filtrar por rangos de total comprado y de fechas de compra"."""

    @pytest.fixture
    def escenario(self, client, db_session, categoria_prueba, usuario_vendedor, h_vendedor):
        """Ana compra 10.000 hoy y 30.000 hace 40 dias; Beto compra 100.000 hoy; Carla no ha comprado."""
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata", "10000.00", 100)
        ana = _crear_cliente(client, h_vendedor, nombre="Ana", documento="1")
        beto = _crear_cliente(client, h_vendedor, nombre="Beto", documento="2")
        carla = _crear_cliente(client, h_vendedor, nombre="Carla", documento="3")

        def comprar(cliente, cantidad):
            r = _vender(
                client, h_vendedor, producto.id, cantidad, pagos_en_efectivo(f"{cantidad * 10000}"), cliente_id=cliente["id"]
            )
            assert r.status_code == 201, r.text
            return r.json()["id"]

        comprar(ana, 1)
        vieja = comprar(ana, 3)
        comprar(beto, 10)
        db_session.get(Venta, vieja).fecha = datetime.now(timezone.utc) - timedelta(days=40)
        db_session.commit()
        return {"ana": ana, "beto": beto, "carla": carla, "vieja": vieja}

    def _nombres(self, client, headers, **params):
        respuesta = client.get("/clientes", params=params, headers=headers)
        assert respuesta.status_code == 200, respuesta.text
        return [c["nombre"] for c in respuesta.json()]

    def test_ficha_con_total_e_historial(self, client, h_vendedor, usuario_vendedor, escenario):
        ficha = client.get(f"/clientes/{escenario['ana']['id']}", headers=h_vendedor).json()
        assert ficha["numero_ventas"] == 2
        assert D(ficha["total_comprado"]) == D("40000")
        assert ficha["ultima_compra"] is not None
        assert [D(v["total"]) for v in ficha["ventas"]] == [D("10000"), D("30000")]  # de la mas reciente a la mas antigua
        primera = ficha["ventas"][0]
        assert primera["vendedor"] == usuario_vendedor.nombre
        assert primera["pagos"][0]["metodo_pago"] == "efectivo"

    def test_ficha_dice_quien_recogio_la_autorizacion(self, client, h_vendedor, usuario_vendedor, escenario):
        """Aceptacion 3.2: la ficha muestra quien recogio la autorizacion (el empleado que registro al cliente)."""
        ficha = client.get(f"/clientes/{escenario['ana']['id']}", headers=h_vendedor).json()
        assert ficha['autorizacion_recogida_por'] == usuario_vendedor.nombre

    def test_ficha_de_un_cliente_sin_compras(self, client, h_vendedor, escenario):
        ficha = client.get(f"/clientes/{escenario['carla']['id']}", headers=h_vendedor).json()
        assert (ficha["numero_ventas"], D(ficha["total_comprado"]), ficha["ultima_compra"], ficha["ventas"]) == (0, D("0"), None, [])

    def test_el_listado_trae_el_resumen(self, client, h_vendedor, escenario):
        filas = {c["nombre"]: c for c in client.get("/clientes", headers=h_vendedor).json()}
        assert (filas["Ana"]["numero_ventas"], D(filas["Ana"]["total_comprado"])) == (2, D("40000"))
        assert (filas["Carla"]["numero_ventas"], D(filas["Carla"]["total_comprado"])) == (0, D("0"))

    def test_rango_de_total_comprado(self, client, h_vendedor, escenario):
        assert self._nombres(client, h_vendedor, total_min=50000) == ["Beto"]
        assert self._nombres(client, h_vendedor, total_max=40000) == ["Ana", "Carla"]
        assert self._nombres(client, h_vendedor, total_min=1, total_max=40000) == ["Ana"]

    def test_rango_de_fechas_cuenta_solo_las_compras_del_rango(self, client, h_vendedor, escenario):
        hoy = _hoy_en_bogota()
        reciente = self._nombres(client, h_vendedor, desde=(hoy - timedelta(days=7)).isoformat())
        assert reciente == ["Ana", "Beto"]  # Carla no compro en el rango
        filas = {
            c["nombre"]: c
            for c in client.get("/clientes", params={"desde": (hoy - timedelta(days=7)).isoformat()}, headers=h_vendedor).json()
        }
        assert D(filas["Ana"]["total_comprado"]) == D("10000")  # la compra de hace 40 dias no cuenta

        antiguo = self._nombres(client, h_vendedor, hasta=(hoy - timedelta(days=30)).isoformat())
        assert antiguo == ["Ana"]

    def test_fecha_y_total_se_combinan(self, client, h_vendedor, escenario):
        hoy = _hoy_en_bogota().isoformat()
        assert self._nombres(client, h_vendedor, desde=hoy, total_min=50000) == ["Beto"]
        assert self._nombres(client, h_vendedor, desde=hoy, total_min=200000) == []

    def test_rangos_invertidos_422(self, client, h_vendedor):
        assert client.get("/clientes", params={"total_min": 10, "total_max": 5}, headers=h_vendedor).status_code == 422
        assert client.get("/clientes", params={"desde": "2026-10-10", "hasta": "2026-10-01"}, headers=h_vendedor).status_code == 422


# ---------------------------------------------------------------------------
# Cliente en la venta y descuento propio
# ---------------------------------------------------------------------------


class TestClienteEnLaVenta:
    """HU-07: "asociar un cliente a la venta ... un cliente desactivado o con la autorizacion revocada no
    pueda asociarse"."""

    @pytest.fixture
    def producto(self, db_session, categoria_prueba):
        return _crear_producto(db_session, categoria_prueba.id, "Piñata", "20000.00", 50)

    def test_la_venta_queda_asociada_al_cliente(self, client, db_session, producto, h_vendedor):
        cliente = _crear_cliente(client, h_vendedor)
        respuesta = _vender(client, h_vendedor, producto.id, pagos=pagos_en_efectivo("20000"), cliente_id=cliente["id"])
        assert respuesta.status_code == 201
        assert respuesta.json()["cliente_id"] == cliente["id"]
        assert db_session.get(Venta, respuesta.json()["id"]).cliente_id == cliente["id"]

    def test_venta_sin_cliente_sigue_funcionando(self, client, producto, h_vendedor):
        respuesta = _vender(client, h_vendedor, producto.id, pagos=pagos_en_efectivo("20000"))
        assert respuesta.status_code == 201
        assert respuesta.json()["cliente_id"] is None

    def test_cliente_inexistente_404_y_no_descuenta_stock(self, client, db_session, producto, h_vendedor):
        respuesta = _vender(client, h_vendedor, producto.id, pagos=pagos_en_efectivo("20000"), cliente_id=9999)
        assert respuesta.status_code == 404
        db_session.refresh(producto)
        assert producto.stock_actual == 50

    def test_cliente_desactivado_no_se_asocia(self, client, db_session, producto, h_vendedor):
        cliente = _crear_cliente(client, h_vendedor)
        client.patch(f"/clientes/{cliente['id']}", json={"activo": False}, headers=h_vendedor)
        respuesta = _vender(client, h_vendedor, producto.id, pagos=pagos_en_efectivo("20000"), cliente_id=cliente["id"])
        assert respuesta.status_code == 422
        db_session.refresh(producto)
        assert producto.stock_actual == 50

    def test_cliente_con_autorizacion_revocada_no_se_asocia(self, client, db_session, producto, h_vendedor):
        cliente = _crear_cliente(client, h_vendedor)
        db_session.get(Cliente, cliente["id"]).autorizacion_revocada_en = datetime.now(timezone.utc)
        db_session.commit()
        respuesta = _vender(client, h_vendedor, producto.id, pagos=pagos_en_efectivo("20000"), cliente_id=cliente["id"])
        assert respuesta.status_code == 422

    def test_el_historial_muestra_el_cliente(self, client, producto, h_vendedor):
        cliente = _crear_cliente(client, h_vendedor, nombre="Lucía")
        _vender(client, h_vendedor, producto.id, pagos=pagos_en_efectivo("20000"), cliente_id=cliente["id"])
        _vender(client, h_vendedor, producto.id, pagos=pagos_en_efectivo("20000"))
        ventas = client.get("/ventas/hoy", headers=h_vendedor).json()["ventas"]
        assert sorted(v["cliente"] or "" for v in ventas) == ["", "Lucía"]


class TestDescuentoDelCliente:
    """HU-06: "al asociar un cliente con descuento propio, se sugiera ese descuento ... nunca se sumen los
    dos (el del cliente tiene prioridad)" y los topes no limitan "a los descuentos sugeridos"."""

    @pytest.fixture
    def producto(self, db_session, categoria_prueba):
        return _crear_producto(db_session, categoria_prueba.id, "Piñata", "20000.00", 50)

    def _cliente_con_descuento(self, client, h_vendedor, h_admin, tipo, valor):
        cliente = _crear_cliente(client, h_vendedor)
        client.put(f"/clientes/{cliente['id']}/descuento", json={"tipo": tipo, "valor": valor}, headers=h_admin)
        return cliente

    def test_aplica_el_descuento_propio(self, client, producto, h_vendedor, h_admin):
        cliente = self._cliente_con_descuento(client, h_vendedor, h_admin, "porcentaje", "10")
        respuesta = _vender(
            client, h_vendedor, producto.id, pagos=pagos_en_efectivo("18000"),
            cliente_id=cliente["id"], descuento={"origen": "cliente"},
        )
        assert respuesta.status_code == 201, respuesta.text
        venta = respuesta.json()
        assert venta["descuento_origen"] == "cliente"
        assert (venta["descuento_tipo"], D(venta["descuento_valor"]), D(venta["descuento_monto"])) == ("porcentaje", D("10"), D("2000"))
        assert D(venta["total"]) == D("18000")

    def test_el_backend_usa_el_descuento_vigente_y_no_el_que_manda_el_pos(self, client, producto, h_vendedor, h_admin):
        cliente = self._cliente_con_descuento(client, h_vendedor, h_admin, "monto", "1000")
        respuesta = _vender(
            client, h_vendedor, producto.id, pagos=pagos_en_efectivo("19000"),
            cliente_id=cliente["id"], descuento={"origen": "cliente", "tipo": "porcentaje", "valor": "90"},
        )
        assert respuesta.status_code == 201
        assert D(respuesta.json()["descuento_monto"]) == D("1000")

    def test_descuento_en_pesos_mayor_al_subtotal_se_limita(self, client, producto, h_vendedor, h_admin):
        cliente = self._cliente_con_descuento(client, h_vendedor, h_admin, "monto", "50000")
        respuesta = _vender(client, h_vendedor, producto.id, cliente_id=cliente["id"], descuento={"origen": "cliente"})
        assert respuesta.status_code == 201
        assert (D(respuesta.json()["descuento_monto"]), D(respuesta.json()["total"])) == (D("20000"), D("0"))

    def test_los_topes_del_vendedor_no_limitan_el_descuento_del_cliente(self, client, db_session, producto, h_vendedor, h_admin):
        db_session.merge(TopeDescuento(id=1, tope_porcentaje=D("5"), tope_monto=D("500")))
        db_session.commit()
        cliente = self._cliente_con_descuento(client, h_vendedor, h_admin, "porcentaje", "30")
        respuesta = _vender(
            client, h_vendedor, producto.id, pagos=pagos_en_efectivo("14000"),
            cliente_id=cliente["id"], descuento={"origen": "cliente"},
        )
        assert respuesta.status_code == 201

    def test_el_vendedor_puede_cambiarlo_a_manual_y_ahi_si_hay_topes(self, client, db_session, producto, h_vendedor, h_admin):
        db_session.merge(TopeDescuento(id=1, tope_porcentaje=D("5"), tope_monto=None))
        db_session.commit()
        cliente = self._cliente_con_descuento(client, h_vendedor, h_admin, "porcentaje", "30")
        respuesta = _vender(
            client, h_vendedor, producto.id, cliente_id=cliente["id"],
            descuento={"origen": "manual", "tipo": "porcentaje", "valor": "20"},
        )
        assert respuesta.status_code == 422

    def test_sin_cliente_o_sin_descuento_propio_es_422(self, client, db_session, producto, h_vendedor):
        sin_cliente = _vender(client, h_vendedor, producto.id, descuento={"origen": "cliente"})
        assert sin_cliente.status_code == 422
        cliente = _crear_cliente(client, h_vendedor)
        sin_descuento = _vender(client, h_vendedor, producto.id, cliente_id=cliente["id"], descuento={"origen": "cliente"})
        assert sin_descuento.status_code == 422
        db_session.refresh(producto)
        assert producto.stock_actual == 50


# ---------------------------------------------------------------------------
# Solicitudes de titulares (Habeas Data)
# ---------------------------------------------------------------------------


class TestSolicitudesDeTitulares:
    """HU-07: "el administrador pueda registrar solicitudes de consulta, actualizacion, supresion y
    revocatoria con su fecha limite legal; que al resolver una supresion los datos personales queden
    anonimizados y las ventas se conserven; y que el vendedor reciba 403"."""

    def _solicitar(self, client, h_admin, cliente_id, tipo, descripcion=None):
        respuesta = client.post(
            "/solicitudes-titular", json={"cliente_id": cliente_id, "tipo": tipo, "descripcion": descripcion}, headers=h_admin
        )
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    def test_vendedor_recibe_403_en_todo(self, client, h_vendedor):
        assert client.get("/solicitudes-titular", headers=h_vendedor).status_code == 403
        assert client.post("/solicitudes-titular", json={"cliente_id": 1, "tipo": "consulta"}, headers=h_vendedor).status_code == 403
        assert client.patch("/solicitudes-titular/1", json={"estado": "en_tramite"}, headers=h_vendedor).status_code == 403

    def test_registra_con_fecha_limite_y_estado_recibida(self, client, h_vendedor, h_admin):
        cliente = _crear_cliente(client, h_vendedor)
        consulta = self._solicitar(client, h_admin, cliente["id"], "consulta", "Quiere saber qué datos tenemos")
        reclamo = self._solicitar(client, h_admin, cliente["id"], "actualizacion")

        assert consulta["estado"] == "recibida"
        assert consulta["cliente_nombre"] == cliente["nombre"]
        assert consulta["vencida"] is False
        hoy = datetime.now().date()
        assert date.fromisoformat(consulta["fecha_limite"]) > hoy
        # El reclamo tiene un plazo mayor que la consulta.
        assert date.fromisoformat(reclamo["fecha_limite"]) > date.fromisoformat(consulta["fecha_limite"])

    def test_cliente_inexistente_404(self, client, h_admin):
        assert client.post("/solicitudes-titular", json={"cliente_id": 999, "tipo": "consulta"}, headers=h_admin).status_code == 404

    def test_resolver_y_rechazar_exigen_respuesta(self, client, h_vendedor, h_admin):
        cliente = _crear_cliente(client, h_vendedor)
        solicitud = self._solicitar(client, h_admin, cliente["id"], "consulta")
        assert client.patch(f"/solicitudes-titular/{solicitud['id']}", json={"estado": "resuelta"}, headers=h_admin).status_code == 422
        assert client.patch(f"/solicitudes-titular/{solicitud['id']}", json={"estado": "recibida"}, headers=h_admin).status_code == 422

    def test_flujo_normal_y_cierre_definitivo(self, client, usuario_administrador, h_vendedor, h_admin):
        cliente = _crear_cliente(client, h_vendedor)
        solicitud = self._solicitar(client, h_admin, cliente["id"], "consulta")
        url = f"/solicitudes-titular/{solicitud['id']}"

        en_tramite = client.patch(url, json={"estado": "en_tramite"}, headers=h_admin).json()
        assert en_tramite["estado"] == "en_tramite"
        assert en_tramite["resuelta_en"] is None

        resuelta = client.patch(url, json={"estado": "resuelta", "respuesta": "Se le envió su información."}, headers=h_admin).json()
        assert resuelta["estado"] == "resuelta"
        assert resuelta["resuelta_en"] is not None
        assert resuelta["atendida_por"] == usuario_administrador.nombre
        assert resuelta["respuesta"] == "Se le envió su información."

        assert client.patch(url, json={"estado": "en_tramite"}, headers=h_admin).status_code == 409

    def test_listado_y_filtros(self, client, h_vendedor, h_admin):
        cliente = _crear_cliente(client, h_vendedor)
        a = self._solicitar(client, h_admin, cliente["id"], "actualizacion")
        b = self._solicitar(client, h_admin, cliente["id"], "consulta")
        client.patch(f"/solicitudes-titular/{b['id']}", json={"estado": "resuelta", "respuesta": "ok"}, headers=h_admin)

        pendientes = client.get("/solicitudes-titular", params={"pendientes": True}, headers=h_admin).json()
        assert [s["id"] for s in pendientes] == [a["id"]]
        resueltas = client.get("/solicitudes-titular", params={"estado": "resuelta"}, headers=h_admin).json()
        assert [s["id"] for s in resueltas] == [b["id"]]
        del_cliente = client.get("/solicitudes-titular", params={"cliente_id": cliente["id"]}, headers=h_admin).json()
        assert len(del_cliente) == 2

    def test_una_solicitud_vencida_se_marca(self, client, db_session, h_vendedor, h_admin):
        from app.models.cliente import SolicitudTitular

        cliente = _crear_cliente(client, h_vendedor)
        solicitud = self._solicitar(client, h_admin, cliente["id"], "consulta")
        db_session.get(SolicitudTitular, solicitud["id"]).fecha_limite = _hoy_en_bogota() - timedelta(days=3)
        db_session.commit()
        assert client.get("/solicitudes-titular", headers=h_admin).json()[0]["vencida"] is True

    def test_supresion_anonimiza_y_conserva_las_ventas(
        self, client, db_session, categoria_prueba, h_vendedor, h_admin
    ):
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata", "20000.00", 10)
        cliente = _crear_cliente(client, h_vendedor)
        client.put(f"/clientes/{cliente['id']}/descuento", json={"tipo": "porcentaje", "valor": "10"}, headers=h_admin)
        venta = _vender(client, h_vendedor, producto.id, pagos=pagos_en_efectivo("20000"), cliente_id=cliente["id"]).json()

        solicitud = self._solicitar(client, h_admin, cliente["id"], "supresion", descripcion="Soy Ana, mi cel es 3001234567")
        url = f"/solicitudes-titular/{solicitud['id']}"
        # Mientras solo esta en tramite, los datos siguen intactos.
        client.patch(url, json={"estado": "en_tramite"}, headers=h_admin)
        assert db_session.get(Cliente, cliente["id"]).anonimizado_en is None

        client.patch(url, json={"estado": "resuelta", "respuesta": "Datos suprimidos."}, headers=h_admin)
        db_session.expire_all()
        anonimo = db_session.get(Cliente, cliente["id"])
        # La descripcion libre de sus solicitudes se borra; el resto de la solicitud se conserva.
        solicitudes = client.get("/solicitudes-titular", headers=h_admin).json()
        assert [s["descripcion"] for s in solicitudes] == [None]
        assert solicitudes[0]["tipo"] == "supresion" and solicitudes[0]["estado"] == "resuelta"
        assert anonimo.nombre == NOMBRE_ANONIMIZADO
        assert (anonimo.documento, anonimo.telefono, anonimo.email) == (None, None, None)
        assert (anonimo.descuento_tipo, anonimo.descuento_valor) == (None, None)
        assert anonimo.anonimizado_en is not None
        assert anonimo.activo is False
        assert anonimo.autorizacion_revocada_en is not None
        assert anonimo.utilizable is False

        # La venta se conserva, asociada al cliente anonimizado.
        db_session.refresh(db_session.get(Venta, venta["id"]))
        assert db_session.get(Venta, venta["id"]).cliente_id == cliente["id"]
        ficha = client.get(f"/clientes/{cliente['id']}", headers=h_vendedor).json()
        assert ficha["nombre"] == NOMBRE_ANONIMIZADO
        assert ficha["numero_ventas"] == 1

        # Ya no se puede editar, ni asignar descuento, ni abrir nuevas solicitudes, ni vender.
        assert client.patch(f"/clientes/{cliente['id']}", json={"nombre": "Otra vez"}, headers=h_vendedor).status_code == 409
        assert client.put(f"/clientes/{cliente['id']}/descuento", json={"tipo": "monto", "valor": "5"}, headers=h_admin).status_code == 409
        assert client.post("/solicitudes-titular", json={"cliente_id": cliente["id"], "tipo": "consulta"}, headers=h_admin).status_code == 409
        assert _vender(client, h_vendedor, producto.id, pagos=pagos_en_efectivo("20000"), cliente_id=cliente["id"]).status_code == 422

    def test_supresion_rechazada_no_toca_los_datos(self, client, db_session, h_vendedor, h_admin):
        cliente = _crear_cliente(client, h_vendedor)
        solicitud = self._solicitar(client, h_admin, cliente["id"], "supresion")
        client.patch(
            f"/solicitudes-titular/{solicitud['id']}",
            json={"estado": "rechazada", "respuesta": "Tiene una obligación contable pendiente."},
            headers=h_admin,
        )
        db_session.expire_all()
        assert db_session.get(Cliente, cliente["id"]).nombre == cliente["nombre"]
        assert db_session.get(Cliente, cliente["id"]).anonimizado_en is None

    def test_revocatoria_bloquea_el_uso_en_ventas_nuevas(self, client, db_session, categoria_prueba, h_vendedor, h_admin):
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata", "20000.00", 10)
        cliente = _crear_cliente(client, h_vendedor)
        solicitud = self._solicitar(client, h_admin, cliente["id"], "revocatoria")
        client.patch(
            f"/solicitudes-titular/{solicitud['id']}", json={"estado": "resuelta", "respuesta": "Revocada."}, headers=h_admin
        )
        db_session.expire_all()
        revocado = db_session.get(Cliente, cliente["id"])
        assert revocado.autorizacion_revocada_en is not None
        assert revocado.anonimizado_en is None
        assert revocado.nombre == cliente["nombre"]  # revocar no borra los datos
        assert _vender(client, h_vendedor, producto.id, pagos=pagos_en_efectivo("20000"), cliente_id=cliente["id"]).status_code == 422
        assert cliente["nombre"] not in [c["nombre"] for c in client.get("/clientes", params={"solo_utilizables": True}, headers=h_vendedor).json()]


# ---------------------------------------------------------------------------
# HU-08: vendedor por venta
# ---------------------------------------------------------------------------


class TestVendedorPorVenta:
    """HU-08: el desplegable lista a los vendedores y administradores activos; la venta queda a nombre
    del elegido; los inactivos y el propietario no aparecen y el servidor rechaza un usuario invalido."""

    @pytest.fixture
    def producto(self, db_session, categoria_prueba):
        return _crear_producto(db_session, categoria_prueba.id, "Piñata", "20000.00", 50)

    def test_lista_solo_vendedores_y_administradores_activos(
        self, client, db_session, usuario_vendedor, usuario_administrador, usuario_propietario, h_vendedor
    ):
        inactivo = _crear_usuario(db_session, "inactivo.prueba", RolUsuario.VENDEDOR)
        inactivo.activo = False
        db_session.commit()

        respuesta = client.get("/ventas/vendedores", headers=h_vendedor)
        assert respuesta.status_code == 200
        ids = {u["id"] for u in respuesta.json()}
        assert ids == {usuario_vendedor.id, usuario_administrador.id}
        assert set(respuesta.json()[0]) == {"id", "nombre"}  # nada de usernames ni hashes

    def test_el_propietario_no_accede_a_la_lista(self, client, usuario_propietario):
        assert client.get("/ventas/vendedores", headers=_auth(client, usuario_propietario)).status_code == 403

    def test_por_defecto_la_venta_es_del_usuario_de_la_sesion(self, client, producto, usuario_vendedor, h_vendedor):
        venta = _vender(client, h_vendedor, producto.id, pagos=pagos_en_efectivo("20000")).json()
        assert venta["usuario_id"] == usuario_vendedor.id

    def test_la_venta_queda_a_nombre_del_vendedor_elegido(
        self, client, db_session, producto, usuario_vendedor, usuario_administrador, h_vendedor
    ):
        venta = _vender(
            client, h_vendedor, producto.id, pagos=pagos_en_efectivo("20000"), vendedor_id=usuario_administrador.id
        ).json()
        assert venta["usuario_id"] == usuario_administrador.id
        assert db_session.get(Venta, venta["id"]).usuario_id == usuario_administrador.id

        # Cambiarlo en una venta no afecta a las demas (se asigna por venta).
        otra = _vender(client, h_vendedor, producto.id, pagos=pagos_en_efectivo("20000")).json()
        assert otra["usuario_id"] == usuario_vendedor.id

    def test_el_historial_y_el_ticket_muestran_al_vendedor_elegido(
        self, client, producto, usuario_administrador, h_admin, usuario_vendedor, h_vendedor
    ):
        _vender(client, h_vendedor, producto.id, pagos=pagos_en_efectivo("20000"), vendedor_id=usuario_administrador.id)
        ventas = client.get("/ventas/hoy", headers=h_admin).json()["ventas"]
        assert [v["vendedor"] for v in ventas] == [usuario_administrador.nombre]

    def test_el_vendedor_ve_en_su_historial_lo_que_registro_a_nombre_de_otro(
        self, client, db_session, producto, usuario_vendedor, usuario_administrador, h_vendedor, h_admin
    ):
        """Decision del 13-10-2026: el vendedor tambien ve lo que registro a nombre de otra persona."""
        a_nombre_de_otro = _vender(
            client, h_vendedor, producto.id, pagos=pagos_en_efectivo("20000"), vendedor_id=usuario_administrador.id
        ).json()
        propia = _vender(client, h_vendedor, producto.id, pagos=pagos_en_efectivo("20000")).json()
        # Una venta que el administrador registro a nombre del vendedor tambien le pertenece.
        del_admin = _vender(
            client, h_admin, producto.id, pagos=pagos_en_efectivo("20000"), vendedor_id=usuario_vendedor.id
        ).json()
        # Una venta ajena: ni la registro ni quedo a su nombre.
        ajena = _vender(client, h_admin, producto.id, pagos=pagos_en_efectivo("20000")).json()

        ventas = client.get("/ventas/hoy", headers=h_vendedor).json()["ventas"]
        por_id = {v["id"]: v for v in ventas}
        assert set(por_id) == {a_nombre_de_otro["id"], propia["id"], del_admin["id"]}
        assert ajena["id"] not in por_id
        # Solo se avisa quien la registro cuando es una persona distinta del vendedor.
        assert por_id[a_nombre_de_otro["id"]]["vendedor"] == usuario_administrador.nombre
        assert por_id[a_nombre_de_otro["id"]]["registrada_por"] == usuario_vendedor.nombre
        assert por_id[propia["id"]]["registrada_por"] is None
        assert por_id[del_admin["id"]]["registrada_por"] == usuario_administrador.nombre

        # El administrador sigue viendo todas.
        assert len(client.get("/ventas/hoy", headers=h_admin).json()["ventas"]) == 4
        assert db_session.get(Venta, propia["id"]).registrada_por_id == usuario_vendedor.id

    def test_otro_vendedor_no_ve_ventas_que_no_son_suyas(
        self, client, db_session, producto, usuario_administrador, h_vendedor
    ):
        segundo = _crear_usuario(db_session, "segundo.vendedor", RolUsuario.VENDEDOR)
        h_segundo = _auth(client, segundo)
        _vender(client, h_vendedor, producto.id, pagos=pagos_en_efectivo("20000"), vendedor_id=usuario_administrador.id)
        assert client.get("/ventas/hoy", headers=h_segundo).json()["cantidad_ventas"] == 0

    def test_el_servidor_rechaza_usuarios_invalidos(
        self, client, db_session, producto, usuario_propietario, h_vendedor
    ):
        inactivo = _crear_usuario(db_session, "inactivo.prueba", RolUsuario.VENDEDOR)
        inactivo.activo = False
        db_session.commit()

        for vendedor_id in (usuario_propietario.id, inactivo.id, 9999):
            respuesta = _vender(client, h_vendedor, producto.id, pagos=pagos_en_efectivo("20000"), vendedor_id=vendedor_id)
            assert respuesta.status_code == 422, vendedor_id
        db_session.refresh(producto)
        assert producto.stock_actual == 50
