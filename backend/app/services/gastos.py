"""Logica de negocio de los gastos y sus categorias (Adendo v3, Fase G1: RF-059 a RF-066, RF-075).

Igual que `services/compras.py`, este modulo NO hace commit/rollback: el router que lo invoca envuelve la
llamada en la transaccion y traduce las excepciones de dominio a codigos HTTP.

Los permisos por duenio del gasto se validan AQUI (en el servidor): un vendedor solo ve, edita y anula lo que
registro el mismo; lo ajeno se responde como si no existiera (404). La lista unificada con las compras recibidas
(`vw_gastos_unificados`) solo se entrega al administrador y al propietario.
"""

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.categoria_gasto import CategoriaGasto
from app.models.gasto import Gasto
from app.models.pago_venta import PlataformaTransferencia
from app.models.usuario import RolUsuario, Usuario
from app.models.venta import MetodoPago
from app.schemas.gasto import (
    EstadoGasto,
    GastoIn,
    GastoOut,
    GastoPatch,
    OrigenGasto,
    ResumenGastosOut,
    TotalCategoriaOut,
    TotalMetodoOut,
)
from app.services.caja import gasto_cubierto_por_corte
from app.services.csv_export import generar_csv
from app.services.exceptions import (
    CategoriaGastoNoEncontradaError,
    GastoConflictoError,
    GastoInvalidoError,
    GastoNoEncontradoError,
    GastoSinPermisoError,
)

MULTIPLO_EFECTIVO = Decimal("50")
CERO = Decimal("0")

_SELECT_UNIFICADO = """
SELECT v.origen, v.origen_id AS id, v.fecha, v.categoria_id, v.categoria, v.descripcion, v.beneficiario,
       v.monto, v.metodo_pago, v.plataforma, v.registrado_por_id, ur.nombre AS registrado_por, v.creado_en,
       g.actualizado_en, ua.nombre AS actualizado_por, v.anulado, g.anulado_en, un.nombre AS anulado_por,
       g.motivo_anulacion,
       EXISTS (SELECT 1 FROM cortes_caja cc WHERE cc.estado = 'cerrada' AND v.creado_en >= cc.abierta_en AND v.creado_en <= cc.cerrada_en) AS cubierto_por_corte
FROM vw_gastos_unificados v
JOIN usuarios ur ON ur.id = v.registrado_por_id
LEFT JOIN gastos g ON v.origen = 'gasto' AND g.id = v.origen_id
LEFT JOIN usuarios ua ON ua.id = g.actualizado_por_id
LEFT JOIN usuarios un ON un.id = g.anulado_por_id
"""

_CATEGORIA_DE_SISTEMA = "(v.origen = 'compra' OR v.categoria_id IN (SELECT id FROM categorias_gasto WHERE es_sistema))"


def hoy_en_bogota() -> date:
    """Devuelve el dia de hoy en la zona horaria del negocio."""
    return datetime.now(ZoneInfo(settings.zona_horaria)).date()


def _ahora() -> datetime:
    """Devuelve el momento actual en UTC (con zona), para las marcas de edicion y anulacion."""
    return datetime.now(timezone.utc)


# --- Categorias -----------------------------------------------------------------------------------------------


def listar_categorias(db: Session, solo_activas: bool) -> list[CategoriaGasto]:
    """Lista las categorias de gasto, ordenadas por nombre.

    Args:
        db: Sesion activa.
        solo_activas: Si es True, deja fuera las desactivadas (lo que ve el vendedor).

    Returns:
        list[CategoriaGasto]: Las categorias.
    """
    consulta = db.query(CategoriaGasto)
    if solo_activas:
        consulta = consulta.filter(CategoriaGasto.activa.is_(True))
    return consulta.order_by(func.lower(CategoriaGasto.nombre), CategoriaGasto.id).all()


def _nombre_repetido(db: Session, nombre: str, excepto_id: int | None = None) -> bool:
    """Indica si ya existe otra categoria con ese nombre (sin distinguir mayusculas)."""
    consulta = db.query(CategoriaGasto.id).filter(func.lower(CategoriaGasto.nombre) == nombre.lower())
    if excepto_id is not None:
        consulta = consulta.filter(CategoriaGasto.id != excepto_id)
    return consulta.first() is not None


def crear_categoria(db: Session, nombre: str) -> CategoriaGasto:
    """Crea una categoria de gasto activa.

    Args:
        db: Sesion activa, dentro de una transaccion del llamador.
        nombre: Nombre ya normalizado.

    Returns:
        CategoriaGasto: La categoria creada (aun no commiteada).

    Raises:
        GastoConflictoError: Si ya existe una categoria con ese nombre.
    """
    if _nombre_repetido(db, nombre):
        raise GastoConflictoError(f"Ya existe una categoria llamada «{nombre}».")
    categoria = CategoriaGasto(nombre=nombre)
    db.add(categoria)
    db.flush()
    return categoria


def modificar_categoria(db: Session, categoria_id: int, nombre: str | None, activa: bool | None) -> CategoriaGasto:
    """Renombra, activa o desactiva una categoria. La de sistema no se toca.

    Args:
        db: Sesion activa, dentro de una transaccion del llamador.
        categoria_id: Categoria a modificar.
        nombre: Nombre nuevo, o None para dejar el actual.
        activa: Estado nuevo, o None para dejarlo.

    Returns:
        CategoriaGasto: La categoria (aun no commiteada).

    Raises:
        CategoriaGastoNoEncontradaError: Si no existe.
        GastoConflictoError: Si es la de sistema, o el nombre ya lo usa otra.
    """
    categoria = db.query(CategoriaGasto).filter(CategoriaGasto.id == categoria_id).with_for_update().one_or_none()
    if categoria is None:
        raise CategoriaGastoNoEncontradaError(categoria_id)
    if categoria.es_sistema:
        raise GastoConflictoError(f"La categoria «{categoria.nombre}» es de sistema: no se renombra ni se desactiva.")
    if nombre is not None and nombre != categoria.nombre:
        if _nombre_repetido(db, nombre, excepto_id=categoria.id):
            raise GastoConflictoError(f"Ya existe una categoria llamada «{nombre}».")
        categoria.nombre = nombre
    if activa is not None:
        categoria.activa = activa
    db.flush()
    return categoria


def _categoria_activa(db: Session, categoria_id: int) -> CategoriaGasto:
    """Devuelve la categoria si existe y esta activa.

    Raises:
        CategoriaGastoNoEncontradaError: Si no existe.
        GastoInvalidoError: Si esta desactivada.
    """
    categoria = db.query(CategoriaGasto).filter(CategoriaGasto.id == categoria_id).one_or_none()
    if categoria is None:
        raise CategoriaGastoNoEncontradaError(categoria_id)
    if not categoria.activa:
        raise GastoInvalidoError(f"La categoria «{categoria.nombre}» esta desactivada.")
    return categoria


# --- Reglas del pago ------------------------------------------------------------------------------------------


def validar_pago(monto: Decimal, metodo_pago: MetodoPago, plataforma: PlataformaTransferencia | None) -> None:
    """Valida el monto y la plataforma segun la forma de pago.

    En efectivo el monto es multiplo de $50, igual que las ventas. La plataforma es obligatoria en toda
    transferencia nueva y no se admite en las demas formas de pago.

    Args:
        monto: Monto en pesos enteros.
        metodo_pago: Forma de pago.
        plataforma: Plataforma de la transferencia, si la hay.

    Raises:
        GastoInvalidoError: Si alguna regla no se cumple.
    """
    if metodo_pago == MetodoPago.EFECTIVO and monto % MULTIPLO_EFECTIVO != 0:
        raise GastoInvalidoError("Un gasto en efectivo debe ser múltiplo de $50.")
    if metodo_pago == MetodoPago.TRANSFERENCIA and plataforma is None:
        raise GastoInvalidoError("Indica la plataforma de la transferencia (Nequi o Daviplata).")
    if metodo_pago != MetodoPago.TRANSFERENCIA and plataforma is not None:
        raise GastoInvalidoError("La plataforma solo aplica a las transferencias.")


# --- Escritura -------------------------------------------------------------------------------------------------


def _fecha_del_gasto(usuario: Usuario, fecha: date | None) -> date:
    """Resuelve la fecha de un gasto nuevo: el vendedor solo registra con la de hoy; el administrador, hasta hoy.

    Raises:
        GastoSinPermisoError: Si un vendedor manda una fecha distinta de la de hoy.
        GastoInvalidoError: Si la fecha del administrador es futura.
    """
    hoy = hoy_en_bogota()
    if fecha is None:
        return hoy
    if usuario.rol != RolUsuario.ADMINISTRADOR:
        if fecha != hoy:
            raise GastoSinPermisoError("El vendedor registra los gastos con la fecha de hoy.")
        return hoy
    if fecha > hoy:
        raise GastoInvalidoError("La fecha del gasto no puede ser futura.")
    return fecha


def crear_gasto(db: Session, usuario: Usuario, datos: GastoIn) -> Gasto:
    """Registra un gasto a nombre de `usuario` (RF-059).

    Args:
        db: Sesion activa, dentro de una transaccion del llamador.
        usuario: Quien lo registra (administrador o vendedor).
        datos: Datos del gasto.

    Returns:
        Gasto: El gasto creado (aun no commiteado).

    Raises:
        CategoriaGastoNoEncontradaError: Si la categoria no existe.
        GastoInvalidoError: Si la categoria esta desactivada o el pago no cumple las reglas.
        GastoSinPermisoError: Si un vendedor manda una fecha que no es la de hoy.
    """
    fecha = _fecha_del_gasto(usuario, datos.fecha)
    validar_pago(datos.monto, datos.metodo_pago, datos.plataforma)
    _categoria_activa(db, datos.categoria_id)
    gasto = Gasto(
        fecha=fecha,
        categoria_id=datos.categoria_id,
        descripcion=datos.descripcion,
        beneficiario=datos.beneficiario or None,
        monto=datos.monto,
        metodo_pago=datos.metodo_pago,
        plataforma=datos.plataforma,
        registrado_por_id=usuario.id,
    )
    db.add(gasto)
    db.flush()
    return gasto


def _gasto_modificable(db: Session, usuario: Usuario, gasto_id: int) -> Gasto:
    """Carga un gasto con `SELECT ... FOR UPDATE` verificando que `usuario` pueda modificarlo.

    El administrador modifica cualquiera; el vendedor, solo los suyos (lo ajeno responde como inexistente) y
    mientras ningun corte de caja cerrado lo cubra (RF-074).

    Raises:
        GastoNoEncontradoError: Si no existe o, para un vendedor, no es suyo.
        GastoConflictoError: Si el gasto ya esta anulado.
        GastoSinPermisoError: Si es de un vendedor y un corte cerrado ya lo cubre.
    """
    gasto = db.query(Gasto).filter(Gasto.id == gasto_id).with_for_update().one_or_none()
    if gasto is None or (usuario.rol != RolUsuario.ADMINISTRADOR and gasto.registrado_por_id != usuario.id):
        raise GastoNoEncontradoError(gasto_id)
    if gasto.anulado_en is not None:
        raise GastoConflictoError("El gasto ya está anulado: no se puede modificar. Si fue un error, regístralo de nuevo.")
    if usuario.rol != RolUsuario.ADMINISTRADOR and gasto_cubierto_por_corte(db, gasto.creado_en):
        raise GastoSinPermisoError(
            "Este gasto ya quedó incluido en un corte de caja cerrado. Pídele al administrador que lo modifique."
        )
    return gasto


def editar_gasto(db: Session, usuario: Usuario, gasto_id: int, datos: GastoPatch) -> Gasto:
    """Edita un gasto vigente; solo cambian los campos que `datos` trae (RF-061).

    Queda registrado quien y cuando lo edito por ultima vez. Solo el administrador cambia la fecha.

    Args:
        db: Sesion activa, dentro de una transaccion del llamador.
        usuario: Quien edita.
        gasto_id: Gasto a editar.
        datos: Campos a cambiar (los no enviados no se tocan; `plataforma` y `beneficiario` aceptan null).

    Returns:
        Gasto: El gasto editado (aun no commiteado).

    Raises:
        GastoNoEncontradoError: Si no existe o es de otra persona y quien edita es vendedor.
        GastoConflictoError: Si esta anulado.
        GastoInvalidoError: Si no hay cambios o los datos no cumplen las reglas.
        GastoSinPermisoError: Si un vendedor intenta cambiar la fecha.
    """
    enviados = datos.model_fields_set
    if not enviados:
        raise GastoInvalidoError("No hay cambios que guardar.")
    gasto = _gasto_modificable(db, usuario, gasto_id)

    metodo = datos.metodo_pago if "metodo_pago" in enviados and datos.metodo_pago else gasto.metodo_pago
    monto = datos.monto if "monto" in enviados and datos.monto is not None else gasto.monto
    if "plataforma" in enviados:
        plataforma = datos.plataforma
    elif "metodo_pago" in enviados and metodo != MetodoPago.TRANSFERENCIA:
        plataforma = None  # Cambiar a efectivo o tarjeta limpia la plataforma que tenia.
    else:
        plataforma = gasto.plataforma
    validar_pago(monto, metodo, plataforma)

    if "categoria_id" in enviados and datos.categoria_id is not None and datos.categoria_id != gasto.categoria_id:
        _categoria_activa(db, datos.categoria_id)
        gasto.categoria_id = datos.categoria_id
    if "descripcion" in enviados and datos.descripcion is not None:
        gasto.descripcion = datos.descripcion
    if "beneficiario" in enviados:
        gasto.beneficiario = datos.beneficiario or None
    if "fecha" in enviados and datos.fecha is not None and datos.fecha != gasto.fecha:
        if usuario.rol != RolUsuario.ADMINISTRADOR:
            raise GastoSinPermisoError("Solo el administrador puede cambiar la fecha de un gasto.")
        gasto.fecha = _fecha_del_gasto(usuario, datos.fecha)
    gasto.monto = monto
    gasto.metodo_pago = metodo
    gasto.plataforma = plataforma
    gasto.actualizado_en = _ahora()
    gasto.actualizado_por_id = usuario.id
    db.flush()
    return gasto


def anular_gasto(db: Session, usuario: Usuario, gasto_id: int, motivo: str) -> Gasto:
    """Anula un gasto vigente con su motivo (RF-062). No se borra ni se reactiva.

    Args:
        db: Sesion activa, dentro de una transaccion del llamador.
        usuario: Quien anula.
        gasto_id: Gasto a anular.
        motivo: Por que se anula.

    Returns:
        Gasto: El gasto anulado (aun no commiteado).

    Raises:
        GastoNoEncontradoError: Si no existe o es de otra persona y quien anula es vendedor.
        GastoConflictoError: Si ya estaba anulado.
    """
    gasto = _gasto_modificable(db, usuario, gasto_id)
    gasto.anulado_en = _ahora()
    gasto.anulado_por_id = usuario.id
    gasto.motivo_anulacion = motivo
    db.flush()
    return gasto


# --- Lectura ---------------------------------------------------------------------------------------------------


@dataclass
class FiltrosGastos:
    """Filtros de la lista de gastos.

    Attributes:
        desde: Primer dia (inclusivo).
        hasta: Ultimo dia (inclusivo).
        categoria_id: Solo esta categoria.
        metodo_pago: Solo esta forma de pago.
        estado: vigente / anulado, o None para ambos.
        origen: gasto / compra, o None para ambos.
    """

    desde: date
    hasta: date
    categoria_id: int | None = None
    metodo_pago: MetodoPago | None = None
    estado: EstadoGasto | None = None
    origen: OrigenGasto | None = None


def _condiciones(filtros: FiltrosGastos, vendedor_id: int | None = None) -> tuple[list[str], dict]:
    """Arma el WHERE de la lista unificada.

    Si `vendedor_id` viene, la lista queda limitada a SUS gastos (nunca compras ni lo de otros); el filtro vive
    aqui, en el servidor.

    Args:
        filtros: Rango y filtros.
        vendedor_id: Id del vendedor que consulta, o None para administrador y propietario.

    Returns:
        tuple: (condiciones, parametros).
    """
    condiciones = ["v.fecha >= :desde", "v.fecha <= :hasta"]
    parametros: dict = {"desde": filtros.desde, "hasta": filtros.hasta}
    if vendedor_id is not None:
        condiciones += ["v.origen = 'gasto'", "v.registrado_por_id = :usuario_id"]
        parametros["usuario_id"] = vendedor_id
    if filtros.categoria_id is not None:
        condiciones.append("v.categoria_id = :categoria_id")
        parametros["categoria_id"] = filtros.categoria_id
    if filtros.metodo_pago is not None:
        condiciones.append("v.metodo_pago = CAST(:metodo_pago AS metodo_pago)")
        parametros["metodo_pago"] = filtros.metodo_pago.value
    if filtros.estado is not None:
        condiciones.append("v.anulado" if filtros.estado == EstadoGasto.ANULADO else "NOT v.anulado")
    if filtros.origen is not None:
        condiciones.append("v.origen = :origen")
        parametros["origen"] = filtros.origen.value
    return condiciones, parametros


def _a_gasto_out(fila, usuario: Usuario) -> GastoOut:
    """Convierte una fila de la lista unificada en `GastoOut`, marcando si `usuario` puede modificarla."""
    datos = dict(fila._mapping)
    editable = (
        datos["origen"] == "gasto"
        and not datos["anulado"]
        and (
            usuario.rol == RolUsuario.ADMINISTRADOR
            or (
                usuario.rol == RolUsuario.VENDEDOR
                and datos["registrado_por_id"] == usuario.id
                and not datos["cubierto_por_corte"]
            )
        )
    )
    return GastoOut(**datos, editable=editable)


def consultar_gastos(
    db: Session, usuario: Usuario, filtros: FiltrosGastos, limite: int | None = None, desplazamiento: int = 0
) -> list[GastoOut]:
    """Lista los gastos y (para administrador y propietario) las compras recibidas, de lo mas reciente a lo mas antiguo.

    Args:
        db: Sesion activa.
        usuario: Quien consulta; define que filas puede ver.
        filtros: Rango y filtros.
        limite: Maximo de filas, o None para todas (exportacion).
        desplazamiento: Filas a saltar (paginacion).

    Returns:
        list[GastoOut]: Las filas de la pagina.
    """
    condiciones, parametros = _condiciones(filtros, usuario.id if usuario.rol == RolUsuario.VENDEDOR else None)
    sql = (
        _SELECT_UNIFICADO
        + " WHERE "
        + " AND ".join(condiciones)
        + " ORDER BY v.fecha DESC, v.creado_en DESC, v.origen, v.origen_id DESC"
    )
    if limite is not None:
        sql += " LIMIT :limite OFFSET :desplazamiento"
        parametros.update(limite=limite, desplazamiento=desplazamiento)
    return [_a_gasto_out(fila, usuario) for fila in db.execute(text(sql), parametros)]


def obtener_gasto(db: Session, usuario: Usuario, gasto_id: int) -> GastoOut:
    """Devuelve un gasto como lo ve `usuario` (un vendedor no ve el de otra persona).

    Args:
        db: Sesion activa.
        usuario: Quien consulta.
        gasto_id: Id del gasto.

    Returns:
        GastoOut: El gasto.

    Raises:
        GastoNoEncontradoError: Si no existe o, para un vendedor, no es suyo.
    """
    sql = _SELECT_UNIFICADO + " WHERE v.origen = 'gasto' AND v.origen_id = :gasto_id"
    parametros: dict = {"gasto_id": gasto_id}
    if usuario.rol == RolUsuario.VENDEDOR:
        sql += " AND v.registrado_por_id = :usuario_id"
        parametros["usuario_id"] = usuario.id
    fila = db.execute(text(sql), parametros).first()
    if fila is None:
        raise GastoNoEncontradoError(gasto_id)
    return _a_gasto_out(fila, usuario)


def resumen_de_gastos(db: Session, filtros: FiltrosGastos) -> ResumenGastosOut:
    """Totales vigentes del rango por categoria y por forma de pago, con y sin las compras de mercancia (RF-066).

    Los gastos anulados no suman; las compras cuentan una vez recibidas. Solo para administrador y propietario.

    Args:
        db: Sesion activa.
        filtros: Rango (los demas filtros tambien se respetan, salvo el de estado: siempre solo los vigentes).

    Returns:
        ResumenGastosOut: Los totales.
    """
    filtros = FiltrosGastos(
        desde=filtros.desde,
        hasta=filtros.hasta,
        categoria_id=filtros.categoria_id,
        metodo_pago=filtros.metodo_pago,
        estado=EstadoGasto.VIGENTE,
        origen=filtros.origen,
    )
    lista, parametros = _condiciones(filtros)
    condiciones = " AND ".join(lista)
    por_categoria = db.execute(
        text(
            "SELECT v.categoria_id, v.categoria, count(*) AS cantidad, SUM(v.monto) AS total "
            f"FROM vw_gastos_unificados v WHERE {condiciones} "
            "GROUP BY v.categoria_id, v.categoria ORDER BY total DESC, v.categoria"
        ),
        parametros,
    ).all()
    por_metodo = db.execute(
        text(
            f"SELECT v.metodo_pago, SUM(v.monto) AS total FROM vw_gastos_unificados v WHERE {condiciones} "
            "GROUP BY v.metodo_pago ORDER BY total DESC, v.metodo_pago"
        ),
        parametros,
    ).all()
    totales = db.execute(
        text(
            "SELECT COALESCE(SUM(v.monto), 0) AS total, "
            f"COALESCE(SUM(v.monto) FILTER (WHERE {_CATEGORIA_DE_SISTEMA}), 0) AS mercancia "
            f"FROM vw_gastos_unificados v WHERE {condiciones}"
        ),
        parametros,
    ).one()
    return ResumenGastosOut(
        desde=filtros.desde,
        hasta=filtros.hasta,
        total=totales.total,
        total_compras=totales.mercancia,
        total_operativo=totales.total - totales.mercancia,
        por_categoria=[
            TotalCategoriaOut(categoria_id=f.categoria_id, categoria=f.categoria, cantidad=f.cantidad, total=f.total)
            for f in por_categoria
        ],
        por_metodo_pago=[TotalMetodoOut(metodo_pago=f.metodo_pago, total=f.total) for f in por_metodo],
    )


# --- Exportacion -----------------------------------------------------------------------------------------------

_ENCABEZADOS_CSV = [
    "Fecha",
    "Origen",
    "Categoría",
    "Descripción",
    "Beneficiario",
    "Forma de pago",
    "Plataforma",
    "Monto",
    "Estado",
    "Registrado por",
    "Motivo de anulación",
]


def exportar_gastos_csv(db: Session, usuario: Usuario, filtros: FiltrosGastos) -> str:
    """Genera el CSV de los gastos y compras del rango y los filtros, una fila por gasto o compra (RF-066).

    Args:
        db: Sesion activa.
        usuario: Quien exporta (administrador o propietario).
        filtros: Rango y filtros; `estado=None` incluye los anulados.

    Returns:
        str: El CSV con BOM y punto y coma.
    """
    filas = consultar_gastos(db, usuario, filtros)
    return generar_csv(
        _ENCABEZADOS_CSV,
        (
            [
                fila.fecha.isoformat(),
                fila.origen.value,
                fila.categoria,
                fila.descripcion,
                fila.beneficiario,
                fila.metodo_pago.value if fila.metodo_pago else "",
                fila.plataforma.value if fila.plataforma else "",
                fila.monto.quantize(Decimal("1")),
                "anulado" if fila.anulado else "vigente",
                fila.registrado_por,
                fila.motivo_anulacion,
            ]
            for fila in filas
        ),
    )
