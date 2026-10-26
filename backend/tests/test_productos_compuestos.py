"""Pruebas de productos compuestos (paquetes y anchetas) definidos desde la API.

Cubre lo acordado en la Fase 6: al crear/editar un producto se puede definir su
receta (`componentes`), la tarjeta/listado expone de que esta compuesto, un
componente desactivado se sigue descontando al armar (comportamiento vigente),
y antes de desactivar un producto se puede consultar en que compuestos participa
(`GET /productos/{id}/usado-en`) para avisar al administrador.
"""

from decimal import Decimal

from fastapi.testclient import TestClient

from app.models.producto import Producto, TipoProducto
from tests.conftest import obtener_token, pagos_en_efectivo


def _auth(client: TestClient, usuario) -> dict[str, str]:
    """Devuelve el header Authorization para el usuario dado."""
    return {"Authorization": f"Bearer {obtener_token(client, usuario.username)}"}


def _producto(db_session, categoria_id, nombre, stock=10, tipo=TipoProducto.UNIDAD) -> Producto:
    """Crea un producto directamente en la base de prueba."""
    producto = Producto(
        nombre=nombre, categoria_id=categoria_id, precio_venta=Decimal("1000.00"),
        stock_actual=stock, stock_minimo=1, tipo=tipo,
    )
    db_session.add(producto)
    db_session.commit()
    db_session.refresh(producto)
    return producto


def _crear_ancheta(client, headers, categoria_id, componentes, **extra):
    """POST /productos de una ancheta con la receta dada."""
    cuerpo = {
        "nombre": "Ancheta cumpleanos", "categoria_id": categoria_id, "tipo": "ancheta",
        "precio_venta": "25000", "stock_inicial": 0, "componentes": componentes, **extra,
    }
    return client.post("/productos", json=cuerpo, headers=headers)


class TestCrearConReceta:
    """Alta de un producto compuesto con su receta."""

    def test_crea_ancheta_y_devuelve_de_que_esta_compuesta(
        self, client, db_session, categoria_prueba, usuario_administrador
    ):
        h = _auth(client, usuario_administrador)
        globo = _producto(db_session, categoria_prueba.id, "Globo")
        dulce = _producto(db_session, categoria_prueba.id, "Dulce")

        r = _crear_ancheta(client, h, categoria_prueba.id, [
            {"producto_id": globo.id, "cantidad": 3}, {"producto_id": dulce.id, "cantidad": 10},
        ])

        assert r.status_code == 201, r.text
        recetas = {c["nombre"]: c for c in r.json()["componentes"]}
        assert recetas["Globo"]["cantidad"] == 3 and recetas["Globo"]["producto_id"] == globo.id
        assert recetas["Dulce"]["cantidad"] == 10 and recetas["Dulce"]["activo"] is True

    def test_producto_simple_sale_con_receta_vacia(self, client, db_session, categoria_prueba, usuario_administrador):
        _producto(db_session, categoria_prueba.id, "Globo")
        r = client.get("/productos", headers=_auth(client, usuario_administrador))
        assert r.json()["productos"][0]["componentes"] == []

    def test_listado_incluye_los_componentes_de_la_ancheta(
        self, client, db_session, categoria_prueba, usuario_administrador
    ):
        h = _auth(client, usuario_administrador)
        globo = _producto(db_session, categoria_prueba.id, "Globo")
        _crear_ancheta(client, h, categoria_prueba.id, [{"producto_id": globo.id, "cantidad": 2}])

        productos = {p["nombre"]: p for p in client.get("/productos", headers=h).json()["productos"]}
        assert [c["nombre"] for c in productos["Ancheta cumpleanos"]["componentes"]] == ["Globo"]

    def test_unidad_no_puede_tener_componentes(self, client, db_session, categoria_prueba, usuario_administrador):
        globo = _producto(db_session, categoria_prueba.id, "Globo")
        r = _crear_ancheta(
            client, _auth(client, usuario_administrador), categoria_prueba.id,
            [{"producto_id": globo.id, "cantidad": 1}], tipo="unidad",
        )
        assert r.status_code == 422

    def test_rechaza_repetidos_inexistentes_inactivos_y_cantidades_invalidas(
        self, client, db_session, categoria_prueba, usuario_administrador
    ):
        h = _auth(client, usuario_administrador)
        globo = _producto(db_session, categoria_prueba.id, "Globo")
        inactivo = _producto(db_session, categoria_prueba.id, "Descontinuado")
        inactivo.activo = False
        db_session.commit()

        repetido = [{"producto_id": globo.id, "cantidad": 1}, {"producto_id": globo.id, "cantidad": 2}]
        assert _crear_ancheta(client, h, categoria_prueba.id, repetido).status_code == 422
        assert _crear_ancheta(client, h, categoria_prueba.id, [{"producto_id": 99999, "cantidad": 1}]).status_code == 404
        assert _crear_ancheta(client, h, categoria_prueba.id, [{"producto_id": inactivo.id, "cantidad": 1}]).status_code == 409
        assert _crear_ancheta(client, h, categoria_prueba.id, [{"producto_id": globo.id, "cantidad": 0}]).status_code == 422
        assert _crear_ancheta(client, h, categoria_prueba.id, [{"producto_id": globo.id, "cantidad": 1.5}]).status_code == 422

    def test_una_receta_invalida_no_deja_el_producto_a_medias(
        self, client, db_session, categoria_prueba, usuario_administrador
    ):
        h = _auth(client, usuario_administrador)
        _crear_ancheta(client, h, categoria_prueba.id, [{"producto_id": 99999, "cantidad": 1}])
        assert client.get("/productos", headers=h).json()["total"] == 0

    def test_solo_el_administrador_define_recetas(self, client, categoria_prueba, usuario_vendedor):
        r = _crear_ancheta(client, _auth(client, usuario_vendedor), categoria_prueba.id, [])
        assert r.status_code == 403


class TestEditarReceta:
    """Cambiar, conservar o vaciar la receta de un producto existente."""

    def test_reemplaza_conserva_y_vacia(self, client, db_session, categoria_prueba, usuario_administrador):
        h = _auth(client, usuario_administrador)
        globo = _producto(db_session, categoria_prueba.id, "Globo")
        dulce = _producto(db_session, categoria_prueba.id, "Dulce")
        ancheta_id = _crear_ancheta(
            client, h, categoria_prueba.id, [{"producto_id": globo.id, "cantidad": 3}]
        ).json()["id"]

        # Reemplaza (incluye el mismo componente con otra cantidad: no debe chocar con la unicidad).
        r = client.patch(f"/productos/{ancheta_id}", headers=h, json={"componentes": [
            {"producto_id": globo.id, "cantidad": 5}, {"producto_id": dulce.id, "cantidad": 1},
        ]})
        assert r.status_code == 200, r.text
        assert {c["nombre"]: c["cantidad"] for c in r.json()["componentes"]} == {"Globo": 5, "Dulce": 1}

        # Sin la clave `componentes`, la receta se conserva.
        r = client.patch(f"/productos/{ancheta_id}", headers=h, json={"nombre": "Ancheta grande"})
        assert len(r.json()["componentes"]) == 2

        # Lista vacia la deja sin receta.
        r = client.patch(f"/productos/{ancheta_id}", headers=h, json={"componentes": []})
        assert r.json()["componentes"] == []

    def test_no_permite_ciclos(self, client, db_session, categoria_prueba, usuario_administrador):
        h = _auth(client, usuario_administrador)
        a = _producto(db_session, categoria_prueba.id, "Paquete A", tipo=TipoProducto.PAQUETE)
        b = _producto(db_session, categoria_prueba.id, "Paquete B", tipo=TipoProducto.PAQUETE)
        assert client.patch(f"/productos/{a.id}", headers=h, json={"componentes": [
            {"producto_id": b.id, "cantidad": 1}]}).status_code == 200

        assert client.patch(f"/productos/{b.id}", headers=h, json={"componentes": [
            {"producto_id": a.id, "cantidad": 1}]}).status_code == 409
        assert client.patch(f"/productos/{a.id}", headers=h, json={"componentes": [
            {"producto_id": a.id, "cantidad": 1}]}).status_code == 409

    def test_no_se_puede_pasar_a_unidad_con_receta(self, client, db_session, categoria_prueba, usuario_administrador):
        h = _auth(client, usuario_administrador)
        globo = _producto(db_session, categoria_prueba.id, "Globo")
        ancheta_id = _crear_ancheta(
            client, h, categoria_prueba.id, [{"producto_id": globo.id, "cantidad": 1}]
        ).json()["id"]

        assert client.patch(f"/productos/{ancheta_id}", headers=h, json={"tipo": "unidad"}).status_code == 422
        assert client.patch(
            f"/productos/{ancheta_id}", headers=h, json={"tipo": "unidad", "componentes": []}
        ).status_code == 200


class TestUsadoEnYDesactivacion:
    """Aviso al desactivar: el componente sigue en las recetas y se sigue descontando."""

    def test_usado_en_lista_las_anchetas_que_lo_llevan(
        self, client, db_session, categoria_prueba, usuario_administrador
    ):
        h = _auth(client, usuario_administrador)
        globo = _producto(db_session, categoria_prueba.id, "Globo")
        libre = _producto(db_session, categoria_prueba.id, "Suelto")
        _crear_ancheta(client, h, categoria_prueba.id, [{"producto_id": globo.id, "cantidad": 2}])

        r = client.get(f"/productos/{globo.id}/usado-en", headers=h)
        assert r.status_code == 200
        assert [(u["nombre"], u["tipo"]) for u in r.json()] == [("Ancheta cumpleanos", "ancheta")]
        assert client.get(f"/productos/{libre.id}/usado-en", headers=h).json() == []
        assert client.get("/productos/99999/usado-en", headers=h).status_code == 404

    def test_usado_en_solo_para_administrador(self, client, db_session, categoria_prueba, usuario_vendedor):
        globo = _producto(db_session, categoria_prueba.id, "Globo")
        assert client.get(f"/productos/{globo.id}/usado-en", headers=_auth(client, usuario_vendedor)).status_code == 403

    def test_componente_desactivado_se_sigue_descontando_al_vender_la_ancheta(
        self, client, db_session, categoria_prueba, usuario_administrador, usuario_vendedor
    ):
        h = _auth(client, usuario_administrador)
        globo = _producto(db_session, categoria_prueba.id, "Globo", stock=10)
        ancheta_id = _crear_ancheta(
            client, h, categoria_prueba.id, [{"producto_id": globo.id, "cantidad": 2}]
        ).json()["id"]

        assert client.patch(f"/productos/{globo.id}/desactivar", headers=h).status_code == 200
        venta = client.post(
            "/ventas", headers=_auth(client, usuario_vendedor),
            json={"pagos": pagos_en_efectivo("25000"), "detalles": [{"producto_id": ancheta_id, "cantidad": 1}]},
        )

        assert venta.status_code == 201, venta.text
        db_session.refresh(globo)
        assert globo.stock_actual == 8
        # El componente inactivo sigue visible en la tarjeta de la ancheta, marcado como inactivo.
        ancheta = next(p for p in client.get("/productos", headers=h).json()["productos"] if p["id"] == ancheta_id)
        assert ancheta["componentes"][0]["activo"] is False
