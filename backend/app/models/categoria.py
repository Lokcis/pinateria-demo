"""Modelo de Categoria de productos."""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Categoria(Base):
    """Representa una categoria del catalogo de productos (RF-006).

    Attributes:
        id: Identificador unico autoincremental.
        nombre: Nombre de la categoria, unico.
        descripcion: Descripcion opcional de la categoria.
    """

    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(80), nullable=False, unique=True, index=True)
    descripcion = Column(String(255), nullable=True)

    productos = relationship("Producto", back_populates="categoria")

    def __repr__(self) -> str:
        """Retorna una representacion legible de la categoria para logs/debug."""
        return f"<Categoria id={self.id} nombre={self.nombre!r}>"
