"""Modelo de Usuario y su enum de roles."""

import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class RolUsuario(str, enum.Enum):
    """Roles disponibles para un usuario del sistema.

    Attributes:
        ADMINISTRADOR: Control total, incluida la gestion de proveedores.
        VENDEDOR: Acceso al modulo POS y consulta/ajuste de inventario.
        PROPIETARIO: Acceso de solo lectura via el Dashboard PWA remoto.
    """

    ADMINISTRADOR = "administrador"
    VENDEDOR = "vendedor"
    PROPIETARIO = "propietario"


class Usuario(Base):
    """Representa una cuenta de acceso al sistema (empleado o propietario).

    Attributes:
        id: Identificador unico autoincremental.
        nombre: Nombre completo del usuario.
        username: Nombre de usuario para iniciar sesion. Unico.
        password_hash: Hash bcrypt de la contrasena. Nunca se almacena
            en texto plano.
        rol: Rol del usuario, determina sus permisos (RBAC a nivel de
            aplicacion via FastAPI/JWT).
        activo: Indica si el usuario puede iniciar sesion.
        creado_en: Marca de tiempo de creacion del registro.
    """

    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(120), nullable=False)
    username = Column(String(60), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    rol = Column(Enum(RolUsuario, name="rol_usuario", values_callable=lambda enum_cls: [m.value for m in enum_cls]), nullable=False)
    activo = Column(Boolean, nullable=False, default=True, server_default="true")
    creado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    ventas = relationship("Venta", back_populates="usuario", foreign_keys="Venta.usuario_id")
    compras = relationship("Compra", back_populates="usuario")
    ajustes_inventario = relationship("AjusteInventario", back_populates="usuario")

    def __repr__(self) -> str:
        """Retorna una representacion legible del usuario para logs/debug."""
        return f"<Usuario id={self.id} username={self.username!r} rol={self.rol}>"
