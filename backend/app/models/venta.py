"""Modelo de Venta y su enum de metodo de pago."""

import enum

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Enum, ForeignKey, Index, Integer, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.descuento import OrigenDescuento, TipoDescuento


class MetodoPago(str, enum.Enum):
    """Metodo de pago usado en una venta.

    Attributes:
        EFECTIVO: Pago en efectivo.
        TARJETA: Pago con tarjeta debito/credito.
        TRANSFERENCIA: Pago por transferencia o billetera digital.
    """

    EFECTIVO = "efectivo"
    TARJETA = "tarjeta"
    TRANSFERENCIA = "transferencia"


class Venta(Base):
    """Representa el encabezado de una transaccion de venta en el POS (HU-01, HU-05, HU-06).

    Orden de calculo (Adendo v2): `subtotal` (suma de las lineas) ->
    `descuento_monto` sobre el subtotal -> redondeo a multiplo de $50
    (`ajuste_redondeo`) -> `total`. Los metodos de pago viven en
    `pagos_venta` (antes `ventas.metodo_pago`, eliminada en la migracion
    0002). No existe un campo de estado: una venta que debe anularse se
    maneja como un proceso de negocio separado.

    Attributes:
        id: Identificador unico autoincremental.
        usuario_id: FK al vendedor que realizo la venta, elegido en el POS
            (HU-08). ON DELETE RESTRICT: protege el historial contable.
        registrada_por_id: FK al usuario que tenia la sesion y registro la venta
            (puede ser distinto de `usuario_id`). NULL en las ventas anteriores a
            la migracion 0007, que se entienden registradas por el vendedor.
        cliente_id: FK al cliente asociado, o None si no estaba registrado
            (Fase A2). ON DELETE RESTRICT.
        fecha: Marca de tiempo en la que se realizo la venta. En una venta registrada sin conexion
            (Fase 9) es la hora en que se hizo en la tienda, no la de su envio al servidor.
        uuid_cliente: Identificador que genera el POS al confirmar la venta (Fase 9). Hace el envio
            idempotente: reenviar la misma venta no la duplica. NULL en las ventas anteriores a la 0008.
        sin_conexion: True si la venta se hizo sin conexion y se envio despues (Fase 9). Sus precios
            son los que vio el cliente en la tienda.
        sincronizada_en: Momento en que el servidor la recibio, solo si se hizo sin conexion.
        subtotal: Suma de los `subtotal` de `detalle_ventas`.
        descuento_origen: ninguno / cliente / general / manual.
        descuento_tipo: porcentaje / monto, o None sin descuento.
        descuento_valor: Valor ingresado (porcentaje o pesos), o None.
        descuento_monto: Descuento en pesos aplicado (0 a `subtotal`).
        ajuste_redondeo: Ajuste a multiplo de $50, despues del descuento.
        total: `subtotal - descuento_monto + ajuste_redondeo`.
        detalles: Lineas de detalle asociadas a esta venta.
        pagos: Pagos de la venta; su suma es igual a `total`.
    """

    __tablename__ = "ventas"
    __table_args__ = (
        CheckConstraint("total >= 0", name="ventas_total_check"),
        CheckConstraint("subtotal >= 0", name="ventas_subtotal_check"),
        CheckConstraint("descuento_monto >= 0", name="ventas_descuento_monto_check"),
        CheckConstraint("descuento_monto <= subtotal", name="ck_ventas_descuento"),
        CheckConstraint("total = subtotal - descuento_monto + ajuste_redondeo", name="ck_ventas_total_coherente"),
        Index("ix_ventas_fecha", "fecha"),
        Index("ix_ventas_usuario", "usuario_id"),
        Index("ix_ventas_registrada_por", "registrada_por_id"),
        Index("ix_ventas_cliente", "cliente_id"),
        Index("ux_ventas_uuid_cliente", "uuid_cliente", unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    registrada_por_id = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="RESTRICT"), nullable=True)
    fecha = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    uuid_cliente = Column(UUID(as_uuid=True), nullable=True)
    sin_conexion = Column(Boolean, nullable=False, default=False, server_default="false")
    sincronizada_en = Column(DateTime(timezone=True), nullable=True)
    subtotal = Column(Numeric(10, 2), nullable=False)
    descuento_origen = Column(
        Enum(OrigenDescuento, name="origen_descuento", values_callable=lambda enum_cls: [m.value for m in enum_cls]),
        nullable=False,
        default=OrigenDescuento.NINGUNO,
        server_default=OrigenDescuento.NINGUNO.value,
    )
    descuento_tipo = Column(
        Enum(TipoDescuento, name="tipo_descuento", values_callable=lambda enum_cls: [m.value for m in enum_cls]),
        nullable=True,
    )
    descuento_valor = Column(Numeric(10, 2), nullable=True)
    descuento_monto = Column(Numeric(10, 2), nullable=False, default=0, server_default="0")
    ajuste_redondeo = Column(Numeric(10, 2), nullable=False, default=0, server_default="0")
    total = Column(Numeric(10, 2), nullable=False)

    usuario = relationship("Usuario", back_populates="ventas", foreign_keys=[usuario_id])
    registrada_por = relationship("Usuario", foreign_keys=[registrada_por_id])
    cliente = relationship("Cliente", back_populates="ventas")
    detalles = relationship("DetalleVenta", back_populates="venta", cascade="all, delete-orphan")
    pagos = relationship("PagoVenta", back_populates="venta", cascade="all, delete-orphan", order_by="PagoVenta.id")

    def __repr__(self) -> str:
        """Retorna una representacion legible de la venta para logs/debug."""
        return f"<Venta id={self.id} total={self.total} fecha={self.fecha}>"
