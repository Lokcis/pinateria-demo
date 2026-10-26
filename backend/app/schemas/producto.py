"""Esquemas Pydantic para Producto."""

from datetime import datetime
from decimal import Decimal

from pydantic import AliasPath, BaseModel, ConfigDict, Field, field_validator

from app.models.ajuste_inventario import TipoAjuste
from app.models.producto import TipoProducto
from app.schemas.tipos import NombreCapitalizado, TextoCapitalizado


class ComponenteIn(BaseModel):
    """Un componente de la receta de un producto compuesto (paquete o ancheta).

    Attributes:
        producto_id: Id del producto que se consume como parte de la receta.
        cantidad: Unidades de ese producto por cada unidad del compuesto.
            Entera y mayor a cero: el descuento de stock no admite fracciones.
    """

    producto_id: int
    cantidad: int = Field(ge=1)


class ComponenteOut(BaseModel):
    """Un componente de la receta, con los datos que necesita la tarjeta del producto.

    Attributes:
        producto_id: Id del producto componente.
        nombre: Nombre del producto componente.
        cantidad: Unidades requeridas por cada unidad del compuesto.
        activo: Si el componente sigue activo (un componente inactivo se
            sigue descontando al armar; se expone para poder avisarlo).
    """

    model_config = ConfigDict(from_attributes=True)

    producto_id: int = Field(validation_alias="producto_componente_id")
    nombre: str = Field(validation_alias=AliasPath("producto_componente", "nombre"))
    cantidad: int
    activo: bool = Field(validation_alias=AliasPath("producto_componente", "activo"))


class UsadoEnOut(BaseModel):
    """Producto compuesto (activo o no) en cuya receta participa un producto.

    Attributes:
        id: Id del producto compuesto.
        nombre: Nombre del producto compuesto.
        tipo: Tipo del compuesto (paquete/ancheta).
        activo: Si el compuesto esta activo.
    """

    id: int
    nombre: str
    tipo: TipoProducto
    activo: bool


class ProductoOut(BaseModel):
    """Representacion de un producto expuesta por la API.

    Attributes:
        id: Identificador unico del producto.
        nombre: Nombre comercial del producto.
        descripcion: Descripcion opcional.
        categoria_id: Id de la categoria a la que pertenece.
        codigo_barras: Codigo de barras, si tiene.
        tipo: Tipo de producto (unidad/paquete/ancheta).
        precio_venta: Precio de venta al publico.
        stock_actual: Unidades disponibles ya ensambladas.
        stock_minimo: Umbral de alerta de reabastecimiento.
        activo: Si el producto esta disponible para la venta.
        componentes: Receta del producto (vacia si no es compuesto).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str | None
    categoria_id: int
    categoria_nombre: str
    codigo_barras: str | None
    tipo: TipoProducto
    precio_venta: Decimal
    stock_actual: int
    stock_minimo: int
    activo: bool
    componentes: list[ComponenteOut] = []


class ProductoCrearIn(BaseModel):
    """Payload para dar de alta un producto nuevo (HU-02, RF-016).

    `codigo_barras` es opcional (HU-02: anchetas, mermas o mercancia
    artesanal sin etiqueta de fabrica); `nombre`, `precio_venta`,
    `categoria_id` y `stock_inicial` son obligatorios.

    Attributes:
        nombre: Nombre comercial del producto.
        descripcion: Descripcion opcional.
        categoria_id: Id de la categoria a la que pertenece.
        codigo_barras: Codigo de barras, opcional.
        tipo: Tipo de producto (unidad/paquete/ancheta). Por defecto, unidad.
        precio_venta: Precio de venta al publico. Debe ser >= 0.
        stock_inicial: Unidades disponibles al momento de crear el producto.
        stock_minimo: Umbral de alerta de reabastecimiento. Por defecto, 5.
        componentes: Receta, solo para productos paquete/ancheta.
    """

    nombre: NombreCapitalizado = Field(min_length=1, max_length=150)
    descripcion: TextoCapitalizado | None = Field(default=None, max_length=255)
    categoria_id: int
    codigo_barras: str | None = Field(default=None, max_length=50)
    tipo: TipoProducto = TipoProducto.UNIDAD
    precio_venta: Decimal = Field(ge=0)
    stock_inicial: int = Field(ge=0)
    stock_minimo: int = Field(default=5, ge=0)
    componentes: list[ComponenteIn] = []


class ProductoEditarIn(BaseModel):
    """Payload para editar los atributos generales de un producto ya existente (RF-016).

    Todos los campos son opcionales: solo se actualizan los que vengan
    presentes en el payload (los ausentes conservan su valor actual).
    No incluye `stock_actual` ni `stock_minimo`: esos se manejan con sus
    propios endpoints (`/ajustes` y `/stock-minimo`) para mantener la
    trazabilidad de por que cambia el stock.

    Attributes:
        nombre: Nuevo nombre comercial.
        descripcion: Nueva descripcion.
        categoria_id: Nueva categoria.
        codigo_barras: Nuevo codigo de barras (o `None` para quitarlo).
        tipo: Nuevo tipo de producto.
        precio_venta: Nuevo precio de venta. Debe ser >= 0.
        componentes: Nueva receta completa (reemplaza la anterior; `[]` la
            vacia; ausente la conserva).
    """

    nombre: NombreCapitalizado | None = Field(default=None, min_length=1, max_length=150)
    descripcion: TextoCapitalizado | None = Field(default=None, max_length=255)
    categoria_id: int | None = None
    codigo_barras: str | None = Field(default=None, max_length=50)
    tipo: TipoProducto | None = None
    precio_venta: Decimal | None = Field(default=None, ge=0)
    componentes: list[ComponenteIn] | None = None


class CatalogoOut(BaseModel):
    """Pagina de resultados del catalogo de productos (RF-006).

    Attributes:
        total: Cantidad total de productos que cumplen el filtro,
            sin aplicar paginacion (para que el frontend calcule
            cuantas paginas hay).
        productos: Los productos de la pagina actual.
    """

    total: int
    productos: list[ProductoOut]


class StockMinimoIn(BaseModel):
    """Payload para actualizar el stock minimo de un producto (RF-007).

    Attributes:
        stock_minimo: Nuevo umbral de alerta de reabastecimiento. Debe
            ser mayor o igual a cero.
    """

    stock_minimo: int = Field(ge=0)


class AjusteInventarioIn(BaseModel):
    """Payload para registrar un ajuste manual de inventario (RF-009).

    Attributes:
        tipo: Tipo de ajuste (entrada/salida/merma/correccion).
        cantidad: Magnitud con signo del ajuste. Distinta de cero:
            positiva incrementa el stock, negativa lo decrementa.
        motivo: Justificacion textual obligatoria, para trazabilidad.
    """

    tipo: TipoAjuste
    cantidad: int
    motivo: TextoCapitalizado = Field(min_length=1, max_length=255)

    @field_validator("cantidad")
    @classmethod
    def _cantidad_distinta_de_cero(cls, valor: int) -> int:
        """Rechaza un ajuste que no moveria el stock (misma regla que el CHECK de la tabla)."""
        if valor == 0:
            raise ValueError("La cantidad del ajuste debe ser distinta de cero.")
        return valor


class AjusteInventarioOut(BaseModel):
    """Representacion de un ajuste de inventario ya registrado.

    Attributes:
        id: Identificador unico del ajuste.
        producto_id: Producto afectado por el ajuste.
        usuario_id: Usuario que registro el ajuste.
        tipo: Tipo de ajuste (entrada/salida/merma/correccion).
        cantidad: Magnitud con signo del ajuste.
        motivo: Justificacion textual registrada.
        fecha: Marca de tiempo en la que se registro el ajuste.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    usuario_id: int
    tipo: TipoAjuste
    cantidad: int
    motivo: str
    fecha: datetime
