"""Modelos de descuentos: tipos, descuento general y topes del descuento manual (Adendo v2, Fase A1)."""

import enum

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Enum, ForeignKey, Integer, Numeric, SmallInteger, func

from app.core.database import Base


class TipoDescuento(str, enum.Enum):
    """Forma de un descuento (RF-027).

    Attributes:
        PORCENTAJE: Porcentaje del subtotal (0 a 100).
        MONTO: Monto fijo en pesos.
    """

    PORCENTAJE = "porcentaje"
    MONTO = "monto"


class OrigenDescuento(str, enum.Enum):
    """De donde salio el descuento aplicado a una venta (RF-028).

    Attributes:
        NINGUNO: La venta no tuvo descuento.
        CLIENTE: Descuento propio del cliente (Fase A2).
        GENERAL: Descuento general sugerido por el sistema.
        MANUAL: El usuario lo cambio o lo quito durante la venta.
    """

    NINGUNO = "ninguno"
    CLIENTE = "cliente"
    GENERAL = "general"
    MANUAL = "manual"


def _enum_tipo_descuento() -> Enum:
    """Columna ENUM `tipo_descuento` compartida por varias tablas."""
    return Enum(TipoDescuento, name="tipo_descuento", values_callable=lambda enum_cls: [m.value for m in enum_cls])


class DescuentoGeneral(Base):
    """Descuento sugerido a los clientes sin registro; una sola fila (id = 1) (RF-026).

    Attributes:
        id: Siempre 1.
        tipo: porcentaje / monto.
        valor: Porcentaje (hasta 100) o monto en pesos. Debe ser > 0.
        activo: Si esta apagado, no se sugiere.
        actualizado_por: Administrador que lo modifico por ultima vez.
        actualizado_en: Fecha de la ultima modificacion.
    """

    __tablename__ = "descuento_general"
    __table_args__ = (
        CheckConstraint("id = 1", name="descuento_general_id_check"),
        CheckConstraint("valor > 0", name="descuento_general_valor_check"),
        CheckConstraint("tipo <> 'porcentaje' OR valor <= 100", name="ck_descuento_general_porcentaje"),
    )

    id = Column(SmallInteger, primary_key=True, default=1, server_default="1")
    tipo = Column(_enum_tipo_descuento(), nullable=False)
    valor = Column(Numeric(10, 2), nullable=False)
    activo = Column(Boolean, nullable=False, default=False, server_default="false")
    actualizado_por = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True)
    actualizado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class TopeDescuento(Base):
    """Topes del descuento manual de un vendedor; una sola fila (id = 1) (RF-042).

    Se deben cumplir ambos. NULL significa "sin tope". No aplican al
    administrador ni a los descuentos sugeridos (cliente y general).

    Attributes:
        id: Siempre 1.
        tope_porcentaje: Porcentaje maximo del subtotal (0 a 100), o None.
        tope_monto: Monto maximo en pesos, o None.
        actualizado_por: Administrador que lo modifico por ultima vez.
        actualizado_en: Fecha de la ultima modificacion.
    """

    __tablename__ = "tope_descuento"
    __table_args__ = (
        CheckConstraint("id = 1", name="tope_descuento_id_check"),
        CheckConstraint(
            "tope_porcentaje > 0 AND tope_porcentaje <= 100", name="tope_descuento_tope_porcentaje_check"
        ),
        CheckConstraint("tope_monto > 0", name="tope_descuento_tope_monto_check"),
    )

    id = Column(SmallInteger, primary_key=True, default=1, server_default="1")
    tope_porcentaje = Column(Numeric(5, 2), nullable=True)
    tope_monto = Column(Numeric(10, 2), nullable=True)
    actualizado_por = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True)
    actualizado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
