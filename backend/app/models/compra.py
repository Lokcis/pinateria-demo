"""Modelo de Compra y su enum de estado."""

import enum

from sqlalchemy import CheckConstraint, Column, DateTime, Enum, ForeignKey, Index, Integer, Numeric, func
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.pago_venta import PlataformaTransferencia
from app.models.venta import MetodoPago


class EstadoCompra(str, enum.Enum):
    """Estado de una orden de compra a proveedor (RF-010, RF-011).

    Attributes:
        PENDIENTE: Orden creada, aun no recibida en bodega.
        RECIBIDA: Orden recibida; al marcarla como recibida, el stock de
            cada producto se incrementa en la cantidad correspondiente.
        CANCELADA: Orden cancelada, no afecta inventario.
    """

    PENDIENTE = "pendiente"
    RECIBIDA = "recibida"
    CANCELADA = "cancelada"


class Compra(Base):
    """Representa el encabezado de una orden de compra a un proveedor.

    Attributes:
        id: Identificador unico autoincremental.
        proveedor_id: FK a `proveedores.id`. ON DELETE RESTRICT.
        usuario_id: FK al usuario que registro la compra. ON DELETE
            RESTRICT.
        fecha: Marca de tiempo de creacion de la orden.
        estado: Estado actual de la orden (pendiente/recibida/cancelada).
        total: Monto total de la compra. Debe ser >= 0.
        metodo_pago: Forma de pago, que se pide al recibirla (Adendo v3). NULL en las compras anteriores,
            que suman en los gastos pero no afectan la caja.
        plataforma: nequi / daviplata; solo si el pago fue una transferencia.
        recibida_en: Momento en que se recibio la compra. NULL en las anteriores al Adendo v3 y en las
            que no estan recibidas; sus informes usan `fecha`.
        detalles: Lineas de detalle asociadas a esta compra.
    """

    __tablename__ = "compras"
    __table_args__ = (
        CheckConstraint("total >= 0", name="compras_total_check"),
        CheckConstraint("plataforma IS NULL OR metodo_pago = 'transferencia'", name="ck_compra_plataforma"),
        Index("ix_compras_proveedor", "proveedor_id"),
        Index("ix_compras_fecha", "fecha"),
    )

    id = Column(Integer, primary_key=True, index=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id", ondelete="RESTRICT"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    fecha = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    estado = Column(
        Enum(EstadoCompra, name="estado_compra", values_callable=lambda enum_cls: [m.value for m in enum_cls]),
        nullable=False,
        default=EstadoCompra.PENDIENTE,
        server_default=EstadoCompra.PENDIENTE.value,
    )
    total = Column(Numeric(10, 2), nullable=False, default=0, server_default="0")
    metodo_pago = Column(
        Enum(MetodoPago, name="metodo_pago", values_callable=lambda enum_cls: [m.value for m in enum_cls]),
        nullable=True,
    )
    plataforma = Column(
        Enum(
            PlataformaTransferencia,
            name="plataforma_transferencia",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        nullable=True,
    )
    recibida_en = Column(DateTime(timezone=True), nullable=True)

    proveedor = relationship("Proveedor", back_populates="compras")
    usuario = relationship("Usuario", back_populates="compras")
    detalles = relationship("DetalleCompra", back_populates="compra", cascade="all, delete-orphan")

    @property
    def proveedor_nombre(self) -> str:
        """Nombre de la empresa proveedora, para serializar la compra."""
        return self.proveedor.nombre_empresa

    def __repr__(self) -> str:
        """Retorna una representacion legible de la compra para logs/debug."""
        return f"<Compra id={self.id} total={self.total} estado={self.estado}>"
