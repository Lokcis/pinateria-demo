"""Pruebas de aceptacion de HU-02 (Registro de Productos con Atributos Flexibles).

Cada clase cita, en su docstring, el criterio exacto de
`HistoriasDeUsuario_PinateriaDemo_v1_0.docx` que cubre. Incluye
tambien RF-016 (edicion y desactivacion), adelantado de Fase 5 porque
HU-02 depende de el.
"""

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.producto import Producto
from tests.conftest import obtener_token

PAYLOAD_BASE = {
    "nombre": "Ancheta artesanal de cumpleaños",
    "precio_venta": "45000.00",
    "stock_inicial": 3,
}


class TestAltaDeProductosConCodigoDeBarrasOpcional:
    """HU-02: "el formulario de creacion permita guardar un producto dejando el campo codigo_barras vacio"."""

    def test_crea_producto_sin_codigo_de_barras(
        self, client: TestClient, categoria_prueba, usuario_administrador
    ):
        token = obtener_token(client, usuario_administrador.username)

        respuesta = client.post(
            "/productos",
            json={**PAYLOAD_BASE, "categoria_id": categoria_prueba.id},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert respuesta.status_code == 201
        cuerpo = respuesta.json()
        assert cuerpo["codigo_barras"] is None
        assert cuerpo["nombre"] == PAYLOAD_BASE["nombre"]
        assert cuerpo["stock_actual"] == 3

    def test_crea_producto_con_codigo_de_barras(
        self, client: TestClient, categoria_prueba, usuario_administrador
    ):
        token = obtener_token(client, usuario_administrador.username)

        respuesta = client.post(
            "/productos",
            json={**PAYLOAD_BASE, "categoria_id": categoria_prueba.id, "codigo_barras": "7501234500000"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert respuesta.status_code == 201
        assert respuesta.json()["codigo_barras"] == "7501234500000"

    def test_codigo_de_barras_duplicado_es_rechazado(
        self, client: TestClient, categoria_prueba, usuario_administrador
    ):
        token = obtener_token(client, usuario_administrador.username)
        headers = {"Authorization": f"Bearer {token}"}
        client.post(
            "/productos",
            json={**PAYLOAD_BASE, "categoria_id": categoria_prueba.id, "codigo_barras": "7501234500001"},
            headers=headers,
        )

        respuesta = client.post(
            "/productos",
            json={
                **PAYLOAD_BASE,
                "nombre": "Otro producto",
                "categoria_id": categoria_prueba.id,
                "codigo_barras": "7501234500001",
            },
            headers=headers,
        )

        assert respuesta.status_code == 409


class TestValidacionDeCamposObligatorios:
    """HU-02: "el sistema arroje un error de validacion si los campos nombre, precio, categoria o stock_inicial estan ausentes"."""

    def test_sin_nombre_da_422(self, client: TestClient, categoria_prueba, usuario_administrador):
        token = obtener_token(client, usuario_administrador.username)
        payload = {**PAYLOAD_BASE, "categoria_id": categoria_prueba.id}
        del payload["nombre"]

        respuesta = client.post("/productos", json=payload, headers={"Authorization": f"Bearer {token}"})

        assert respuesta.status_code == 422

    def test_sin_precio_da_422(self, client: TestClient, categoria_prueba, usuario_administrador):
        token = obtener_token(client, usuario_administrador.username)
        payload = {**PAYLOAD_BASE, "categoria_id": categoria_prueba.id}
        del payload["precio_venta"]

        respuesta = client.post("/productos", json=payload, headers={"Authorization": f"Bearer {token}"})

        assert respuesta.status_code == 422

    def test_sin_categoria_da_422(self, client: TestClient, usuario_administrador):
        token = obtener_token(client, usuario_administrador.username)

        respuesta = client.post("/productos", json=PAYLOAD_BASE, headers={"Authorization": f"Bearer {token}"})

        assert respuesta.status_code == 422

    def test_sin_stock_inicial_da_422(self, client: TestClient, categoria_prueba, usuario_administrador):
        token = obtener_token(client, usuario_administrador.username)
        payload = {**PAYLOAD_BASE, "categoria_id": categoria_prueba.id}
        del payload["stock_inicial"]

        respuesta = client.post("/productos", json=payload, headers={"Authorization": f"Bearer {token}"})

        assert respuesta.status_code == 422

    def test_categoria_inexistente_da_404(self, client: TestClient, usuario_administrador):
        token = obtener_token(client, usuario_administrador.username)

        respuesta = client.post(
            "/productos",
            json={**PAYLOAD_BASE, "categoria_id": 999999},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert respuesta.status_code == 404

    def test_vendedor_no_puede_crear_productos(self, client: TestClient, categoria_prueba, usuario_vendedor):
        token = obtener_token(client, usuario_vendedor.username)

        respuesta = client.post(
            "/productos",
            json={**PAYLOAD_BASE, "categoria_id": categoria_prueba.id},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert respuesta.status_code == 403


class TestProductoVisibleDeInmediatoEnElPOS:
    """HU-02: "el registro sea persistido correctamente en PostgreSQL y sea inmediatamente visible en el POS"."""

    def test_producto_recien_creado_aparece_en_busqueda_del_pos(
        self, client: TestClient, categoria_prueba, usuario_administrador
    ):
        token = obtener_token(client, usuario_administrador.username)
        headers = {"Authorization": f"Bearer {token}"}
        client.post(
            "/productos",
            json={**PAYLOAD_BASE, "nombre": "Ancheta recien creada", "categoria_id": categoria_prueba.id},
            headers=headers,
        )

        respuesta = client.get("/productos/buscar", params={"q": "recien creada"}, headers=headers)

        assert respuesta.status_code == 200
        nombres = [p["nombre"] for p in respuesta.json()]
        assert "Ancheta recien creada" in nombres

    def test_producto_recien_creado_aparece_en_el_catalogo(
        self, client: TestClient, categoria_prueba, usuario_administrador
    ):
        token = obtener_token(client, usuario_administrador.username)
        headers = {"Authorization": f"Bearer {token}"}
        respuesta_creacion = client.post(
            "/productos",
            json={**PAYLOAD_BASE, "categoria_id": categoria_prueba.id},
            headers=headers,
        )
        producto_id = respuesta_creacion.json()["id"]

        respuesta = client.get("/productos", headers=headers)

        assert respuesta.status_code == 200
        ids = [p["id"] for p in respuesta.json()["productos"]]
        assert producto_id in ids


class TestEdicionYDesactivacion:
    """RF-016: edicion y desactivacion de productos (adelantado de Fase 5 para poder cerrar HU-02)."""

    def _crear(self, client: TestClient, categoria_id: int, token: str) -> int:
        respuesta = client.post(
            "/productos",
            json={**PAYLOAD_BASE, "categoria_id": categoria_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        return respuesta.json()["id"]

    def test_editar_nombre_y_precio(self, client: TestClient, categoria_prueba, usuario_administrador):
        token = obtener_token(client, usuario_administrador.username)
        headers = {"Authorization": f"Bearer {token}"}
        producto_id = self._crear(client, categoria_prueba.id, token)

        respuesta = client.patch(
            f"/productos/{producto_id}",
            json={"nombre": "Ancheta editada", "precio_venta": "50000.00"},
            headers=headers,
        )

        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert cuerpo["nombre"] == "Ancheta editada"
        assert Decimal(cuerpo["precio_venta"]) == Decimal("50000.00")
        assert cuerpo["stock_actual"] == 3  # no se toca al editar

    def test_editar_no_toca_campos_ausentes(self, client: TestClient, categoria_prueba, usuario_administrador):
        token = obtener_token(client, usuario_administrador.username)
        headers = {"Authorization": f"Bearer {token}"}
        producto_id = self._crear(client, categoria_prueba.id, token)

        respuesta = client.patch(f"/productos/{producto_id}", json={"nombre": "Solo nombre"}, headers=headers)

        assert respuesta.status_code == 200
        assert Decimal(respuesta.json()["precio_venta"]) == Decimal(PAYLOAD_BASE["precio_venta"])

    def test_editar_categoria_inexistente_da_404(
        self, client: TestClient, categoria_prueba, usuario_administrador
    ):
        token = obtener_token(client, usuario_administrador.username)
        headers = {"Authorization": f"Bearer {token}"}
        producto_id = self._crear(client, categoria_prueba.id, token)

        respuesta = client.patch(f"/productos/{producto_id}", json={"categoria_id": 999999}, headers=headers)

        assert respuesta.status_code == 404

    def test_vendedor_no_puede_editar(self, client: TestClient, categoria_prueba, usuario_administrador, usuario_vendedor):
        token_admin = obtener_token(client, usuario_administrador.username)
        producto_id = self._crear(client, categoria_prueba.id, token_admin)
        token_vendedor = obtener_token(client, usuario_vendedor.username)

        respuesta = client.patch(
            f"/productos/{producto_id}",
            json={"nombre": "x"},
            headers={"Authorization": f"Bearer {token_vendedor}"},
        )

        assert respuesta.status_code == 403

    def test_desactivar_y_reactivar_producto(
        self, client: TestClient, categoria_prueba, usuario_administrador, db_session: Session
    ):
        token = obtener_token(client, usuario_administrador.username)
        headers = {"Authorization": f"Bearer {token}"}
        producto_id = self._crear(client, categoria_prueba.id, token)

        respuesta_desactivar = client.patch(f"/productos/{producto_id}/desactivar", headers=headers)
        assert respuesta_desactivar.status_code == 200
        assert respuesta_desactivar.json()["activo"] is False

        producto_db = db_session.query(Producto).filter(Producto.id == producto_id).one()
        assert producto_db.activo is False

        respuesta_reactivar = client.patch(f"/productos/{producto_id}/reactivar", headers=headers)
        assert respuesta_reactivar.status_code == 200
        assert respuesta_reactivar.json()["activo"] is True

    def test_producto_desactivado_no_aparece_en_busqueda_del_pos(
        self, client: TestClient, categoria_prueba, usuario_administrador
    ):
        token = obtener_token(client, usuario_administrador.username)
        headers = {"Authorization": f"Bearer {token}"}
        producto_id = self._crear(client, categoria_prueba.id, token)
        client.patch(f"/productos/{producto_id}/desactivar", headers=headers)

        respuesta = client.get("/productos/buscar", params={"q": "ancheta"}, headers=headers)

        assert respuesta.status_code == 200
        ids = [p["id"] for p in respuesta.json()]
        assert producto_id not in ids
