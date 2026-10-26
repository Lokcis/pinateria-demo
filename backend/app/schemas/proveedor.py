"""Esquemas Pydantic para Proveedor (RF-012)."""

from datetime import datetime

import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.schemas.tipos import NombreCapitalizado, NombreOpcionalCapitalizado, TextoCapitalizado

_PATRON_TELEFONO = re.compile(r"^\d{7,15}$")
_PATRON_EMAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")


def _validar_telefono(valor: str | None) -> str | None:
    """Exige que el telefono tenga solo digitos (7 a 15)."""
    if valor is not None and not _PATRON_TELEFONO.match(valor):
        raise ValueError("El telefono debe contener solo numeros (7 a 15 digitos).")
    return valor


def _validar_email(valor: str | None) -> str | None:
    """Exige un correo con formato usuario@dominio.tld."""
    if valor is not None and not _PATRON_EMAIL.match(valor):
        raise ValueError("El correo no tiene un formato valido.")
    return valor


# El limite de largo va en el `str` (no en la union con None): con `str | None` un null explicito
# hacia fallar la validacion con un TypeError (500) en vez de aceptarse.
Telefono = Annotated[Annotated[str, Field(max_length=15)] | None, AfterValidator(_validar_telefono)]
Email = Annotated[Annotated[str, Field(max_length=120)] | None, AfterValidator(_validar_email)]


class ProveedorCrearIn(BaseModel):
    """Payload para dar de alta un proveedor.

    Attributes:
        nombre_empresa: Razon social o nombre comercial (obligatorio).
        nombre_contacto: Persona de contacto.
        telefono: Telefono de contacto.
        email: Correo de contacto.
        direccion: Direccion fisica.
        notas: Notas libres.
    """

    nombre_empresa: NombreCapitalizado = Field(min_length=1, max_length=150)
    nombre_contacto: NombreOpcionalCapitalizado | None = Field(default=None, max_length=120)
    telefono: Telefono = None
    email: Email = None
    direccion: str | None = Field(default=None, max_length=255)
    notas: TextoCapitalizado | None = Field(default=None, max_length=255)


class ProveedorEditarIn(BaseModel):
    """Payload para editar un proveedor; solo se actualizan los campos presentes."""

    nombre_empresa: NombreCapitalizado | None = Field(default=None, min_length=1, max_length=150)
    nombre_contacto: NombreOpcionalCapitalizado | None = Field(default=None, max_length=120)
    telefono: Telefono = None
    email: Email = None
    direccion: str | None = Field(default=None, max_length=255)
    notas: TextoCapitalizado | None = Field(default=None, max_length=255)


class ProveedorOut(BaseModel):
    """Representacion de un proveedor expuesta por la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre_empresa: str
    nombre_contacto: str | None
    telefono: str | None
    email: str | None
    direccion: str | None
    notas: str | None
    creado_en: datetime
