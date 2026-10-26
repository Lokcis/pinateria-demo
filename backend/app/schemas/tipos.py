"""Tipos de campo reutilizables de los esquemas: textos que se guardan con la primera letra en mayuscula.

Se combinan con `Field(...)` para los largos: `nombre: NombreCapitalizado = Field(min_length=1, max_length=150)`.
Primero se valida el largo con el texto original y despues se normaliza.
"""

from typing import Annotated

from pydantic import AfterValidator

from app.services.texto import capitalizar_nombre, capitalizar_texto


def _nombre_no_vacio(valor: str) -> str:
    """Normaliza un nombre y rechaza el que queda vacio (solo espacios)."""
    resultado = capitalizar_nombre(valor)
    if not resultado:
        raise ValueError("El nombre no puede quedar vacío.")
    return resultado


NombreCapitalizado = Annotated[str, AfterValidator(_nombre_no_vacio)]
"""Nombre obligatorio: primera letra en mayuscula, el resto en minuscula y sin espacios sobrantes."""

NombreOpcionalCapitalizado = Annotated[str, AfterValidator(capitalizar_nombre)]
"""Nombre que puede ir vacio (ej. persona de contacto): se normaliza si se escribe."""

TextoCapitalizado = Annotated[str, AfterValidator(capitalizar_texto)]
"""Texto libre (descripcion, nota, motivo): recortado y con la primera letra en mayuscula."""
