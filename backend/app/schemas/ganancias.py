"""Esquemas Pydantic de costos y ganancias (Adendo v2, Fase A3: RF-037 a RF-040, HU-09).

Solo los usan endpoints de administrador y propietario: el vendedor nunca ve costos.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.producto import TipoProducto


class CostoProductoOut(BaseModel):
    """Un producto en la tabla de costos.

    Attributes:
        producto_id: Id del producto.
        nombre: Nombre del producto.
        categoria: Nombre de su categoria.
        tipo: unidad / paquete / ancheta.
        activo: Si sigue a la venta.
        precio_venta: Precio de venta actual.
        costo_unitario: Costo ingresado a mano, o None ("sin costo").
        costo_sugerido: Para paquetes y anchetas, suma del costo de sus
            componentes por la cantidad de la receta; None si no tiene receta
            o si a algun componente le falta el costo.
        sugerido_incompleto: True si tiene receta pero a algun componente le
            falta el costo (por eso no hay sugerido).
    """

    producto_id: int
    nombre: str
    categoria: str
    tipo: TipoProducto
    activo: bool
    precio_venta: Decimal
    costo_unitario: Decimal | None
    costo_sugerido: Decimal | None
    sugerido_incompleto: bool


class TablaCostosOut(BaseModel):
    """Respuesta de `GET /costos`.

    Attributes:
        productos: Productos ordenados por nombre.
        lineas_por_completar: Lineas de ventas pasadas sin costo cuyo producto
            ya tiene costo (las que completaria `POST /costos/completar-ventas`).
    """

    productos: list[CostoProductoOut]
    lineas_por_completar: int


class CostoIn(BaseModel):
    """Payload de `PATCH /productos/{id}/costo`.

    Attributes:
        costo_unitario: Costo de compra (>= 0, hasta 2 decimales), o None para dejarlo sin costo.
    """

    costo_unitario: Decimal | None = Field(..., ge=0, max_digits=10, decimal_places=2)


class CompletarCostosOut(BaseModel):
    """Respuesta de `POST /costos/completar-ventas`.

    Attributes:
        lineas_completadas: Lineas de venta que recibieron el costo actual de su producto.
    """

    lineas_completadas: int


class MargenOut(BaseModel):
    """Ingreso neto, costo y margen de un conjunto de lineas con costo.

    Attributes:
        ingreso_neto: Subtotal menos el descuento repartido.
        costo_total: Costo por cantidad.
        margen: `ingreso_neto - costo_total`.
        margen_porcentaje: Margen sobre el ingreso neto (0 a 100), o None si no hubo ingreso.
    """

    ingreso_neto: Decimal
    costo_total: Decimal
    margen: Decimal
    margen_porcentaje: Decimal | None


class MargenDiaOut(MargenOut):
    """Margen de un dia del rango (los dias sin ventas van en cero).

    Attributes:
        fecha: Dia, en la zona horaria del negocio.
    """

    fecha: date


class MargenProductoOut(MargenOut):
    """Margen de un producto en el rango.

    Attributes:
        producto_id: Id del producto.
        nombre: Nombre del producto.
        unidades: Unidades vendidas con costo.
    """

    producto_id: int
    nombre: str
    unidades: int


class SinCostoOut(BaseModel):
    """Lineas vendidas sin costo, que quedan fuera del margen.

    Attributes:
        lineas: Cantidad de lineas sin costo.
        ingreso_neto: Ingreso neto de esas lineas.
    """

    lineas: int
    ingreso_neto: Decimal


class GananciaNetaOut(BaseModel):
    """Ganancia neta y resultado de caja del rango (Adendo v3, Fase G3: RF-067).

    La ganancia neta resta al margen bruto solo los gastos OPERATIVOS: las compras de mercancia ya entran en el
    margen como costo de lo vendido, y contarlas tambien al comprarlas las duplicaria. El resultado de caja, en
    cambio, es una cifra de flujo de dinero (lo cobrado menos TODO lo gastado, compras incluidas); no es una
    ganancia contable.

    Attributes:
        margen_bruto: Margen del rango (`resumen.margen`), solo con lineas con costo.
        gastos_operativos: Gastos vigentes del rango sin las compras de mercancia (por la fecha del gasto).
        ganancia_neta: `margen_bruto - gastos_operativos`.
        incompleta: True si hay ventas sin costo cargado: la ganancia neta esta incompleta, faltan costos.
        ventas_cobradas: Suma de los pagos de las ventas del rango.
        compras_recibidas: Compras de mercancia recibidas en el rango (ya incluidas en `gastos_totales`).
        gastos_totales: Todos los gastos vigentes del rango, incluidas las compras recibidas.
        resultado_de_caja: `ventas_cobradas - gastos_totales`.
    """

    margen_bruto: Decimal
    gastos_operativos: Decimal
    ganancia_neta: Decimal
    incompleta: bool
    ventas_cobradas: Decimal
    compras_recibidas: Decimal
    gastos_totales: Decimal
    resultado_de_caja: Decimal


class GananciasOut(BaseModel):
    """Respuesta de `GET /ganancias` (RF-038, RF-039, RF-067).

    El ajuste por redondeo de cada venta no entra en el margen por producto
    (docs/03, seccion 7.8).

    Attributes:
        desde: Primer dia del rango (inclusivo).
        hasta: Ultimo dia del rango (inclusivo).
        resumen: Margen del rango, solo con lineas con costo.
        por_dia: Margen de cada dia del rango.
        por_producto: Margen por producto, de mayor a menor margen.
        sin_costo: Lineas sin costo, excluidas del margen.
        neta: Ganancia neta y resultado de caja del rango (Adendo v3, Fase G3).
        generado_en: Momento del calculo (UTC).
    """

    desde: date
    hasta: date
    resumen: MargenOut
    por_dia: list[MargenDiaOut]
    por_producto: list[MargenProductoOut]
    sin_costo: SinCostoOut
    neta: GananciaNetaOut
    generado_en: datetime
