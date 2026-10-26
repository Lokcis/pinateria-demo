"""Logica de negocio de la caja y el corte de caja (Adendo v3, Fase G2: RF-069 a RF-074).

Igual que `services/gastos.py`, este modulo NO hace commit/rollback: el router que lo invoca envuelve la
llamada en la transaccion y traduce las excepciones de dominio a codigos HTTP.

El efectivo esperado de una caja abierta se calcula en vivo; al cerrarla se guarda una FOTO de todas las cifras
y el corte cerrado ya no se modifica. Todas las horas de la caja salen del reloj de la base de datos (`now()`),
el mismo que marca `ventas.fecha` y `gastos.creado_en`, para que el periodo [abierta_en, cerrada_en] los incluya
sin diferencias de reloj entre la aplicacion y la base.
"""

from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from app.core.config import settings
from app.models.corte_caja import CorteCaja, EstadoCorteCaja
from app.models.movimiento_caja import MovimientoCaja, TipoMovimientoCaja
from app.models.usuario import RolUsuario, Usuario
from app.schemas.caja import (
    CajaActualOut,
    CerrarCajaIn,
    CifrasCajaOut,
    CorteCajaDetalleOut,
    CorteCajaOut,
    MovimientoCajaIn,
    MovimientoCajaOut,
    VentasTardiasOut,
)
from app.services.csv_export import generar_csv
from app.services.exceptions import CajaConflictoError, CajaInvalidaError, CorteNoEncontradoError

MULTIPLO_EFECTIVO = Decimal("50")
CERO = Decimal("0")

_VENTAS_POR_METODO = text(
    "SELECT p.metodo_pago::text AS metodo, COALESCE(SUM(p.monto), 0) AS total "
    "FROM pagos_venta p JOIN ventas v ON v.id = p.venta_id "
    "WHERE v.fecha >= :desde AND v.fecha <= :hasta GROUP BY p.metodo_pago"
)
_GASTOS_EFECTIVO = text(
    "SELECT COALESCE(SUM(monto), 0) FROM gastos "
    "WHERE metodo_pago = 'efectivo' AND anulado_en IS NULL AND creado_en >= :desde AND creado_en <= :hasta"
)
_COMPRAS_EFECTIVO = text(
    "SELECT COALESCE(SUM(total), 0) FROM compras "
    "WHERE estado = 'recibida' AND metodo_pago = 'efectivo' AND recibida_en >= :desde AND recibida_en <= :hasta"
)
_VENTAS_TARDIAS = text(
    "SELECT count(*), COALESCE(SUM(total), 0) FROM ventas "
    "WHERE sin_conexion AND fecha >= :desde AND fecha <= :hasta AND sincronizada_en > :hasta"
)


def ahora_de_la_base(db: Session) -> datetime:
    """Devuelve la hora actual segun la base de datos (con zona), la que usan las marcas de la caja."""
    return db.execute(select(func.now())).scalar_one()


def _validar_efectivo(monto: Decimal, que: str) -> None:
    """Valida que un monto en efectivo sea multiplo de $50, igual que los pagos de las ventas.

    Args:
        monto: Monto en pesos enteros.
        que: Nombre del monto para el mensaje ("La base", "El retiro"...).

    Raises:
        CajaInvalidaError: Si no es multiplo de $50.
    """
    if monto % MULTIPLO_EFECTIVO != 0:
        raise CajaInvalidaError(f"{que} debe ser múltiplo de $50.")


# --- Consulta de la caja -------------------------------------------------------------------------------------


def corte_abierto(db: Session, bloquear: bool = False) -> CorteCaja | None:
    """Devuelve el corte abierto (hay a lo sumo uno) o None.

    Args:
        db: Sesion activa.
        bloquear: Si es True, toma `SELECT ... FOR UPDATE` (para cerrarla o moverla sin carreras).

    Returns:
        CorteCaja | None: La caja abierta.
    """
    consulta = db.query(CorteCaja).filter(CorteCaja.estado == EstadoCorteCaja.ABIERTA)
    if bloquear:
        consulta = consulta.with_for_update()
    return consulta.one_or_none()


def gasto_cubierto_por_corte(db: Session, creado_en: datetime) -> bool:
    """Indica si algun corte CERRADO cubre el momento en que se registro un gasto (RF-074).

    Un gasto esta "cubierto" si su `creado_en` cae entre `abierta_en` y `cerrada_en` de un corte cerrado.

    Args:
        db: Sesion activa.
        creado_en: Hora real del registro del gasto.

    Returns:
        bool: True si ya quedo incluido en un corte cerrado.
    """
    return (
        db.query(CorteCaja.id)
        .filter(
            CorteCaja.estado == EstadoCorteCaja.CERRADA,
            CorteCaja.abierta_en <= creado_en,
            CorteCaja.cerrada_en >= creado_en,
        )
        .first()
        is not None
    )


def _cifras_en_vivo(db: Session, corte: CorteCaja, hasta: datetime) -> CifrasCajaOut:
    """Calcula las cifras de un corte desde su apertura hasta `hasta` (RF-070).

    `efectivo esperado = base + ventas en efectivo + ingresos - gastos en efectivo - compras en efectivo - retiros`.
    Las ventas cuentan por su hora real (`ventas.fecha`, tambien en las hechas sin conexion), los gastos por
    `creado_en` (no por su fecha contable) y las compras por la hora de recepcion. Las compras anteriores a
    la migracion 0009 no tienen forma de pago y no afectan la caja.

    Args:
        db: Sesion activa.
        corte: El corte (abierto o cerrado).
        hasta: Fin del periodo (inclusive).

    Returns:
        CifrasCajaOut: Las cifras.
    """
    periodo = {"desde": corte.abierta_en, "hasta": hasta}
    ventas = {fila.metodo: fila.total for fila in db.execute(_VENTAS_POR_METODO, periodo)}
    gastos = db.execute(_GASTOS_EFECTIVO, periodo).scalar_one()
    compras = db.execute(_COMPRAS_EFECTIVO, periodo).scalar_one()
    movimientos = dict(
        db.query(MovimientoCaja.tipo, func.coalesce(func.sum(MovimientoCaja.monto), 0))
        .filter(MovimientoCaja.corte_id == corte.id)
        .group_by(MovimientoCaja.tipo)
        .all()
    )
    ingresos = movimientos.get(TipoMovimientoCaja.INGRESO, CERO)
    retiros = movimientos.get(TipoMovimientoCaja.RETIRO, CERO)
    ventas_efectivo = ventas.get("efectivo", CERO)
    return CifrasCajaOut(
        base_inicial=corte.base_inicial,
        ventas_efectivo=ventas_efectivo,
        ingresos=ingresos,
        gastos_efectivo=gastos,
        compras_efectivo=compras,
        retiros=retiros,
        efectivo_esperado=corte.base_inicial + ventas_efectivo + ingresos - gastos - compras - retiros,
        ventas_tarjeta=ventas.get("tarjeta", CERO),
        ventas_transferencia=ventas.get("transferencia", CERO),
    )


def _foto(corte: CorteCaja) -> CifrasCajaOut:
    """Arma las cifras de un corte cerrado a partir de la foto guardada al cerrar."""
    return CifrasCajaOut(
        base_inicial=corte.base_inicial,
        ventas_efectivo=corte.ventas_efectivo,
        ingresos=corte.ingresos_caja,
        gastos_efectivo=corte.gastos_efectivo,
        compras_efectivo=corte.compras_efectivo,
        retiros=corte.retiros_caja,
        efectivo_esperado=corte.efectivo_esperado,
        ventas_tarjeta=corte.ventas_tarjeta,
        ventas_transferencia=corte.ventas_transferencia,
    )


def _nombres(db: Session, ids: set[int | None]) -> dict[int, str]:
    """Devuelve {id: nombre} de los usuarios dados (ignora los None)."""
    ids_reales = {i for i in ids if i is not None}
    if not ids_reales:
        return {}
    return {u.id: u.nombre for u in db.query(Usuario.id, Usuario.nombre).filter(Usuario.id.in_(ids_reales))}


def _a_corte_out(corte: CorteCaja, nombres: dict[int, str]) -> CorteCajaOut:
    """Convierte un corte en la fila del historial."""
    return CorteCajaOut(
        id=corte.id,
        estado=corte.estado,
        abierta_en=corte.abierta_en,
        abierta_por=nombres[corte.abierta_por_id],
        cerrada_en=corte.cerrada_en,
        cerrada_por=nombres.get(corte.cerrada_por_id),
        base_inicial=corte.base_inicial,
        efectivo_esperado=corte.efectivo_esperado,
        efectivo_contado=corte.efectivo_contado,
        diferencia=corte.diferencia,
    )


def _movimientos_out(db: Session, corte_id: int) -> list[MovimientoCajaOut]:
    """Lista los ingresos y retiros de un corte, del mas antiguo al mas reciente."""
    filas = (
        db.query(MovimientoCaja, Usuario.nombre)
        .join(Usuario, Usuario.id == MovimientoCaja.usuario_id)
        .filter(MovimientoCaja.corte_id == corte_id)
        .order_by(MovimientoCaja.creado_en, MovimientoCaja.id)
        .all()
    )
    return [
        MovimientoCajaOut(
            id=m.id, tipo=m.tipo, monto=m.monto, motivo=m.motivo, usuario=nombre, creado_en=m.creado_en
        )
        for m, nombre in filas
    ]


def caja_actual(db: Session) -> CajaActualOut:
    """Estado de la caja: si esta abierta y, en ese caso, el efectivo esperado en vivo (RF-070).

    Args:
        db: Sesion activa.

    Returns:
        CajaActualOut: Estado, cifras en vivo y movimientos del corte abierto.
    """
    ahora = ahora_de_la_base(db)
    corte = corte_abierto(db)
    if corte is None:
        return CajaActualOut(abierta=False, corte=None, cifras=None, movimientos=[], generado_en=ahora)
    nombres = _nombres(db, {corte.abierta_por_id})
    return CajaActualOut(
        abierta=True,
        corte=_a_corte_out(corte, nombres),
        cifras=_cifras_en_vivo(db, corte, ahora),
        movimientos=_movimientos_out(db, corte.id),
        generado_en=ahora,
    )


# --- Escritura -------------------------------------------------------------------------------------------------


def abrir_caja(db: Session, usuario: Usuario, base_inicial: Decimal) -> CorteCaja:
    """Abre la caja con la base indicada (RF-069). Solo puede haber una abierta.

    Args:
        db: Sesion activa, dentro de una transaccion del llamador.
        usuario: Quien la abre.
        base_inicial: Efectivo con que arranca (multiplo de $50).

    Returns:
        CorteCaja: El corte abierto (aun no commiteado).

    Raises:
        CajaInvalidaError: Si la base no es multiplo de $50.
        CajaConflictoError: Si ya hay una caja abierta.
    """
    _validar_efectivo(base_inicial, "La base")
    if corte_abierto(db) is not None:
        raise CajaConflictoError("Ya hay una caja abierta: ciérrala antes de abrir otra.")
    corte = CorteCaja(abierta_en=ahora_de_la_base(db), abierta_por_id=usuario.id, base_inicial=base_inicial)
    db.add(corte)
    try:
        db.flush()
    except IntegrityError as exc:  # Otra persona la abrio al mismo tiempo: gana el indice unico parcial.
        raise CajaConflictoError("Ya hay una caja abierta: ciérrala antes de abrir otra.") from exc
    return corte


def registrar_movimiento(db: Session, usuario: Usuario, datos: MovimientoCajaIn) -> MovimientoCaja:
    """Registra un ingreso o retiro manual en la caja abierta (RF-071).

    Args:
        db: Sesion activa, dentro de una transaccion del llamador.
        usuario: Quien lo registra.
        datos: Tipo, monto y motivo.

    Returns:
        MovimientoCaja: El movimiento (aun no commiteado).

    Raises:
        CajaInvalidaError: Si el monto no es multiplo de $50.
        CajaConflictoError: Si no hay una caja abierta.
    """
    _validar_efectivo(datos.monto, "El monto")
    corte = corte_abierto(db, bloquear=True)
    if corte is None:
        raise CajaConflictoError("No hay una caja abierta: ábrela para registrar ingresos o retiros.")
    movimiento = MovimientoCaja(
        corte_id=corte.id, tipo=datos.tipo, monto=datos.monto, motivo=datos.motivo, usuario_id=usuario.id
    )
    db.add(movimiento)
    db.flush()
    return movimiento


def cerrar_caja(db: Session, usuario: Usuario, datos: CerrarCajaIn) -> CorteCaja:
    """Cierra la caja: calcula el esperado, la diferencia con lo contado y guarda la foto del corte (RF-072).

    El cierre no se repite ni se edita. El POS no deja cerrar si el equipo tiene ventas sin enviar, pero eso
    lo valida la pantalla (la cola vive en el navegador); aqui, una venta sin conexion enviada despues del
    cierre no altera la foto y se informa en la ficha.

    Args:
        db: Sesion activa, dentro de una transaccion del llamador.
        usuario: Quien cierra.
        datos: Efectivo contado y observaciones.

    Returns:
        CorteCaja: El corte cerrado (aun no commiteado).

    Raises:
        CajaInvalidaError: Si lo contado no es multiplo de $50.
        CajaConflictoError: Si no hay una caja abierta.
    """
    _validar_efectivo(datos.efectivo_contado, "El efectivo contado")
    corte = corte_abierto(db, bloquear=True)
    if corte is None:
        raise CajaConflictoError("No hay una caja abierta que cerrar.")
    cierre = ahora_de_la_base(db)
    cifras = _cifras_en_vivo(db, corte, cierre)
    corte.estado = EstadoCorteCaja.CERRADA
    corte.cerrada_en = cierre
    corte.cerrada_por_id = usuario.id
    corte.ventas_efectivo = cifras.ventas_efectivo
    corte.ingresos_caja = cifras.ingresos
    corte.gastos_efectivo = cifras.gastos_efectivo
    corte.compras_efectivo = cifras.compras_efectivo
    corte.retiros_caja = cifras.retiros
    corte.efectivo_esperado = cifras.efectivo_esperado
    corte.efectivo_contado = datos.efectivo_contado
    corte.diferencia = datos.efectivo_contado - cifras.efectivo_esperado
    corte.ventas_tarjeta = cifras.ventas_tarjeta
    corte.ventas_transferencia = cifras.ventas_transferencia
    corte.observaciones = datos.observaciones or None
    db.flush()
    return corte


# --- Historial -------------------------------------------------------------------------------------------------


def _consulta_de_cortes(db: Session, usuario: Usuario, desde: date | None, hasta: date | None):
    """Arma la consulta del historial: un vendedor solo ve los cortes que abrio o cerro el.

    Args:
        db: Sesion activa.
        usuario: Quien consulta.
        desde: Primer dia por fecha de apertura (hora de Bogota), o None.
        hasta: Ultimo dia por fecha de apertura, o None.

    Returns:
        Query: La consulta de `CorteCaja`.
    """
    consulta = db.query(CorteCaja)
    if usuario.rol == RolUsuario.VENDEDOR:
        consulta = consulta.filter((CorteCaja.abierta_por_id == usuario.id) | (CorteCaja.cerrada_por_id == usuario.id))
    dia = func.date(func.timezone(settings.zona_horaria, CorteCaja.abierta_en))
    if desde is not None:
        consulta = consulta.filter(dia >= desde)
    if hasta is not None:
        consulta = consulta.filter(dia <= hasta)
    return consulta


def listar_cortes(
    db: Session,
    usuario: Usuario,
    desde: date | None,
    hasta: date | None,
    limite: int | None = None,
    desplazamiento: int = 0,
) -> list[CorteCajaOut]:
    """Lista los cortes, del mas reciente al mas antiguo (RF-073).

    Args:
        db: Sesion activa.
        usuario: Quien consulta; un vendedor solo ve los que abrio o cerro el.
        desde: Primer dia (por apertura), o None.
        hasta: Ultimo dia (por apertura), o None.
        limite: Maximo de filas, o None para todas.
        desplazamiento: Filas a saltar.

    Returns:
        list[CorteCajaOut]: Las filas de la pagina.
    """
    consulta = _consulta_de_cortes(db, usuario, desde, hasta).order_by(CorteCaja.abierta_en.desc(), CorteCaja.id.desc())
    if limite is not None:
        consulta = consulta.limit(limite).offset(desplazamiento)
    cortes = consulta.all()
    nombres = _nombres(db, {c.abierta_por_id for c in cortes} | {c.cerrada_por_id for c in cortes})
    return [_a_corte_out(c, nombres) for c in cortes]


def obtener_corte(db: Session, usuario: Usuario, corte_id: int) -> CorteCajaDetalleOut:
    """Devuelve la ficha de un corte: su foto, sus movimientos y las ventas sin conexion enviadas despues del cierre.

    Un corte abierto se muestra con sus cifras en vivo. Un vendedor solo ve los que abrio o cerro el (lo ajeno
    responde como inexistente).

    Args:
        db: Sesion activa.
        usuario: Quien consulta.
        corte_id: Id del corte.

    Returns:
        CorteCajaDetalleOut: La ficha.

    Raises:
        CorteNoEncontradoError: Si no existe o, para un vendedor, no es suyo.
    """
    corte = _consulta_de_cortes(db, usuario, None, None).filter(CorteCaja.id == corte_id).one_or_none()
    if corte is None:
        raise CorteNoEncontradoError(corte_id)
    nombres = _nombres(db, {corte.abierta_por_id, corte.cerrada_por_id})
    base = _a_corte_out(corte, nombres)
    if corte.estado == EstadoCorteCaja.CERRADA:
        cifras = _foto(corte)
        tardias = db.execute(_VENTAS_TARDIAS, {"desde": corte.abierta_en, "hasta": corte.cerrada_en}).one()
        ventas_tardias = VentasTardiasOut(cantidad=tardias[0], total=tardias[1])
    else:
        cifras = _cifras_en_vivo(db, corte, ahora_de_la_base(db))
        ventas_tardias = VentasTardiasOut(cantidad=0, total=CERO)
    return CorteCajaDetalleOut(
        **base.model_dump(),
        cifras=cifras,
        observaciones=corte.observaciones,
        movimientos=_movimientos_out(db, corte.id),
        ventas_sin_conexion_tardias=ventas_tardias,
    )


# --- Exportacion -----------------------------------------------------------------------------------------------

_ENCABEZADOS_CSV = [
    "Corte",
    "Apertura",
    "Cierre",
    "Abrió",
    "Cerró",
    "Base inicial",
    "Ventas en efectivo",
    "Ingresos",
    "Gastos en efectivo",
    "Compras en efectivo",
    "Retiros",
    "Efectivo esperado",
    "Efectivo contado",
    "Diferencia",
    "Ventas con tarjeta",
    "Ventas por transferencia",
    "Observaciones",
]


def _hora_local(momento: datetime | None) -> str:
    """Formatea una hora en la zona del negocio ("2026-10-19 18:30"), o vacio si falta."""
    if momento is None:
        return ""
    return momento.astimezone(ZoneInfo(settings.zona_horaria)).strftime("%Y-%m-%d %H:%M")


def exportar_cortes_csv(db: Session, usuario: Usuario, desde: date | None, hasta: date | None) -> str:
    """Genera el CSV de los cortes CERRADOS del rango, una fila por corte con las cifras de su foto (RF-073).

    Args:
        db: Sesion activa.
        usuario: Quien exporta (administrador o propietario).
        desde: Primer dia (por apertura), o None.
        hasta: Ultimo dia (por apertura), o None.

    Returns:
        str: El CSV con BOM y punto y coma.
    """
    cortes = (
        _consulta_de_cortes(db, usuario, desde, hasta)
        .filter(CorteCaja.estado == EstadoCorteCaja.CERRADA)
        .order_by(CorteCaja.abierta_en, CorteCaja.id)
        .all()
    )
    nombres = _nombres(db, {c.abierta_por_id for c in cortes} | {c.cerrada_por_id for c in cortes})
    entero = Decimal("1")
    return generar_csv(
        _ENCABEZADOS_CSV,
        (
            [
                c.id,
                _hora_local(c.abierta_en),
                _hora_local(c.cerrada_en),
                nombres[c.abierta_por_id],
                nombres[c.cerrada_por_id],
                c.base_inicial.quantize(entero),
                c.ventas_efectivo.quantize(entero),
                c.ingresos_caja.quantize(entero),
                c.gastos_efectivo.quantize(entero),
                c.compras_efectivo.quantize(entero),
                c.retiros_caja.quantize(entero),
                c.efectivo_esperado.quantize(entero),
                c.efectivo_contado.quantize(entero),
                c.diferencia.quantize(entero),
                c.ventas_tarjeta.quantize(entero),
                c.ventas_transferencia.quantize(entero),
                c.observaciones,
            ]
            for c in cortes
        ),
    )
