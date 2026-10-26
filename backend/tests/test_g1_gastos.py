"""Pruebas de aceptacion de HU-12 (gastos del negocio) — Adendo v3, Fase G1 (RF-059 a RF-066, RF-068, RF-075).

Cada clase cita, en su docstring, el criterio de `docs/02-historias-de-usuario.md` (seccion 3.12) que cubre.
Las pruebas de ganancia neta y de caja son de las Fases G3 y G2.
"""

import csv
import io
from datetime import timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.categoria_gasto import CategoriaGasto
from app.models.compra import Compra, EstadoCompra
from app.models.proveedor import Proveedor
from app.services.gastos import hoy_en_bogota
from tests.conftest import obtener_token
from tests.test_hu01_venta import _crear_producto

D = Decimal


def _auth(client: TestClient, usuario) -> dict[str, str]:
    """Devuelve el header Authorization para el usuario dado."""
    return {"Authorization": f"Bearer {obtener_token(client, usuario.username)}"}


def _categoria(db_session: Session, nombre: str, *, sistema: bool = False, activa: bool = True) -> CategoriaGasto:
    """Crea una categoria de gasto (las pruebas no cargan la siembra de la migracion 0009)."""
    categoria = CategoriaGasto(nombre=nombre, es_sistema=sistema, activa=activa)
    db_session.add(categoria)
    db_session.commit()
    return categoria


@pytest.fixture
def cat_sistema(db_session: Session) -> CategoriaGasto:
    """La categoria de sistema "Compra de mercancía"."""
    return _categoria(db_session, "Compra de mercancía", sistema=True)


@pytest.fixture
def cat_arriendo(db_session: Session) -> CategoriaGasto:
    """Una categoria editable activa."""
    return _categoria(db_session, "Arriendo")


@pytest.fixture
def cat_servicios(db_session: Session) -> CategoriaGasto:
    """Otra categoria editable activa."""
    return _categoria(db_session, "Servicios públicos")


@pytest.fixture
def otro_vendedor(db_session: Session):
    """Un segundo vendedor, para probar el filtro por duenio."""
    from tests.conftest import _crear_usuario
    from app.models.usuario import RolUsuario

    return _crear_usuario(db_session, "vendedor.otro", RolUsuario.VENDEDOR)


def _gasto(categoria_id: int, monto: str = "20000", metodo: str = "efectivo", **extra) -> dict:
    """Cuerpo de `POST /gastos` con valores validos por defecto."""
    cuerpo = {"categoria_id": categoria_id, "descripcion": "Pago del mes", "monto": monto, "metodo_pago": metodo}
    cuerpo.update(extra)
    return cuerpo


def _registrar(client, headers, categoria_id, monto="20000", metodo="efectivo", **extra) -> dict:
    """Registra un gasto y devuelve el JSON; falla si el servidor no responde 201."""
    respuesta = client.post("/gastos", json=_gasto(categoria_id, monto, metodo, **extra), headers=headers)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _hoy() -> str:
    """Hoy en la zona del negocio, en ISO."""
    return hoy_en_bogota().isoformat()


def _ids(respuesta) -> list[tuple[str, int]]:
    """(origen, id) de cada fila de una respuesta de lista."""
    assert respuesta.status_code == 200, respuesta.text
    return [(f["origen"], f["id"]) for f in respuesta.json()]


def _compra_recibida(client, db_session, headers, categoria_prueba, total_costo="1000", cantidad=10, pago=None):
    """Crea una compra, la recibe por la API con la forma de pago dada y devuelve su JSON."""
    proveedor = Proveedor(nombre_empresa="Papeles del valle sas")
    db_session.add(proveedor)
    db_session.commit()
    producto = _crear_producto(db_session, categoria_prueba.id, f"Papel {total_costo}-{cantidad}", "5000", 0)
    compra = client.post(
        "/compras",
        json={
            "proveedor_id": proveedor.id,
            "detalles": [{"producto_id": producto.id, "cantidad": cantidad, "costo_unitario": total_costo}],
        },
        headers=headers,
    ).json()
    recibida = client.patch(f"/compras/{compra['id']}/recibir", json=pago or {"metodo_pago": "efectivo"}, headers=headers)
    assert recibida.status_code == 200, recibida.text
    return recibida.json()


class TestAcceso:
    """HU-12: "el propietario solo pueda consultar (registrar, editar y anular responden 403)"; el vendedor no ve totales."""

    def test_propietario_consulta_pero_no_escribe(
        self, client, usuario_administrador, usuario_propietario, cat_arriendo
    ):
        gasto = _registrar(client, _auth(client, usuario_administrador), cat_arriendo.id)
        h = _auth(client, usuario_propietario)

        assert client.get("/gastos", headers=h).status_code == 200
        assert client.get(f"/gastos/{gasto['id']}", headers=h).status_code == 200
        assert client.get("/gastos/resumen", headers=h).status_code == 200
        assert client.get("/categorias-gasto", headers=h).status_code == 200
        assert client.post("/gastos", json=_gasto(cat_arriendo.id), headers=h).status_code == 403
        assert client.patch(f"/gastos/{gasto['id']}", json={"descripcion": "Otro"}, headers=h).status_code == 403
        assert client.post(f"/gastos/{gasto['id']}/anular", json={"motivo": "Prueba"}, headers=h).status_code == 403

    def test_vendedor_no_ve_totales_ni_exporta_ni_administra_categorias(
        self, client, usuario_vendedor, cat_arriendo
    ):
        h = _auth(client, usuario_vendedor)

        assert client.get("/gastos/resumen", headers=h).status_code == 403
        assert client.get("/gastos/exportar", headers=h).status_code == 403
        assert client.post("/categorias-gasto", json={"nombre": "Nueva"}, headers=h).status_code == 403
        assert client.patch(f"/categorias-gasto/{cat_arriendo.id}", json={"activa": False}, headers=h).status_code == 403

    def test_sin_token_401(self, client):
        for metodo, ruta in (("GET", "/gastos"), ("POST", "/gastos"), ("GET", "/categorias-gasto"), ("GET", "/gastos/resumen")):
            assert client.request(metodo, ruta).status_code == 401


class TestRegistrarGasto:
    """HU-12: "registrar un gasto con categoría, descripción, monto, forma de pago (con Nequi o Daviplata si es
    transferencia), fecha y beneficiario opcional, y que un gasto en efectivo exija un múltiplo de $50"."""

    @pytest.mark.parametrize("rol", ["usuario_administrador", "usuario_vendedor"])
    def test_administrador_y_vendedor_registran(self, client, request, cat_arriendo, rol):
        usuario = request.getfixturevalue(rol)

        gasto = _registrar(
            client, _auth(client, usuario), cat_arriendo.id, "150000", "efectivo", beneficiario="Doña maria"
        )

        assert gasto["origen"] == "gasto"
        assert gasto["categoria"] == "Arriendo"
        assert D(gasto["monto"]) == D("150000")
        assert gasto["fecha"] == _hoy()
        assert gasto["registrado_por_id"] == usuario.id
        assert gasto["beneficiario"] == "Doña maria"
        assert gasto["anulado"] is False and gasto["editable"] is True

    def test_efectivo_exige_multiplo_de_50(self, client, usuario_vendedor, cat_arriendo):
        h = _auth(client, usuario_vendedor)

        assert client.post("/gastos", json=_gasto(cat_arriendo.id, "20025"), headers=h).status_code == 422
        assert client.post("/gastos", json=_gasto(cat_arriendo.id, "20050"), headers=h).status_code == 201
        # Con tarjeta no aplica el multiplo.
        assert client.post("/gastos", json=_gasto(cat_arriendo.id, "20025", "tarjeta"), headers=h).status_code == 201

    @pytest.mark.parametrize("monto", ["0", "-50", "1000.50"])
    def test_monto_en_pesos_enteros_y_positivo(self, client, usuario_administrador, cat_arriendo, monto):
        respuesta = client.post(
            "/gastos", json=_gasto(cat_arriendo.id, monto, "tarjeta"), headers=_auth(client, usuario_administrador)
        )

        assert respuesta.status_code == 422

    def test_transferencia_exige_plataforma_y_las_otras_no_la_admiten(self, client, usuario_vendedor, cat_arriendo):
        h = _auth(client, usuario_vendedor)

        assert client.post("/gastos", json=_gasto(cat_arriendo.id, metodo="transferencia"), headers=h).status_code == 422
        assert client.post(
            "/gastos", json=_gasto(cat_arriendo.id, metodo="efectivo", plataforma="nequi"), headers=h
        ).status_code == 422
        creado = client.post(
            "/gastos", json=_gasto(cat_arriendo.id, metodo="transferencia", plataforma="daviplata"), headers=h
        )
        assert creado.status_code == 201
        assert creado.json()["plataforma"] == "daviplata"

    def test_categoria_inexistente_404_y_desactivada_422(self, client, db_session, usuario_vendedor):
        h = _auth(client, usuario_vendedor)
        inactiva = _categoria(db_session, "Vieja", activa=False)

        assert client.post("/gastos", json=_gasto(9999), headers=h).status_code == 404
        assert client.post("/gastos", json=_gasto(inactiva.id), headers=h).status_code == 422

    def test_textos_quedan_con_la_primera_letra_en_mayuscula(self, client, usuario_administrador, cat_arriendo):
        gasto = _registrar(
            client,
            _auth(client, usuario_administrador),
            cat_arriendo.id,
            descripcion="  PAGO del LOCAL  ",
            beneficiario="inmobiliaria SANTA fe",
        )

        assert gasto["descripcion"] == "Pago del local"
        assert gasto["beneficiario"] == "Inmobiliaria santa fe"

    def test_beneficiario_vacio_se_guarda_como_nulo(self, client, usuario_administrador, cat_arriendo):
        gasto = _registrar(client, _auth(client, usuario_administrador), cat_arriendo.id, beneficiario="   ")

        assert gasto["beneficiario"] is None

    def test_vendedor_siempre_registra_con_la_fecha_de_hoy(self, client, usuario_vendedor, cat_arriendo):
        h = _auth(client, usuario_vendedor)
        ayer = (hoy_en_bogota() - timedelta(days=1)).isoformat()

        assert client.post("/gastos", json=_gasto(cat_arriendo.id, fecha=ayer), headers=h).status_code == 403
        assert client.post("/gastos", json=_gasto(cat_arriendo.id, fecha=_hoy()), headers=h).status_code == 201
        assert _registrar(client, h, cat_arriendo.id)["fecha"] == _hoy()

    def test_administrador_elige_una_fecha_anterior_pero_no_futura(self, client, usuario_administrador, cat_arriendo):
        h = _auth(client, usuario_administrador)
        hace_tres_dias = (hoy_en_bogota() - timedelta(days=3)).isoformat()
        manana = (hoy_en_bogota() + timedelta(days=1)).isoformat()

        assert _registrar(client, h, cat_arriendo.id, fecha=hace_tres_dias)["fecha"] == hace_tres_dias
        assert client.post("/gastos", json=_gasto(cat_arriendo.id, fecha=manana), headers=h).status_code == 422


class TestVendedorSoloTocaLoSuyo:
    """HU-12: "el vendedor solo vea, edite y anule los gastos que él registró (los de otras personas responden 404 o
    403 aunque conozca el id), que no vea totales, compras ni ganancias"."""

    def test_la_lista_del_vendedor_solo_trae_los_suyos(
        self, client, usuario_vendedor, otro_vendedor, usuario_administrador, cat_arriendo
    ):
        mio = _registrar(client, _auth(client, usuario_vendedor), cat_arriendo.id)
        ajeno = _registrar(client, _auth(client, otro_vendedor), cat_arriendo.id)
        del_admin = _registrar(client, _auth(client, usuario_administrador), cat_arriendo.id)

        vendedor = _ids(client.get("/gastos", headers=_auth(client, usuario_vendedor)))
        admin = _ids(client.get("/gastos", headers=_auth(client, usuario_administrador)))

        assert vendedor == [("gasto", mio["id"])]
        assert set(admin) == {("gasto", mio["id"]), ("gasto", ajeno["id"]), ("gasto", del_admin["id"])}

    def test_lo_ajeno_responde_404_en_leer_editar_y_anular(
        self, client, usuario_vendedor, otro_vendedor, cat_arriendo
    ):
        ajeno = _registrar(client, _auth(client, otro_vendedor), cat_arriendo.id)
        h = _auth(client, usuario_vendedor)

        assert client.get(f"/gastos/{ajeno['id']}", headers=h).status_code == 404
        assert client.patch(f"/gastos/{ajeno['id']}", json={"descripcion": "Robado"}, headers=h).status_code == 404
        assert client.post(f"/gastos/{ajeno['id']}/anular", json={"motivo": "No es mio"}, headers=h).status_code == 404
        # Y el gasto ajeno quedo intacto.
        intacto = client.get(f"/gastos/{ajeno['id']}", headers=_auth(client, otro_vendedor)).json()
        assert intacto["descripcion"] == "Pago del mes" and intacto["anulado"] is False

    def test_el_vendedor_edita_y_anula_lo_suyo(self, client, usuario_vendedor, cat_arriendo):
        h = _auth(client, usuario_vendedor)
        gasto = _registrar(client, h, cat_arriendo.id)

        editado = client.patch(f"/gastos/{gasto['id']}", json={"monto": "30000"}, headers=h)
        anulado = client.post(f"/gastos/{gasto['id']}/anular", json={"motivo": "Lo anoté dos veces"}, headers=h)

        assert editado.status_code == 200 and D(editado.json()["monto"]) == D("30000")
        assert anulado.status_code == 200 and anulado.json()["anulado"] is True

    def test_el_vendedor_no_cambia_la_fecha(self, client, usuario_vendedor, cat_arriendo):
        h = _auth(client, usuario_vendedor)
        gasto = _registrar(client, h, cat_arriendo.id)
        ayer = (hoy_en_bogota() - timedelta(days=1)).isoformat()

        assert client.patch(f"/gastos/{gasto['id']}", json={"fecha": ayer}, headers=h).status_code == 403

    def test_el_vendedor_no_ve_compras_ni_siquiera_filtrando(
        self, client, db_session, usuario_administrador, usuario_vendedor, categoria_prueba, cat_sistema
    ):
        compra = _compra_recibida(client, db_session, _auth(client, usuario_administrador), categoria_prueba)
        h = _auth(client, usuario_vendedor)

        assert _ids(client.get("/gastos", headers=h)) == []
        assert _ids(client.get("/gastos?origen=compra", headers=h)) == []
        assert client.get(f"/gastos/{compra['id']}", headers=h).status_code == 404

    def test_el_administrador_edita_y_anula_cualquiera(
        self, client, usuario_administrador, usuario_vendedor, cat_arriendo, cat_servicios
    ):
        gasto = _registrar(client, _auth(client, usuario_vendedor), cat_arriendo.id)
        h = _auth(client, usuario_administrador)

        editado = client.patch(f"/gastos/{gasto['id']}", json={"categoria_id": cat_servicios.id}, headers=h)
        anulado = client.post(f"/gastos/{gasto['id']}/anular", json={"motivo": "Duplicado"}, headers=h)

        assert editado.status_code == 200 and editado.json()["categoria"] == "Servicios públicos"
        assert anulado.status_code == 200


class TestEditarGasto:
    """HU-12 / RF-061: editar categoría, descripción, monto, forma de pago, beneficiario y (solo administrador) fecha;
    queda quién y cuándo lo editó."""

    def test_solo_cambian_los_campos_enviados_y_queda_quien_edito(
        self, client, usuario_administrador, usuario_vendedor, cat_arriendo
    ):
        gasto = _registrar(client, _auth(client, usuario_vendedor), cat_arriendo.id, beneficiario="Pedro")

        editado = client.patch(
            f"/gastos/{gasto['id']}", json={"descripcion": "pago atrasado"}, headers=_auth(client, usuario_administrador)
        ).json()

        assert editado["descripcion"] == "Pago atrasado"
        assert editado["beneficiario"] == "Pedro" and D(editado["monto"]) == D("20000")
        assert editado["actualizado_por"] == usuario_administrador.nombre
        assert editado["actualizado_en"] is not None
        assert editado["registrado_por_id"] == usuario_vendedor.id

    def test_beneficiario_se_puede_borrar_con_null(self, client, usuario_administrador, cat_arriendo):
        h = _auth(client, usuario_administrador)
        gasto = _registrar(client, h, cat_arriendo.id, beneficiario="Pedro")

        editado = client.patch(f"/gastos/{gasto['id']}", json={"beneficiario": None}, headers=h)

        assert editado.json()["beneficiario"] is None

    def test_cambiar_a_transferencia_exige_plataforma_y_dejarla_la_limpia(
        self, client, usuario_administrador, cat_arriendo
    ):
        h = _auth(client, usuario_administrador)
        gasto = _registrar(client, h, cat_arriendo.id)

        assert client.patch(f"/gastos/{gasto['id']}", json={"metodo_pago": "transferencia"}, headers=h).status_code == 422
        a_nequi = client.patch(
            f"/gastos/{gasto['id']}", json={"metodo_pago": "transferencia", "plataforma": "nequi"}, headers=h
        )
        assert a_nequi.status_code == 200 and a_nequi.json()["plataforma"] == "nequi"
        a_tarjeta = client.patch(f"/gastos/{gasto['id']}", json={"metodo_pago": "tarjeta"}, headers=h)
        assert a_tarjeta.status_code == 200 and a_tarjeta.json()["plataforma"] is None

    def test_cambiar_a_efectivo_revalida_el_multiplo_de_50(self, client, usuario_administrador, cat_arriendo):
        h = _auth(client, usuario_administrador)
        gasto = _registrar(client, h, cat_arriendo.id, "20025", "tarjeta")

        assert client.patch(f"/gastos/{gasto['id']}", json={"metodo_pago": "efectivo"}, headers=h).status_code == 422
        assert client.patch(
            f"/gastos/{gasto['id']}", json={"metodo_pago": "efectivo", "monto": "20050"}, headers=h
        ).status_code == 200

    def test_la_fecha_la_cambia_solo_el_administrador_y_no_a_futuro(
        self, client, usuario_administrador, cat_arriendo
    ):
        h = _auth(client, usuario_administrador)
        gasto = _registrar(client, h, cat_arriendo.id)
        anterior = (hoy_en_bogota() - timedelta(days=5)).isoformat()
        futura = (hoy_en_bogota() + timedelta(days=2)).isoformat()

        assert client.patch(f"/gastos/{gasto['id']}", json={"fecha": anterior}, headers=h).json()["fecha"] == anterior
        assert client.patch(f"/gastos/{gasto['id']}", json={"fecha": futura}, headers=h).status_code == 422

    def test_sin_cambios_422_y_a_una_categoria_desactivada_422(
        self, client, db_session, usuario_administrador, cat_arriendo
    ):
        h = _auth(client, usuario_administrador)
        gasto = _registrar(client, h, cat_arriendo.id)
        inactiva = _categoria(db_session, "Vieja", activa=False)

        assert client.patch(f"/gastos/{gasto['id']}", json={}, headers=h).status_code == 422
        assert client.patch(f"/gastos/{gasto['id']}", json={"categoria_id": inactiva.id}, headers=h).status_code == 422
        assert client.patch("/gastos/9999", json={"monto": "50"}, headers=h).status_code == 404


class TestAnularGasto:
    """HU-12: "anular exija un motivo, que el gasto siga visible tachado con quién, cuándo y por qué, que deje de sumar
    en los totales y que no se pueda borrar ni reactivar"."""

    def test_el_motivo_es_obligatorio(self, client, usuario_administrador, cat_arriendo):
        h = _auth(client, usuario_administrador)
        gasto = _registrar(client, h, cat_arriendo.id)

        assert client.post(f"/gastos/{gasto['id']}/anular", json={}, headers=h).status_code == 422
        assert client.post(f"/gastos/{gasto['id']}/anular", json={"motivo": "  "}, headers=h).status_code == 422
        assert client.get(f"/gastos/{gasto['id']}", headers=h).json()["anulado"] is False

    def test_queda_visible_con_quien_cuando_y_por_que_y_no_suma(self, client, usuario_administrador, cat_arriendo):
        h = _auth(client, usuario_administrador)
        quedan = _registrar(client, h, cat_arriendo.id, "10000")
        anulado = _registrar(client, h, cat_arriendo.id, "40000")

        respuesta = client.post(f"/gastos/{anulado['id']}/anular", json={"motivo": "monto mal digitado"}, headers=h)

        assert respuesta.status_code == 200
        fila = respuesta.json()
        assert fila["anulado"] is True and fila["editable"] is False
        assert fila["anulado_por"] == usuario_administrador.nombre
        assert fila["anulado_en"] is not None
        assert fila["motivo_anulacion"] == "Monto mal digitado"
        todos = client.get("/gastos", headers=h).json()
        assert {f["id"] for f in todos} == {quedan["id"], anulado["id"]}  # sigue en la lista
        assert client.get("/gastos?estado=vigente", headers=h).json()[0]["id"] == quedan["id"]
        resumen = client.get("/gastos/resumen", headers=h).json()
        assert D(resumen["total"]) == D("10000")  # y no suma
        assert resumen["por_categoria"][0]["cantidad"] == 1

    def test_no_se_anula_dos_veces_ni_se_edita_uno_anulado(self, client, usuario_administrador, cat_arriendo):
        h = _auth(client, usuario_administrador)
        gasto = _registrar(client, h, cat_arriendo.id)
        client.post(f"/gastos/{gasto['id']}/anular", json={"motivo": "Error"}, headers=h)

        assert client.post(f"/gastos/{gasto['id']}/anular", json={"motivo": "Otra vez"}, headers=h).status_code == 409
        assert client.patch(f"/gastos/{gasto['id']}", json={"monto": "50"}, headers=h).status_code == 409

    def test_no_existe_borrar(self, client, usuario_administrador, cat_arriendo):
        h = _auth(client, usuario_administrador)
        gasto = _registrar(client, h, cat_arriendo.id)

        assert client.delete(f"/gastos/{gasto['id']}", headers=h).status_code == 405
        assert client.get(f"/gastos/{gasto['id']}", headers=h).status_code == 200


class TestCategorias:
    """HU-12: "crear, renombrar y desactivar categorías, que 'Compra de mercancía' no se pueda modificar, que una
    categoría desactivada no se ofrezca para gastos nuevos pero conserve los antiguos y que los nombres queden con la
    primera letra en mayúscula"."""

    def test_el_administrador_crea_con_la_primera_letra_en_mayuscula(self, client, usuario_administrador):
        h = _auth(client, usuario_administrador)

        creada = client.post("/categorias-gasto", json={"nombre": "  gastos DE oficina "}, headers=h)

        assert creada.status_code == 201
        assert creada.json()["nombre"] == "Gastos de oficina"
        assert creada.json()["activa"] is True and creada.json()["es_sistema"] is False

    def test_nombre_repetido_sin_distinguir_mayusculas_409(self, client, usuario_administrador, cat_arriendo):
        h = _auth(client, usuario_administrador)

        assert client.post("/categorias-gasto", json={"nombre": "ARRIENDO"}, headers=h).status_code == 409
        otra = client.post("/categorias-gasto", json={"nombre": "Otra"}, headers=h).json()
        assert client.patch(f"/categorias-gasto/{otra['id']}", json={"nombre": "arriendo"}, headers=h).status_code == 409

    def test_renombrar_y_desactivar(self, client, usuario_administrador, cat_arriendo):
        h = _auth(client, usuario_administrador)

        renombrada = client.patch(f"/categorias-gasto/{cat_arriendo.id}", json={"nombre": "alquiler del local"}, headers=h)
        desactivada = client.patch(f"/categorias-gasto/{cat_arriendo.id}", json={"activa": False}, headers=h)

        assert renombrada.json()["nombre"] == "Alquiler del local"
        assert desactivada.json()["activa"] is False
        assert client.patch("/categorias-gasto/9999", json={"activa": False}, headers=h).status_code == 404

    def test_la_de_sistema_no_se_toca(self, client, usuario_administrador, cat_sistema):
        h = _auth(client, usuario_administrador)

        assert client.patch(f"/categorias-gasto/{cat_sistema.id}", json={"nombre": "Otro"}, headers=h).status_code == 409
        assert client.patch(f"/categorias-gasto/{cat_sistema.id}", json={"activa": False}, headers=h).status_code == 409

    def test_desactivada_no_se_ofrece_al_vendedor_pero_conserva_los_gastos_antiguos(
        self, client, usuario_administrador, usuario_vendedor, cat_arriendo, cat_servicios
    ):
        hv = _auth(client, usuario_vendedor)
        ha = _auth(client, usuario_administrador)
        antiguo = _registrar(client, hv, cat_arriendo.id)

        client.patch(f"/categorias-gasto/{cat_arriendo.id}", json={"activa": False}, headers=ha)

        nombres_vendedor = [c["nombre"] for c in client.get("/categorias-gasto", headers=hv).json()]
        nombres_admin = [c["nombre"] for c in client.get("/categorias-gasto", headers=ha).json()]
        assert nombres_vendedor == ["Servicios públicos"]
        assert set(nombres_admin) == {"Arriendo", "Servicios públicos"}
        assert client.post("/gastos", json=_gasto(cat_arriendo.id), headers=hv).status_code == 422
        conservado = client.get(f"/gastos/{antiguo['id']}", headers=hv).json()
        assert conservado["categoria"] == "Arriendo"

    def test_nombre_vacio_422(self, client, usuario_administrador):
        h = _auth(client, usuario_administrador)

        assert client.post("/categorias-gasto", json={"nombre": "   "}, headers=h).status_code == 422
        assert client.post("/categorias-gasto", json={"nombre": "x" * 61}, headers=h).status_code == 422


class TestComprasEnLaVentanaDeGastos:
    """HU-12: "al recibir una compra se pida su forma de pago y las compras recibidas aparezcan (solo para el
    administrador y el propietario) como filas de solo lectura de la categoría 'Compra de mercancía', con su fecha de
    recepción, sumando al total de gastos; las pendientes y las canceladas no"."""

    def test_recibir_pide_la_forma_de_pago(self, client, db_session, usuario_administrador, categoria_prueba):
        h = _auth(client, usuario_administrador)
        proveedor = Proveedor(nombre_empresa="Proveedor sas")
        db_session.add(proveedor)
        db_session.commit()
        producto = _crear_producto(db_session, categoria_prueba.id, "Papel", "5000", 0)
        compra = client.post(
            "/compras",
            json={"proveedor_id": proveedor.id, "detalles": [{"producto_id": producto.id, "cantidad": 2, "costo_unitario": "100"}]},
            headers=h,
        ).json()

        assert client.patch(f"/compras/{compra['id']}/recibir", headers=h).status_code == 422
        assert client.patch(
            f"/compras/{compra['id']}/recibir", json={"metodo_pago": "transferencia"}, headers=h
        ).status_code == 422
        assert client.patch(
            f"/compras/{compra['id']}/recibir", json={"metodo_pago": "efectivo", "plataforma": "nequi"}, headers=h
        ).status_code == 422
        # Una validacion fallida no recibe la compra ni mueve stock.
        assert client.get(f"/compras/{compra['id']}", headers=h).json()["estado"] == "pendiente"

        recibida = client.patch(
            f"/compras/{compra['id']}/recibir",
            json={"metodo_pago": "transferencia", "plataforma": "nequi"},
            headers=h,
        ).json()
        assert recibida["estado"] == "recibida"
        assert recibida["metodo_pago"] == "transferencia" and recibida["plataforma"] == "nequi"
        assert recibida["recibida_en"] is not None

    def test_la_compra_recibida_aparece_como_fila_de_solo_lectura(
        self, client, db_session, usuario_administrador, usuario_propietario, categoria_prueba, cat_sistema
    ):
        ha = _auth(client, usuario_administrador)
        compra = _compra_recibida(client, db_session, ha, categoria_prueba, "1000", 10, {"metodo_pago": "tarjeta"})

        for headers in (ha, _auth(client, usuario_propietario)):
            filas = client.get("/gastos", headers=headers).json()
            assert len(filas) == 1
            fila = filas[0]
            assert fila["origen"] == "compra" and fila["id"] == compra["id"]
            assert fila["categoria"] == "Compra de mercancía" and fila["categoria_id"] == cat_sistema.id
            assert D(fila["monto"]) == D("10000")
            assert fila["metodo_pago"] == "tarjeta"
            assert fila["fecha"] == _hoy()
            assert fila["editable"] is False and fila["anulado"] is False
            assert "Compra #" in fila["descripcion"] and "Papeles del valle sas" in fila["descripcion"]

    def test_las_compras_no_se_editan_ni_se_anulan_desde_gastos(
        self, client, db_session, usuario_administrador, categoria_prueba, cat_sistema
    ):
        h = _auth(client, usuario_administrador)
        compra = _compra_recibida(client, db_session, h, categoria_prueba)

        assert client.patch(f"/gastos/{compra['id']}", json={"monto": "50"}, headers=h).status_code == 404
        assert client.post(f"/gastos/{compra['id']}/anular", json={"motivo": "Motivo cualquiera"}, headers=h).status_code == 404

    def test_pendientes_y_canceladas_no_cuentan(
        self, client, db_session, usuario_administrador, categoria_prueba, cat_sistema
    ):
        h = _auth(client, usuario_administrador)
        proveedor = Proveedor(nombre_empresa="Proveedor sas")
        db_session.add(proveedor)
        db_session.commit()
        for estado in (EstadoCompra.PENDIENTE, EstadoCompra.CANCELADA):
            db_session.add(Compra(proveedor_id=proveedor.id, usuario_id=usuario_administrador.id, estado=estado, total=D("9000")))
        db_session.commit()

        assert client.get("/gastos", headers=h).json() == []
        assert D(client.get("/gastos/resumen", headers=h).json()["total"]) == 0

    def test_compra_anterior_sin_forma_de_pago_suma_en_los_gastos(
        self, client, db_session, usuario_administrador, cat_sistema
    ):
        h = _auth(client, usuario_administrador)
        proveedor = Proveedor(nombre_empresa="Proveedor sas")
        db_session.add(proveedor)
        db_session.commit()
        db_session.add(
            Compra(proveedor_id=proveedor.id, usuario_id=usuario_administrador.id, estado=EstadoCompra.RECIBIDA, total=D("9000"))
        )
        db_session.commit()

        fila = client.get("/gastos", headers=h).json()[0]
        resumen = client.get("/gastos/resumen", headers=h).json()

        assert fila["metodo_pago"] is None and fila["origen"] == "compra"
        assert D(resumen["total"]) == D("9000")
        assert resumen["por_metodo_pago"] == [{"metodo_pago": None, "total": "9000.00"}]


class TestFiltrosYTotales:
    """HU-12: "validar los filtros por rango, categoría, forma de pago y estado, y los totales por categoría y por forma
    de pago"."""

    def _datos(self, client, h, cat_arriendo, cat_servicios):
        hace_diez = (hoy_en_bogota() - timedelta(days=10)).isoformat()
        return {
            "arriendo": _registrar(client, h, cat_arriendo.id, "100000", "transferencia", plataforma="nequi"),
            "luz": _registrar(client, h, cat_servicios.id, "30050", "tarjeta"),
            "agua": _registrar(client, h, cat_servicios.id, "20000", "efectivo"),
            "viejo": _registrar(client, h, cat_servicios.id, "5000", "efectivo", fecha=hace_diez),
        }

    def test_filtra_por_rango_categoria_y_forma_de_pago(
        self, client, usuario_administrador, cat_arriendo, cat_servicios
    ):
        h = _auth(client, usuario_administrador)
        g = self._datos(client, h, cat_arriendo, cat_servicios)
        todos = {("gasto", x["id"]) for x in g.values()}

        assert set(_ids(client.get("/gastos", headers=h))) == todos - {("gasto", g["viejo"]["id"])}  # solo hoy
        desde = (hoy_en_bogota() - timedelta(days=30)).isoformat()
        assert set(_ids(client.get(f"/gastos?desde={desde}", headers=h))) == todos
        assert set(_ids(client.get(f"/gastos?desde={desde}&categoria_id={cat_servicios.id}", headers=h))) == {
            ("gasto", g["luz"]["id"]),
            ("gasto", g["agua"]["id"]),
            ("gasto", g["viejo"]["id"]),
        }
        assert _ids(client.get("/gastos?metodo_pago=transferencia", headers=h)) == [("gasto", g["arriendo"]["id"])]

    def test_filtra_por_estado(self, client, usuario_administrador, cat_arriendo, cat_servicios):
        h = _auth(client, usuario_administrador)
        g = self._datos(client, h, cat_arriendo, cat_servicios)
        client.post(f"/gastos/{g['agua']['id']}/anular", json={"motivo": "Error"}, headers=h)

        assert _ids(client.get("/gastos?estado=anulado", headers=h)) == [("gasto", g["agua"]["id"])]
        assert ("gasto", g["agua"]["id"]) not in _ids(client.get("/gastos?estado=vigente", headers=h))
        assert ("gasto", g["agua"]["id"]) in _ids(client.get("/gastos", headers=h))

    def test_totales_por_categoria_y_por_forma_de_pago(
        self, client, db_session, usuario_administrador, categoria_prueba, cat_sistema, cat_arriendo, cat_servicios
    ):
        h = _auth(client, usuario_administrador)
        self._datos(client, h, cat_arriendo, cat_servicios)
        _compra_recibida(client, db_session, h, categoria_prueba, "1000", 10, {"metodo_pago": "efectivo"})
        desde = (hoy_en_bogota() - timedelta(days=30)).isoformat()

        resumen = client.get(f"/gastos/resumen?desde={desde}", headers=h).json()

        assert D(resumen["total"]) == D("165050")  # 100000 + 30050 + 20000 + 5000 + 10000 de la compra
        assert D(resumen["total_compras"]) == D("10000")
        assert D(resumen["total_operativo"]) == D("155050")
        por_categoria = {c["categoria"]: (c["cantidad"], D(c["total"])) for c in resumen["por_categoria"]}
        assert por_categoria == {
            "Arriendo": (1, D("100000")),
            "Servicios públicos": (3, D("55050")),
            "Compra de mercancía": (1, D("10000")),
        }
        por_metodo = {m["metodo_pago"]: D(m["total"]) for m in resumen["por_metodo_pago"]}
        assert por_metodo == {"transferencia": D("100000"), "tarjeta": D("30050"), "efectivo": D("35000")}
        assert [c["categoria"] for c in resumen["por_categoria"]][0] == "Arriendo"  # de mayor a menor

    def test_los_gastos_manuales_de_la_categoria_de_sistema_no_son_operativos(
        self, client, usuario_administrador, cat_sistema, cat_arriendo
    ):
        h = _auth(client, usuario_administrador)
        _registrar(client, h, cat_sistema.id, "10000")
        _registrar(client, h, cat_arriendo.id, "4000")

        resumen = client.get("/gastos/resumen", headers=h).json()

        assert D(resumen["total_compras"]) == D("10000") and D(resumen["total_operativo"]) == D("4000")

    def test_pagina_y_ordena_de_lo_mas_reciente_a_lo_mas_antiguo(
        self, client, usuario_administrador, cat_arriendo
    ):
        h = _auth(client, usuario_administrador)
        ids = [_registrar(client, h, cat_arriendo.id, str(50 * (n + 1)))["id"] for n in range(5)]

        primera = [f["id"] for f in client.get("/gastos?tamano_pagina=2&pagina=1", headers=h).json()]
        tercera = [f["id"] for f in client.get("/gastos?tamano_pagina=2&pagina=3", headers=h).json()]

        assert primera == [ids[4], ids[3]]
        assert tercera == [ids[0]]
        assert client.get("/gastos?tamano_pagina=500", headers=h).status_code == 422

    def test_rango_invalido_422(self, client, usuario_administrador):
        h = _auth(client, usuario_administrador)
        manana = (hoy_en_bogota() + timedelta(days=1)).isoformat()

        assert client.get(f"/gastos?hasta={manana}", headers=h).status_code == 422
        assert client.get(f"/gastos?desde={_hoy()}&hasta=2020-01-01", headers=h).status_code == 422
        assert client.get("/gastos/resumen?desde=2020-01-01", headers=h).status_code == 422


class TestExportarCSV:
    """HU-12: "Exportar genere un CSV (UTF-8 con BOM, punto y coma) con las mismas filas y filtros ... y que lo puedan
    hacer el administrador y el propietario pero no el vendedor"."""

    def _leer(self, respuesta) -> list[list[str]]:
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.content.startswith(b"\xef\xbb\xbf")  # BOM
        return list(csv.reader(io.StringIO(respuesta.content.decode("utf-8-sig")), delimiter=";"))

    def test_administrador_y_propietario_exportan_con_bom_y_punto_y_coma(
        self, client, db_session, usuario_administrador, usuario_propietario, usuario_vendedor,
        categoria_prueba, cat_sistema, cat_servicios
    ):
        ha = _auth(client, usuario_administrador)
        _registrar(client, ha, cat_servicios.id, "30050", "tarjeta", descripcion="Factura de luz", beneficiario="Epm")
        _compra_recibida(client, db_session, ha, categoria_prueba, "1000", 10, {"metodo_pago": "transferencia", "plataforma": "daviplata"})

        for usuario in (usuario_administrador, usuario_propietario):
            respuesta = client.get("/gastos/exportar", headers=_auth(client, usuario))
            filas = self._leer(respuesta)
            assert respuesta.headers["content-type"] == "text/csv; charset=utf-8"
            assert f'filename="gastos_{_hoy()}_a_{_hoy()}.csv"' in respuesta.headers["content-disposition"]
            assert filas[0][:3] == ["Fecha", "Origen", "Categoría"]
            assert len(filas) == 3  # encabezado + gasto + compra
            por_origen = {f[1]: f for f in filas[1:]}
            assert por_origen["gasto"][2:9] == ["Servicios públicos", "Factura de luz", "Epm", "tarjeta", "", "30050", "vigente"]
            assert por_origen["compra"][2] == "Compra de mercancía"
            assert por_origen["compra"][5:9] == ["transferencia", "daviplata", "10000", "vigente"]

        assert client.get("/gastos/exportar", headers=_auth(client, usuario_vendedor)).status_code == 403

    def test_el_navegador_puede_leer_el_nombre_del_archivo(self, client, usuario_administrador):
        h = {**_auth(client, usuario_administrador), "Origin": "http://localhost:5173"}

        respuesta = client.get("/gastos/exportar", headers=h)

        assert "content-disposition" in respuesta.headers["access-control-expose-headers"].lower()

    def test_los_anulados_salen_solo_si_se_piden(self, client, usuario_administrador, cat_arriendo):
        h = _auth(client, usuario_administrador)
        _registrar(client, h, cat_arriendo.id, "10000")
        anulado = _registrar(client, h, cat_arriendo.id, "40000")
        client.post(f"/gastos/{anulado['id']}/anular", json={"motivo": "Error de digitación"}, headers=h)

        sin = self._leer(client.get("/gastos/exportar", headers=h))
        con = self._leer(client.get("/gastos/exportar?incluir_anulados=true", headers=h))

        assert len(sin) == 2
        assert len(con) == 3
        fila_anulada = next(f for f in con[1:] if f[8] == "anulado")
        assert fila_anulada[7] == "40000" and fila_anulada[10] == "Error de digitación"

    def test_respeta_los_filtros(self, client, usuario_administrador, cat_arriendo, cat_servicios):
        h = _auth(client, usuario_administrador)
        _registrar(client, h, cat_arriendo.id, "10000")
        _registrar(client, h, cat_servicios.id, "20000")

        filas = self._leer(client.get(f"/gastos/exportar?categoria_id={cat_servicios.id}", headers=h))

        assert [f[2] for f in filas[1:]] == ["Servicios públicos"]

    def test_un_texto_que_parece_formula_no_se_ejecuta_en_excel(self, client, db_session, usuario_administrador, cat_arriendo):
        h = _auth(client, usuario_administrador)
        _registrar(client, h, cat_arriendo.id, descripcion="=HYPERLINK(\"http://x\")", beneficiario="+57 300")

        fila = self._leer(client.get("/gastos/exportar", headers=h))[1]

        assert fila[3].startswith("'=") and fila[4] == "'+57 300"

    def test_las_comas_y_los_saltos_de_linea_no_rompen_las_columnas(self, client, usuario_administrador, cat_arriendo):
        h = _auth(client, usuario_administrador)
        _registrar(client, h, cat_arriendo.id, descripcion="Pago; con punto y coma y \"comillas\"")

        filas = self._leer(client.get("/gastos/exportar", headers=h))

        assert filas[1][3] == "Pago; con punto y coma y \"comillas\""
        assert len(filas[1]) == len(filas[0])
