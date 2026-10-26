"""Pruebas de aceptacion de HU-13 (caja y corte de caja) — Adendo v3, Fase G2 (RF-069 a RF-074).

Cada clase cita, en su docstring, el criterio de `docs/02-historias-de-usuario.md` (seccion 3.13) que cubre.

Sobre el reloj: estas pruebas corren dentro de una sola transaccion, y `now()` de Postgres vale lo mismo en toda
ella. Por eso abrir, vender, gastar y cerrar ocurren "en el mismo instante" (los limites del periodo son
inclusivos) y, cuando una prueba necesita que algo pase ANTES de abrir o DESPUES de cerrar, mueve esa marca de
tiempo con `_mover` en vez de esperar.
"""

import csv
import io
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.categoria_gasto import CategoriaGasto
from app.models.corte_caja import CorteCaja, EstadoCorteCaja
from app.models.usuario import RolUsuario
from app.services.gastos import hoy_en_bogota
from tests.conftest import _crear_usuario, obtener_token, pagos_en_efectivo
from tests.test_g1_gastos import _compra_recibida
from tests.test_hu01_venta import _crear_producto

D = Decimal


def _auth(client, usuario) -> dict[str, str]:
    """Devuelve el header Authorization para el usuario dado."""
    return {"Authorization": f"Bearer {obtener_token(client, usuario.username)}"}


@pytest.fixture
def categoria_gasto(db_session: Session) -> CategoriaGasto:
    """Una categoria de gasto editable y activa."""
    categoria = CategoriaGasto(nombre="Arriendo")
    db_session.add(categoria)
    db_session.commit()
    return categoria


@pytest.fixture
def otro_vendedor(db_session: Session):
    """Un segundo vendedor, para probar que cada uno ve solo sus cortes."""
    return _crear_usuario(db_session, "vendedor.otro", RolUsuario.VENDEDOR)


@pytest.fixture
def producto(db_session: Session, categoria_prueba):
    """Un producto de $5.000 con existencias de sobra."""
    return _crear_producto(db_session, categoria_prueba.id, "Globo metalizado", "5000.00", 500)


def _abrir(client, headers, base="100000"):
    """Abre la caja y devuelve la respuesta."""
    return client.post("/caja/abrir", json={"base_inicial": base}, headers=headers)


def _abrir_ok(client, headers, base="100000") -> dict:
    """Abre la caja; falla si el servidor no responde 201."""
    respuesta = _abrir(client, headers, base)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _cerrar(client, headers, contado, observaciones=None):
    """Cierra la caja y devuelve la respuesta."""
    cuerpo = {"efectivo_contado": contado}
    if observaciones is not None:
        cuerpo["observaciones"] = observaciones
    return client.post("/caja/cerrar", json=cuerpo, headers=headers)


def _cerrar_ok(client, headers, contado, observaciones=None) -> dict:
    """Cierra la caja; falla si el servidor no responde 200."""
    respuesta = _cerrar(client, headers, contado, observaciones)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _vender(client, headers, producto, cantidad, pagos):
    """Registra una venta de `cantidad` unidades con los pagos dados; falla si no responde 201."""
    respuesta = client.post(
        "/ventas",
        json={"detalles": [{"producto_id": producto.id, "cantidad": cantidad}], "pagos": pagos},
        headers=headers,
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _gastar(client, headers, categoria_id, monto, metodo="efectivo", **extra) -> dict:
    """Registra un gasto; falla si el servidor no responde 201."""
    cuerpo = {"categoria_id": categoria_id, "descripcion": "Pago del mes", "monto": monto, "metodo_pago": metodo}
    cuerpo.update(extra)
    respuesta = client.post("/gastos", json=cuerpo, headers=headers)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _movimiento(client, headers, tipo, monto, motivo="Consignación al banco"):
    """Registra un ingreso o retiro y devuelve la respuesta."""
    return client.post("/caja/movimientos", json={"tipo": tipo, "monto": monto, "motivo": motivo}, headers=headers)


def _mover(db_session: Session, tabla: str, columna: str, id_: int, intervalo: str) -> None:
    """Corre una marca de tiempo (por ejemplo, '-1 day') para simular que algo paso antes o despues."""
    db_session.execute(
        text(f"UPDATE {tabla} SET {columna} = {columna} + CAST(:i AS interval) WHERE id = :id"),
        {"i": intervalo, "id": id_},
    )


def _actual(client, headers) -> dict:
    """Devuelve `GET /caja/actual`."""
    respuesta = client.get("/caja/actual", headers=headers)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


class TestAcceso:
    """HU-13: el administrador y el vendedor manejan la caja; el propietario solo consulta."""

    def test_propietario_consulta_pero_no_opera(self, client, usuario_administrador, usuario_propietario):
        _abrir_ok(client, _auth(client, usuario_administrador))
        h = _auth(client, usuario_propietario)

        assert client.get("/caja/actual", headers=h).status_code == 200
        assert client.get("/caja/cortes", headers=h).status_code == 200
        assert _abrir(client, h).status_code == 403
        assert _movimiento(client, h, "ingreso", "50000").status_code == 403
        assert _cerrar(client, h, "100000").status_code == 403

    def test_vendedor_no_exporta(self, client, usuario_vendedor):
        assert client.get("/caja/cortes/exportar", headers=_auth(client, usuario_vendedor)).status_code == 403

    def test_sin_token_401(self, client):
        assert client.get("/caja/actual").status_code == 401
        assert client.post("/caja/abrir", json={"base_inicial": "0"}).status_code == 401


class TestAbrirCaja:
    """HU-13: abrir la caja con la base; una sola caja abierta a la vez; la base en efectivo va en múltiplos de $50."""

    @pytest.mark.parametrize("rol", ["usuario_administrador", "usuario_vendedor"])
    def test_administrador_y_vendedor_abren_y_queda_quien_la_abrio(self, client, request, rol):
        usuario = request.getfixturevalue(rol)

        cuerpo = _abrir_ok(client, _auth(client, usuario), "150000")

        assert cuerpo["abierta"] is True
        assert cuerpo["corte"]["abierta_por"] == usuario.nombre
        assert cuerpo["corte"]["estado"] == "abierta"
        assert cuerpo["cifras"]["base_inicial"] == "150000.00"
        assert cuerpo["cifras"]["efectivo_esperado"] == "150000.00"

    def test_sin_caja_abierta_actual_lo_dice(self, client, usuario_vendedor):
        cuerpo = _actual(client, _auth(client, usuario_vendedor))

        assert cuerpo["abierta"] is False
        assert cuerpo["corte"] is None and cuerpo["cifras"] is None and cuerpo["movimientos"] == []

    def test_la_base_puede_ser_cero(self, client, usuario_vendedor):
        assert _abrir(client, _auth(client, usuario_vendedor), "0").status_code == 201

    @pytest.mark.parametrize("base", ["100025", "49", "100000.50", "-50"])
    def test_base_invalida_422(self, client, usuario_vendedor, base):
        assert _abrir(client, _auth(client, usuario_vendedor), base).status_code == 422

    def test_ya_hay_una_abierta_409(self, client, usuario_administrador, usuario_vendedor):
        _abrir_ok(client, _auth(client, usuario_administrador))

        respuesta = _abrir(client, _auth(client, usuario_vendedor), "50000")

        assert respuesta.status_code == 409
        assert "ya hay una caja abierta" in respuesta.json()["detail"].lower()

    def test_el_indice_unico_impide_dos_abiertas_aunque_se_salte_la_aplicacion(
        self, db_session: Session, usuario_administrador
    ):
        """Garantia de la base de datos (docs/12, seccion 9): una sola caja abierta."""
        db_session.add(CorteCaja(abierta_por_id=usuario_administrador.id, base_inicial=D("0")))
        db_session.commit()
        db_session.add(CorteCaja(abierta_por_id=usuario_administrador.id, base_inicial=D("0")))

        with pytest.raises(IntegrityError):
            db_session.commit()


class TestEfectivoEsperado:
    """HU-13: el efectivo esperado = base + ventas en efectivo + ingresos − gastos − compras − retiros."""

    def test_formula_con_numeros_exactos(
        self, client, db_session, categoria_prueba, categoria_gasto, producto, usuario_administrador, usuario_vendedor
    ):
        admin, vendedor = _auth(client, usuario_administrador), _auth(client, usuario_vendedor)
        _abrir_ok(client, vendedor, "100000")

        # Ventas: 20.000 en efectivo con vueltas (reciben 50.000: solo abonan 20.000) ...
        _vender(client, vendedor, producto, 4, [{"metodo_pago": "efectivo", "monto": "20000", "monto_recibido": "50000"}])
        # ... una mixta: 10.000 en efectivo + 15.000 con tarjeta ...
        _vender(
            client,
            vendedor,
            producto,
            5,
            [
                {"metodo_pago": "efectivo", "monto": "10000", "monto_recibido": "10000"},
                {"metodo_pago": "tarjeta", "monto": "15000"},
            ],
        )
        # ... y una por Nequi, que no toca el efectivo.
        _vender(client, vendedor, producto, 2, [{"metodo_pago": "transferencia", "plataforma": "nequi", "monto": "10000"}])
        # Gastos: solo cuenta el vigente en efectivo (5.000); el de tarjeta y el anulado no.
        _gastar(client, vendedor, categoria_gasto.id, "5000", "efectivo")
        _gastar(client, vendedor, categoria_gasto.id, "7000", "tarjeta")
        anulado = _gastar(client, admin, categoria_gasto.id, "3000", "efectivo")
        assert client.post(f"/gastos/{anulado['id']}/anular", json={"motivo": "Error de digitación"}, headers=admin).status_code == 200
        # Compras recibidas: 12.000 en efectivo cuentan; la de transferencia no.
        _compra_recibida(client, db_session, admin, categoria_prueba, "1200", 10, {"metodo_pago": "efectivo"})
        _compra_recibida(
            client, db_session, admin, categoria_prueba, "900", 10, {"metodo_pago": "transferencia", "plataforma": "nequi"}
        )
        # Movimientos manuales.
        assert _movimiento(client, vendedor, "ingreso", "20000", "Cambio para la caja").status_code == 201
        assert _movimiento(client, vendedor, "retiro", "30000").status_code == 201

        cifras = _actual(client, vendedor)["cifras"]

        assert D(cifras["base_inicial"]) == 100000
        assert D(cifras["ventas_efectivo"]) == 30000
        assert D(cifras["ingresos"]) == 20000
        assert D(cifras["gastos_efectivo"]) == 5000
        assert D(cifras["compras_efectivo"]) == 12000
        assert D(cifras["retiros"]) == 30000
        # 100.000 + 30.000 + 20.000 − 5.000 − 12.000 − 30.000
        assert D(cifras["efectivo_esperado"]) == 103000
        # Informativo, para el datafono y el banco.
        assert D(cifras["ventas_tarjeta"]) == 15000
        assert D(cifras["ventas_transferencia"]) == 10000

    def test_lo_anterior_a_la_apertura_no_cuenta(
        self, client, db_session, categoria_prueba, categoria_gasto, producto, usuario_administrador, usuario_vendedor
    ):
        admin, vendedor = _auth(client, usuario_administrador), _auth(client, usuario_vendedor)
        venta = _vender(client, vendedor, producto, 4, pagos_en_efectivo("20000"))
        gasto = _gastar(client, vendedor, categoria_gasto.id, "5000")
        compra = _compra_recibida(client, db_session, admin, categoria_prueba, "1200", 10, {"metodo_pago": "efectivo"})
        for tabla, columna, id_ in (
            ("ventas", "fecha", venta["id"]),
            ("gastos", "creado_en", gasto["id"]),
            ("compras", "recibida_en", compra["id"]),
        ):
            _mover(db_session, tabla, columna, id_, "-1 day")

        cuerpo = _abrir_ok(client, vendedor, "100000")

        cifras = cuerpo["cifras"]
        assert D(cifras["ventas_efectivo"]) == 0 and D(cifras["gastos_efectivo"]) == 0 and D(cifras["compras_efectivo"]) == 0
        assert D(cifras["efectivo_esperado"]) == 100000

    def test_el_gasto_cuenta_por_su_hora_de_registro_no_por_su_fecha_contable(
        self, client, categoria_gasto, usuario_administrador
    ):
        """Un gasto de ayer registrado hoy (con la caja abierta) sale hoy de la caja: es cuando se pagó."""
        admin = _auth(client, usuario_administrador)
        _abrir_ok(client, admin, "100000")
        ayer = (hoy_en_bogota() - timedelta(days=1)).isoformat()

        _gastar(client, admin, categoria_gasto.id, "8000", fecha=ayer)

        assert D(_actual(client, admin)["cifras"]["efectivo_esperado"]) == 92000

    def test_compra_anterior_sin_forma_de_pago_no_afecta_la_caja(
        self, client, db_session, categoria_prueba, usuario_administrador
    ):
        admin = _auth(client, usuario_administrador)
        compra = _compra_recibida(client, db_session, admin, categoria_prueba, "1200", 10, {"metodo_pago": "efectivo"})
        db_session.execute(
            text("UPDATE compras SET metodo_pago = NULL, recibida_en = NULL WHERE id = :id"), {"id": compra["id"]}
        )

        cuerpo = _abrir_ok(client, admin, "100000")

        assert D(cuerpo["cifras"]["compras_efectivo"]) == 0

    def test_la_venta_sin_conexion_cuenta_por_la_hora_en_que_se_hizo(
        self, client, db_session, producto, usuario_vendedor
    ):
        vendedor = _auth(client, usuario_vendedor)
        corte_id = _abrir_ok(client, vendedor, "100000")["corte"]["id"]
        _mover(db_session, "cortes_caja", "abierta_en", corte_id, "-5 hours")

        def enviar(horas_atras):
            return client.post(
                "/ventas",
                json={
                    "detalles": [{"producto_id": producto.id, "cantidad": 2}],
                    "pagos": pagos_en_efectivo("10000"),
                    "uuid_cliente": str(uuid.uuid4()),
                    "sin_conexion": {"fecha": (datetime.now(timezone.utc) - timedelta(hours=horas_atras)).isoformat()},
                },
                headers=vendedor,
            )

        assert enviar(2).status_code == 201  # Hecha durante el turno: cuenta.
        assert enviar(8).status_code == 201  # Hecha antes de abrir la caja: no cuenta.

        assert D(_actual(client, vendedor)["cifras"]["ventas_efectivo"]) == 10000


class TestMovimientosDeCaja:
    """HU-13: ingresos y retiros manuales con motivo, solo con la caja abierta y en múltiplos de $50."""

    def test_ingreso_y_retiro_mueven_el_esperado_y_quedan_en_la_lista(self, client, usuario_vendedor):
        h = _auth(client, usuario_vendedor)
        _abrir_ok(client, h, "100000")

        despues_ingreso = _movimiento(client, h, "ingreso", "20000", "cambio para la caja")
        despues_retiro = _movimiento(client, h, "retiro", "50000", "consignación al banco")

        assert despues_ingreso.status_code == 201 and despues_retiro.status_code == 201
        caja = despues_retiro.json()
        assert D(caja["cifras"]["efectivo_esperado"]) == 70000
        assert [(m["tipo"], D(m["monto"]), m["motivo"], m["usuario"]) for m in caja["movimientos"]] == [
            ("ingreso", 20000, "Cambio para la caja", usuario_vendedor.nombre),
            ("retiro", 50000, "Consignación al banco", usuario_vendedor.nombre),
        ]

    def test_sin_caja_abierta_409(self, client, usuario_vendedor):
        respuesta = _movimiento(client, _auth(client, usuario_vendedor), "ingreso", "20000")

        assert respuesta.status_code == 409

    @pytest.mark.parametrize("monto", ["20025", "0", "-50", "50.5"])
    def test_monto_invalido_422(self, client, usuario_vendedor, monto):
        h = _auth(client, usuario_vendedor)
        _abrir_ok(client, h)

        assert _movimiento(client, h, "retiro", monto).status_code == 422

    def test_el_motivo_es_obligatorio(self, client, usuario_vendedor):
        h = _auth(client, usuario_vendedor)
        _abrir_ok(client, h)

        assert _movimiento(client, h, "retiro", "50000", "").status_code == 422
        assert client.post("/caja/movimientos", json={"tipo": "retiro", "monto": "50000"}, headers=h).status_code == 422

    def test_tipo_desconocido_422(self, client, usuario_vendedor):
        h = _auth(client, usuario_vendedor)
        _abrir_ok(client, h)

        assert _movimiento(client, h, "prestamo", "50000").status_code == 422


class TestCerrarCaja:
    """HU-13: cerrar con el efectivo contado; la diferencia y la foto del corte; el cierre no se repite ni se edita."""

    @pytest.mark.parametrize(
        "contado, diferencia",
        [("130000", 0), ("131000", 1000), ("129000", -1000)],
        ids=["cuadra", "sobra", "falta"],
    )
    def test_diferencia_es_contado_menos_esperado(
        self, client, producto, usuario_vendedor, contado, diferencia
    ):
        h = _auth(client, usuario_vendedor)
        _abrir_ok(client, h, "100000")
        _vender(client, h, producto, 6, pagos_en_efectivo("30000"))

        corte = _cerrar_ok(client, h, contado)

        assert corte["estado"] == "cerrada"
        assert D(corte["efectivo_esperado"]) == 130000
        assert D(corte["efectivo_contado"]) == D(contado)
        assert D(corte["diferencia"]) == diferencia
        assert corte["cerrada_por"] == usuario_vendedor.nombre and corte["cerrada_en"] is not None

    def test_guarda_la_foto_de_todas_las_cifras(
        self, client, db_session, categoria_gasto, producto, usuario_administrador, usuario_vendedor
    ):
        admin, vendedor = _auth(client, usuario_administrador), _auth(client, usuario_vendedor)
        _abrir_ok(client, vendedor, "100000")
        _vender(client, vendedor, producto, 4, pagos_en_efectivo("20000"))
        _vender(client, vendedor, producto, 3, [{"metodo_pago": "tarjeta", "monto": "15000"}])
        _vender(client, vendedor, producto, 2, [{"metodo_pago": "transferencia", "plataforma": "daviplata", "monto": "10000"}])
        _gastar(client, vendedor, categoria_gasto.id, "5000")
        _movimiento(client, vendedor, "ingreso", "20000", "Cambio")
        _movimiento(client, vendedor, "retiro", "30000", "Consignación")

        corte = _cerrar_ok(client, admin, "105000", "todo en orden")

        cifras = corte["cifras"]
        assert [D(cifras[k]) for k in ("base_inicial", "ventas_efectivo", "ingresos", "gastos_efectivo", "compras_efectivo", "retiros")] == [
            100000, 20000, 20000, 5000, 0, 30000
        ]
        assert D(cifras["efectivo_esperado"]) == 105000
        assert D(cifras["ventas_tarjeta"]) == 15000 and D(cifras["ventas_transferencia"]) == 10000
        assert corte["observaciones"] == "Todo en orden"
        assert [m["tipo"] for m in corte["movimientos"]] == ["ingreso", "retiro"]
        assert corte["abierta_por"] == usuario_vendedor.nombre and corte["cerrada_por"] == usuario_administrador.nombre
        # Y queda guardada en la base, no solo en la respuesta.
        guardado = db_session.get(CorteCaja, corte["id"])
        assert guardado.estado == EstadoCorteCaja.CERRADA and guardado.efectivo_esperado == D("105000")

    @pytest.mark.parametrize("contado", ["100025", "-50", "100000.5"])
    def test_contado_invalido_422_y_la_caja_sigue_abierta(self, client, usuario_vendedor, contado):
        h = _auth(client, usuario_vendedor)
        _abrir_ok(client, h)

        assert _cerrar(client, h, contado).status_code == 422
        assert _actual(client, h)["abierta"] is True

    def test_sin_caja_abierta_409(self, client, usuario_vendedor):
        assert _cerrar(client, _auth(client, usuario_vendedor), "0").status_code == 409

    def test_el_cierre_no_se_repite(self, client, usuario_vendedor):
        h = _auth(client, usuario_vendedor)
        _abrir_ok(client, h)
        _cerrar_ok(client, h, "100000")

        assert _cerrar(client, h, "100000").status_code == 409

    def test_despues_de_cerrar_se_puede_abrir_otra_y_el_nuevo_corte_empieza_de_cero(
        self, client, db_session, producto, usuario_vendedor
    ):
        h = _auth(client, usuario_vendedor)
        primero = _abrir_ok(client, h, "100000")["corte"]["id"]
        venta = _vender(client, h, producto, 6, pagos_en_efectivo("30000"))
        _cerrar_ok(client, h, "130000")
        # El primer turno pasa a ayer (con el reloj congelado de la prueba, todo coincidiria en el mismo instante).
        _mover(db_session, "cortes_caja", "cerrada_en", primero, "-1 hour")
        _mover(db_session, "cortes_caja", "abierta_en", primero, "-1 day")
        _mover(db_session, "ventas", "fecha", venta["id"], "-1 day")

        segunda = _abrir_ok(client, h, "50000")

        assert segunda["corte"]["id"] != primero
        assert D(segunda["cifras"]["ventas_efectivo"]) == 0
        assert D(segunda["cifras"]["efectivo_esperado"]) == 50000

    def test_la_caja_cerrada_aparece_como_no_abierta(self, client, usuario_vendedor):
        h = _auth(client, usuario_vendedor)
        _abrir_ok(client, h)
        _cerrar_ok(client, h, "100000")

        assert _actual(client, h)["abierta"] is False

    def test_el_corte_cerrado_no_se_altera_aunque_despues_se_anule_un_gasto_o_llegue_otra_venta(
        self, client, db_session, categoria_gasto, producto, usuario_administrador, usuario_vendedor
    ):
        """Docs/12, 5.4: el corte conserva la foto de cuando se cerró."""
        admin, vendedor = _auth(client, usuario_administrador), _auth(client, usuario_vendedor)
        _abrir_ok(client, vendedor, "100000")
        gasto = _gastar(client, vendedor, categoria_gasto.id, "5000")
        corte = _cerrar_ok(client, vendedor, "95000")

        # El administrador anula el gasto cubierto y se registra otra venta, ya fuera del corte.
        assert client.post(f"/gastos/{gasto['id']}/anular", json={"motivo": "Error de digitación"}, headers=admin).status_code == 200
        venta = _vender(client, vendedor, producto, 4, pagos_en_efectivo("20000"))
        _mover(db_session, "ventas", "fecha", venta["id"], "1 day")

        ficha = client.get(f"/caja/cortes/{corte['id']}", headers=admin).json()
        assert ficha["cifras"] == corte["cifras"]
        assert D(ficha["efectivo_esperado"]) == 95000 and D(ficha["diferencia"]) == 0


class TestVentasSinConexionEnviadasDespuesDelCierre:
    """HU-13: una venta sin conexión enviada después del cierre no altera el corte; se informa en su ficha."""

    def test_no_altera_la_foto_y_se_informa(self, client, db_session, producto, usuario_vendedor):
        h = _auth(client, usuario_vendedor)
        corte_id = _abrir_ok(client, h, "100000")["corte"]["id"]
        _mover(db_session, "cortes_caja", "abierta_en", corte_id, "-5 hours")
        corte = _cerrar_ok(client, h, "100000")
        durante_el_turno = datetime.fromisoformat(corte["cerrada_en"]) - timedelta(hours=1)

        enviada = client.post(
            "/ventas",
            json={
                "detalles": [{"producto_id": producto.id, "cantidad": 4}],
                "pagos": pagos_en_efectivo("20000"),
                "uuid_cliente": str(uuid.uuid4()),
                "sin_conexion": {"fecha": durante_el_turno.isoformat()},
            },
            headers=h,
        )

        assert enviada.status_code == 201, enviada.text
        ficha = client.get(f"/caja/cortes/{corte['id']}", headers=h).json()
        assert D(ficha["cifras"]["ventas_efectivo"]) == 0  # La foto no cambia.
        assert D(ficha["diferencia"]) == 0
        assert ficha["ventas_sin_conexion_tardias"]["cantidad"] == 1
        assert D(ficha["ventas_sin_conexion_tardias"]["total"]) == 20000

    def test_sin_ventas_tardias_el_aviso_va_en_cero(self, client, usuario_vendedor):
        h = _auth(client, usuario_vendedor)
        _abrir_ok(client, h)
        corte = _cerrar_ok(client, h, "100000")

        assert corte["ventas_sin_conexion_tardias"]["cantidad"] == 0
        assert D(corte["ventas_sin_conexion_tardias"]["total"]) == 0


class TestBloqueoDelVendedorPorCorteCerrado:
    """HU-13 / RF-074: tras un corte cerrado, el vendedor ya no edita ni anula los gastos que cubre; el administrador sí."""

    def _gasto_cubierto(self, client, categoria_id, usuario_vendedor):
        """El vendedor registra un gasto con la caja abierta y luego se cierra: el corte lo cubre."""
        vendedor = _auth(client, usuario_vendedor)
        _abrir_ok(client, vendedor)
        gasto = _gastar(client, vendedor, categoria_id, "5000")
        _cerrar_ok(client, vendedor, "95000")
        return vendedor, gasto

    def test_el_vendedor_no_edita_ni_anula_lo_cubierto(self, client, categoria_gasto, usuario_vendedor):
        vendedor, gasto = self._gasto_cubierto(client, categoria_gasto.id, usuario_vendedor)

        editar = client.patch(f"/gastos/{gasto['id']}", json={"monto": "6000"}, headers=vendedor)
        anular = client.post(f"/gastos/{gasto['id']}/anular", json={"motivo": "Me equivoqué"}, headers=vendedor)

        assert editar.status_code == 403 and anular.status_code == 403
        assert "corte de caja" in editar.json()["detail"]
        assert client.get(f"/gastos/{gasto['id']}", headers=vendedor).json()["anulado"] is False

    def test_la_lista_lo_marca_como_no_editable(self, client, categoria_gasto, usuario_vendedor):
        vendedor, gasto = self._gasto_cubierto(client, categoria_gasto.id, usuario_vendedor)

        fila = client.get(f"/gastos/{gasto['id']}", headers=vendedor).json()

        assert fila["cubierto_por_corte"] is True and fila["editable"] is False

    def test_el_administrador_si_puede_y_el_corte_conserva_su_foto(
        self, client, categoria_gasto, usuario_administrador, usuario_vendedor
    ):
        vendedor, gasto = self._gasto_cubierto(client, categoria_gasto.id, usuario_vendedor)
        admin = _auth(client, usuario_administrador)

        editado = client.patch(f"/gastos/{gasto['id']}", json={"monto": "6000"}, headers=admin)

        assert editado.status_code == 200
        assert editado.json()["editable"] is True
        corte = client.get("/caja/cortes", headers=admin).json()[0]
        assert D(client.get(f"/caja/cortes/{corte['id']}", headers=admin).json()["cifras"]["gastos_efectivo"]) == 5000

    def test_mientras_la_caja_sigue_abierta_el_vendedor_si_edita(self, client, categoria_gasto, usuario_vendedor):
        vendedor = _auth(client, usuario_vendedor)
        _abrir_ok(client, vendedor)
        gasto = _gastar(client, vendedor, categoria_gasto.id, "5000")

        editado = client.patch(f"/gastos/{gasto['id']}", json={"monto": "6000"}, headers=vendedor)

        assert editado.status_code == 200 and editado.json()["editable"] is True
        assert D(_actual(client, vendedor)["cifras"]["gastos_efectivo"]) == 6000

    def test_un_gasto_posterior_al_corte_no_queda_bloqueado(self, client, db_session, categoria_gasto, usuario_vendedor):
        vendedor, _ = self._gasto_cubierto(client, categoria_gasto.id, usuario_vendedor)
        nuevo = _gastar(client, vendedor, categoria_gasto.id, "2000")
        _mover(db_session, "gastos", "creado_en", nuevo["id"], "1 hour")  # Registrado despues del cierre.

        editado = client.patch(f"/gastos/{nuevo['id']}", json={"monto": "2500"}, headers=vendedor)

        assert editado.status_code == 200 and editado.json()["cubierto_por_corte"] is False

    def test_un_gasto_anterior_a_la_apertura_no_queda_bloqueado(
        self, client, db_session, categoria_gasto, usuario_vendedor
    ):
        vendedor = _auth(client, usuario_vendedor)
        antes = _gastar(client, vendedor, categoria_gasto.id, "2000")
        _mover(db_session, "gastos", "creado_en", antes["id"], "-1 day")
        _abrir_ok(client, vendedor)
        _cerrar_ok(client, vendedor, "100000")

        assert client.patch(f"/gastos/{antes['id']}", json={"monto": "2500"}, headers=vendedor).status_code == 200


class TestHistorialDeCortes:
    """HU-13: historial de cortes; el vendedor ve solo los que abrió o cerró él."""

    def _dos_cortes(self, client, db_session, usuario_administrador, usuario_vendedor, otro_vendedor):
        """Un corte del vendedor y otro del otro vendedor; el primero se mueve a ayer para que no choquen."""
        h1, h2 = _auth(client, usuario_vendedor), _auth(client, otro_vendedor)
        primero = _abrir_ok(client, h1, "100000")["corte"]["id"]
        _cerrar_ok(client, h1, "100000")
        for columna in ("abierta_en", "cerrada_en"):
            _mover(db_session, "cortes_caja", columna, primero, "-1 day")
        segundo = _abrir_ok(client, h2, "50000")["corte"]["id"]
        _cerrar_ok(client, h2, "50000")
        return primero, segundo

    def test_cada_vendedor_ve_solo_los_suyos(
        self, client, db_session, usuario_administrador, usuario_vendedor, otro_vendedor
    ):
        primero, segundo = self._dos_cortes(client, db_session, usuario_administrador, usuario_vendedor, otro_vendedor)
        h1, h2 = _auth(client, usuario_vendedor), _auth(client, otro_vendedor)

        assert [c["id"] for c in client.get("/caja/cortes", headers=h1).json()] == [primero]
        assert [c["id"] for c in client.get("/caja/cortes", headers=h2).json()] == [segundo]
        assert client.get(f"/caja/cortes/{segundo}", headers=h1).status_code == 404
        assert client.get(f"/caja/cortes/{primero}", headers=h2).status_code == 404

    def test_el_vendedor_ve_tambien_el_que_cerro_aunque_lo_abrio_otro(
        self, client, usuario_administrador, usuario_vendedor
    ):
        _abrir_ok(client, _auth(client, usuario_administrador))
        corte = _cerrar_ok(client, _auth(client, usuario_vendedor), "100000")

        h = _auth(client, usuario_vendedor)
        assert [c["id"] for c in client.get("/caja/cortes", headers=h).json()] == [corte["id"]]
        assert client.get(f"/caja/cortes/{corte['id']}", headers=h).status_code == 200

    def test_administrador_y_propietario_ven_todos_del_mas_reciente_al_mas_antiguo(
        self, client, db_session, usuario_administrador, usuario_propietario, usuario_vendedor, otro_vendedor
    ):
        primero, segundo = self._dos_cortes(client, db_session, usuario_administrador, usuario_vendedor, otro_vendedor)

        for usuario in (usuario_administrador, usuario_propietario):
            lista = client.get("/caja/cortes", headers=_auth(client, usuario)).json()
            assert [c["id"] for c in lista] == [segundo, primero]

    def test_filtra_por_rango_de_apertura_y_pagina(
        self, client, db_session, usuario_administrador, usuario_vendedor, otro_vendedor
    ):
        primero, segundo = self._dos_cortes(client, db_session, usuario_administrador, usuario_vendedor, otro_vendedor)
        admin = _auth(client, usuario_administrador)
        ayer = hoy_en_bogota() - timedelta(days=1)

        solo_ayer = client.get("/caja/cortes", params={"desde": ayer.isoformat(), "hasta": ayer.isoformat()}, headers=admin)
        pagina_2 = client.get("/caja/cortes", params={"pagina": 2, "tamano_pagina": 1}, headers=admin)

        assert [c["id"] for c in solo_ayer.json()] == [primero]
        assert [c["id"] for c in pagina_2.json()] == [primero]

    def test_rango_invertido_422(self, client, usuario_administrador):
        respuesta = client.get(
            "/caja/cortes", params={"desde": "2026-10-20", "hasta": "2026-10-01"}, headers=_auth(client, usuario_administrador)
        )

        assert respuesta.status_code == 422

    def test_la_ficha_de_un_corte_abierto_muestra_las_cifras_en_vivo(self, client, producto, usuario_vendedor):
        h = _auth(client, usuario_vendedor)
        corte_id = _abrir_ok(client, h, "100000")["corte"]["id"]
        _vender(client, h, producto, 4, pagos_en_efectivo("20000"))

        ficha = client.get(f"/caja/cortes/{corte_id}", headers=h).json()

        assert ficha["estado"] == "abierta" and ficha["cerrada_en"] is None and ficha["diferencia"] is None
        assert D(ficha["cifras"]["efectivo_esperado"]) == 120000

    def test_corte_inexistente_404(self, client, usuario_administrador):
        assert client.get("/caja/cortes/99999", headers=_auth(client, usuario_administrador)).status_code == 404


class TestExportarCortes:
    """HU-13: exportar los cortes a CSV (UTF-8 con BOM, punto y coma), solo administrador y propietario."""

    def test_una_fila_por_corte_cerrado_con_las_cifras_de_su_foto(
        self, client, producto, usuario_administrador, usuario_propietario, usuario_vendedor
    ):
        vendedor = _auth(client, usuario_vendedor)
        _abrir_ok(client, vendedor, "100000")
        _vender(client, vendedor, producto, 4, pagos_en_efectivo("20000"))
        _cerrar_ok(client, vendedor, "119000", "=Faltaron mil")
        _abrir_ok(client, vendedor, "50000")  # Este sigue abierto: no sale.

        for usuario in (usuario_administrador, usuario_propietario):
            respuesta = client.get("/caja/cortes/exportar", headers=_auth(client, usuario))

            assert respuesta.status_code == 200
            assert respuesta.headers["content-type"].startswith("text/csv")
            assert "attachment" in respuesta.headers["content-disposition"]
            contenido = respuesta.content.decode("utf-8")
            assert contenido.startswith("﻿")
            filas = list(csv.reader(io.StringIO(contenido.lstrip("﻿")), delimiter=";"))
            assert len(filas) == 2
            encabezado, fila = filas
            assert encabezado[0] == "Corte" and "Efectivo esperado" in encabezado
            datos = dict(zip(encabezado, fila))
            assert datos["Base inicial"] == "100000" and datos["Ventas en efectivo"] == "20000"
            assert datos["Efectivo esperado"] == "120000" and datos["Efectivo contado"] == "119000"
            assert datos["Diferencia"] == "-1000"
            assert datos["Abrió"] == usuario_vendedor.nombre
            assert datos["Observaciones"].startswith("'")  # Un texto que empieza por = no se ejecuta en Excel.

    def test_sin_cortes_solo_trae_el_encabezado(self, client, usuario_administrador):
        respuesta = client.get("/caja/cortes/exportar", headers=_auth(client, usuario_administrador))

        assert respuesta.status_code == 200
        assert len(respuesta.content.decode("utf-8").strip().splitlines()) == 1

    def test_rango_invertido_422(self, client, usuario_administrador):
        respuesta = client.get(
            "/caja/cortes/exportar",
            params={"desde": "2026-10-20", "hasta": "2026-10-01"},
            headers=_auth(client, usuario_administrador),
        )

        assert respuesta.status_code == 422
