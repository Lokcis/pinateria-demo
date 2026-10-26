"""Modelo de MovimientoCaja: ingresos y retiros manuales de una caja abierta (Adendo v3, Fase G2)."""

import enum

from sqlalchemy import CheckConstraint, Column, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, func

from app.core.database import Base


class TipoMovimientoCaja(str, enum.Enum):
    """Tipo de movimiento manual de efectivo.

    Attributes:
        INGRESO: Entra efectivo a la caja (por ejemplo, para dar cambio).
        RETIRO: Sale efectivo de la caja (por ejemplo, una consignacion al banco).
    """

    INGRESO = "ingreso"
    RETIRO = "retiro"


class MovimientoCaja(Base):
    """Un ingreso o retiro manual de efectivo en una caja abierta (RF-071).

    Sin estos movimientos el corte siempre saldria descuadrado cuando se consigna o se retira dinero. No se
    modifican ni se borran.

    Attributes:
        id: Identificador unico autoincremental.
        corte_id: FK a `cortes_caja.id`; debe estar abierta (lo valida la aplicacion). ON DELETE RESTRICT.
        tipo: ingreso / retiro.
        monto: Pesos enteros, mayor que cero, multiplo de $50.
        motivo: Para que se hizo (por ejemplo, "Consignacion al banco").
        usuario_id: FK al usuario que lo registro. ON DELETE RESTRICT.
        creado_en: Hora del movimiento.
    """

    __tablename__ = "movimientos_caja"
    __table_args__ = (
        CheckConstraint("monto > 0", name="movimientos_caja_monto_check"),
        Index("ix_movimientos_caja_corte", "corte_id"),
    )

    id = Column(Integer, primary_key=True)
    corte_id = Column(Integer, ForeignKey("cortes_caja.id", ondelete="RESTRICT"), nullable=False)
    tipo = Column(
        Enum(
            TipoMovimientoCaja,
            name="tipo_movimiento_caja",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        nullable=False,
    )
    monto = Column(Numeric(10, 2), nullable=False)
    motivo = Column(String(255), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    creado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self) -> str:
        """Retorna una representacion legible del movimiento para logs/debug."""
        return f"<MovimientoCaja id={self.id} tipo={self.tipo} monto={self.monto}>"
