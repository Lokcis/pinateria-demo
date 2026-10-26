"""Modelo de AjusteInventario y su enum de tipo."""

import enum

from sqlalchemy import CheckConstraint, Column, DateTime, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class TipoAjuste(str, enum.Enum):
    """Tipo de movimiento manual de inventario (RF-007).

    Attributes:
        ENTRADA: Incremento manual de stock (ej. conteo fisico encontro
            mas unidades de las registradas).
        SALIDA: Decremento manual de stock no asociado a una venta (ej.
            uso interno, muestra).
        MERMA: Decremento por perdida, dano o vencimiento.
        CORRECCION: Ajuste correctivo tras un conteo fisico.
    """

    ENTRADA = "entrada"
    SALIDA = "salida"
    MERMA = "merma"
    CORRECCION = "correccion"


class AjusteInventario(Base):
    """Bitacora de movimientos manuales de stock, con motivo obligatorio (RF-007).

    `cantidad` es un valor con signo: positivo incrementa
    `productos.stock_actual` y negativo lo decrementa. El unico
    invariante de base de datos es que no sea cero (un ajuste que no
    mueve nada no tiene razon de existir); el signo esperado segun
    `tipo` (ENTRADA/CORRECCION positivos, SALIDA/MERMA negativos, o
    CORRECCION en cualquier direccion) se valida en la capa de
    aplicacion, no aqui.

    Attributes:
        id: Identificador unico autoincremental.
        producto_id: FK a `productos.id`. ON DELETE RESTRICT.
        usuario_id: FK al usuario que registro el ajuste. ON DELETE
            RESTRICT.
        tipo: Tipo de ajuste (entrada/salida/merma/correccion).
        cantidad: Magnitud con signo del ajuste. Debe ser distinta de cero.
        motivo: Justificacion textual obligatoria, para trazabilidad y
            auditoria.
        fecha: Marca de tiempo en la que se registro el ajuste.
    """

    __tablename__ = "ajustes_inventario"
    __table_args__ = (
        CheckConstraint("cantidad <> 0", name="ajustes_inventario_cantidad_check"),
        Index("ix_ajustes_producto", "producto_id"),
        Index("ix_ajustes_fecha", "fecha"),
    )

    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id", ondelete="RESTRICT"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    tipo = Column(Enum(TipoAjuste, name="tipo_ajuste", values_callable=lambda enum_cls: [m.value for m in enum_cls]), nullable=False)
    cantidad = Column(Integer, nullable=False)
    motivo = Column(String(255), nullable=False)
    fecha = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    producto = relationship("Producto", back_populates="ajustes_inventario")
    usuario = relationship("Usuario", back_populates="ajustes_inventario")

    def __repr__(self) -> str:
        """Retorna una representacion legible del ajuste para logs/debug."""
        return (
            f"<AjusteInventario producto_id={self.producto_id} tipo={self.tipo} "
            f"cantidad={self.cantidad}>"
        )
