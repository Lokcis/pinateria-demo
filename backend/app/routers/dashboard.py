"""Router del Dashboard de solo lectura para el propietario (HU-03, RF-013, RF-014)."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import requerir_roles
from app.models.compra import Compra, EstadoCompra
from app.models.detalle_venta import DetalleVenta
from app.models.pago_venta import PagoVenta
from app.models.producto import Producto
from app.models.usuario import RolUsuario, Usuario
from app.models.venta import Venta
from app.schemas.dashboard import (
    AlertaStockOut,
    ComprasRangoOut,
    ItemListaComprasOut,
    ListaComprasOut,
    ProductoTopOut,
    VentaDiaOut,
    ResumenDashboardOut,
)
from app.services.rangos import rango_de_fechas

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

TOP_PRODUCTOS = 5

_CONSULTA_ALERTAS = text(
    "SELECT id, nombre, categoria, stock_actual, stock_minimo "
    "FROM vw_alertas_stock_bajo ORDER BY (stock_actual - stock_minimo), nombre"
)

_CONSULTA_LISTA_COMPRAS = text(
    "SELECT id, nombre, categoria, stock_actual, stock_minimo "
    "FROM vw_alertas_stock_bajo ORDER BY categoria, nombre, id"
)

_solo_lectura = requerir_roles(RolUsuario.PROPIETARIO, RolUsuario.ADMINISTRADOR)


@router.get("/resumen", response_model=ResumenDashboardOut)
def resumen_del_dia(
    desde: date | None = Query(None, description="Primer dia (inclusivo). Por defecto, hasta."),
    hasta: date | None = Query(None, description="Ultimo dia (inclusivo). Por defecto, hoy."),
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(_solo_lectura),
) -> ResumenDashboardOut:
    """Resumen de un rango de dias (por defecto hoy): ventas, metodos de pago, top, serie y compras.

    Los dias se calculan en `ZONA_HORARIA` (America/Bogota), como `GET /ventas/hoy`.
    Todo se agrega en SQL, sin cargar las ventas en memoria: el Dashboard debe
    cargar en menos de 10 s desde una red movil (HU-03). Las alertas de stock
    reflejan el estado actual, no el del rango.

    Args:
        desde: Primer dia del rango (inclusivo).
        hasta: Ultimo dia del rango (inclusivo, no futuro).
        db: Sesion de base de datos inyectada.
        _usuario: Usuario autenticado (PROPIETARIO o ADMINISTRADOR).

    Returns:
        ResumenDashboardOut: El resumen del rango.

    Raises:
        HTTPException: 422 si el rango es invalido (ver `rango_de_fechas`).
    """
    desde, hasta, inicio, fin = rango_de_fechas(desde, hasta)
    ventas_del_rango = (Venta.fecha >= inicio, Venta.fecha < fin)

    # Adendo v2 (RF-041): el total por metodo suma el monto de cada pago, asi una
    # venta con pagos mixtos aporta a cada metodo lo que se pago con el.
    por_metodo = dict(
        db.query(PagoVenta.metodo_pago, func.sum(PagoVenta.monto))
        .join(Venta, Venta.id == PagoVenta.venta_id)
        .filter(*ventas_del_rango)
        .group_by(PagoVenta.metodo_pago)
        .all()
    )
    total_vendido = db.query(func.coalesce(func.sum(Venta.total), 0)).filter(*ventas_del_rango).scalar()
    cantidad_ventas = db.query(func.count(Venta.id)).filter(*ventas_del_rango).scalar() or 0
    ticket_promedio = (total_vendido / cantidad_ventas) if cantidad_ventas else Decimal("0")

    dia = func.date(func.timezone(settings.zona_horaria, Venta.fecha))
    por_dia = {
        d: (total, cantidad)
        for d, total, cantidad in db.query(dia, func.sum(Venta.total), func.count(Venta.id))
        .filter(*ventas_del_rango)
        .group_by(dia)
        .all()
    }
    serie = []
    for indice in range((hasta - desde).days + 1):
        d = desde + timedelta(days=indice)
        total_dia, cantidad_dia = por_dia.get(d, (Decimal("0"), 0))
        serie.append(VentaDiaOut(fecha=d, total=total_dia, cantidad=cantidad_dia))

    unidades = func.sum(DetalleVenta.cantidad)
    top = (
        db.query(Producto.id, Producto.nombre, unidades, func.sum(DetalleVenta.subtotal))
        .join(DetalleVenta, DetalleVenta.producto_id == Producto.id)
        .join(Venta, Venta.id == DetalleVenta.venta_id)
        .filter(*ventas_del_rango)
        .group_by(Producto.id, Producto.nombre)
        .order_by(unidades.desc(), Producto.nombre)
        .limit(TOP_PRODUCTOS)
        .all()
    )

    filtro_compras = (Compra.fecha >= inicio, Compra.fecha < fin)
    compras = dict(
        db.query(Compra.estado, func.count(Compra.id)).filter(*filtro_compras).group_by(Compra.estado).all()
    )
    total_recibido = (
        db.query(func.coalesce(func.sum(Compra.total), 0))
        .filter(*filtro_compras, Compra.estado == EstadoCompra.RECIBIDA)
        .scalar()
    )

    alertas = db.execute(text("SELECT count(*) FROM vw_alertas_stock_bajo")).scalar() or 0

    return ResumenDashboardOut(
        desde=desde,
        hasta=hasta,
        ventas_por_dia=serie,
        total_vendido=total_vendido,
        cantidad_ventas=cantidad_ventas,
        ticket_promedio=ticket_promedio,
        total_por_metodo=por_metodo,
        top_productos=[
            ProductoTopOut(producto_id=pid, nombre=nombre, unidades=int(cant), total=total)
            for pid, nombre, cant, total in top
        ],
        compras=ComprasRangoOut(
            recibidas=compras.get(EstadoCompra.RECIBIDA, 0),
            pendientes=compras.get(EstadoCompra.PENDIENTE, 0),
            total_recibido=total_recibido,
        ),
        alertas_stock_bajo=alertas,
        generado_en=datetime.now(timezone.utc),
    )


@router.get("/alertas-stock", response_model=list[AlertaStockOut])
def alertas_de_stock_bajo(
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(_solo_lectura),
) -> list[AlertaStockOut]:
    """Productos activos con `stock_actual <= stock_minimo` (vista `vw_alertas_stock_bajo`).

    Se lee la vista en vivo, no la tabla `notificaciones`: asi el tablero refleja
    el estado real aunque la tarea Celery aun no haya corrido (RF-013).

    Args:
        db: Sesion de base de datos inyectada.
        _usuario: Usuario autenticado (PROPIETARIO o ADMINISTRADOR).

    Returns:
        list[AlertaStockOut]: Los productos en alerta, los mas criticos primero.
    """
    filas = db.execute(_CONSULTA_ALERTAS).all()
    return [
        AlertaStockOut(
            id=f.id, nombre=f.nombre, categoria=f.categoria, stock_actual=f.stock_actual, stock_minimo=f.stock_minimo
        )
        for f in filas
    ]


@router.get("/lista-compras", response_model=ListaComprasOut)
def lista_de_compras(
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(_solo_lectura),
) -> ListaComprasOut:
    """Lista de compras con lo que falta para llegar al stock minimo (Adendo v2, mejora B1: RF-044).

    Se calcula en vivo desde la vista `vw_alertas_stock_bajo` (productos activos con
    `stock_actual <= stock_minimo`), no desde las notificaciones, para que nunca quede
    desactualizada. Incluye los productos justo en el minimo (faltante 0) y los
    compuestos; la cantidad a comprar la decide el propietario.

    Args:
        db: Sesion de base de datos inyectada.
        _usuario: Usuario autenticado (PROPIETARIO o ADMINISTRADOR).

    Returns:
        ListaComprasOut: Los productos ordenados por categoria y nombre.
    """
    filas = db.execute(_CONSULTA_LISTA_COMPRAS).all()
    return ListaComprasOut(
        productos=[
            ItemListaComprasOut(
                producto_id=f.id,
                nombre=f.nombre,
                categoria=f.categoria,
                stock_actual=f.stock_actual,
                stock_minimo=f.stock_minimo,
                faltante=f.stock_minimo - f.stock_actual,
            )
            for f in filas
        ],
        generado_en=datetime.now(timezone.utc),
    )
