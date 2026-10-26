"""Modelo de CategoriaGasto: las categorias editables de los gastos (Adendo v3, Fase G1, RF-060)."""

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, func
from sqlalchemy.sql import expression

from app.core.database import Base

NOMBRE_CATEGORIA_COMPRAS = "Compra de mercancía"
"""Nombre de la categoria de sistema bajo la que la vista unificada muestra las compras recibidas."""


class CategoriaGasto(Base):
    """Categoria de un gasto (arriendo, servicios, nomina...). El administrador las crea, renombra y desactiva.

    Attributes:
        id: Identificador unico autoincremental.
        nombre: Nombre, unico sin distinguir mayusculas (primera letra en mayuscula, RF-058).
        activa: Una categoria desactivada no se ofrece para gastos nuevos pero conserva los antiguos.
        es_sistema: True solo en "Compra de mercancia": no se renombra ni se desactiva.
        creada_en: Fecha de creacion.
    """

    __tablename__ = "categorias_gasto"
    __table_args__ = (
        Index("ux_categorias_gasto_sistema", "es_sistema", unique=True, postgresql_where=expression.text("es_sistema")),
    )

    id = Column(Integer, primary_key=True)
    nombre = Column(String(60), nullable=False)
    activa = Column(Boolean, nullable=False, default=True, server_default=expression.true())
    es_sistema = Column(Boolean, nullable=False, default=False, server_default=expression.false())
    creada_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self) -> str:
        """Retorna una representacion legible de la categoria para logs/debug."""
        return f"<CategoriaGasto id={self.id} nombre={self.nombre!r}>"


Index("ux_categorias_gasto_nombre", func.lower(CategoriaGasto.nombre), unique=True)
