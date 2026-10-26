"""Pruebas de la Fase G3 del Adendo v3: ganancia neta y resultado de caja en `GET /ganancias` (RF-067).

La ganancia neta resta al margen bruto solo los gastos operativos (sin las compras de mercancia, que ya estan en
el costo de lo vendido); el resultado de caja es lo cobrado menos todos los gastos, compras incluidas.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.categoria_gasto import CategoriaGasto
from app.services.gastos import hoy_en_bogota
from tests.conftest import obtener_token, pagos_en_efectivo
from tests.test_g1_gastos import _compra_recibida
from tests.test_hu01_venta import _crear_producto

D = Decimal


def _auth(client, usuario) -> dict[str, str]:
    """Devuelve el header Authorization para el usuario dado."""
    return {"Authorization": f"Bearer {obtener_token(client, usuario.username)}"}


@pytest.fixture
def cat_arriendo(db_session: Session) -> CategoriaGasto:
    """Una categoria de gasto operativo."""
    categoria = CategoriaGasto(nombre="Arriendo")
    db_session.add(categoria)
    db_session.commit()
    return categoria


@pytest.fixture
def cat_sistema(db_session: Session) -> CategoriaGasto:
    """La categoria de sistema "Compra de mercancía"."""
    categoria = CategoriaGasto(nombre="Compra de mercancía", es_sistema=True)
    db_session.add(categoria)
    db_session.commit()
    return categoria


def _producto(db_session, categoria_id, nombre="Piñata", precio="10000.00", costo="6000"):
    """Crea un producto de $10.000 con costo (o sin costo si `costo` es None)."""
    producto = _crear_producto(db_session, categoria_id, nombre, precio, 100)
    producto.costo_unitario = D(costo) if costo is not None else None
    db_session.commit()
    return producto


def _vender(client, headers, producto, cantidad, pagos):
    """Registra una venta; falla si no responde 201."""
    respuesta = client.post(
        "/ventas",
        json={"detalles": [{"producto_id": producto.id, "cantidad": cantidad}], "pagos": pagos},
        headers=headers,
    )
    assert respuesta.status_code == 201, respuesta.text


def _gastar(client, headers, categoria_id, monto, metodo="efectivo", **extra):
    """Registra un gasto; falla si no responde 201."""
    cuerpo = {"categoria_id": categoria_id, "descripcion": "Pago del mes", "monto": monto, "metodo_pago": metodo}
    cuerpo.update(extra)
    respuesta = client.post("/gastos", json=cuerpo, headers=headers)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _neta(client, headers, **params) -> dict:
    """Devuelve `neta` de `GET /ganancias` del dia de hoy (o del rango dado)."""
    respuesta = client.get("/ganancias", params=params, headers=headers)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["neta"]


class TestGananciaNeta:
    """RF-067: ganancia neta = margen bruto − gastos operativos; el resultado de caja aparte."""

    def test_formula_con_numeros_exactos(
        self, client, db_session, categoria_prueba, cat_arriendo, usuario_administrador
    ):
        admin = _auth(client, usuario_administrador)
        producto = _producto(db_session, categoria_prueba.id)
        # Vende 3 × $10.000 con costo $6.000: ingreso 30.000, costo 18.000, margen 12.000.
        _vender(client, admin, producto, 3, pagos_en_efectivo("30000"))
        # Un gasto operativo de $5.000 y una compra de mercancía de $10.000 (recibida en efectivo).
        _gastar(client, admin, cat_arriendo.id, "5000")
        _compra_recibida(client, db_session, admin, categoria_prueba, "1000", 10, {"metodo_pago": "efectivo"})

        neta = _neta(client, admin)

        assert D(neta["margen_bruto"]) == 12000
        assert D(neta["gastos_operativos"]) == 5000
        assert D(neta["ganancia_neta"]) == 7000  # 12.000 − 5.000: la compra NO resta (ya esta en el costo).
        assert neta["incompleta"] is False
        assert D(neta["ventas_cobradas"]) == 30000
        assert D(neta["compras_recibidas"]) == 10000
        assert D(neta["gastos_totales"]) == 15000
        assert D(neta["resultado_de_caja"]) == 15000  # 30.000 − (5.000 + 10.000): aqui la compra SI resta.

    def test_sin_gastos_la_neta_es_el_margen(self, client, db_session, categoria_prueba, usuario_administrador):
        admin = _auth(client, usuario_administrador)
        _vender(client, admin, _producto(db_session, categoria_prueba.id), 3, pagos_en_efectivo("30000"))

        neta = _neta(client, admin)

        assert D(neta["ganancia_neta"]) == D(neta["margen_bruto"]) == 12000
        assert D(neta["gastos_operativos"]) == 0 and D(neta["compras_recibidas"]) == 0

    def test_la_neta_puede_ser_negativa(self, client, db_session, categoria_prueba, cat_arriendo, usuario_administrador):
        admin = _auth(client, usuario_administrador)
        _vender(client, admin, _producto(db_session, categoria_prueba.id), 3, pagos_en_efectivo("30000"))
        _gastar(client, admin, cat_arriendo.id, "20000")

        assert D(_neta(client, admin)["ganancia_neta"]) == -8000

    def test_los_gastos_anulados_no_restan(self, client, db_session, categoria_prueba, cat_arriendo, usuario_administrador):
        admin = _auth(client, usuario_administrador)
        _vender(client, admin, _producto(db_session, categoria_prueba.id), 3, pagos_en_efectivo("30000"))
        gasto = _gastar(client, admin, cat_arriendo.id, "5000")
        assert client.post(f"/gastos/{gasto['id']}/anular", json={"motivo": "Error de digitación"}, headers=admin).status_code == 200

        neta = _neta(client, admin)

        assert D(neta["gastos_operativos"]) == 0 and D(neta["gastos_totales"]) == 0
        assert D(neta["ganancia_neta"]) == 12000

    def test_un_gasto_manual_en_la_categoria_de_sistema_cuenta_como_mercancia_no_como_operativo(
        self, client, db_session, categoria_prueba, cat_sistema, usuario_administrador
    ):
        admin = _auth(client, usuario_administrador)
        _vender(client, admin, _producto(db_session, categoria_prueba.id), 3, pagos_en_efectivo("30000"))
        _gastar(client, admin, cat_sistema.id, "4000")

        neta = _neta(client, admin)

        assert D(neta["gastos_operativos"]) == 0
        assert D(neta["ganancia_neta"]) == 12000
        assert D(neta["compras_recibidas"]) == 4000 and D(neta["gastos_totales"]) == 4000
        assert D(neta["resultado_de_caja"]) == 26000

    def test_los_gastos_se_filtran_por_su_fecha_contable(
        self, client, db_session, categoria_prueba, cat_arriendo, usuario_administrador
    ):
        admin = _auth(client, usuario_administrador)
        _vender(client, admin, _producto(db_session, categoria_prueba.id), 3, pagos_en_efectivo("30000"))
        ayer = (hoy_en_bogota() - timedelta(days=1)).isoformat()
        _gastar(client, admin, cat_arriendo.id, "5000", fecha=ayer)

        hoy = _neta(client, admin)
        rango = _neta(client, admin, desde=ayer, hasta=hoy_en_bogota().isoformat())

        assert D(hoy["gastos_operativos"]) == 0
        assert D(rango["gastos_operativos"]) == 5000 and D(rango["ganancia_neta"]) == 7000

    def test_con_ventas_sin_costo_la_neta_queda_incompleta(self, client, db_session, categoria_prueba, usuario_administrador):
        admin = _auth(client, usuario_administrador)
        _vender(client, admin, _producto(db_session, categoria_prueba.id, "Con costo"), 3, pagos_en_efectivo("30000"))
        _vender(client, admin, _producto(db_session, categoria_prueba.id, "Sin costo", costo=None), 1, pagos_en_efectivo("10000"))

        neta = _neta(client, admin)

        assert neta["incompleta"] is True
        assert D(neta["margen_bruto"]) == 12000  # Lo vendido sin costo no entra en el margen ...
        assert D(neta["ventas_cobradas"]) == 40000  # ... pero si en lo cobrado.

    def test_lo_cobrado_cuenta_todos_los_medios_de_pago_y_sin_vueltas(
        self, client, db_session, categoria_prueba, usuario_administrador
    ):
        admin = _auth(client, usuario_administrador)
        producto = _producto(db_session, categoria_prueba.id)
        _vender(client, admin, producto, 2, [{"metodo_pago": "efectivo", "monto": "10000", "monto_recibido": "50000"},
                                             {"metodo_pago": "tarjeta", "monto": "10000"}])

        assert D(_neta(client, admin)["ventas_cobradas"]) == 20000


class TestPermisos:
    """RF-040 / RF-067: la ganancia neta es del administrador y el propietario; el vendedor recibe 403."""

    def test_vendedor_403(self, client, usuario_vendedor):
        assert client.get("/ganancias", headers=_auth(client, usuario_vendedor)).status_code == 403

    def test_propietario_la_ve(self, client, db_session, categoria_prueba, cat_arriendo, usuario_administrador, usuario_propietario):
        admin = _auth(client, usuario_administrador)
        _vender(client, admin, _producto(db_session, categoria_prueba.id), 3, pagos_en_efectivo("30000"))
        _gastar(client, admin, cat_arriendo.id, "5000")

        neta = _neta(client, _auth(client, usuario_propietario))

        assert D(neta["ganancia_neta"]) == 7000
