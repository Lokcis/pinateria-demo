"""Pruebas de Fase 2 - Modulo Inventario: catalogo, stock minimo y ajustes manuales (RF-006 a RF-009)."""

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.notificacion import Notificacion, TipoNotificacion
from app.models.producto import Producto, TipoProducto
from app.tasks.alertas import revisar_stock_bajo_impl
from tests.conftest import obtener_token


def _crear_producto(
    db_session: Session,
    categoria_id: int,
    nombre: str,
    precio_venta: str = "10000.00",
    stock_actual: int = 10,
    stock_minimo: int = 5,
    activo: bool = True,
) -> Producto:
    """Crea y persiste un producto de prueba."""
    producto = Producto(
        nombre=nombre,
        categoria_id=categoria_id,
        tipo=TipoProducto.UNIDAD,
        precio_venta=Decimal(precio_venta),
        stock_actual=stock_actual,
        stock_minimo=stock_minimo,
        activo=activo,
    )
    db_session.add(producto)
    db_session.commit()
    db_session.refresh(producto)
    return producto


class TestCatalogo:
    """RF-006: catalogo de productos con filtro y paginacion."""

    def test_vendedor_puede_listar_el_catalogo(self, client: TestClient, db_session, categoria_prueba, usuario_vendedor):
        _crear_producto(db_session, categoria_prueba.id, "Piñata Mickey Mouse")
        _crear_producto(db_session, categoria_prueba.id, "Globo metalizado")
        token = obtener_token(client, usuario_vendedor.username)

        respuesta = client.get("/productos", headers={"Authorization": f"Bearer {token}"})

        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert cuerpo["total"] == 2
        assert len(cuerpo["productos"]) == 2

    def test_filtro_por_nombre(self, client: TestClient, db_session, categoria_prueba, usuario_vendedor):
        _crear_producto(db_session, categoria_prueba.id, "Piñata Mickey Mouse")
        _crear_producto(db_session, categoria_prueba.id, "Globo metalizado")
        token = obtener_token(client, usuario_vendedor.username)

        respuesta = client.get(
            "/productos", params={"q": "mickey"}, headers={"Authorization": f"Bearer {token}"}
        )

        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert cuerpo["total"] == 1
        assert cuerpo["productos"][0]["nombre"] == "Piñata Mickey Mouse"

    def test_productos_inactivos_no_aparecen_por_defecto(
        self, client: TestClient, db_session, categoria_prueba, usuario_vendedor
    ):
        _crear_producto(db_session, categoria_prueba.id, "Producto descontinuado", activo=False)
        token = obtener_token(client, usuario_vendedor.username)

        respuesta = client.get("/productos", headers={"Authorization": f"Bearer {token}"})

        assert respuesta.status_code == 200
        assert respuesta.json()["total"] == 0

    def test_paginacion(self, client: TestClient, db_session, categoria_prueba, usuario_vendedor):
        for i in range(5):
            _crear_producto(db_session, categoria_prueba.id, f"Producto {i}")
        token = obtener_token(client, usuario_vendedor.username)

        respuesta = client.get(
            "/productos",
            params={"pagina": 2, "tamano_pagina": 2},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert cuerpo["total"] == 5
        assert len(cuerpo["productos"]) == 2

    def test_requiere_autenticacion(self, client: TestClient):
        respuesta = client.get("/productos")
        assert respuesta.status_code == 401


class TestStockMinimo:
    """RF-007: configurar stock minimo por producto."""

    def test_administrador_puede_actualizar_stock_minimo(
        self, client: TestClient, db_session, categoria_prueba, usuario_administrador
    ):
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata Mickey Mouse", stock_minimo=5)
        token = obtener_token(client, usuario_administrador.username)

        respuesta = client.patch(
            f"/productos/{producto.id}/stock-minimo",
            json={"stock_minimo": 12},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert respuesta.status_code == 200
        assert respuesta.json()["stock_minimo"] == 12

    def test_vendedor_no_puede_actualizar_stock_minimo(
        self, client: TestClient, db_session, categoria_prueba, usuario_vendedor
    ):
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata Mickey Mouse")
        token = obtener_token(client, usuario_vendedor.username)

        respuesta = client.patch(
            f"/productos/{producto.id}/stock-minimo",
            json={"stock_minimo": 12},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert respuesta.status_code == 403

    def test_producto_inexistente_da_404(self, client: TestClient, usuario_administrador):
        token = obtener_token(client, usuario_administrador.username)

        respuesta = client.patch(
            "/productos/999999/stock-minimo",
            json={"stock_minimo": 12},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert respuesta.status_code == 404

    def test_stock_minimo_negativo_es_rechazado(
        self, client: TestClient, db_session, categoria_prueba, usuario_administrador
    ):
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata Mickey Mouse")
        token = obtener_token(client, usuario_administrador.username)

        respuesta = client.patch(
            f"/productos/{producto.id}/stock-minimo",
            json={"stock_minimo": -1},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert respuesta.status_code == 422


class TestAjustesManuales:
    """RF-009: ajustes manuales de inventario con motivo registrado."""

    def test_entrada_incrementa_stock(self, client: TestClient, db_session, categoria_prueba, usuario_vendedor):
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata Mickey Mouse", stock_actual=10)
        token = obtener_token(client, usuario_vendedor.username)

        respuesta = client.post(
            f"/productos/{producto.id}/ajustes",
            json={"tipo": "entrada", "cantidad": 5, "motivo": "Conteo fisico encontro unidades de mas"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert respuesta.status_code == 201
        cuerpo = respuesta.json()
        assert cuerpo["cantidad"] == 5
        db_session.refresh(producto)
        assert producto.stock_actual == 15

    def test_merma_decrementa_stock(self, client: TestClient, db_session, categoria_prueba, usuario_vendedor):
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata Mickey Mouse", stock_actual=10)
        token = obtener_token(client, usuario_vendedor.username)

        respuesta = client.post(
            f"/productos/{producto.id}/ajustes",
            json={"tipo": "merma", "cantidad": -3, "motivo": "Piñatas dañadas por humedad"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert respuesta.status_code == 201
        db_session.refresh(producto)
        assert producto.stock_actual == 7

    def test_entrada_con_cantidad_negativa_es_rechazada(
        self, client: TestClient, db_session, categoria_prueba, usuario_vendedor
    ):
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata Mickey Mouse", stock_actual=10)
        token = obtener_token(client, usuario_vendedor.username)

        respuesta = client.post(
            f"/productos/{producto.id}/ajustes",
            json={"tipo": "entrada", "cantidad": -5, "motivo": "Motivo invalido"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert respuesta.status_code == 400

    def test_merma_no_puede_dejar_stock_negativo(
        self, client: TestClient, db_session, categoria_prueba, usuario_vendedor
    ):
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata Mickey Mouse", stock_actual=2)
        token = obtener_token(client, usuario_vendedor.username)

        respuesta = client.post(
            f"/productos/{producto.id}/ajustes",
            json={"tipo": "merma", "cantidad": -5, "motivo": "Se perdieron mas de las que hay"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert respuesta.status_code == 409

    def test_motivo_vacio_es_rechazado(self, client: TestClient, db_session, categoria_prueba, usuario_vendedor):
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata Mickey Mouse")
        token = obtener_token(client, usuario_vendedor.username)

        respuesta = client.post(
            f"/productos/{producto.id}/ajustes",
            json={"tipo": "merma", "cantidad": -1, "motivo": ""},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert respuesta.status_code == 422

    def test_historial_de_ajustes_del_mas_reciente_al_mas_antiguo(
        self, client: TestClient, db_session, categoria_prueba, usuario_vendedor
    ):
        producto = _crear_producto(db_session, categoria_prueba.id, "Piñata Mickey Mouse", stock_actual=10)
        token = obtener_token(client, usuario_vendedor.username)
        headers = {"Authorization": f"Bearer {token}"}

        client.post(
            f"/productos/{producto.id}/ajustes",
            json={"tipo": "entrada", "cantidad": 5, "motivo": "Primer ajuste"},
            headers=headers,
        )
        client.post(
            f"/productos/{producto.id}/ajustes",
            json={"tipo": "merma", "cantidad": -2, "motivo": "Segundo ajuste"},
            headers=headers,
        )

        respuesta = client.get(f"/productos/{producto.id}/ajustes", headers=headers)

        assert respuesta.status_code == 200
        motivos = [a["motivo"] for a in respuesta.json()]
        assert motivos == ["Segundo ajuste", "Primer ajuste"]


class TestAlertasStockBajo:
    """RF-008: alerta automatica cuando un producto alcanza el stock minimo."""

    def test_crea_notificacion_para_producto_bajo_el_minimo(self, db_session, categoria_prueba):
        _crear_producto(db_session, categoria_prueba.id, "Piñata Mickey Mouse", stock_actual=2, stock_minimo=5)

        creadas = revisar_stock_bajo_impl(db_session)

        assert creadas == 1
        notificacion = db_session.query(Notificacion).one()
        assert notificacion.tipo == TipoNotificacion.STOCK_BAJO
        assert not notificacion.leida

    def test_no_duplica_notificacion_ya_existente_sin_leer(self, db_session, categoria_prueba):
        _crear_producto(db_session, categoria_prueba.id, "Piñata Mickey Mouse", stock_actual=2, stock_minimo=5)

        revisar_stock_bajo_impl(db_session)
        creadas_segunda_corrida = revisar_stock_bajo_impl(db_session)

        assert creadas_segunda_corrida == 0
        assert db_session.query(Notificacion).count() == 1

    def test_no_alerta_productos_con_stock_suficiente(self, db_session, categoria_prueba):
        _crear_producto(db_session, categoria_prueba.id, "Piñata Mickey Mouse", stock_actual=20, stock_minimo=5)

        creadas = revisar_stock_bajo_impl(db_session)

        assert creadas == 0
        assert db_session.query(Notificacion).count() == 0

    def test_vuelve_a_alertar_tras_marcar_leida_la_anterior(self, db_session, categoria_prueba):
        _crear_producto(db_session, categoria_prueba.id, "Piñata Mickey Mouse", stock_actual=2, stock_minimo=5)

        revisar_stock_bajo_impl(db_session)
        db_session.query(Notificacion).update({Notificacion.leida: True})
        db_session.commit()
        creadas_segunda_corrida = revisar_stock_bajo_impl(db_session)

        assert creadas_segunda_corrida == 1
        assert db_session.query(Notificacion).count() == 2
