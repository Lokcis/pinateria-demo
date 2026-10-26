"""Pruebas de aceptacion de HU-09 (modulo de ganancias) — Adendo v2, Fase A3 (RF-037 a RF-040).

Cada clase cita, en su docstring, el criterio de `docs/02-historias-de-usuario.md`
(seccion 3.9) que cubre.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.producto import TipoProducto
from app.models.producto_componente import ProductoComponente
from tests.conftest import obtener_token, pagos_en_efectivo
from tests.test_hu01_venta import _crear_producto

D = Decimal


def _auth(client: TestClient, usuario) -> dict[str, str]:
    """Devuelve el header Authorization para el usuario dado."""
    return {"Authorization": f"Bearer {obtener_token(client, usuario.username)}"}


def _producto(db_session: Session, categoria_id: int, nombre: str, precio: str, costo: str | None, **kwargs):
    """Crea un producto con stock 50 y el costo dado."""
    producto = _crear_producto(db_session, categoria_id, nombre, precio, 50, **kwargs)
    producto.costo_unitario = D(costo) if costo is not None else None
    db_session.commit()
    return producto


def _vender(client, headers, lineas, total, descuento=None):
    """Hace `POST /ventas` en efectivo exacto; `lineas` es [(producto_id, cantidad)]."""
    cuerpo = {
        "detalles": [{"producto_id": p, "cantidad": c} for p, c in lineas],
        "pagos": pagos_en_efectivo(total),
    }
    if descuento:
        cuerpo["descuento"] = descuento
    respuesta = client.post("/ventas", json=cuerpo, headers=headers)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _claves(objeto) -> set[str]:
    """Todas las claves de un JSON anidado."""
    if isinstance(objeto, dict):
        return set(objeto) | set().union(*(_claves(v) for v in objeto.values()))
    if isinstance(objeto, list):
        return set().union(*(_claves(v) for v in objeto)) if objeto else set()
    return set()


class TestAcceso:
    """HU-09: "el vendedor reciba 403 al consultar costos y ganancias ...; solo el administrador y
    el propietario acceden". Modificar costos es solo del administrador."""

    @pytest.mark.parametrize("ruta", ["/costos", "/ganancias"])
    def test_administrador_y_propietario_consultan(self, client, usuario_administrador, usuario_propietario, ruta):
        assert client.get(ruta, headers=_auth(client, usuario_administrador)).status_code == 200
        assert client.get(ruta, headers=_auth(client, usuario_propietario)).status_code == 200

    @pytest.mark.parametrize("ruta", ["/costos", "/ganancias"])
    def test_vendedor_403_y_sin_token_401(self, client, usuario_vendedor, ruta):
        assert client.get(ruta, headers=_auth(client, usuario_vendedor)).status_code == 403
        assert client.get(ruta).status_code == 401

    def test_solo_el_administrador_modifica(
        self, client, db_session, categoria_prueba, usuario_vendedor, usuario_propietario
    ):
        producto = _producto(db_session, categoria_prueba.id, "Globo", "1000", None)
        for usuario in (usuario_vendedor, usuario_propietario):
            headers = _auth(client, usuario)
            assert client.patch(
                f"/productos/{producto.id}/costo", json={"costo_unitario": "500"}, headers=headers
            ).status_code == 403
            assert client.post("/costos/completar-ventas", headers=headers).status_code == 403


class TestCostos:
    """HU-09: "el administrador pueda registrar a mano el costo de cada producto y que, para una
    ancheta, el sistema muestre un costo sugerido (suma de los costos de sus componentes)"."""

    def test_guardar_y_quitar_el_costo(self, client, db_session, categoria_prueba, usuario_administrador):
        producto = _producto(db_session, categoria_prueba.id, "Globo", "1000", None)
        headers = _auth(client, usuario_administrador)

        guardado = client.patch(f"/productos/{producto.id}/costo", json={"costo_unitario": "450.50"}, headers=headers)
        assert guardado.status_code == 200
        assert D(guardado.json()["costo_unitario"]) == D("450.50")

        quitado = client.patch(f"/productos/{producto.id}/costo", json={"costo_unitario": None}, headers=headers)
        assert quitado.json()["costo_unitario"] is None

    @pytest.mark.parametrize("costo", ["-1", "10.555"])
    def test_costo_invalido_es_422(self, client, db_session, categoria_prueba, usuario_administrador, costo):
        producto = _producto(db_session, categoria_prueba.id, "Globo", "1000", None)
        respuesta = client.patch(
            f"/productos/{producto.id}/costo", json={"costo_unitario": costo}, headers=_auth(client, usuario_administrador)
        )
        assert respuesta.status_code == 422

    def test_producto_inexistente_es_404(self, client, usuario_administrador):
        respuesta = client.patch(
            "/productos/999999/costo", json={"costo_unitario": "1"}, headers=_auth(client, usuario_administrador)
        )
        assert respuesta.status_code == 404

    def test_costo_sugerido_de_una_ancheta_e_incompleto(
        self, client, db_session, categoria_prueba, usuario_administrador
    ):
        globo = _producto(db_session, categoria_prueba.id, "Globo", "1000", "300")
        vela = _producto(db_session, categoria_prueba.id, "Vela", "800", None)
        ancheta = _producto(db_session, categoria_prueba.id, "Ancheta", "9000", None, tipo=TipoProducto.ANCHETA)
        db_session.add(ProductoComponente(producto_padre_id=ancheta.id, producto_componente_id=globo.id, cantidad=3))
        db_session.add(ProductoComponente(producto_padre_id=ancheta.id, producto_componente_id=vela.id, cantidad=2))
        db_session.commit()
        headers = _auth(client, usuario_administrador)

        fila = next(p for p in client.get("/costos", headers=headers).json()["productos"] if p["nombre"] == "Ancheta")
        assert (fila["costo_sugerido"], fila["sugerido_incompleto"]) == (None, True)

        client.patch(f"/productos/{vela.id}/costo", json={"costo_unitario": "250"}, headers=headers)
        fila = next(p for p in client.get("/costos", headers=headers).json()["productos"] if p["nombre"] == "Ancheta")
        assert (D(fila["costo_sugerido"]), fila["sugerido_incompleto"]) == (D("1400"), False)  # 3 x 300 + 2 x 250
        globo_fila = next(p for p in client.get("/costos", headers=headers).json()["productos"] if p["nombre"] == "Globo")
        assert (globo_fila["costo_sugerido"], globo_fila["sugerido_incompleto"]) == (None, False)

    def test_filtros_sin_costo_e_inactivos(self, client, db_session, categoria_prueba, usuario_propietario):
        _producto(db_session, categoria_prueba.id, "Con costo", "1000", "500")
        _producto(db_session, categoria_prueba.id, "Sin costo", "1000", None)
        inactivo = _producto(db_session, categoria_prueba.id, "Inactivo", "1000", None)
        inactivo.activo = False
        db_session.commit()
        headers = _auth(client, usuario_propietario)

        nombres = lambda params: [p["nombre"] for p in client.get("/costos", params=params, headers=headers).json()["productos"]]  # noqa: E731
        assert nombres({}) == ["Con costo", "Sin costo"]
        assert nombres({"solo_sin_costo": True}) == ["Sin costo"]
        assert nombres({"solo_sin_costo": True, "incluir_inactivos": True}) == ["Inactivo", "Sin costo"]


class TestMargen:
    """HU-09: "el margen bruto de una linea sea el subtotal menos el descuento prorrateado menos el
    costo por la cantidad, y que los productos sin costo se excluyan del margen y se informen como
    'sin costo'"; "cada linea vendida guarde el costo vigente y que cambiar el costo de un producto
    despues no altere el margen de las ventas pasadas"."""

    def test_margen_con_descuento_repartido_y_lineas_sin_costo(
        self, client, db_session, categoria_prueba, usuario_administrador, usuario_propietario
    ):
        piñata = _producto(db_session, categoria_prueba.id, "Piñata", "60000", "35000")
        globo = _producto(db_session, categoria_prueba.id, "Globo", "40000", None)
        _vender(
            client, _auth(client, usuario_administrador), [(piñata.id, 1), (globo.id, 1)], "90000",
            descuento={"origen": "manual", "tipo": "monto", "valor": "10000"},
        )

        cuerpo = client.get("/ganancias", headers=_auth(client, usuario_propietario)).json()

        assert {k: D(v) for k, v in cuerpo["resumen"].items()} == {
            "ingreso_neto": D("54000"), "costo_total": D("35000"), "margen": D("19000"), "margen_porcentaje": D("35.2")
        }
        assert (cuerpo["sin_costo"]["lineas"], D(cuerpo["sin_costo"]["ingreso_neto"])) == (1, D("36000"))
        assert [(p["nombre"], p["unidades"], D(p["margen"])) for p in cuerpo["por_producto"]] == [("Piñata", 1, D("19000"))]

    def test_cambiar_el_costo_despues_no_altera_ventas_pasadas(
        self, client, db_session, categoria_prueba, usuario_administrador
    ):
        globo = _producto(db_session, categoria_prueba.id, "Globo", "1000", "400")
        headers = _auth(client, usuario_administrador)
        _vender(client, headers, [(globo.id, 2)], "2000")

        client.patch(f"/productos/{globo.id}/costo", json={"costo_unitario": "900"}, headers=headers)
        _vender(client, headers, [(globo.id, 1)], "1000")

        resumen = client.get("/ganancias", headers=headers).json()["resumen"]
        # 2 x (1000 - 400) + 1 x (1000 - 900) = 1300
        assert D(resumen["margen"]) == D("1300")

    def test_el_ajuste_por_redondeo_no_entra_en_el_margen(
        self, client, db_session, categoria_prueba, usuario_administrador
    ):
        dulce = _producto(db_session, categoria_prueba.id, "Dulce", "1010", "500")
        _vender(client, _auth(client, usuario_administrador), [(dulce.id, 3)], "3050")  # 3030 -> 3050

        resumen = client.get("/ganancias", headers=_auth(client, usuario_administrador)).json()["resumen"]
        assert (D(resumen["ingreso_neto"]), D(resumen["margen"])) == (D("3030"), D("1530"))

    def test_por_dia_incluye_los_dias_sin_ventas_en_cero(
        self, client, db_session, categoria_prueba, usuario_administrador
    ):
        globo = _producto(db_session, categoria_prueba.id, "Globo", "1000", "400")
        headers = _auth(client, usuario_administrador)
        _vender(client, headers, [(globo.id, 1)], "1000")
        hoy = date.fromisoformat(client.get("/ganancias", headers=headers).json()["hasta"])

        cuerpo = client.get(
            "/ganancias", params={"desde": (hoy - timedelta(days=2)).isoformat(), "hasta": hoy.isoformat()}, headers=headers
        ).json()

        assert [(d["fecha"], D(d["margen"])) for d in cuerpo["por_dia"]] == [
            ((hoy - timedelta(days=2)).isoformat(), 0),
            ((hoy - timedelta(days=1)).isoformat(), 0),
            (hoy.isoformat(), D("600")),
        ]
        assert cuerpo["por_dia"][0]["margen_porcentaje"] is None

    def test_rango_futuro_es_422(self, client, usuario_administrador):
        mañana = (date.today() + timedelta(days=2)).isoformat()
        respuesta = client.get("/ganancias", params={"hasta": mañana}, headers=_auth(client, usuario_administrador))
        assert respuesta.status_code == 422


class TestCompletarVentasPasadas:
    """Decision del 08-10-2026: el administrador puede llenar, con el costo actual, solo las lineas
    de ventas pasadas que no tienen costo; las que ya tienen costo no se tocan."""

    def test_completa_solo_las_lineas_sin_costo(self, client, db_session, categoria_prueba, usuario_administrador):
        con_costo = _producto(db_session, categoria_prueba.id, "Piñata", "5000", "3000")
        sin_costo = _producto(db_session, categoria_prueba.id, "Globo", "1000", None)
        headers = _auth(client, usuario_administrador)
        _vender(client, headers, [(con_costo.id, 1), (sin_costo.id, 2)], "7000")

        client.patch(f"/productos/{sin_costo.id}/costo", json={"costo_unitario": "300"}, headers=headers)
        client.patch(f"/productos/{con_costo.id}/costo", json={"costo_unitario": "4500"}, headers=headers)
        assert client.get("/costos", headers=headers).json()["lineas_por_completar"] == 1

        assert client.post("/costos/completar-ventas", headers=headers).json() == {"lineas_completadas": 1}
        assert client.post("/costos/completar-ventas", headers=headers).json() == {"lineas_completadas": 0}

        cuerpo = client.get("/ganancias", headers=headers).json()
        # Piñata conserva 3000 (no se toca); Globo toma 300: 5000 - 3000 + 2 x (1000 - 300) = 3400
        assert D(cuerpo["resumen"]["margen"]) == D("3400")
        assert cuerpo["sin_costo"]["lineas"] == 0


class TestElVendedorNoVeCostos:
    """HU-09: el vendedor "no vea el costo en ninguna pantalla" (RF-040)."""

    def test_ninguna_respuesta_del_vendedor_incluye_costos(
        self, client, db_session, categoria_prueba, usuario_vendedor
    ):
        globo = _producto(db_session, categoria_prueba.id, "Globo", "1000", "400", codigo_barras="7700000000001")
        headers = _auth(client, usuario_vendedor)

        respuestas = [
            client.get("/productos", headers=headers).json(),
            client.get("/productos/buscar", params={"q": "glo"}, headers=headers).json(),
            client.get("/productos/buscar", params={"q": "7700000000001"}, headers=headers).json(),
            _vender(client, headers, [(globo.id, 1)], "1000"),
            client.get("/ventas/hoy", headers=headers).json(),
        ]

        for respuesta in respuestas:
            assert not any("costo" in clave for clave in _claves(respuesta)), respuesta
