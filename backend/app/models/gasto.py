"""Modelo de Gasto: un gasto del negocio con su categoria, forma de pago y anulacion (Adendo v3, Fase G1)."""

from sqlalchemy import CheckConstraint, Column, Date, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, func, text

from app.core.database import Base
from app.models.pago_venta import PlataformaTransferencia
from app.models.venta import MetodoPago


class Gasto(Base):
    """Un gasto del negocio (RF-059, RF-061, RF-062, RF-075).

    Un gasto no se borra ni se reactiva: solo se anula, con motivo, y los anulados no suman en ningun total.
    El vendedor solo ve, edita y anula los que registro el (`registrado_por_id`); eso lo valida el servidor.

    Attributes:
        id: Identificador unico autoincremental.
        fecha: Dia contable del gasto, en la zona del negocio. Los informes y la ganancia neta la usan.
            El vendedor siempre registra con la de hoy; el administrador puede elegir una anterior.
        categoria_id: FK a `categorias_gasto.id`. ON DELETE RESTRICT.
        descripcion: Que se pago (primera letra en mayuscula).
        beneficiario: A quien se pago, en texto libre (sin documentos de identidad); opcional.
        monto: Pesos enteros, mayor que cero; en efectivo, multiplo de $50 (lo valida la aplicacion).
        metodo_pago: efectivo / tarjeta / transferencia.
        plataforma: nequi / daviplata; solo en transferencias.
        registrado_por_id: FK al usuario que lo registro. ON DELETE RESTRICT.
        creado_en: Hora real del registro; la caja (Fase G2) la usa, no `fecha`.
        actualizado_en: Hora de la ultima edicion.
        actualizado_por_id: FK al usuario que hizo la ultima edicion.
        anulado_en: Hora de la anulacion.
        anulado_por_id: FK al usuario que lo anulo.
        motivo_anulacion: Motivo escrito al anular.
    """

    __tablename__ = "gastos"
    __table_args__ = (
        CheckConstraint("monto > 0", name="gastos_monto_check"),
        CheckConstraint("plataforma IS NULL OR metodo_pago = 'transferencia'", name="ck_gasto_plataforma"),
        CheckConstraint(
            "(anulado_en IS NULL AND anulado_por_id IS NULL AND motivo_anulacion IS NULL) "
            "OR (anulado_en IS NOT NULL AND anulado_por_id IS NOT NULL AND motivo_anulacion IS NOT NULL)",
            name="ck_gasto_anulacion",
        ),
        Index("ix_gastos_fecha", "fecha", "categoria_id"),
        Index("ix_gastos_registrado_por", "registrado_por_id", "creado_en"),
        Index("ix_gastos_creado_en", "creado_en"),
    )

    id = Column(Integer, primary_key=True)
    fecha = Column(
        Date,
        nullable=False,
        server_default=text("((now() AT TIME ZONE 'America/Bogota')::date)"),
    )
    categoria_id = Column(Integer, ForeignKey("categorias_gasto.id", ondelete="RESTRICT"), nullable=False)
    descripcion = Column(String(255), nullable=False)
    beneficiario = Column(String(120), nullable=True)
    monto = Column(Numeric(10, 2), nullable=False)
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
    registrado_por_id = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    creado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), nullable=True)
    actualizado_por_id = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True)
    anulado_en = Column(DateTime(timezone=True), nullable=True)
    anulado_por_id = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True)
    motivo_anulacion = Column(String(255), nullable=True)

    def __repr__(self) -> str:
        """Retorna una representacion legible del gasto para logs/debug."""
        return f"<Gasto id={self.id} monto={self.monto} metodo={self.metodo_pago}>"
