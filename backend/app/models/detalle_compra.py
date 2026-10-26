"""Modelo de DetalleCompra: linea individual de una orden de compra."""

from sqlalchemy import CheckConstraint, Column, ForeignKey, Index, Integer, Numeric
from sqlalchemy.orm import relationship

from app.core.database import Base


class DetalleCompra(Base):
    """Representa una linea de producto dentro de una orden de compra.

    Al marcar la compra como RECIBIDA, cada linea incrementa
    `productos.stock_actual` del producto correspondiente en `cantidad`
    (logica de aplicacion, no un trigger de base de datos).

    Attributes:
        id: Identificador unico autoincremental.
        compra_id: FK a `compras.id`. ON DELETE CASCADE.
        producto_id: FK a `productos.id`. ON DELETE RESTRICT.
        cantidad: Cantidad ordenada/recibida de este producto. Debe ser > 0.
        costo_unitario: Costo unitario pactado con el proveedor.
        subtotal: `cantidad * costo_unitario`, almacenado explicitamente.
    """

    __tablename__ = "detalle_compras"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="detalle_compras_cantidad_check"),
        CheckConstraint("costo_unitario >= 0", name="detalle_compras_costo_unitario_check"),
        CheckConstraint("subtotal >= 0", name="detalle_compras_subtotal_check"),
        Index("ix_detalle_compras_compra", "compra_id"),
        Index("ix_detalle_compras_producto", "producto_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    compra_id = Column(Integer, ForeignKey("compras.id", ondelete="CASCADE"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id", ondelete="RESTRICT"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    costo_unitario = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)

    compra = relationship("Compra", back_populates="detalles")
    producto = relationship("Producto", back_populates="detalles_compra")

    @property
    def producto_nombre(self) -> str:
        """Nombre del producto de la linea, para serializar el detalle."""
        return self.producto.nombre

    def __repr__(self) -> str:
        """Retorna una representacion legible del detalle para logs/debug."""
        return (
            f"<DetalleCompra compra_id={self.compra_id} producto_id={self.producto_id} "
            f"cantidad={self.cantidad}>"
        )
