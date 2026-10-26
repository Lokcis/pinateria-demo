"""Esquemas Pydantic del descuento general y de los topes del descuento manual (Adendo v2, Fase A1)."""

from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.descuento import TipoDescuento


class DescuentoGeneralIn(BaseModel):
    """Payload de `PUT /descuentos/general` (RF-026).

    Attributes:
        tipo: porcentaje / monto.
        valor: Porcentaje (hasta 100) o pesos enteros. Mayor que cero.
        activo: Si se sugiere en las ventas.
    """

    tipo: TipoDescuento
    valor: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    activo: bool

    @model_validator(mode="after")
    def _validar_valor(self) -> "DescuentoGeneralIn":
        """Un porcentaje no supera 100 y un monto no lleva centavos."""
        if self.tipo == TipoDescuento.PORCENTAJE and self.valor > 100:
            raise ValueError("Un descuento en porcentaje no puede superar el 100 %.")
        if self.tipo == TipoDescuento.MONTO and self.valor != self.valor.to_integral_value():
            raise ValueError("Un descuento en pesos debe ser un valor entero, sin centavos.")
        return self


class DescuentoGeneralOut(BaseModel):
    """Descuento general vigente.

    Attributes:
        tipo: porcentaje / monto.
        valor: Porcentaje o pesos.
        activo: Si se sugiere en las ventas.
    """

    tipo: TipoDescuento
    valor: Decimal
    activo: bool


class TopesDescuentoIn(BaseModel):
    """Payload de `PUT /descuentos/topes` (RF-042). None = sin tope.

    Attributes:
        tope_porcentaje: Porcentaje maximo del subtotal (mayor que 0, hasta 100), o None.
        tope_monto: Monto maximo en pesos enteros (mayor que 0), o None.
    """

    tope_porcentaje: Decimal | None = Field(None, gt=0, le=100, max_digits=5, decimal_places=2)
    tope_monto: Decimal | None = Field(None, gt=0, max_digits=10, decimal_places=2)

    @model_validator(mode="after")
    def _validar_monto_entero(self) -> "TopesDescuentoIn":
        """El tope en pesos no lleva centavos."""
        if self.tope_monto is not None and self.tope_monto != self.tope_monto.to_integral_value():
            raise ValueError("El tope en pesos debe ser un valor entero, sin centavos.")
        return self


class TopesDescuentoOut(BaseModel):
    """Topes vigentes del descuento manual del vendedor.

    Attributes:
        tope_porcentaje: Porcentaje maximo, o None (sin tope).
        tope_monto: Monto maximo, o None (sin tope).
        descripcion: Texto listo para mostrar (ej. "hasta 10 % del subtotal y hasta $5.000").
    """

    tope_porcentaje: Decimal | None
    tope_monto: Decimal | None
    descripcion: str


class ConfiguracionDescuentosOut(BaseModel):
    """Respuesta de `GET /descuentos/configuracion`.

    Attributes:
        general: Descuento general configurado, o None si nunca se configuro.
        topes: Topes del descuento manual.
    """

    general: DescuentoGeneralOut | None
    topes: TopesDescuentoOut
