"""Esquemas Pydantic para la gestion de usuarios (RF-015)."""

import re
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.models.usuario import RolUsuario
from app.schemas.tipos import NombreCapitalizado

_PATRON_USERNAME = re.compile(r"^[A-Za-z0-9._-]{3,60}$")


def _validar_username(valor: str) -> str:
    """Exige un usuario de 3 a 60 caracteres: letras, numeros, punto, guion y guion bajo."""
    if not _PATRON_USERNAME.match(valor):
        raise ValueError("El usuario debe tener de 3 a 60 caracteres: letras, numeros, punto, guion o guion bajo.")
    return valor


Username = Annotated[str, AfterValidator(_validar_username)]
Password = Annotated[str, Field(min_length=8, max_length=72)]
Nombre = Annotated[NombreCapitalizado, Field(min_length=1, max_length=120)]


class UsuarioOut(BaseModel):
    """Usuario expuesto por la API. Nunca incluye `password_hash`.

    Attributes:
        id: Identificador del usuario.
        nombre: Nombre completo.
        username: Nombre de usuario para iniciar sesion.
        rol: Rol asignado.
        activo: Si puede iniciar sesion.
        creado_en: Fecha de creacion.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    username: str
    rol: RolUsuario
    activo: bool
    creado_en: datetime


class UsuarioCrearIn(BaseModel):
    """Payload para crear un usuario con contrasena temporal.

    Attributes:
        nombre: Nombre completo.
        username: Usuario de acceso, unico.
        password: Contrasena temporal (8 a 72 caracteres, limite de bcrypt).
        rol: Rol a asignar.
    """

    nombre: Nombre
    username: Username
    password: Password
    rol: RolUsuario


class UsuarioEditarIn(BaseModel):
    """Payload parcial para editar un usuario; solo se aplican los campos enviados.

    Attributes:
        nombre: Nuevo nombre.
        username: Nuevo usuario de acceso.
        rol: Nuevo rol.
        activo: False desactiva la cuenta (no se borra).
    """

    nombre: Nombre | None = None
    username: Username | None = None
    rol: RolUsuario | None = None
    activo: bool | None = None


class RestablecerPasswordIn(BaseModel):
    """Payload con la contrasena temporal que fija el administrador.

    Attributes:
        password: Nueva contrasena temporal.
    """

    password: Password


class CambiarPasswordIn(BaseModel):
    """Payload para que un usuario cambie su propia contrasena.

    Attributes:
        password_actual: Contrasena vigente, para confirmar identidad.
        password_nueva: Nueva contrasena.
    """

    password_actual: str = Field(..., min_length=1, max_length=72)
    password_nueva: Password
