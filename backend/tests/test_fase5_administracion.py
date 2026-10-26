"""Pruebas de la Fase 5 (Modulo de Administracion): RF-015 (usuarios y roles) y RF-017 (categorias).

Cubre las decisiones acordadas: el administrador crea usuarios de cualquier rol,
desactivar no borra, la contrasena temporal la fija el administrador y cada
usuario puede cambiar la suya, y un administrador no puede desactivarse ni
quitarse el rol a si mismo. RF-016 (productos) se verifica en `test_hu02_alta_productos.py`.
"""

from decimal import Decimal

from fastapi.testclient import TestClient

from app.models.categoria import Categoria
from app.models.producto import Producto
from app.models.usuario import Usuario
from tests.conftest import obtener_token


def _auth(client: TestClient, usuario) -> dict[str, str]:
    """Devuelve el header Authorization para el usuario dado."""
    return {"Authorization": f"Bearer {obtener_token(client, usuario.username)}"}


NUEVO = {"nombre": "Ana Perez", "username": "ana.perez", "password": "temporal-123", "rol": "vendedor"}


class TestUsuariosRbac:
    """RF-015: solo el administrador gestiona usuarios; los demas reciben 403."""

    def test_vendedor_y_propietario_reciben_403(self, client, usuario_vendedor, usuario_propietario):
        for usuario in (usuario_vendedor, usuario_propietario):
            h = _auth(client, usuario)
            assert client.get("/usuarios", headers=h).status_code == 403
            assert client.post("/usuarios", json=NUEVO, headers=h).status_code == 403
            assert client.patch("/usuarios/1", json={"activo": False}, headers=h).status_code == 403
            assert client.post("/usuarios/1/password", json={"password": "otra-clave-1"}, headers=h).status_code == 403

    def test_sin_token_401(self, client):
        assert client.get("/usuarios").status_code == 401


class TestUsuariosCrud:
    """RF-015: alta, listado, edicion, desactivacion y restablecimiento de contrasena."""

    def test_crea_usuario_de_cualquier_rol_sin_exponer_hash(self, client, usuario_administrador):
        h = _auth(client, usuario_administrador)
        for i, rol in enumerate(["administrador", "vendedor", "propietario"]):
            r = client.post("/usuarios", json={**NUEVO, "username": f"usuario{i}", "rol": rol}, headers=h)
            assert r.status_code == 201, r.text
            cuerpo = r.json()
            assert cuerpo["rol"] == rol and cuerpo["activo"] is True
            assert "password" not in cuerpo and "password_hash" not in cuerpo

    def test_nuevo_usuario_puede_iniciar_sesion_con_la_temporal(self, client, usuario_administrador):
        client.post("/usuarios", json=NUEVO, headers=_auth(client, usuario_administrador))
        r = client.post("/login", data={"username": "ana.perez", "password": "temporal-123"})
        assert r.status_code == 200

    def test_username_duplicado_409_sin_distinguir_mayusculas(self, client, usuario_administrador):
        h = _auth(client, usuario_administrador)
        assert client.post("/usuarios", json=NUEVO, headers=h).status_code == 201
        r = client.post("/usuarios", json={**NUEVO, "username": "ANA.PEREZ"}, headers=h)
        assert r.status_code == 409

    def test_valida_username_y_contrasena_corta(self, client, usuario_administrador):
        h = _auth(client, usuario_administrador)
        assert client.post("/usuarios", json={**NUEVO, "username": "a b"}, headers=h).status_code == 422
        assert client.post("/usuarios", json={**NUEVO, "password": "corta"}, headers=h).status_code == 422
        assert client.post("/usuarios", json={**NUEVO, "rol": "root"}, headers=h).status_code == 422

    def test_lista_incluye_inactivos(self, client, db_session, usuario_administrador, usuario_vendedor):
        usuario_vendedor.activo = False
        db_session.commit()
        r = client.get("/usuarios", headers=_auth(client, usuario_administrador))
        assert r.status_code == 200
        por_username = {u["username"]: u for u in r.json()}
        assert por_username[usuario_vendedor.username]["activo"] is False

    def test_edita_nombre_y_rol(self, client, usuario_administrador, usuario_vendedor):
        r = client.patch(
            f"/usuarios/{usuario_vendedor.id}",
            json={"nombre": "  Nuevo Nombre ", "rol": "propietario"},
            headers=_auth(client, usuario_administrador),
        )
        assert r.status_code == 200
        assert r.json()["nombre"] == "Nuevo nombre" and r.json()["rol"] == "propietario"

    def test_editar_a_username_ocupado_409_y_campos_nulos_422(self, client, usuario_administrador, usuario_vendedor):
        h = _auth(client, usuario_administrador)
        r = client.patch(f"/usuarios/{usuario_vendedor.id}", json={"username": usuario_administrador.username}, headers=h)
        assert r.status_code == 409
        r = client.patch(f"/usuarios/{usuario_vendedor.id}", json={"nombre": None}, headers=h)
        assert r.status_code == 422

    def test_usuario_inexistente_404(self, client, usuario_administrador):
        h = _auth(client, usuario_administrador)
        assert client.patch("/usuarios/99999", json={"activo": False}, headers=h).status_code == 404
        assert client.post("/usuarios/99999/password", json={"password": "otra-clave-1"}, headers=h).status_code == 404

    def test_desactivar_conserva_historial_y_bloquea_login_y_token(self, client, db_session, usuario_administrador, usuario_vendedor):
        token_vendedor = obtener_token(client, usuario_vendedor.username)
        r = client.patch(f"/usuarios/{usuario_vendedor.id}", json={"activo": False}, headers=_auth(client, usuario_administrador))
        assert r.status_code == 200 and r.json()["activo"] is False
        # La fila sigue existiendo (no se borra).
        assert db_session.get(Usuario, usuario_vendedor.id) is not None
        # No puede iniciar sesion ni usar un token vigente.
        assert client.post("/login", data={"username": usuario_vendedor.username, "password": "clave-de-prueba-123"}).status_code == 401
        assert client.get("/categorias", headers={"Authorization": f"Bearer {token_vendedor}"}).status_code == 401

    def test_reactivar_usuario(self, client, db_session, usuario_administrador, usuario_vendedor):
        usuario_vendedor.activo = False
        db_session.commit()
        r = client.patch(f"/usuarios/{usuario_vendedor.id}", json={"activo": True}, headers=_auth(client, usuario_administrador))
        assert r.json()["activo"] is True
        assert client.post("/login", data={"username": usuario_vendedor.username, "password": "clave-de-prueba-123"}).status_code == 200

    def test_admin_no_puede_desactivarse_ni_quitarse_el_rol(self, client, usuario_administrador):
        h = _auth(client, usuario_administrador)
        assert client.patch(f"/usuarios/{usuario_administrador.id}", json={"activo": False}, headers=h).status_code == 403
        assert client.patch(f"/usuarios/{usuario_administrador.id}", json={"rol": "vendedor"}, headers=h).status_code == 403
        # Editar su nombre o mantener el rol si esta permitido.
        r = client.patch(f"/usuarios/{usuario_administrador.id}", json={"nombre": "Yo", "rol": "administrador"}, headers=h)
        assert r.status_code == 200

    def test_admin_restablece_contrasena_temporal(self, client, usuario_administrador, usuario_vendedor):
        r = client.post(f"/usuarios/{usuario_vendedor.id}/password", json={"password": "temporal-nueva-1"}, headers=_auth(client, usuario_administrador))
        assert r.status_code == 204
        assert client.post("/login", data={"username": usuario_vendedor.username, "password": "clave-de-prueba-123"}).status_code == 401
        assert client.post("/login", data={"username": usuario_vendedor.username, "password": "temporal-nueva-1"}).status_code == 200

    def test_contrasena_temporal_corta_422(self, client, usuario_administrador, usuario_vendedor):
        r = client.post(f"/usuarios/{usuario_vendedor.id}/password", json={"password": "corta"}, headers=_auth(client, usuario_administrador))
        assert r.status_code == 422


class TestCambiarPasswordPropia:
    """RF-015: cada usuario cambia su propia contrasena confirmando la actual."""

    def test_cambia_su_contrasena(self, client, usuario_vendedor):
        r = client.post(
            "/cambiar-password",
            json={"password_actual": "clave-de-prueba-123", "password_nueva": "clave-nueva-456"},
            headers=_auth(client, usuario_vendedor),
        )
        assert r.status_code == 204
        assert client.post("/login", data={"username": usuario_vendedor.username, "password": "clave-de-prueba-123"}).status_code == 401
        assert client.post("/login", data={"username": usuario_vendedor.username, "password": "clave-nueva-456"}).status_code == 200

    def test_contrasena_actual_incorrecta_400(self, client, usuario_propietario):
        r = client.post(
            "/cambiar-password",
            json={"password_actual": "equivocada", "password_nueva": "clave-nueva-456"},
            headers=_auth(client, usuario_propietario),
        )
        assert r.status_code == 400

    def test_nueva_contrasena_corta_422_y_requiere_sesion(self, client, usuario_vendedor):
        r = client.post(
            "/cambiar-password",
            json={"password_actual": "clave-de-prueba-123", "password_nueva": "corta"},
            headers=_auth(client, usuario_vendedor),
        )
        assert r.status_code == 422
        assert client.post("/cambiar-password", json={"password_actual": "x", "password_nueva": "clave-nueva-456"}).status_code == 401


class TestCategoriasCrud:
    """RF-017: alta, edicion y baja de categorias, solo administrador; no se borra una con productos."""

    def test_vendedor_lee_pero_no_modifica(self, client, categoria_prueba, usuario_vendedor):
        h = _auth(client, usuario_vendedor)
        assert client.get("/categorias", headers=h).status_code == 200
        assert client.post("/categorias", json={"nombre": "Nueva"}, headers=h).status_code == 403
        assert client.patch(f"/categorias/{categoria_prueba.id}", json={"nombre": "X"}, headers=h).status_code == 403
        assert client.delete(f"/categorias/{categoria_prueba.id}", headers=h).status_code == 403

    def test_propietario_recibe_403(self, client, usuario_propietario):
        assert client.post("/categorias", json={"nombre": "Nueva"}, headers=_auth(client, usuario_propietario)).status_code == 403

    def test_crea_categoria(self, client, usuario_administrador):
        r = client.post("/categorias", json={"nombre": "  Globos ", "descripcion": "De latex"}, headers=_auth(client, usuario_administrador))
        assert r.status_code == 201
        assert r.json()["nombre"] == "Globos" and r.json()["descripcion"] == "De latex"

    def test_nombre_duplicado_409_y_vacio_422(self, client, categoria_prueba, usuario_administrador):
        h = _auth(client, usuario_administrador)
        assert client.post("/categorias", json={"nombre": categoria_prueba.nombre.upper()}, headers=h).status_code == 409
        assert client.post("/categorias", json={"nombre": "   "}, headers=h).status_code == 422

    def test_edita_categoria(self, client, categoria_prueba, usuario_administrador):
        h = _auth(client, usuario_administrador)
        r = client.patch(f"/categorias/{categoria_prueba.id}", json={"nombre": "Renombrada", "descripcion": None}, headers=h)
        assert r.status_code == 200
        assert r.json()["nombre"] == "Renombrada" and r.json()["descripcion"] is None

    def test_editar_a_nombre_ocupado_409_y_conservar_el_propio_ok(self, client, db_session, categoria_prueba, usuario_administrador):
        otra = Categoria(nombre="Otra")
        db_session.add(otra)
        db_session.commit()
        h = _auth(client, usuario_administrador)
        assert client.patch(f"/categorias/{otra.id}", json={"nombre": categoria_prueba.nombre}, headers=h).status_code == 409
        assert client.patch(f"/categorias/{otra.id}", json={"nombre": "OTRA"}, headers=h).status_code == 200

    def test_categoria_inexistente_404(self, client, usuario_administrador):
        h = _auth(client, usuario_administrador)
        assert client.patch("/categorias/99999", json={"nombre": "X"}, headers=h).status_code == 404
        assert client.delete("/categorias/99999", headers=h).status_code == 404

    def test_elimina_categoria_sin_productos(self, client, db_session, usuario_administrador):
        categoria = Categoria(nombre="Vacia")
        db_session.add(categoria)
        db_session.commit()
        r = client.delete(f"/categorias/{categoria.id}", headers=_auth(client, usuario_administrador))
        assert r.status_code == 204
        assert db_session.get(Categoria, categoria.id) is None

    def test_no_elimina_categoria_con_productos(self, client, db_session, categoria_prueba, usuario_administrador):
        db_session.add(Producto(nombre="Piñata", categoria_id=categoria_prueba.id, precio_venta=Decimal("5000"), stock_actual=1))
        db_session.commit()
        r = client.delete(f"/categorias/{categoria_prueba.id}", headers=_auth(client, usuario_administrador))
        assert r.status_code == 409
        assert db_session.get(Categoria, categoria_prueba.id) is not None
