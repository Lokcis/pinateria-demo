"""Esquemas Pydantic para Categoria."""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.tipos import NombreCapitalizado, TextoCapitalizado


class CategoriaOut(BaseModel):
    """Representacion de una categoria expuesta por la API.

    Attributes:
        id: Identificador unico de la categoria.
        nombre: Nombre de la categoria.
        descripcion: Descripcion opcional.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str | None


class CategoriaCrearIn(BaseModel):
    """Payload para dar de alta una categoria (RF-017).

    Attributes:
        nombre: Nombre unico de la categoria (1 a 80 caracteres).
        descripcion: Descripcion opcional (hasta 255 caracteres).
    """

    nombre: NombreCapitalizado = Field(..., min_length=1, max_length=80)
    descripcion: TextoCapitalizado | None = Field(None, max_length=255)


class CategoriaEditarIn(BaseModel):
    """Payload parcial para editar una categoria; solo se aplican los campos enviados.

    Attributes:
        nombre: Nuevo nombre.
        descripcion: Nueva descripcion (null la borra).
    """

    nombre: NombreCapitalizado | None = Field(None, min_length=1, max_length=80)
    descripcion: TextoCapitalizado | None = Field(None, max_length=255)
