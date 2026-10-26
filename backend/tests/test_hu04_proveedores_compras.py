"""Pruebas de aceptacion de HU-04 (Restriccion de Informacion Sensible de Proveedores) y Fase 3.

Cada clase cita, en su docstring, el criterio exacto de
`HistoriasDeUsuario_PinateriaDemo_v1_0.docx` que cubre. Incluye
ademas RF-010 (ordenes de compra), RF-011 (stock al recibir) y RF-012
(directorio e historial por proveedor/producto).
"""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.producto import Producto
from app.models.proveedor import Proveedor
from tests.conftest import obtener_token, pagos_en_efectivo

PAYLOAD_PROVEEDOR = {"nombre_empresa": "Papeles del valle sas", "nombre_contacto": "Marta ruiz", "telefono": "3001112233"}


PAGO_EFECTIVO = {"metodo_pago": "efectivo"}
"""Cuerpo de `PATCH /compras/{id}/recibir` (Adendo v3: la recepcion pide la forma de pago)."""

def _auth(client: TestClient, usuario) -> dict[str, str]:
    """Devuelve el header Authorization para el usuario dado."""
    return {"Authorization": f"Bearer {obtener_token(client, usuario.username)}"}


@pytest.fixture
def proveedor(db_session: Session) -> Proveedor:
    """Proveedor de prueba ya persistido."""
    prov = Proveedor(**PAYLOAD_PROVEEDOR)
    db_session.add(prov)
    db_session.commit()
    db_session.refresh(prov)
    return prov


@pytest.fixture
def producto(db_session: Session, categoria_prueba) -> Producto:
    """Producto de prueba con stock inicial 10."""
    prod = Producto(nombre="Papel china rojo", categoria_id=categoria_prueba.id, precio_venta=Decimal("1500"), stock_actual=10)
    db_session.add(prod)
    db_session.commit()
    db_session.refresh(prod)
    return prod


@pytest.fixture
def producto2(db_session: Session, categoria_prueba) -> Producto:
    """Segundo producto de prueba con stock inicial 0."""
    prod = Producto(nombre="Confeti", categoria_id=categoria_prueba.id, precio_venta=Decimal("800"), stock_actual=0)
    db_session.add(prod)
    db_session.commit()
    db_session.refresh(prod)
    return prod


def _orden(proveedor_id: int, *lineas: tuple[int, int, str]) -> dict:
    """Arma el payload de `POST /compras` a partir de tuplas (producto_id, cantidad, costo)."""
    return {
        "proveedor_id": proveedor_id,
        "detalles": [{"producto_id": p, "cantidad": c, "costo_unitario": costo} for p, c, costo in lineas],
    }


class TestVendedorNoAccedeAProveedores:
    """HU-04: "cualquier intento de acceso directo vía URL (ej. /api/v1/suppliers) por un 'Vendedor' retorne un código de estado 403 Forbidden"."""

    @pytest.mark.parametrize(
        ("metodo", "ruta"),
        [
            ("GET", "/proveedores"),
            ("POST", "/proveedores"),
            ("GET", "/proveedores/1"),
            ("PATCH", "/proveedores/1"),
            ("DELETE", "/proveedores/1"),
            ("GET", "/compras"),
            ("POST", "/compras"),
            ("GET", "/compras/1"),
            ("PATCH", "/compras/1/recibir"),
            ("PATCH", "/compras/1/cancelar"),
        ],
    )
    def test_vendedor_recibe_403_en_todas_las_rutas(self, client: TestClient, usuario_vendedor, metodo, ruta):
        respuesta = client.request(metodo, ruta, json={} if metodo in {"POST", "PATCH"} else None, headers=_auth(client, usuario_vendedor))

        assert respuesta.status_code == 403

    def test_propietario_tampoco_accede(self, client: TestClient, usuario_propietario):
        respuesta = client.get("/proveedores", headers=_auth(client, usuario_propietario))

        assert respuesta.status_code == 403

    def test_sin_token_recibe_401(self, client: TestClient):
        assert client.get("/proveedores").status_code == 401


class TestAdministradorCrudCompletoDeProveedores:
    """HU-04: "el usuario 'Administrador' pueda realizar CRUD completo sobre el directorio de proveedores"."""

    def test_crea_lista_lee_edita_y_elimina(self, client: TestClient, usuario_administrador):
        h = _auth(client, usuario_administrador)

        creado = client.post("/proveedores", json=PAYLOAD_PROVEEDOR, headers=h)
        assert creado.status_code == 201
        pid = creado.json()["id"]

        assert [p["id"] for p in client.get("/proveedores", headers=h).json()] == [pid]
        assert [p["id"] for p in client.get("/proveedores?q=valle", headers=h).json()] == [pid]
        assert client.get("/proveedores?q=zzz", headers=h).json() == []
        assert client.get(f"/proveedores/{pid}", headers=h).json()["nombre_contacto"] == "Marta ruiz"

        editado = client.patch(f"/proveedores/{pid}", json={"telefono": "3109998877"}, headers=h)
        assert editado.status_code == 200
        assert editado.json()["telefono"] == "3109998877"
        assert editado.json()["nombre_empresa"] == PAYLOAD_PROVEEDOR["nombre_empresa"]

        assert client.delete(f"/proveedores/{pid}", headers=h).status_code == 204
        assert client.get(f"/proveedores/{pid}", headers=h).status_code == 404

    def test_nombre_de_empresa_es_obligatorio(self, client: TestClient, usuario_administrador):
        h = _auth(client, usuario_administrador)

        assert client.post("/proveedores", json={"telefono": "1"}, headers=h).status_code == 422
        assert client.post("/proveedores", json={"nombre_empresa": ""}, headers=h).status_code == 422

    def test_no_se_elimina_proveedor_con_compras(self, client: TestClient, usuario_administrador, proveedor, producto):
        h = _auth(client, usuario_administrador)
        assert client.post("/compras", json=_orden(proveedor.id, (producto.id, 1, "100")), headers=h).status_code == 201

        respuesta = client.delete(f"/proveedores/{proveedor.id}", headers=h)

        assert respuesta.status_code == 409
        assert client.get(f"/proveedores/{proveedor.id}", headers=h).status_code == 200


class TestOrdenesDeCompra:
    """RF-010: "registrar órdenes de compra y entrada de mercancía"."""

    def test_crea_orden_pendiente_con_total_y_sin_mover_stock(
        self, client: TestClient, db_session: Session, usuario_administrador, proveedor, producto, producto2
    ):
        h = _auth(client, usuario_administrador)

        respuesta = client.post(
            "/compras", json=_orden(proveedor.id, (producto.id, 5, "1000.50"), (producto2.id, 2, "300")), headers=h
        )

        assert respuesta.status_code == 201
        cuerpo = respuesta.json()
        assert cuerpo["estado"] == "pendiente"
        assert Decimal(cuerpo["total"]) == Decimal("5600.00")  # 5602.50 redondeado a 50
        assert cuerpo["proveedor_nombre"] == "Papeles del valle sas"
        assert len(cuerpo["detalles"]) == 2
        db_session.refresh(producto)
        assert producto.stock_actual == 10

    def test_proveedor_o_producto_inexistente_da_404(self, client: TestClient, usuario_administrador, proveedor, producto):
        h = _auth(client, usuario_administrador)

        assert client.post("/compras", json=_orden(9999, (producto.id, 1, "1")), headers=h).status_code == 404
        assert client.post("/compras", json=_orden(proveedor.id, (9999, 1, "1")), headers=h).status_code == 404

    def test_rechaza_orden_sin_lineas_o_cantidad_invalida(self, client: TestClient, usuario_administrador, proveedor, producto):
        h = _auth(client, usuario_administrador)

        assert client.post("/compras", json={"proveedor_id": proveedor.id, "detalles": []}, headers=h).status_code == 422
        assert client.post("/compras", json=_orden(proveedor.id, (producto.id, 0, "1")), headers=h).status_code == 422
        assert client.post("/compras", json=_orden(proveedor.id, (producto.id, 1, "-1")), headers=h).status_code == 422


class TestRecibirCompraActualizaStock:
    """RF-011: "actualizar automáticamente el stock al registrar una entrada de mercancía"."""

    def test_recibir_incrementa_stock_de_cada_linea(
        self, client: TestClient, db_session: Session, usuario_administrador, proveedor, producto, producto2
    ):
        h = _auth(client, usuario_administrador)
        compra = client.post(
            "/compras", json=_orden(proveedor.id, (producto.id, 5, "100"), (producto2.id, 7, "50")), headers=h
        ).json()

        respuesta = client.patch(f"/compras/{compra['id']}/recibir", json=PAGO_EFECTIVO, headers=h)

        assert respuesta.status_code == 200
        assert respuesta.json()["estado"] == "recibida"
        db_session.refresh(producto)
        db_session.refresh(producto2)
        assert producto.stock_actual == 15
        assert producto2.stock_actual == 7

    def test_lineas_repetidas_del_mismo_producto_se_suman(
        self, client: TestClient, db_session: Session, usuario_administrador, proveedor, producto
    ):
        h = _auth(client, usuario_administrador)
        compra = client.post(
            "/compras", json=_orden(proveedor.id, (producto.id, 2, "100"), (producto.id, 3, "90")), headers=h
        ).json()

        client.patch(f"/compras/{compra['id']}/recibir", json=PAGO_EFECTIVO, headers=h)

        db_session.refresh(producto)
        assert producto.stock_actual == 15

    def test_no_se_recibe_dos_veces(self, client: TestClient, db_session: Session, usuario_administrador, proveedor, producto):
        h = _auth(client, usuario_administrador)
        compra = client.post("/compras", json=_orden(proveedor.id, (producto.id, 5, "100")), headers=h).json()
        assert client.patch(f"/compras/{compra['id']}/recibir", json=PAGO_EFECTIVO, headers=h).status_code == 200

        segunda = client.patch(f"/compras/{compra['id']}/recibir", json=PAGO_EFECTIVO, headers=h)

        assert segunda.status_code == 409
        db_session.refresh(producto)
        assert producto.stock_actual == 15

    def test_cancelar_no_mueve_stock_y_bloquea_recepcion(
        self, client: TestClient, db_session: Session, usuario_administrador, proveedor, producto
    ):
        h = _auth(client, usuario_administrador)
        compra = client.post("/compras", json=_orden(proveedor.id, (producto.id, 5, "100")), headers=h).json()

        cancelada = client.patch(f"/compras/{compra['id']}/cancelar", headers=h)

        assert cancelada.status_code == 200
        assert cancelada.json()["estado"] == "cancelada"
        assert client.patch(f"/compras/{compra['id']}/recibir", json=PAGO_EFECTIVO, headers=h).status_code == 409
        assert client.patch(f"/compras/{compra['id']}/cancelar", headers=h).status_code == 409
        db_session.refresh(producto)
        assert producto.stock_actual == 10

    def test_compra_inexistente_da_404(self, client: TestClient, usuario_administrador):
        h = _auth(client, usuario_administrador)

        assert client.patch("/compras/9999/recibir", json=PAGO_EFECTIVO, headers=h).status_code == 404
        assert client.patch("/compras/9999/cancelar", headers=h).status_code == 404
        assert client.get("/compras/9999", headers=h).status_code == 404


class TestHistorialDeCompras:
    """RF-012: "historial de compras por proveedor y por producto"."""

    def test_filtra_por_proveedor_producto_y_estado(
        self, client: TestClient, db_session: Session, usuario_administrador, proveedor, producto, producto2
    ):
        h = _auth(client, usuario_administrador)
        otro = client.post("/proveedores", json={"nombre_empresa": "Otro SAS"}, headers=h).json()
        c1 = client.post("/compras", json=_orden(proveedor.id, (producto.id, 1, "10")), headers=h).json()
        c2 = client.post("/compras", json=_orden(otro["id"], (producto.id, 1, "10"), (producto2.id, 1, "10")), headers=h).json()
        client.patch(f"/compras/{c1['id']}/recibir", json=PAGO_EFECTIVO, headers=h)

        def ids(query: str) -> list[int]:
            return [c["id"] for c in client.get(f"/compras{query}", headers=h).json()]

        assert ids("") == [c2["id"], c1["id"]]
        assert ids(f"?proveedor_id={proveedor.id}") == [c1["id"]]
        assert ids(f"?producto_id={producto2.id}") == [c2["id"]]
        assert ids(f"?producto_id={producto.id}") == [c2["id"], c1["id"]]
        assert ids("?estado=recibida") == [c1["id"]]
        assert ids("?estado=pendiente") == [c2["id"]]

    def test_pagina_por_compras_no_por_lineas(
        self, client: TestClient, usuario_administrador, proveedor, producto, producto2
    ):
        h = _auth(client, usuario_administrador)
        for _ in range(3):
            client.post("/compras", json=_orden(proveedor.id, (producto.id, 1, "1"), (producto2.id, 1, "1")), headers=h)

        pagina = client.get("/compras?tamano_pagina=2&pagina=1", headers=h).json()
        resto = client.get("/compras?tamano_pagina=2&pagina=2", headers=h).json()

        assert len(pagina) == 2
        assert len(resto) == 1
        assert all(len(c["detalles"]) == 2 for c in pagina + resto)


class TestValidacionDeContacto:
    """Teléfono solo con números y correo con formato válido (RF-012)."""

    @pytest.mark.parametrize("telefono", ["300-111-2233", "abc1234567", "+573001112233", "123", "300 111 2233"])
    def test_telefono_con_caracteres_no_numericos_es_rechazado(self, client: TestClient, usuario_administrador, telefono):
        h = _auth(client, usuario_administrador)

        respuesta = client.post("/proveedores", json={"nombre_empresa": "X", "telefono": telefono}, headers=h)

        assert respuesta.status_code == 422

    def test_telefono_y_correo_en_null_se_aceptan(self, client: TestClient, usuario_administrador):
        """Un null explicito (lo que manda el formulario al dejar el campo vacio) no debe dar 500."""
        h = _auth(client, usuario_administrador)

        respuesta = client.post(
            "/proveedores", json={"nombre_empresa": "X", "telefono": None, "email": None}, headers=h
        )

        assert respuesta.status_code == 201
        assert respuesta.json()["telefono"] is None

    @pytest.mark.parametrize("email", ["sin-arroba", "a@b", "a@@b.com", "a b@c.com", "@dominio.com"])
    def test_correo_invalido_es_rechazado(self, client: TestClient, usuario_administrador, email):
        h = _auth(client, usuario_administrador)

        respuesta = client.post("/proveedores", json={"nombre_empresa": "X", "email": email}, headers=h)

        assert respuesta.status_code == 422

    def test_telefono_y_correo_validos_se_aceptan_tambien_al_editar(self, client: TestClient, usuario_administrador, proveedor):
        h = _auth(client, usuario_administrador)

        ok = client.patch(f"/proveedores/{proveedor.id}", json={"telefono": "3109998877", "email": "ventas@papeles.com.co"}, headers=h)
        mal = client.patch(f"/proveedores/{proveedor.id}", json={"telefono": "31x"}, headers=h)

        assert ok.status_code == 200
        assert mal.status_code == 422


class TestRedondeoA50:
    """Los totales de compras y ventas se redondean siempre al múltiplo de 50 pesos más cercano."""

    @pytest.mark.parametrize(
        ("valor", "esperado"),
        [("1000", "1000.00"), ("1024.99", "1000.00"), ("1025", "1050.00"), ("1049", "1050.00"), ("0", "0.00")],
    )
    def test_funcion_redondea_al_multiplo_de_50_mas_cercano(self, valor, esperado):
        from app.services.redondeo import redondear_a_50

        assert redondear_a_50(Decimal(valor)) == Decimal(esperado)

    def test_compra_siempre_redondea_el_total_a_50(self, client: TestClient, usuario_administrador, proveedor, producto):
        h = _auth(client, usuario_administrador)

        respuesta = client.post("/compras", json=_orden(proveedor.id, (producto.id, 3, "1234")), headers=h)

        cuerpo = respuesta.json()
        assert Decimal(cuerpo["total"]) == Decimal("3700.00")
        assert Decimal(cuerpo["detalles"][0]["subtotal"]) == Decimal("3702.00")

    def test_venta_siempre_redondea_el_total_a_50(self, client: TestClient, db_session: Session, usuario_vendedor, categoria_prueba):
        prod = Producto(nombre="Dulce", categoria_id=categoria_prueba.id, precio_venta=Decimal("1010"), stock_actual=10)
        db_session.add(prod)
        db_session.commit()
        h = _auth(client, usuario_vendedor)

        respuesta = client.post(
            "/ventas", json={"pagos": pagos_en_efectivo("3050"), "detalles": [{"producto_id": prod.id, "cantidad": 3}]}, headers=h
        )

        assert Decimal(respuesta.json()["total"]) == Decimal("3050.00")
