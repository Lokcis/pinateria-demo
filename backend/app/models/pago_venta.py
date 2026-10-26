"""Modelo de PagoVenta y su enum de plataforma de transferencia (Adendo v2, Fase A1)."""

import enum

from sqlalchemy import CheckConstraint, Column, Enum, ForeignKey, Index, Integer, Numeric
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.venta import MetodoPago


class PlataformaTransferencia(str, enum.Enum):
    """Plataforma de un pago por transferencia (RF-023).

    Se llama asi, y no "proveedor", para no confundirse con la tabla `proveedores`.

    Attributes:
        NEQUI: Nequi.
        DAVIPLATA: Daviplata.
    """

    NEQUI = "nequi"
    DAVIPLATA = "daviplata"


class PagoVenta(Base):
    """Una parte del total de una venta, con su metodo de pago (RF-022 a RF-024).

    Una venta tiene uno o mas pagos cuya suma es igual a `ventas.total` (regla
    validada al crear la venta). Una venta en 0 no lleva pagos.

    Attributes:
        id: Identificador unico autoincremental.
        venta_id: FK a `ventas.id`. ON DELETE CASCADE.
        metodo_pago: efectivo / tarjeta / transferencia.
        plataforma: nequi / daviplata; solo en transferencias. Obligatoria en
            pagos nuevos; NULL en las transferencias anteriores al adendo.
        monto: Lo que este pago abona al total. Debe ser > 0.
        monto_recibido: Lo que entrego el cliente; solo y siempre en efectivo,
            mayor o igual que `monto`.
        vueltas: `monto_recibido - monto` en efectivo; 0 en los demas metodos.
    """

    __tablename__ = "pagos_venta"
    __table_args__ = (
        CheckConstraint("monto > 0", name="pagos_venta_monto_check"),
        CheckConstraint("vueltas >= 0", name="pagos_venta_vueltas_check"),
        CheckConstraint("plataforma IS NULL OR metodo_pago = 'transferencia'", name="ck_pago_plataforma"),
        CheckConstraint(
            "(metodo_pago = 'efectivo' AND monto_recibido IS NOT NULL "
            "AND monto_recibido >= monto AND vueltas = monto_recibido - monto) "
            "OR (metodo_pago <> 'efectivo' AND monto_recibido IS NULL AND vueltas = 0)",
            name="ck_pago_efectivo",
        ),
        Index("ix_pagos_venta_venta", "venta_id"),
        Index("ix_pagos_venta_metodo", "metodo_pago"),
    )

    id = Column(Integer, primary_key=True)
    venta_id = Column(Integer, ForeignKey("ventas.id", ondelete="CASCADE"), nullable=False)
    metodo_pago = Column(
        Enum(MetodoPago, name="metodo_pago", values_callable=lambda enum_cls: [m.value for m in enum_cls]),
        nullable=False,
    )
    plataforma = Column(
        Enum(
            PlataformaTransferencia,
            name="plataforma_transferencia",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        nullable=True,
    )
    monto = Column(Numeric(10, 2), nullable=False)
    monto_recibido = Column(Numeric(10, 2), nullable=True)
    vueltas = Column(Numeric(10, 2), nullable=False, default=0, server_default="0")

    venta = relationship("Venta", back_populates="pagos")

    def __repr__(self) -> str:
        """Retorna una representacion legible del pago para logs/debug."""
        return f"<PagoVenta venta_id={self.venta_id} metodo={self.metodo_pago} monto={self.monto}>"
