"""Esquemas Pydantic para Venta, sus lineas de detalle y sus pagos."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.descuento import OrigenDescuento, TipoDescuento
from app.models.pago_venta import PlataformaTransferencia
from app.models.venta import MetodoPago


class DetalleVentaIn(BaseModel):
    """Linea de producto enviada al crear una venta.

    Attributes:
        producto_id: Id del producto a vender.
        cantidad: Cantidad a vender. Debe ser mayor a cero.
        precio_unitario: Precio que vio el cliente en la tienda. Solo se acepta en una venta hecha sin
            conexion (Fase 9): el catalogo guardado en el POS pudo cambiar mientras tanto. En una venta
            normal el precio siempre es el vigente del catalogo.
    """

    producto_id: int
    cantidad: int = Field(..., gt=0)
    precio_unitario: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)


class PagoIn(BaseModel):
    """Un pago de la venta (Adendo v2, RF-022 a RF-024).

    Attributes:
        metodo_pago: efectivo / tarjeta / transferencia.
        plataforma: nequi / daviplata; obligatoria en transferencia.
        monto: Lo que este pago abona al total, en pesos enteros.
        monto_recibido: Lo que entrego el cliente; solo en efectivo.
    """

    metodo_pago: MetodoPago
    plataforma: PlataformaTransferencia | None = None
    monto: Decimal = Field(..., max_digits=10, decimal_places=2)
    monto_recibido: Decimal | None = Field(None, max_digits=10, decimal_places=2)


class DescuentoIn(BaseModel):
    """Descuento elegido en la venta (Adendo v2, RF-026 a RF-028).

    - `ninguno`: sin descuento. Es lo normal: el descuento general no se
      aplica a todas las ventas, el vendedor lo elige.
    - `general`: el vendedor aplico el descuento general; el backend usa la
      configuracion vigente y no mira `tipo` ni `valor`.
    - `manual`: el usuario lo cambio (`tipo` y `valor`) o lo quito (ambos
      en None). Los topes aplican si quien vende es vendedor.
    - `cliente`: el vendedor acepto el descuento propio del cliente asociado a
      la venta; el backend usa el que tiene hoy el cliente y no mira `tipo` ni
      `valor`. Los topes no aplican.

    Attributes:
        origen: De donde sale el descuento.
        tipo: porcentaje / monto (solo manual).
        valor: Porcentaje o pesos (solo manual).
    """

    origen: OrigenDescuento = OrigenDescuento.NINGUNO
    tipo: TipoDescuento | None = None
    valor: Decimal | None = Field(None, max_digits=10, decimal_places=2)


class SinConexionIn(BaseModel):
    """Datos de una venta que se hizo sin conexion y se envia despues (Fase 9).

    Attributes:
        fecha: Hora real de la venta en la tienda, con zona horaria. El servidor la guarda como fecha
            de la venta y la rechaza si es futura o mas antigua que `VENTAS_SIN_CONEXION_DIAS_MAX`.
    """

    fecha: datetime


class VentaIn(BaseModel):
    """Payload para crear una venta (`POST /ventas`).

    Attributes:
        detalles: Lineas de la venta. Debe tener al menos un elemento.
        pagos: Pagos cuya suma es igual al total; vacio si el total es $0.
        descuento: Descuento elegido; por defecto, ninguno.
        cliente_id: Cliente asociado a la venta (Fase A2); None si no esta registrado.
        vendedor_id: Quien realiza la venta (HU-08); None = el usuario de la sesion.
        uuid_cliente: Identificador que genera el POS por venta (Fase 9). Reenviar el mismo no duplica la
            venta: el servidor devuelve la que ya registro. Opcional para quien no lo envie.
        sin_conexion: Presente solo si la venta se hizo sin conexion (Fase 9); exige `uuid_cliente`.
    """

    detalles: list[DetalleVentaIn] = Field(..., min_length=1)
    pagos: list[PagoIn] = Field(default_factory=list, max_length=10)
    descuento: DescuentoIn = Field(default_factory=DescuentoIn)
    cliente_id: int | None = None
    vendedor_id: int | None = None
    uuid_cliente: UUID | None = None
    sin_conexion: SinConexionIn | None = None

    @model_validator(mode="after")
    def _coherencia_sin_conexion(self) -> "VentaIn":
        """Una venta sin conexion lleva su identificador; el precio propio solo se acepta sin conexion."""
        if self.sin_conexion is not None and self.uuid_cliente is None:
            raise ValueError("Una venta hecha sin conexion debe traer su uuid_cliente.")
        if self.sin_conexion is None and any(d.precio_unitario is not None for d in self.detalles):
            raise ValueError("El precio de una linea solo se acepta en ventas hechas sin conexion.")
        return self


class DetalleVentaOut(BaseModel):
    """Linea de detalle de una venta ya confirmada.

    No expone `costo_unitario`: el vendedor nunca ve costos (HU-09).

    Attributes:
        producto_id: Id del producto vendido.
        cantidad: Cantidad vendida.
        precio_unitario: Precio unitario aplicado en el momento de la venta.
        subtotal: `cantidad * precio_unitario`.
        descuento_prorrateado: Parte del descuento de la venta para esta linea.
    """

    model_config = ConfigDict(from_attributes=True)

    producto_id: int
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal
    descuento_prorrateado: Decimal


class PagoOut(BaseModel):
    """Un pago de una venta confirmada.

    Attributes:
        metodo_pago: Metodo del pago.
        plataforma: Plataforma de la transferencia, o None.
        monto: Lo que abono al total.
        monto_recibido: Lo entregado en efectivo, o None.
        vueltas: Cambio devuelto.
    """

    model_config = ConfigDict(from_attributes=True)

    metodo_pago: MetodoPago
    plataforma: PlataformaTransferencia | None
    monto: Decimal
    monto_recibido: Decimal | None
    vueltas: Decimal


class VentaOut(BaseModel):
    """Representacion de una venta confirmada, con sus lineas y sus pagos.

    Attributes:
        id: Identificador unico de la venta.
        usuario_id: Id del vendedor que realizo la venta.
        cliente_id: Id del cliente asociado, o None.
        fecha: Marca de tiempo de la venta.
        uuid_cliente: Identificador que envio el POS, o None.
        sin_conexion: True si la venta se hizo sin conexion y se envio despues.
        subtotal: Suma de las lineas.
        descuento_origen: ninguno / cliente / general / manual.
        descuento_tipo: porcentaje / monto, o None.
        descuento_valor: Valor ingresado, o None.
        descuento_monto: Descuento en pesos.
        ajuste_redondeo: Ajuste a multiplo de $50.
        total: Monto total de la venta.
        detalles: Lineas de detalle de la venta.
        pagos: Pagos de la venta.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int
    cliente_id: int | None
    fecha: datetime
    uuid_cliente: UUID | None = None
    sin_conexion: bool = False
    subtotal: Decimal
    descuento_origen: OrigenDescuento
    descuento_tipo: TipoDescuento | None
    descuento_valor: Decimal | None
    descuento_monto: Decimal
    ajuste_redondeo: Decimal
    total: Decimal
    detalles: list[DetalleVentaOut]
    pagos: list[PagoOut]


class DetalleHistorialOut(BaseModel):
    """Linea de una venta en el historial, con el nombre del producto para mostrarlo.

    Attributes:
        producto_id: Id del producto vendido.
        nombre_producto: Nombre del producto (tal como esta hoy en el catalogo).
        cantidad: Cantidad vendida.
        precio_unitario: Precio unitario aplicado en la venta.
        subtotal: `cantidad * precio_unitario`.
    """

    producto_id: int
    nombre_producto: str
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal


class VentaHistorialOut(BaseModel):
    """Una venta del historial del dia.

    Attributes:
        id: Identificador de la venta.
        fecha: Marca de tiempo de la venta.
        subtotal: Suma de las lineas.
        descuento_origen: De donde salio el descuento.
        descuento_tipo: porcentaje / monto, o None (para reimprimir "Descuento (10 %)").
        descuento_valor: Valor ingresado, o None.
        descuento_monto: Descuento en pesos.
        ajuste_redondeo: Ajuste a multiplo de $50.
        total: Monto total.
        vendedor: Nombre del vendedor que la realizo.
        registrada_por: Nombre de quien la registro, solo si es otra persona (si no, None).
        cliente: Nombre del cliente asociado, o None.
        sin_conexion: True si se hizo sin conexion y se envio despues (Fase 9).
        detalles: Lineas de la venta.
        pagos: Pagos de la venta.
    """

    id: int
    fecha: datetime
    subtotal: Decimal
    descuento_origen: OrigenDescuento
    descuento_tipo: TipoDescuento | None
    descuento_valor: Decimal | None
    descuento_monto: Decimal
    ajuste_redondeo: Decimal
    total: Decimal
    vendedor: str
    registrada_por: str | None = None
    cliente: str | None = None
    sin_conexion: bool = False
    detalles: list[DetalleHistorialOut]
    pagos: list[PagoOut]


class HistorialDiaOut(BaseModel):
    """Historial de ventas de un dia, con su resumen (RF-018).

    Attributes:
        fecha: Dia consultado, en la zona horaria del negocio.
        cantidad_ventas: Numero de ventas incluidas.
        total_vendido: Suma de los totales de las ventas incluidas.
        total_por_metodo: Suma de los montos de los pagos por metodo (Adendo v2, RF-041).
        ventas: Ventas del dia, de la mas reciente a la mas antigua.
    """

    fecha: date
    cantidad_ventas: int
    total_vendido: Decimal
    total_por_metodo: dict[MetodoPago, Decimal]
    ventas: list[VentaHistorialOut]


class VendedorOut(BaseModel):
    """Opcion del desplegable de vendedor del POS (HU-08).

    Attributes:
        id: Id del usuario.
        nombre: Nombre para mostrar.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
