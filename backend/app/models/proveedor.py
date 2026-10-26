"""Modelo de Proveedor."""

from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Proveedor(Base):
    """Representa un proveedor externo de productos.

    Contiene informacion comercial sensible (costos y contactos); el
    acceso se restringe al rol Administrador a nivel de aplicacion
    (RBAC via FastAPI/JWT, RF-012, RF-021) — esta tabla en si no
    distingue roles.

    Attributes:
        id: Identificador unico autoincremental.
        nombre_empresa: Razon social o nombre comercial del proveedor.
        nombre_contacto: Nombre de la persona de contacto (opcional).
        telefono: Telefono de contacto (opcional).
        email: Correo electronico de contacto (opcional).
        direccion: Direccion fisica (opcional).
        notas: Notas libres sobre el proveedor (opcional).
        creado_en: Marca de tiempo de creacion del registro.
    """

    __tablename__ = "proveedores"

    id = Column(Integer, primary_key=True, index=True)
    nombre_empresa = Column(String(150), nullable=False)
    nombre_contacto = Column(String(120), nullable=True)
    telefono = Column(String(30), nullable=True)
    email = Column(String(120), nullable=True)
    direccion = Column(String(255), nullable=True)
    notas = Column(String(255), nullable=True)
    creado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    compras = relationship("Compra", back_populates="proveedor")

    def __repr__(self) -> str:
        """Retorna una representacion legible del proveedor para logs/debug."""
        return f"<Proveedor id={self.id} nombre_empresa={self.nombre_empresa!r}>"
