"""Router de costos y ganancias (Adendo v2, Fase A3: RF-037 a RF-040, HU-09).

Consultar costos y ganancias: administrador y propietario. Modificar costos y
completar las ventas pasadas sin costo: solo administrador. El vendedor recibe
403 en todo (RF-040) y ninguna respuesta que el vea incluye costos.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, text
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import requerir_roles
from app.models.producto import Producto
from app.models.producto_componente import ProductoComponente
from app.models.usuario import RolUsuario, Usuario
from app.schemas.ganancias import (
    CompletarCostosOut,
    CostoIn,
    CostoProductoOut,
    GananciaNetaOut,
    GananciasOut,
    MargenDiaOut,
    MargenOut,
    MargenProductoOut,
    SinCostoOut,
    TablaCostosOut,
)
from app.services.gastos import FiltrosGastos, resumen_de_gastos
from app.services.rangos import rango_de_fechas

router = APIRouter(tags=["ganancias"])

_consulta = requerir_roles(RolUsuario.ADMINISTRADOR, RolUsuario.PROPIETARIO)
_solo_administrador = requerir_roles(RolUsuario.ADMINISTRADOR)

CERO = Decimal("0")

_CONTAR_POR_COMPLETAR = text(
    "SELECT count(*) FROM detalle_ventas d JOIN productos p ON p.id = d.producto_id "
    "WHERE d.costo_unitario IS NULL AND p.costo_unitario IS NOT NULL"
)
_COMPLETAR = text(
    "UPDATE detalle_ventas d SET costo_unitario = p.costo_unitario FROM productos p "
    "WHERE p.id = d.producto_id AND d.costo_unitario IS NULL AND p.costo_unitario IS NOT NULL"
)


def _costo_sugerido(producto: Producto) -> tuple[Decimal | None, bool]:
    """Suma del costo de los componentes por la cantidad de la receta (RF-037).

    Args:
        producto: Producto con sus `componentes` cargados.

    Returns:
        tuple: (sugerido o None, incompleto). Sin receta: (None, False). Si a
        algun componente le falta el costo: (None, True).
    """
    if not producto.componentes:
        return None, False
    total = CERO
    for componente in producto.componentes:
        costo = componente.producto_componente.costo_unitario
        if costo is None:
            return None, True
        total += costo * componente.cantidad
    return total.quantize(Decimal("0.01")), False


def _a_costo_out(producto: Producto) -> CostoProductoOut:
    """Arma la fila de la tabla de costos de un producto.

    Args:
        producto: Producto con categoria y componentes cargados.

    Returns:
        CostoProductoOut: La fila.
    """
    sugerido, incompleto = _costo_sugerido(producto)
    return CostoProductoOut(
        producto_id=producto.id,
        nombre=producto.nombre,
        categoria=producto.categoria.nombre,
        tipo=producto.tipo,
        activo=producto.activo,
        precio_venta=producto.precio_venta,
        costo_unitario=producto.costo_unitario,
        costo_sugerido=sugerido,
        sugerido_incompleto=incompleto,
    )


@router.get("/costos", response_model=TablaCostosOut)
def tabla_de_costos(
    solo_sin_costo: bool = Query(False, description="Solo productos sin costo."),
    incluir_inactivos: bool = Query(False, description="Incluir productos desactivados."),
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(_consulta),
) -> TablaCostosOut:
    """Tabla de costos de los productos, con el sugerido de paquetes y anchetas (RF-037).

    Args:
        solo_sin_costo: Si es True, solo productos sin costo.
        incluir_inactivos: Si es True, incluye los desactivados.
        db: Sesion de base de datos inyectada.
        _usuario: Usuario autenticado (ADMINISTRADOR o PROPIETARIO).

    Returns:
        TablaCostosOut: Los productos y cuantas lineas de ventas pasadas se pueden completar.
    """
    consulta = db.query(Producto).options(
        joinedload(Producto.categoria),
        joinedload(Producto.componentes).joinedload(ProductoComponente.producto_componente),
    )
    if not incluir_inactivos:
        consulta = consulta.filter(Producto.activo.is_(True))
    if solo_sin_costo:
        consulta = consulta.filter(Producto.costo_unitario.is_(None))
    productos = consulta.order_by(Producto.nombre, Producto.id).all()
    return TablaCostosOut(
        productos=[_a_costo_out(p) for p in productos],
        lineas_por_completar=db.execute(_CONTAR_POR_COMPLETAR).scalar() or 0,
    )


@router.patch("/productos/{producto_id}/costo", response_model=CostoProductoOut)
def guardar_costo(
    producto_id: int,
    payload: CostoIn,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(_solo_administrador),
) -> CostoProductoOut:
    """Guarda a mano el costo de un producto (RF-037). Solo administrador.

    Cambiar el costo no altera las ventas pasadas: cada linea guardo el costo
    vigente al venderse.

    Args:
        producto_id: Id del producto.
        payload: Costo nuevo, o None para dejarlo sin costo.
        db: Sesion de base de datos inyectada.
        _usuario: Administrador autenticado.

    Returns:
        CostoProductoOut: La fila actualizada.

    Raises:
        HTTPException: 404 si el producto no existe.
    """
    producto = (
        db.query(Producto)
        .options(
            joinedload(Producto.categoria),
            joinedload(Producto.componentes).joinedload(ProductoComponente.producto_componente),
        )
        .filter(Producto.id == producto_id)
        .one_or_none()
    )
    if producto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"El producto con id={producto_id} no existe.")
    producto.costo_unitario = payload.costo_unitario
    db.commit()
    db.refresh(producto)
    return _a_costo_out(producto)


@router.post("/costos/completar-ventas", response_model=CompletarCostosOut)
def completar_costos_de_ventas(
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(_solo_administrador),
) -> CompletarCostosOut:
    """Llena con el costo actual del producto solo las lineas de ventas pasadas que no tienen costo.

    Es una aproximacion pensada para las ventas hechas antes de cargar los
    costos (decision del 08-10-2026). Las lineas que ya tienen costo no se tocan.

    Args:
        db: Sesion de base de datos inyectada.
        _usuario: Administrador autenticado.

    Returns:
        CompletarCostosOut: Cuantas lineas se completaron.
    """
    resultado = db.execute(_COMPLETAR)
    db.commit()
    return CompletarCostosOut(lineas_completadas=resultado.rowcount)


def _margen(ingreso: Decimal, costo: Decimal) -> MargenOut:
    """Calcula margen y porcentaje a partir del ingreso neto y el costo.

    Args:
        ingreso: Ingreso neto.
        costo: Costo total.

    Returns:
        MargenOut: Ingreso, costo, margen y porcentaje (None si no hubo ingreso).
    """
    margen = ingreso - costo
    porcentaje = (margen * 100 / ingreso).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP) if ingreso else None
    return MargenOut(ingreso_neto=ingreso, costo_total=costo, margen=margen, margen_porcentaje=porcentaje)


def _ganancia_neta(
    db: Session, desde: date, hasta: date, parametros: dict, margen_bruto: Decimal, incompleta: bool
) -> GananciaNetaOut:
    """Ganancia neta y resultado de caja del rango (Adendo v3, Fase G3: RF-067).

    `ganancia neta = margen bruto - gastos operativos` (los gastos vigentes sin las compras de mercancia, que
    ya estan en el costo de lo vendido). `resultado de caja = ventas cobradas - todos los gastos vigentes`,
    compras incluidas. Los gastos se filtran por su fecha contable; las ventas, por su hora (dia de Bogota).

    Args:
        db: Sesion activa.
        desde: Primer dia del rango.
        hasta: Ultimo dia del rango.
        parametros: Parametros `inicio`, `fin` y `zona` ya armados para las consultas de ventas.
        margen_bruto: Margen del rango, solo con lineas con costo.
        incompleta: True si hay ventas sin costo cargado.

    Returns:
        GananciaNetaOut: Las cifras.
    """
    gastos = resumen_de_gastos(db, FiltrosGastos(desde=desde, hasta=hasta))
    cobradas = db.execute(
        text(
            "SELECT COALESCE(SUM(p.monto), 0) FROM pagos_venta p JOIN ventas v ON v.id = p.venta_id "
            "WHERE v.fecha >= :inicio AND v.fecha < :fin"
        ),
        parametros,
    ).scalar_one()
    return GananciaNetaOut(
        margen_bruto=margen_bruto,
        gastos_operativos=gastos.total_operativo,
        ganancia_neta=margen_bruto - gastos.total_operativo,
        incompleta=incompleta,
        ventas_cobradas=cobradas,
        compras_recibidas=gastos.total_compras,
        gastos_totales=gastos.total,
        resultado_de_caja=cobradas - gastos.total,
    )


@router.get("/ganancias", response_model=GananciasOut)
def ganancias(
    desde: date | None = Query(None, description="Primer dia (inclusivo). Por defecto, hasta."),
    hasta: date | None = Query(None, description="Ultimo dia (inclusivo). Por defecto, hoy."),
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(_consulta),
) -> GananciasOut:
    """Margen bruto del rango (resumen, por dia y por producto) y su ganancia neta (RF-038, RF-039, RF-067).

    Lee `vw_margen_detalle`. Solo las lineas con costo entran en el margen; las
    demas se informan en `sin_costo`. Los dias se calculan en `ZONA_HORARIA`.
    `neta` resta al margen los gastos operativos del rango y agrega el resultado de caja.

    Args:
        desde: Primer dia del rango.
        hasta: Ultimo dia del rango (no futuro).
        db: Sesion de base de datos inyectada.
        _usuario: Usuario autenticado (ADMINISTRADOR o PROPIETARIO).

    Returns:
        GananciasOut: El margen del rango y su ganancia neta.

    Raises:
        HTTPException: 422 si el rango es invalido (ver `rango_de_fechas`).
    """
    desde, hasta, inicio, fin = rango_de_fechas(desde, hasta)
    parametros = {"inicio": inicio, "fin": fin, "zona": settings.zona_horaria}

    resumen = db.execute(
        text(
            "SELECT COALESCE(SUM(ingreso_neto), 0), COALESCE(SUM(costo_total), 0) FROM vw_margen_detalle "
            "WHERE fecha >= :inicio AND fecha < :fin AND costo_total IS NOT NULL"
        ),
        parametros,
    ).one()
    sin_costo = db.execute(
        text(
            "SELECT count(*), COALESCE(SUM(ingreso_neto), 0) FROM vw_margen_detalle "
            "WHERE fecha >= :inicio AND fecha < :fin AND costo_total IS NULL"
        ),
        parametros,
    ).one()
    por_dia = {
        fila.dia: (fila.ingreso, fila.costo)
        for fila in db.execute(
            text(
                "SELECT date(timezone(:zona, fecha)) AS dia, SUM(ingreso_neto) AS ingreso, SUM(costo_total) AS costo "
                "FROM vw_margen_detalle WHERE fecha >= :inicio AND fecha < :fin AND costo_total IS NOT NULL "
                "GROUP BY dia"
            ),
            parametros,
        )
    }
    por_producto = db.execute(
        text(
            "SELECT m.producto_id, p.nombre, SUM(m.cantidad) AS unidades, SUM(m.ingreso_neto) AS ingreso, "
            "SUM(m.costo_total) AS costo, SUM(m.margen) AS margen "
            "FROM vw_margen_detalle m JOIN productos p ON p.id = m.producto_id "
            "WHERE m.fecha >= :inicio AND m.fecha < :fin AND m.costo_total IS NOT NULL "
            "GROUP BY m.producto_id, p.nombre ORDER BY margen DESC, p.nombre"
        ),
        parametros,
    ).all()

    serie = []
    for indice in range((hasta - desde).days + 1):
        dia = desde + timedelta(days=indice)
        ingreso, costo = por_dia.get(dia, (CERO, CERO))
        serie.append(MargenDiaOut(fecha=dia, **_margen(ingreso, costo).model_dump()))

    margen_resumen = _margen(resumen[0], resumen[1])
    return GananciasOut(
        desde=desde,
        hasta=hasta,
        resumen=margen_resumen,
        por_dia=serie,
        por_producto=[
            MargenProductoOut(
                producto_id=fila.producto_id,
                nombre=fila.nombre,
                unidades=int(fila.unidades),
                **_margen(fila.ingreso, fila.costo).model_dump(),
            )
            for fila in por_producto
        ],
        sin_costo=SinCostoOut(lineas=sin_costo[0], ingreso_neto=sin_costo[1]),
        neta=_ganancia_neta(db, desde, hasta, parametros, margen_resumen.margen, sin_costo[0] > 0),
        generado_en=datetime.now(timezone.utc),
    )
