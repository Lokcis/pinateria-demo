"""Pruebas de la regla "primera letra en mayuscula y el resto en minuscula" en lo que se registra.

Se aplica a los nombres (producto, categoria, proveedor y su contacto, cliente, usuario) y a los textos
libres (descripciones, notas de proveedor y motivo de un ajuste). NO se toca lo que es un dato exacto:
usuario de acceso, correo, documento, telefono, direccion, codigo de barras.
"""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.schemas.cliente import AutoregistroIn
from app.services.texto import capitalizar_nombre, capitalizar_texto
from tests.conftest import obtener_token
from tests.test_hu01_venta import _crear_producto


def _auth(client: TestClient, usuario) -> dict[str, str]:
    """Devuelve el header Authorization para el usuario dado."""
    return {"Authorization": f"Bearer {obtener_token(client, usuario.username)}"}


class TestFunciones:
    """`capitalizar_nombre` y `capitalizar_texto` (funciones puras)."""

    @pytest.mark.parametrize(
        "entrada, esperado",
        [
            ("piñata mickey mouse", "Piñata mickey mouse"),
            ("PIÑATA MICKEY MOUSE", "Piñata mickey mouse"),
            ("pIñAtA", "Piñata"),
            ("  globo   metalizado  ", "Globo metalizado"),
            ("ñandú", "Ñandú"),
            ("árbol de navidad", "Árbol de navidad"),
            ("a", "A"),
            ("2 globos rojos", "2 globos rojos"),
            ("Papeles del Valle SAS", "Papeles del valle sas"),
            ("", ""),
            ("   ", ""),
        ],
    )
    def test_nombre(self, entrada, esperado):
        assert capitalizar_nombre(entrada) == esperado

    def test_nombre_reduce_espacios_y_saltos_de_linea(self):
        assert capitalizar_nombre("globo\n\tROJO   grande") == "Globo rojo grande"

    def test_texto_recorta_pero_conserva_el_interior(self):
        assert capitalizar_texto("  CON luces\nLED  ") == "Con luces\nled"
        assert capitalizar_texto("   ") == ""

    def test_aplicarla_dos_veces_no_cambia_nada(self):
        una_vez = capitalizar_nombre("  PIÑATA  mickey ")
        assert capitalizar_nombre(una_vez) == una_vez


class TestProductos:
    """Nombre y descripcion de un producto, al crear y al editar."""

    def test_crear_normaliza_nombre_y_descripcion_pero_no_el_codigo_de_barras(
        self, client, categoria_prueba, usuario_administrador
    ):
        r = client.post(
            "/productos",
            json={
                "nombre": "  PIÑATA MICKEY   MOUSE ", "descripcion": " CON luces LED ", "categoria_id": categoria_prueba.id,
                "codigo_barras": "ABC-123x", "tipo": "unidad", "precio_venta": 25000, "stock_inicial": 3,
            },
            headers=_auth(client, usuario_administrador),
        )
        assert r.status_code == 201, r.text
        assert r.json()["nombre"] == "Piñata mickey mouse"
        assert r.json()["descripcion"] == "Con luces led"
        assert r.json()["codigo_barras"] == "ABC-123x"

    def test_editar_normaliza(self, client, db_session, categoria_prueba, usuario_administrador):
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "1000.00", 5)
        r = client.patch(
            f"/productos/{producto.id}", json={"nombre": "GLOBO METALIZADO", "descripcion": "ESTRELLA"},
            headers=_auth(client, usuario_administrador),
        )
        assert r.status_code == 200, r.text
        assert r.json()["nombre"] == "Globo metalizado" and r.json()["descripcion"] == "Estrella"

    def test_un_nombre_de_solo_espacios_se_rechaza(self, client, categoria_prueba, usuario_administrador):
        r = client.post(
            "/productos",
            json={"nombre": "    ", "categoria_id": categoria_prueba.id, "tipo": "unidad", "precio_venta": 1, "stock_inicial": 0},
            headers=_auth(client, usuario_administrador),
        )
        assert r.status_code == 422

    def test_el_motivo_de_un_ajuste_se_normaliza(self, client, db_session, categoria_prueba, usuario_vendedor):
        producto = _crear_producto(db_session, categoria_prueba.id, "Globo", "1000.00", 5)
        r = client.post(
            f"/productos/{producto.id}/ajustes",
            json={"tipo": "merma", "cantidad": -1, "motivo": "  DAÑADO por humedad "},
            headers=_auth(client, usuario_vendedor),
        )
        assert r.status_code == 201, r.text
        assert r.json()["motivo"] == "Dañado por humedad"


class TestCategorias:
    """Nombre y descripcion de una categoria; la regla ayuda a detectar duplicados."""

    def test_crear_y_editar(self, client, usuario_administrador):
        h = _auth(client, usuario_administrador)
        r = client.post("/categorias", json={"nombre": "GLOBOS", "descripcion": "DE FIESTA"}, headers=h)
        assert r.status_code == 201, r.text
        assert r.json()["nombre"] == "Globos" and r.json()["descripcion"] == "De fiesta"

        e = client.patch(f"/categorias/{r.json()['id']}", json={"nombre": "  velas  "}, headers=h)
        assert e.status_code == 200, e.text
        assert e.json()["nombre"] == "Velas"

    def test_escribirla_distinto_ya_no_crea_un_duplicado(self, client, usuario_administrador):
        h = _auth(client, usuario_administrador)
        assert client.post("/categorias", json={"nombre": "Globos"}, headers=h).status_code == 201
        assert client.post("/categorias", json={"nombre": "GLOBOS"}, headers=h).status_code == 409
        assert client.post("/categorias", json={"nombre": " globos "}, headers=h).status_code == 409


class TestProveedores:
    """Empresa, contacto y notas; el correo, la direccion y el telefono no se tocan."""

    def test_crear_y_editar(self, client, usuario_administrador):
        h = _auth(client, usuario_administrador)
        r = client.post(
            "/proveedores",
            json={
                "nombre_empresa": "PAPELES DEL VALLE SAS", "nombre_contacto": "MARTA ruiz", "telefono": "3001112233",
                "email": "Ventas@Papeles.com", "direccion": "Calle 123 # 45-67 Barrio Demo", "notas": "ENTREGA los lunes",
            },
            headers=h,
        )
        assert r.status_code == 201, r.text
        cuerpo = r.json()
        assert cuerpo["nombre_empresa"] == "Papeles del valle sas" and cuerpo["nombre_contacto"] == "Marta ruiz"
        assert cuerpo["notas"] == "Entrega los lunes"
        assert cuerpo["email"] == "Ventas@Papeles.com" and cuerpo["direccion"] == "Calle 123 # 45-67 Barrio Demo"

        e = client.patch(f"/proveedores/{cuerpo['id']}", json={"nombre_empresa": "OTRA EMPRESA", "nombre_contacto": "LUIS"}, headers=h)
        assert e.status_code == 200, e.text
        assert e.json()["nombre_empresa"] == "Otra empresa" and e.json()["nombre_contacto"] == "Luis"

    def test_el_contacto_puede_quedar_vacio(self, client, usuario_administrador):
        r = client.post(
            "/proveedores", json={"nombre_empresa": "x", "nombre_contacto": ""}, headers=_auth(client, usuario_administrador)
        )
        assert r.status_code == 201, r.text
        assert r.json()["nombre_empresa"] == "X"


class TestUsuarios:
    """El nombre se normaliza; el usuario de acceso se deja exactamente como se escribio."""

    def test_crear_y_editar(self, client, usuario_administrador):
        h = _auth(client, usuario_administrador)
        r = client.post(
            "/usuarios",
            json={"nombre": "  ANA   perez ", "username": "Ana.Perez", "password": "temporal-123", "rol": "vendedor"},
            headers=h,
        )
        assert r.status_code == 201, r.text
        assert r.json()["nombre"] == "Ana perez" and r.json()["username"] == "Ana.Perez"

        e = client.patch(f"/usuarios/{r.json()['id']}", json={"nombre": "LUIS gómez"}, headers=h)
        assert e.status_code == 200, e.text
        assert e.json()["nombre"] == "Luis gómez"


class TestClientes:
    """Nombre del cliente, al crear, al editar y en el autorregistro; documento, telefono y correo no se tocan."""

    CUERPO = {
        "nombre": "MARÍA   PÉREZ", "documento": "ab-123", "telefono": "3109998877", "email": "Maria@Correo.com",
        "autorizacion_aceptada": True, "autorizacion_medio": "verbal",
    }

    def test_crear_y_editar(self, client, usuario_vendedor):
        h = _auth(client, usuario_vendedor)
        r = client.post("/clientes", json=self.CUERPO, headers=h)
        assert r.status_code == 201, r.text
        assert r.json()["nombre"] == "María pérez"
        assert r.json()["documento"] == "ab-123" and r.json()["email"] == "Maria@Correo.com"

        e = client.patch(f"/clientes/{r.json()['id']}", json={"nombre": " CARLOS ruiz "}, headers=h)
        assert e.status_code == 200, e.text
        assert e.json()["nombre"] == "Carlos ruiz"

    def test_autorregistro_publico(self):
        datos = AutoregistroIn(nombre="  LUCÍA  mora ", acepta_politica=True)
        assert datos.nombre == "Lucía mora"

    def test_nombre_solo_espacios_se_rechaza(self):
        with pytest.raises(ValidationError):
            AutoregistroIn(nombre="    ", acepta_politica=True)

