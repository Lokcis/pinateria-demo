"""Modelo de Producto y su enum de tipo."""

import enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class TipoProducto(str, enum.Enum):
    """Tipo de producto, determina si participa en composicion tipo BOM.

    Attributes:
        UNIDAD: Producto simple, vendido tal cual (no tiene componentes).
        PAQUETE: Producto compuesto por otros productos en cantidades fijas.
        ANCHETA: Producto compuesto, tipicamente armado a pedido a partir
            de una seleccion de productos individuales.
    """

    UNIDAD = "unidad"
    PAQUETE = "paquete"
    ANCHETA = "ancheta"


class Producto(Base):
    """Representa un producto del catalogo central del negocio.

    Un producto de tipo PAQUETE o ANCHETA puede tener componentes
    definidos en `producto_componentes` (relacion auto-referenciada,
    ver `ProductoComponente`). `stock_actual` siempre representa
    unidades ya ensambladas/listas para vender, incluso para productos
    compuestos: el ensamblaje bajo demanda se resuelve en la capa de
    servicio (`app.services.inventario.consumir_stock`), no aqui.

    Attributes:
        id: Identificador unico autoincremental.
        nombre: Nombre comercial del producto.
        descripcion: Descripcion opcional.
        categoria_id: FK a `categorias.id`. ON DELETE RESTRICT: no se
            puede eliminar una categoria mientras tenga productos.
        codigo_barras: Codigo de barras del producto. Nullable (HU-02:
            anchetas, mermas o mercancia artesanal sin etiqueta de
            fabrica) y unico solo cuando esta presente, garantizado por
            el indice unico parcial `ux_productos_codigo_barras` en
            lugar de una restriccion UNIQUE simple.
        tipo: Tipo de producto (unidad/paquete/ancheta).
        precio_venta: Precio de venta al publico. Debe ser >= 0.
        costo_unitario: Costo de compra ingresado a mano, o None si no esta
            definido (Adendo v2, Fase A3). El vendedor nunca lo ve.
        stock_actual: Unidades disponibles ya ensambladas. Debe ser >= 0.
        stock_minimo: Umbral para alertas de reabastecimiento (RF-008,
            RF-009). Debe ser >= 0.
        activo: Indica si el producto esta disponible para la venta.
        creado_en: Marca de tiempo de creacion del registro.
        actualizado_en: Marca de tiempo de la ultima actualizacion.
    """

    __tablename__ = "productos"
    __table_args__ = (
        CheckConstraint("precio_venta >= 0", name="productos_precio_venta_check"),
        CheckConstraint("costo_unitario >= 0", name="productos_costo_unitario_check"),
        CheckConstraint("stock_actual >= 0", name="productos_stock_actual_check"),
        CheckConstraint("stock_minimo >= 0", name="productos_stock_minimo_check"),
        Index(
            "ux_productos_codigo_barras",
            "codigo_barras",
            unique=True,
            postgresql_where=text("codigo_barras IS NOT NULL"),
        ),
        Index("ix_productos_categoria", "categoria_id"),
        # ix_productos_nombre_trgm (GIN + pg_trgm sobre `nombre`, para busqueda
        # parcial en < 1s por HU-01) requiere `CREATE EXTENSION pg_trgm` y se
        # crea con una migracion manual de Alembic (op.execute), ya que
        # autogenerate no gestiona extensiones. Ver alembic/versions/.
    )

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(String(255), nullable=True)
    categoria_id = Column(
        Integer, ForeignKey("categorias.id", ondelete="RESTRICT"), nullable=False
    )
    codigo_barras = Column(String(50), nullable=True)
    tipo = Column(
        Enum(TipoProducto, name="tipo_producto", values_callable=lambda enum_cls: [m.value for m in enum_cls]),
        nullable=False,
        default=TipoProducto.UNIDAD,
        server_default=TipoProducto.UNIDAD.value,
    )
    precio_venta = Column(Numeric(10, 2), nullable=False)
    costo_unitario = Column(Numeric(10, 2), nullable=True)
    stock_actual = Column(Integer, nullable=False, default=0, server_default="0")
    stock_minimo = Column(Integer, nullable=False, default=5, server_default="5")
    activo = Column(Boolean, nullable=False, default=True, server_default="true")
    creado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    actualizado_en = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    categoria = relationship("Categoria", back_populates="productos")

    componentes = relationship(
        "ProductoComponente",
        foreign_keys="ProductoComponente.producto_padre_id",
        back_populates="producto_padre",
        cascade="all, delete-orphan",
    )
    usado_en = relationship(
        "ProductoComponente",
        foreign_keys="ProductoComponente.producto_componente_id",
        back_populates="producto_componente",
    )

    detalles_venta = relationship("DetalleVenta", back_populates="producto")
    detalles_compra = relationship("DetalleCompra", back_populates="producto")
    ajustes_inventario = relationship("AjusteInventario", back_populates="producto")
    notificaciones = relationship("Notificacion", back_populates="producto")

    @property
    def categoria_nombre(self) -> str:
        """Nombre de la categoria del producto, para exponer en la API sin un JOIN manual en cada schema."""
        return self.categoria.nombre

    def __repr__(self) -> str:
        """Retorna una representacion legible del producto para logs/debug."""
        return f"<Producto id={self.id} nombre={self.nombre!r} tipo={self.tipo}>"
