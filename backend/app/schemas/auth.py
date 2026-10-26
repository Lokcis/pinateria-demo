"""Esquemas Pydantic para autenticacion."""

from pydantic import BaseModel, Field


class Token(BaseModel):
    """Respuesta de un login exitoso.

    Attributes:
        access_token: Token JWT firmado, a enviar en el header
            `Authorization: Bearer <access_token>` de requests subsiguientes.
        token_type: Tipo de token, siempre "bearer".
    """

    access_token: str = Field(..., description="Token JWT firmado.")
    token_type: str = Field(default="bearer", description="Tipo de token.")
