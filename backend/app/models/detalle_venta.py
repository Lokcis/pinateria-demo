"""Modelo de DetalleVenta: linea individual de una venta."""

from sqlalchemy import CheckConstraint, Column, ForeignKey, Index, Integer, Numeric
from sqlalchemy.orm import relationship

from app.core.database import Base


class DetalleVenta(Base):
    """Representa una linea de producto dentro de una venta.

    Attributes:
        id: Identificador unico autoincremental.
        venta_id: FK a `ventas.id`. ON DELETE CASCADE: si se elimina la
            venta, sus lineas dejan de tener sentido por separado.
        producto_id: FK a `productos.id`. ON DELETE RESTRICT: protege el
            historial contable.
        cantidad: Cantidad vendida de este producto. Debe ser > 0.
        precio_unitario: Precio unitario aplicado al momento de la venta
            (se congela aqui para no verse afectado por cambios futuros
            en `productos.precio_venta`).
        subtotal: `cantidad * precio_unitario`, almacenado explicitamente
            para evitar recalcular en cada lectura de reportes.
        descuento_prorrateado: Parte del descuento de la venta que le
            corresponde a esta linea, en proporcion a su subtotal (Adendo v2).
        costo_unitario: Costo del producto al momento de la venta, o None si
            no tenia costo definido (Adendo v2, Fase A3).
    """

    __tablename__ = "detalle_ventas"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="detalle_ventas_cantidad_check"),
        CheckConstraint("precio_unitario >= 0", name="detalle_ventas_precio_unitario_check"),
        CheckConstraint("subtotal >= 0", name="detalle_ventas_subtotal_check"),
        CheckConstraint("descuento_prorrateado >= 0", name="detalle_ventas_descuento_prorrateado_check"),
        CheckConstraint("costo_unitario >= 0", name="detalle_ventas_costo_unitario_check"),
        Index("ix_detalle_ventas_venta", "venta_id"),
        Index("ix_detalle_ventas_producto", "producto_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    venta_id = Column(Integer, ForeignKey("ventas.id", ondelete="CASCADE"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id", ondelete="RESTRICT"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)
    descuento_prorrateado = Column(Numeric(10, 2), nullable=False, default=0, server_default="0")
    costo_unitario = Column(Numeric(10, 2), nullable=True)

    venta = relationship("Venta", back_populates="detalles")
    producto = relationship("Producto", back_populates="detalles_venta")

    def __repr__(self) -> str:
        """Retorna una representacion legible del detalle para logs/debug."""
        return (
            f"<DetalleVenta venta_id={self.venta_id} producto_id={self.producto_id} "
            f"cantidad={self.cantidad}>"
        )
