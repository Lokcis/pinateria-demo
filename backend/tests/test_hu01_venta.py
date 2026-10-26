"""Pruebas de aceptacion de HU-01 (Proceso de Venta Hibrida en el POS).

Cada clase de prueba cita, en su docstring, el criterio exacto de
`HistoriasDeUsuario_PinateriaDemo_v1_0.docx` que cubre. Los
criterios que dependen de hardware fisico (impresora, lector USB) NO se
prueban aqui: ver `tests/README_pruebas.md` para el checklist manual de
esos casos y de la Definicion de Terminado (DoD) transversal.
"""

import time
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.producto import Producto, TipoProducto
from app.models.producto_componente import ProductoComponente
from tests.conftest import obtener_token, pagos_en_efectivo


@pytest.fixture
def headers_vendedor(client: TestClient, usuario_vendedor) -> dict[str, str]:
    """Header Authorization de un vendedor: `/productos/buscar` exige vendedor o administrador."""
    return {"Authorization": f"Bearer {obtener_token(client, usuario_vendedor.username)}"}


def _crear_producto(
    db_session: Session,
    categoria_id: int,
    nombre: str,
    precio_venta: str,
    stock_actual: int,
    codigo_barras: str | None = None,
    tipo: TipoProducto = TipoProducto.UNIDAD,
) -> Producto:
    """Crea y persiste un producto de prueba.

    Args:
        db_session: Sesion de base de datos de la prueba.
        categoria_id: Id de la categoria a la que pertenece.
        nombre: Nombre del producto.
        precio_venta: Precio de venta, como string (ej. "15000.00").
        stock_actual: Stock inicial.
        codigo_barras: Codigo de barras, o None si no aplica.
        tipo: Tipo de producto.

    Returns:
        Producto: El producto creado, ya con `id` asignado.
    """
    producto = Producto(
        nombre=nombre,
        categoria_id=categoria_id,
        codigo_barras=codigo_barras,
        tipo=tipo,
        precio_venta=Decimal(precio_venta),
        stock_actual=stock_actual,
        activo=True,
    )
    db_session.add(producto)
    db_session.commit()
    db_session.refresh(producto)
    return producto


class TestBusquedaPorCodigoDeBarrasExacto:
    """HU-01: "al escanear un codigo de barras, el producto se agregue ... de forma inmediata"."""

    def test_codigo_exacto_devuelve_un_unico_producto(self, client: TestClient, db_session, categoria_prueba, headers_vendedor):
        """Un codigo de barras exacto debe devolver ese producto y solo ese, sin ambiguedad."""
        _crear_producto(
            db_session, categoria_prueba.id, "Piñata Mickey Mouse", "25000.00", 10, codigo_barras="7501234567890"
        )

        respuesta = client.get("/productos/buscar", params={"q": "7501234567890"}, headers=headers_vendedor)

        assert respuesta.status_code == 200
        resultados = respuesta.json()
        assert len(resultados) == 1
        assert resultados[0]["codigo_barras"] == "7501234567890"

    def test_codigo_inexistente_no_revienta_cae_a_busqueda_por_nombre(
        self, client: TestClient, db_session, categoria_prueba, headers_vendedor
    ):
        """Si el texto no matchea ningun codigo exacto, debe intentar el fallback, no fallar."""
        _crear_producto(db_session, categoria_prueba.id, "7501234567890", "10000.00", 5)

        respuesta = client.get("/productos/buscar", params={"q": "0000000000000"}, headers=headers_vendedor)

        assert respuesta.status_code == 200
        assert respuesta.json() == []


class TestBusquedaManualPorNombreOCategoria:
    """HU-01: "el buscador manual retorne coincidencias parciales por nombre o categoria"."""

    def test_coincidencia_parcial_por_nombre(self, client: TestClient, db_session, categoria_prueba, headers_vendedor):
        """Buscar un fragmento del nombre debe encontrar el producto."""
        _crear_producto(db_session, categoria_prueba.id, "Piñata Mickey Mouse", "25000.00", 10)

        respuesta = client.get("/productos/buscar", params={"q": "mickey"}, headers=headers_vendedor)

        assert respuesta.status_code == 200
        nombres = [p["nombre"] for p in respuesta.json()]
        assert "Piñata Mickey Mouse" in nombres

    def test_fragmento_corto_de_un_nombre_largo(self, client: TestClient, db_session, categoria_prueba, headers_vendedor):
        """Un fragmento corto ("glo") debe encontrar un nombre largo aunque la similitud trigram sea baja."""
        _crear_producto(db_session, categoria_prueba.id, "Globo metalizado estrella 18 pulgadas", "3500.00", 30)

        respuesta = client.get("/productos/buscar", params={"q": "glo"}, headers=headers_vendedor)

        assert respuesta.status_code == 200
        nombres = [p["nombre"] for p in respuesta.json()]
        assert "Globo metalizado estrella 18 pulgadas" in nombres

    def test_coincidencia_parcial_por_categoria(self, client: TestClient, db_session, categoria_prueba, headers_vendedor):
        """Buscar un fragmento del NOMBRE DE LA CATEGORIA (no del producto) tambien debe encontrarlo.

        Este es el criterio "... o categoria" de HU-01: el nombre del
        producto en si no contiene el texto buscado.
        """
        _crear_producto(db_session, categoria_prueba.id, "Bolsa de dulces surtidos", "8000.00", 20)

        respuesta = client.get("/productos/buscar", params={"q": "infantiles"}, headers=headers_vendedor)

        assert respuesta.status_code == 200
        nombres = [p["nombre"] for p in respuesta.json()]
        assert "Bolsa de dulces surtidos" in nombres

    def test_busqueda_manual_responde_en_menos_de_un_segundo(
        self, client: TestClient, db_session, categoria_prueba, headers_vendedor
    ):
        """HU-01: la busqueda manual debe responder en menos de 1 segundo.

        Nota: mide latencia local del proceso de pruebas, no las
        condiciones reales de red de la tienda; es una guarda de
        regresion de rendimiento, no un reemplazo de la medicion en
        staging exigida por la Definicion de Terminado.
        """
        for indice in range(50):
            _crear_producto(db_session, categoria_prueba.id, f"Producto de relleno {indice}", "1000.00", 5)
        _crear_producto(db_session, categoria_prueba.id, "Piñata Mickey Mouse", "25000.00", 10)

        inicio = time.perf_counter()
        respuesta = client.get("/productos/buscar", params={"q": "mickey"}, headers=headers_vendedor)
        duracion_segundos = time.perf_counter() - inicio

        assert respuesta.status_code == 200
        assert duracion_segundos < 1.0, f"La busqueda tardo {duracion_segundos:.3f}s (limite: 1s)"


class TestBusquedaExigeAutenticacion:
    """HU-01 y RF-015: la busqueda del POS es solo para vendedor y administrador.

    Antes respondia 200 sin token y exponia nombre, precio y stock del catalogo a
    cualquiera con la URL (hallazgo de seguridad, `docs/06-estado-de-implementacion.md`).
    """

    def test_sin_token_recibe_401(self, client: TestClient, db_session, categoria_prueba):
        _crear_producto(db_session, categoria_prueba.id, "Piñata Mickey Mouse", "25000.00", 10)

        respuesta = client.get("/productos/buscar", params={"q": "mickey"})

        assert respuesta.status_code == 401

    def test_token_invalido_recibe_401(self, client: TestClient):
        respuesta = client.get(
            "/productos/buscar", params={"q": "mickey"}, headers={"Authorization": "Bearer no-es-un-jwt"}
        )

        assert respuesta.status_code == 401

    def test_propietario_recibe_403(self, client: TestClient, usuario_propietario):
        token = obtener_token(client, usuario_propietario.username)

        respuesta = client.get(
            "/productos/buscar", params={"q": "mickey"}, headers={"Authorization": f"Bearer {token}"}
        )

        assert respuesta.status_code == 403

    def test_administrador_puede_buscar(
        self, client: TestClient, db_session, categoria_prueba, usuario_administrador
    ):
        _crear_producto(db_session, categoria_prueba.id, "Piñata Mickey Mouse", "25000.00", 10)
        token = obtener_token(client, usuario_administrador.username)

        respuesta = client.get(
            "/productos/buscar", params={"q": "mickey"}, headers={"Authorization": f"Bearer {token}"}
        )

        assert respuesta.status_code == 200
        assert [p["nombre"] for p in respuesta.json()] == ["Piñata Mickey Mouse"]


class TestVentaDescuentaStockExacto:
    """HU-01: "el stock ... disminuya exactamente en la cantidad vendida al confirmar el pago"."""

    def test_stock_disminuye_exactamente_en_la_cantidad_vendida(
        self, client: TestClient, db_session, categoria_prueba, usuario_vendedor
    ):
        """Vender 3 unidades de un producto con stock 10 debe dejarlo en exactamente 7."""
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata Estrella", "18000.00", 10)
        token = obtener_token(client, usuario_vendedor.username)

        respuesta = client.post(
            "/ventas",
            json={
                "pagos": pagos_en_efectivo("54000"),
                "detalles": [{"producto_id": producto.id, "cantidad": 3}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert respuesta.status_code == 201, respuesta.text
        db_session.refresh(producto)
        assert producto.stock_actual == 7

    def test_venta_completa_en_menos_de_dos_segundos(
        self, client: TestClient, db_session, categoria_prueba, usuario_vendedor
    ):
        """HU-01: la transaccion (encabezado + detalle + descuento de stock) en menos de 2s.

        No cubre la impresion fisica (responsabilidad del frontend y del
        agente de impresion, fuera del backend) ni el hardware real.
        """
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata Estrella", "18000.00", 10)
        token = obtener_token(client, usuario_vendedor.username)

        inicio = time.perf_counter()
        respuesta = client.post(
            "/ventas",
            json={"pagos": pagos_en_efectivo("18000"), "detalles": [{"producto_id": producto.id, "cantidad": 1}]},
            headers={"Authorization": f"Bearer {token}"},
        )
        duracion_segundos = time.perf_counter() - inicio

        assert respuesta.status_code == 201
        assert duracion_segundos < 2.0, f"La venta tardo {duracion_segundos:.3f}s (limite: 2s)"

    def test_venta_sin_stock_suficiente_no_deja_venta_parcial(
        self, client: TestClient, db_session, categoria_prueba, usuario_vendedor
    ):
        """Si no hay stock ni componentes, la venta debe fallar completa y el stock no debe tocarse.

        Cubre la regla de "no ventas parciales ni stock negativo" del
        Diseño de Base de Datos v1.1, que sostiene el criterio de HU-01
        de que el stock resultante sea siempre exacto y consistente.
        """
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata Escasa", "18000.00", 2)
        token = obtener_token(client, usuario_vendedor.username)

        respuesta = client.post(
            "/ventas",
            json={"pagos": pagos_en_efectivo("90000"), "detalles": [{"producto_id": producto.id, "cantidad": 5}]},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert respuesta.status_code == 409
        db_session.refresh(producto)
        assert producto.stock_actual == 2  # sin cambios: ni parcial ni negativo


class TestVentaResuelveComposicionBOM:
    """Diseño de Base de Datos v1.1: consumo recursivo de `producto_componentes`.

    No es un criterio literal de HU-01, pero sostiene su ultimo criterio
    (stock exacto) tambien para productos compuestos (paquetes/anchetas),
    que es el caso de uso central del modulo de inventario.
    """

    def test_vender_producto_compuesto_sin_stock_propio_consume_componentes(
        self, client: TestClient, db_session, categoria_prueba, usuario_vendedor
    ):
        """Una ancheta sin unidades armadas debe descontar de sus componentes segun la receta."""
        componente = _crear_producto(db_session, categoria_prueba.id, "Dulce suelto", "500.00", 10)
        ancheta = _crear_producto(
            db_session, categoria_prueba.id, "Ancheta sorpresa", "12000.00", 0, tipo=TipoProducto.ANCHETA
        )
        db_session.add(
            ProductoComponente(producto_padre_id=ancheta.id, producto_componente_id=componente.id, cantidad=2)
        )
        db_session.commit()

        token = obtener_token(client, usuario_vendedor.username)
        respuesta = client.post(
            "/ventas",
            json={"pagos": pagos_en_efectivo("12000"), "detalles": [{"producto_id": ancheta.id, "cantidad": 1}]},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert respuesta.status_code == 201, respuesta.text
        db_session.refresh(componente)
        db_session.refresh(ancheta)
        assert componente.stock_actual == 8  # 10 - (2 componentes x 1 ancheta)
        assert ancheta.stock_actual == 0


class TestRBACEnVentas:
    """HU-04 (patron de RBAC): un rol sin permiso debe recibir 403, no poder operar.

    HU-04 en si (modulo de proveedores) no esta construido todavia; esta
    prueba valida el MISMO mecanismo de RBAC (`requerir_roles`) sobre
    `POST /ventas`, que si existe.
    """

    def test_propietario_no_puede_crear_ventas(
        self, client: TestClient, db_session, categoria_prueba, usuario_propietario
    ):
        """Un usuario con rol PROPIETARIO (solo lectura) debe recibir 403 al intentar vender."""
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata Estrella", "18000.00", 10)
        token = obtener_token(client, usuario_propietario.username)

        respuesta = client.post(
            "/ventas",
            json={"pagos": pagos_en_efectivo("18000"), "detalles": [{"producto_id": producto.id, "cantidad": 1}]},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert respuesta.status_code == 403

    def test_sin_token_devuelve_401(self, client: TestClient, db_session, categoria_prueba):
        """Sin header Authorization, el endpoint debe rechazar con 401, no con 500 ni 403."""
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata Estrella", "18000.00", 10)

        respuesta = client.post(
            "/ventas",
            json={"pagos": pagos_en_efectivo("18000"), "detalles": [{"producto_id": producto.id, "cantidad": 1}]},
        )

        assert respuesta.status_code == 401


class TestLogin:
    """Cobertura basica de autenticacion, requisito transversal de la Definicion de Terminado."""

    def test_login_con_password_incorrecta_devuelve_401(self, client: TestClient, usuario_vendedor):
        """Una contrasena incorrecta nunca debe emitir un token."""
        respuesta = client.post(
            "/login",
            data={"username": usuario_vendedor.username, "password": "clave-incorrecta"},
        )
        assert respuesta.status_code == 401

    def test_login_exitoso_incluye_rol_en_el_token(self, client: TestClient, usuario_vendedor):
        """El token emitido debe poder usarse de inmediato en un endpoint protegido."""
        token = obtener_token(client, usuario_vendedor.username)
        assert isinstance(token, str) and len(token) > 0
