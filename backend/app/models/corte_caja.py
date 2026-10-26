"""Modelo de CorteCaja: apertura y cierre de la caja, con la foto de las cifras del corte (Adendo v3, Fase G2)."""

import enum

from sqlalchemy import CheckConstraint, Column, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, func, text

from app.core.database import Base


class EstadoCorteCaja(str, enum.Enum):
    """Estado de un corte de caja.

    Attributes:
        ABIERTA: La caja esta abierta; el efectivo esperado se calcula en vivo.
        CERRADA: Se hizo el corte; sus cifras son una foto que ya no cambia.
    """

    ABIERTA = "abierta"
    CERRADA = "cerrada"


class CorteCaja(Base):
    """Una apertura de caja y, al cerrarla, su corte (RF-069, RF-070, RF-072, RF-073).

    Hay una sola caja: un indice unico parcial impide dos cortes abiertos a la vez. Mientras esta abierta solo
    llevan datos la apertura y la base; al cerrar se guarda una FOTO de todas las cifras, que un corte cerrado
    ya no modifica (ni siquiera si despues se anula un gasto o llega una venta sin conexion).

    Attributes:
        id: Identificador unico autoincremental.
        estado: abierta / cerrada.
        abierta_en: Apertura: inicio del periodo del corte.
        abierta_por_id: FK al usuario que abrio. ON DELETE RESTRICT.
        base_inicial: Efectivo con que arranca (multiplo de $50).
        cerrada_en: Cierre.
        cerrada_por_id: FK al usuario que cerro. ON DELETE RESTRICT.
        ventas_efectivo: Foto: pagos en efectivo de las ventas del periodo (el monto abonado; sin vueltas).
        ingresos_caja: Foto: ingresos manuales.
        gastos_efectivo: Foto: gastos vigentes pagados en efectivo.
        compras_efectivo: Foto: compras recibidas pagadas en efectivo.
        retiros_caja: Foto: retiros manuales.
        efectivo_esperado: Foto: base + ventas + ingresos - gastos - compras - retiros.
        efectivo_contado: Lo que se conto al cerrar (multiplo de $50).
        diferencia: `efectivo_contado - efectivo_esperado` (positiva: sobra; negativa: falta).
        ventas_tarjeta: Foto informativa: ventas pagadas con tarjeta en el periodo.
        ventas_transferencia: Foto informativa: ventas pagadas por transferencia (Nequi y Daviplata).
        observaciones: Notas del corte.
    """

    __tablename__ = "cortes_caja"
    __table_args__ = (
        CheckConstraint("base_inicial >= 0", name="cortes_caja_base_check"),
        CheckConstraint("efectivo_contado IS NULL OR efectivo_contado >= 0", name="cortes_caja_contado_check"),
        CheckConstraint(
            "(estado = 'abierta' AND cerrada_en IS NULL AND cerrada_por_id IS NULL AND efectivo_esperado IS NULL "
            "AND efectivo_contado IS NULL AND diferencia IS NULL) "
            "OR (estado = 'cerrada' AND cerrada_en IS NOT NULL AND cerrada_por_id IS NOT NULL "
            "AND efectivo_esperado IS NOT NULL AND efectivo_contado IS NOT NULL AND diferencia IS NOT NULL)",
            name="ck_corte_caja_estado",
        ),
        Index("ux_cortes_caja_abierta", text("(true)"), unique=True, postgresql_where=text("estado = 'abierta'")),
        Index("ix_cortes_caja_abierta_en", "abierta_en"),
    )

    id = Column(Integer, primary_key=True)
    estado = Column(
        Enum(
            EstadoCorteCaja,
            name="estado_corte_caja",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        nullable=False,
        default=EstadoCorteCaja.ABIERTA,
        server_default=EstadoCorteCaja.ABIERTA.value,
    )
    abierta_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    abierta_por_id = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    base_inicial = Column(Numeric(10, 2), nullable=False)
    cerrada_en = Column(DateTime(timezone=True), nullable=True)
    cerrada_por_id = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True)
    ventas_efectivo = Column(Numeric(10, 2), nullable=True)
    ingresos_caja = Column(Numeric(10, 2), nullable=True)
    gastos_efectivo = Column(Numeric(10, 2), nullable=True)
    compras_efectivo = Column(Numeric(10, 2), nullable=True)
    retiros_caja = Column(Numeric(10, 2), nullable=True)
    efectivo_esperado = Column(Numeric(10, 2), nullable=True)
    efectivo_contado = Column(Numeric(10, 2), nullable=True)
    diferencia = Column(Numeric(10, 2), nullable=True)
    ventas_tarjeta = Column(Numeric(10, 2), nullable=True)
    ventas_transferencia = Column(Numeric(10, 2), nullable=True)
    observaciones = Column(String(500), nullable=True)

    def __repr__(self) -> str:
        """Retorna una representacion legible del corte para logs/debug."""
        return f"<CorteCaja id={self.id} estado={self.estado} abierta_en={self.abierta_en}>"
