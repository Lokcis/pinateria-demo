"""Modelo de Notificacion y su enum de tipo."""

import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class TipoNotificacion(str, enum.Enum):
    """Categoria de una notificacion interna del sistema (RF-013, RF-014).

    Attributes:
        STOCK_BAJO: Un producto alcanzo o cruzo su `stock_minimo`.
        SISTEMA: Aviso general del sistema (ej. tarea programada completada).
    """

    STOCK_BAJO = "stock_bajo"
    SISTEMA = "sistema"


class Notificacion(Base):
    """Alertas persistidas para el Dashboard PWA del propietario (RF-013, RF-014).

    Persistir la alerta (en lugar de solo emitirla) evita que el worker
    de Celery reenvie la misma notificacion repetidamente.

    Attributes:
        id: Identificador unico autoincremental.
        tipo: Categoria de la notificacion.
        producto_id: FK a `productos.id`, nullable. ON DELETE SET NULL:
            si el producto que origino la alerta se elimina del
            catalogo, la notificacion historica se conserva con
            `producto_id` en NULL.
        mensaje: Texto de la notificacion.
        leida: Indica si el destinatario ya la marco como leida.
        creada_en: Marca de tiempo de creacion de la notificacion.
    """

    __tablename__ = "notificaciones"
    __table_args__ = (
        Index("ix_notificaciones_leida", "leida"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(
        Enum(TipoNotificacion, name="tipo_notificacion", values_callable=lambda enum_cls: [m.value for m in enum_cls]),
        nullable=False,
        default=TipoNotificacion.STOCK_BAJO,
        server_default=TipoNotificacion.STOCK_BAJO.value,
    )
    producto_id = Column(Integer, ForeignKey("productos.id", ondelete="SET NULL"), nullable=True)
    mensaje = Column(String(255), nullable=False)
    leida = Column(Boolean, nullable=False, default=False, server_default="false")
    creada_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    producto = relationship("Producto", back_populates="notificaciones")

    def __repr__(self) -> str:
        """Retorna una representacion legible de la notificacion para logs/debug."""
        return f"<Notificacion id={self.id} tipo={self.tipo} leida={self.leida}>"
