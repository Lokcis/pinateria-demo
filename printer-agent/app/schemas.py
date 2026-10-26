"""Esquemas del ticket que el frontend envia a `POST /imprimir`.

Reflejan `construirTicket()` en `frontend/src/components/confirmacion-pago.jsx`
y la respuesta `VentaOut` del backend (los montos llegan como texto decimal).
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class LineaTicket(BaseModel):
    """Una linea de producto del ticket.

    Attributes:
        nombre_producto: Nombre a imprimir.
        cantidad: Unidades vendidas. Debe ser mayor a cero.
        precio_unitario: Precio por unidad al momento de la venta.
        subtotal: `cantidad * precio_unitario`.
    """

    nombre_producto: str = Field(..., min_length=1, max_length=150)
    cantidad: int = Field(..., gt=0)
    precio_unitario: Decimal
    subtotal: Decimal


class PagoTicket(BaseModel):
    """Un pago de la venta (Adendo v2, HU-05).

    Attributes:
        metodo_pago: efectivo / tarjeta / transferencia.
        plataforma: nequi / daviplata, solo en transferencia.
        monto: Lo que abono al total.
        monto_recibido: Lo entregado en efectivo, o None.
        vueltas: Cambio devuelto (0 si no es efectivo).
    """

    metodo_pago: str
    plataforma: str | None = None
    monto: Decimal
    monto_recibido: Decimal | None = None
    vueltas: Decimal = Decimal("0")


class TicketIn(BaseModel):
    """Datos de una venta ya confirmada, listos para imprimirse.

    Acepta dos formatos para que el agente se pueda actualizar antes que el
    servidor sin dejar de imprimir:

    - Anterior al Adendo v2: `metodo_pago` (un solo metodo); el ajuste por
      redondeo se deduce de `total` menos la suma de las lineas.
    - Adendo v2 (Fase A1): `pagos`, `subtotal`, `descuento_*` y
      `ajuste_redondeo`. Una venta en $0 no lleva pagos.

    Una venta hecha sin conexion (Fase 9) todavia no tiene numero del servidor: llega con `referencia`
    (el consecutivo local del POS, ej. "SC-0003") y sin `venta_id`.

    Attributes:
        venta_id: Numero de la venta (consecutivo del backend), o None si aun no se envio al servidor.
        referencia: Numero local de una venta hecha sin conexion, o None.
        fecha: Fecha y hora de la venta.
        vendedor: Nombre de quien realizo la venta (Adendo v2, HU-08), o None.
        metodo_pago: Metodo de pago del formato anterior, o None.
        pagos: Pagos de la venta (formato del Adendo v2).
        subtotal: Suma de las lineas, o None (formato anterior).
        descuento_tipo: porcentaje / monto, o None.
        descuento_valor: Valor ingresado del descuento, o None.
        descuento_monto: Descuento en pesos (0 si no hubo).
        ajuste_redondeo: Ajuste a multiplo de $50, o None (formato anterior).
        total: Total de la venta.
        lineas: Productos vendidos; al menos uno.
    """

    venta_id: int | None = None
    referencia: str | None = Field(default=None, pattern=r"^[A-Za-z0-9-]{1,30}$")
    fecha: datetime
    vendedor: str | None = Field(default=None, max_length=120)
    metodo_pago: str | None = None
    pagos: list[PagoTicket] = Field(default_factory=list)
    subtotal: Decimal | None = None
    descuento_tipo: str | None = None
    descuento_valor: Decimal | None = None
    descuento_monto: Decimal = Decimal("0")
    ajuste_redondeo: Decimal | None = None
    total: Decimal
    lineas: list[LineaTicket] = Field(..., min_length=1)

    @property
    def identificador(self) -> int | str:
        """Numero que identifica el ticket: el de la venta o, si aun no se envio, su referencia local."""
        return self.venta_id if self.venta_id is not None else self.referencia

    @model_validator(mode="after")
    def _exigir_identificador(self) -> "TicketIn":
        """El ticket trae el numero de la venta o su referencia local."""
        if self.venta_id is None and self.referencia is None:
            raise ValueError("El ticket debe traer venta_id o referencia.")
        return self

    @model_validator(mode="after")
    def _exigir_forma_de_pago(self) -> "TicketIn":
        """Una venta con total mayor que 0 trae `pagos` o, en el formato anterior, `metodo_pago`."""
        if self.total > 0 and not self.pagos and not self.metodo_pago:
            raise ValueError("El ticket debe traer los pagos de la venta.")
        return self


class RespuestaImpresion(BaseModel):
    """Confirmacion de que el ticket se envio a la impresora.

    Attributes:
        status: Siempre `ok` en una respuesta exitosa.
        modo: Modo del agente (`mock` o `escpos`).
    """

    status: str
    modo: str
