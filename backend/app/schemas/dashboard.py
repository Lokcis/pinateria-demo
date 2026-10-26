"""Esquemas Pydantic del Dashboard del propietario (HU-03, RF-013, RF-014)."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.venta import MetodoPago


class ProductoTopOut(BaseModel):
    """Producto entre los mas vendidos del dia.

    Attributes:
        producto_id: Id del producto.
        nombre: Nombre del producto.
        unidades: Unidades vendidas hoy.
        total: Suma de los subtotales de sus lineas de venta hoy.
    """

    producto_id: int
    nombre: str
    unidades: int
    total: Decimal


class VentaDiaOut(BaseModel):
    """Ventas de un dia dentro del rango consultado (incluye dias sin ventas, en cero).

    Attributes:
        fecha: Dia, en la zona horaria del negocio.
        total: Total vendido ese dia.
        cantidad: Numero de ventas ese dia.
    """

    fecha: date
    total: Decimal
    cantidad: int


class ComprasRangoOut(BaseModel):
    """Resumen de las ordenes de compra creadas en el rango.

    El modelo no guarda la fecha de recepcion, asi que el rango se aplica a la
    fecha de la orden (no a la de su recepcion).

    Attributes:
        recibidas: Ordenes del rango ya recibidas.
        pendientes: Ordenes del rango aun pendientes.
        total_recibido: Suma de los totales de las ordenes recibidas del rango.
    """

    recibidas: int
    pendientes: int
    total_recibido: Decimal


class ResumenDashboardOut(BaseModel):
    """Resumen de un rango de dias para el Dashboard (dias en la zona horaria del negocio).

    Attributes:
        desde: Primer dia del rango (inclusivo).
        hasta: Ultimo dia del rango (inclusivo).
        ventas_por_dia: Total y cantidad de ventas por cada dia del rango.
        total_vendido: Ventas totales del rango (todos los vendedores).
        cantidad_ventas: Numero de ventas del rango.
        ticket_promedio: `total_vendido / cantidad_ventas`; 0 si no hubo ventas.
        total_por_metodo: Total por cada metodo de pago con ventas.
        top_productos: Hasta 5 productos mas vendidos por unidades.
        compras: Resumen de compras a proveedores del rango.
        alertas_stock_bajo: Cantidad actual de productos con `stock_actual <= stock_minimo`.
        generado_en: Momento en que se calculo el resumen (UTC).
    """

    desde: date
    hasta: date
    ventas_por_dia: list[VentaDiaOut]
    total_vendido: Decimal
    cantidad_ventas: int
    ticket_promedio: Decimal
    total_por_metodo: dict[MetodoPago, Decimal]
    top_productos: list[ProductoTopOut]
    compras: ComprasRangoOut
    alertas_stock_bajo: int
    generado_en: datetime


class AlertaStockOut(BaseModel):
    """Fila de la vista `vw_alertas_stock_bajo`.

    Attributes:
        id: Id del producto.
        nombre: Nombre del producto.
        categoria: Nombre de su categoria.
        stock_actual: Unidades disponibles.
        stock_minimo: Umbral configurado.
    """

    id: int
    nombre: str
    categoria: str
    stock_actual: int
    stock_minimo: int


class ItemListaComprasOut(BaseModel):
    """Producto de la lista de compras (Adendo v2, mejora B1: RF-044).

    Attributes:
        producto_id: Id del producto.
        nombre: Nombre del producto.
        categoria: Nombre de su categoria.
        stock_actual: Unidades disponibles.
        stock_minimo: Umbral configurado.
        faltante: `stock_minimo - stock_actual`; 0 si el producto esta justo en el minimo.
    """

    producto_id: int
    nombre: str
    categoria: str
    stock_actual: int
    stock_minimo: int
    faltante: int


class ListaComprasOut(BaseModel):
    """Lista de compras calculada al abrirla (Adendo v2, mejora B1: RF-044, RF-045).

    Attributes:
        productos: Productos activos en stock bajo, por categoria y nombre.
        generado_en: Momento en que se calculo la lista (UTC).
    """

    productos: list[ItemListaComprasOut]
    generado_en: datetime
