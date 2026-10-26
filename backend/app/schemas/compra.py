"""Esquemas Pydantic para Compra y DetalleCompra (RF-010, RF-011)."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.compra import EstadoCompra
from app.models.pago_venta import PlataformaTransferencia
from app.models.venta import MetodoPago


class DetalleCompraIn(BaseModel):
    """Linea de una orden de compra a crear.

    Attributes:
        producto_id: Producto a comprar.
        cantidad: Unidades a ordenar. Debe ser mayor a cero.
        costo_unitario: Costo pactado por unidad. Debe ser >= 0.
    """

    producto_id: int
    cantidad: int = Field(gt=0)
    costo_unitario: Decimal = Field(ge=0, max_digits=10, decimal_places=2)


class CompraIn(BaseModel):
    """Payload para crear una orden de compra (estado inicial: pendiente).

    Attributes:
        proveedor_id: Proveedor al que se le compra.
        detalles: Lineas de la orden (al menos una).
    """

    proveedor_id: int
    detalles: list[DetalleCompraIn] = Field(min_length=1)


class RecibirCompraIn(BaseModel):
    """Payload de `PATCH /compras/{id}/recibir`: como se pago la compra (Adendo v3, RF-063).

    Attributes:
        metodo_pago: efectivo / tarjeta / transferencia.
        plataforma: nequi / daviplata; obligatoria en una transferencia y prohibida en las demas formas de pago.
    """

    metodo_pago: MetodoPago
    plataforma: PlataformaTransferencia | None = None

    @model_validator(mode="after")
    def _plataforma_coherente(self) -> "RecibirCompraIn":
        """Exige la plataforma en toda transferencia y la rechaza en efectivo o tarjeta."""
        if self.metodo_pago == MetodoPago.TRANSFERENCIA and self.plataforma is None:
            raise ValueError("Indica la plataforma de la transferencia (Nequi o Daviplata).")
        if self.metodo_pago != MetodoPago.TRANSFERENCIA and self.plataforma is not None:
            raise ValueError("La plataforma solo aplica a las transferencias.")
        return self


class DetalleCompraOut(BaseModel):
    """Linea de una compra tal como la expone la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    producto_nombre: str
    cantidad: int
    costo_unitario: Decimal
    subtotal: Decimal


class CompraOut(BaseModel):
    """Compra completa con su proveedor y sus lineas."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    proveedor_id: int
    proveedor_nombre: str
    usuario_id: int
    fecha: datetime
    estado: EstadoCompra
    total: Decimal
    metodo_pago: MetodoPago | None
    plataforma: PlataformaTransferencia | None
    recibida_en: datetime | None
    detalles: list[DetalleCompraOut]
