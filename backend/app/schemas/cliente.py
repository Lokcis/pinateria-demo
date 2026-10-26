"""Esquemas Pydantic para clientes y solicitudes de titular (Adendo v2, Fase A2)."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.cliente import (
    EstadoSolicitudTitular,
    MedioAutorizacion,
    OrigenRegistro,
    TipoSolicitudTitular,
)
from app.models.descuento import TipoDescuento
from app.schemas.proveedor import Email, Telefono
from app.services.texto import capitalizar_nombre
from app.schemas.venta import PagoOut


def _texto_o_none(valor: str | None) -> str | None:
    """Recorta espacios; un texto vacio se guarda como NULL."""
    if valor is None:
        return None
    valor = valor.strip()
    return valor or None


class ClienteCrearIn(BaseModel):
    """Payload para registrar un cliente (`POST /clientes`).

    No se puede guardar sin la autorizacion de tratamiento de datos (RF-029).
    La fecha, la version de la politica y el empleado los pone el servidor.

    Attributes:
        nombre: Nombre del cliente (obligatorio).
        documento: Documento de identidad (opcional, unico).
        telefono: Solo digitos (7 a 15).
        email: Correo electronico.
        autorizacion_aceptada: Debe ser True: el titular autorizo el tratamiento.
        autorizacion_medio: Medio por el que autorizo.
        acepta_publicidad: Autorizacion APARTE (opcional) para recibir promociones.
    """

    nombre: str = Field(min_length=1, max_length=150)
    documento: str | None = Field(default=None, max_length=30)
    telefono: Telefono = None
    email: Email = None
    autorizacion_aceptada: bool
    autorizacion_medio: MedioAutorizacion
    acepta_publicidad: bool = False

    @field_validator("nombre")
    @classmethod
    def _nombre_no_vacio(cls, valor: str) -> str:
        """Rechaza nombres formados solo por espacios."""
        valor = valor.strip()
        if not valor:
            raise ValueError("El nombre no puede quedar vacío.")
        return capitalizar_nombre(valor)

    @field_validator("documento")
    @classmethod
    def _documento_limpio(cls, valor: str | None) -> str | None:
        """Recorta el documento; vacio equivale a sin documento."""
        return _texto_o_none(valor)

    @field_validator("autorizacion_aceptada")
    @classmethod
    def _exigir_autorizacion(cls, valor: bool) -> bool:
        """Exige la autorizacion de tratamiento de datos (Ley 1581 de 2012)."""
        if not valor:
            raise ValueError("Debe registrar la autorización del cliente para el tratamiento de sus datos.")
        return valor


class ClienteEditarIn(BaseModel):
    """Payload para editar un cliente; solo se actualizan los campos presentes.

    Attributes:
        nombre: Nuevo nombre.
        documento: Nuevo documento (vacio lo quita).
        telefono: Nuevo telefono.
        email: Nuevo correo.
        activo: Baja o alta logica.
        acepta_publicidad: Da o retira la autorizacion para promociones.
    """

    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    documento: str | None = Field(default=None, max_length=30)
    telefono: Telefono = None
    email: Email = None
    activo: bool | None = None
    acepta_publicidad: bool | None = None

    @field_validator("nombre")
    @classmethod
    def _nombre_no_vacio(cls, valor: str | None) -> str | None:
        """Rechaza nombres formados solo por espacios."""
        if valor is None:
            return None
        valor = valor.strip()
        if not valor:
            raise ValueError("El nombre no puede quedar vacío.")
        return capitalizar_nombre(valor)

    @field_validator("documento")
    @classmethod
    def _documento_limpio(cls, valor: str | None) -> str | None:
        """Recorta el documento; vacio equivale a sin documento."""
        return _texto_o_none(valor)


class DescuentoClienteIn(BaseModel):
    """Descuento propio de un cliente (`PUT /clientes/{id}/descuento`, solo administrador).

    Attributes:
        tipo: porcentaje / monto; None (junto con `valor`) quita el descuento.
        valor: Porcentaje (hasta 100) o pesos; mayor que cero.
    """

    tipo: TipoDescuento | None = None
    valor: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)

    @model_validator(mode="after")
    def _completo_y_en_rango(self) -> "DescuentoClienteIn":
        """Exige tipo y valor juntos, y un porcentaje que no pase de 100."""
        if (self.tipo is None) != (self.valor is None):
            raise ValueError("Indique el tipo y el valor del descuento, o ninguno de los dos para quitarlo.")
        if self.tipo == TipoDescuento.PORCENTAJE and self.valor > 100:
            raise ValueError("Un porcentaje no puede ser mayor a 100.")
        return self


class ClienteOut(BaseModel):
    """Cliente expuesto por la API.

    Attributes:
        id: Identificador del cliente.
        nombre: Nombre.
        documento: Documento de identidad, o None.
        telefono: Telefono, o None.
        email: Correo, o None.
        descuento_tipo: Tipo del descuento propio, o None.
        descuento_valor: Valor del descuento propio, o None.
        activo: Si esta dado de alta.
        acepta_publicidad: Si autorizo, aparte, recibir promociones.
        publicidad_fecha: Cuando dio o retiro esa autorizacion, o None.
        utilizable: Si puede asociarse a una venta nueva (activo y con autorizacion vigente).
        autorizacion_fecha: Cuando autorizo el tratamiento de sus datos.
        autorizacion_medio: Medio de la autorizacion.
        autorizacion_version: Version de la politica que acepto.
        origen_registro: empleado / autoregistro.
        autorizacion_revocada_en: Cuando revoco la autorizacion, o None.
        anonimizado_en: Cuando se suprimieron sus datos, o None.
        creado_en: Fecha de registro.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    documento: str | None
    telefono: str | None
    email: str | None
    descuento_tipo: TipoDescuento | None
    descuento_valor: Decimal | None
    activo: bool
    acepta_publicidad: bool
    publicidad_fecha: datetime | None
    utilizable: bool
    autorizacion_fecha: datetime
    autorizacion_medio: MedioAutorizacion
    autorizacion_version: str
    origen_registro: OrigenRegistro
    autorizacion_revocada_en: datetime | None
    anonimizado_en: datetime | None
    creado_en: datetime


class ClienteListadoOut(ClienteOut):
    """Cliente en el listado, con su resumen de compras.

    Attributes:
        numero_ventas: Ventas asociadas (dentro del rango de fechas, si se filtro).
        total_comprado: Suma de los totales de esas ventas.
        ultima_compra: Fecha de la compra mas reciente, o None.
    """

    numero_ventas: int
    total_comprado: Decimal
    ultima_compra: datetime | None


class VentaClienteOut(BaseModel):
    """Una venta en la ficha del cliente.

    Attributes:
        id: Identificador de la venta.
        fecha: Fecha de la venta.
        total: Total cobrado.
        vendedor: Nombre de quien la realizo.
        pagos: Pagos de la venta.
    """

    id: int
    fecha: datetime
    total: Decimal
    vendedor: str
    pagos: list[PagoOut]


class ClienteFichaOut(ClienteOut):
    """Ficha del cliente: sus datos, el total comprado y su historial de ventas (RF-032).

    Attributes:
        autorizacion_recogida_por: Nombre del empleado que recogio la autorizacion; None si el cliente se registro
            solo por el enlace (o si el empleado ya no existe).
        numero_ventas: Cantidad de ventas.
        total_comprado: Suma de los totales de todas sus ventas.
        ultima_compra: Fecha de la ultima compra, o None.
        ventas: Historial de ventas, de la mas reciente a la mas antigua.
    """

    autorizacion_recogida_por: str | None = None
    numero_ventas: int
    total_comprado: Decimal
    ultima_compra: datetime | None
    ventas: list[VentaClienteOut]


class SeccionPolitica(BaseModel):
    """Una seccion de la politica de tratamiento de datos.

    Attributes:
        titulo: Titulo de la seccion.
        parrafos: Parrafos de texto.
        items: Viñetas (puede ir vacia).
    """

    titulo: str
    parrafos: list[str]
    items: list[str]


class PoliticaOut(BaseModel):
    """Politica de tratamiento de datos vigente: aviso, casillas de autorizacion y texto completo.

    Attributes:
        version: Version que se registra como evidencia en cada autorizacion ("borrador" si faltan datos del negocio).
        datos_completos: Si estan todos los datos del negocio que exige la politica.
        faltantes: Variables de configuracion sin completar.
        aviso: Aviso de privacidad corto, que se muestra antes de guardar.
        texto_autorizacion: Casilla obligatoria, redactada para el propio cliente.
        texto_promociones: Casilla aparte (opcional) para promociones, redactada para el cliente.
        texto_autorizacion_empleado: La misma casilla, redactada para el empleado que registra.
        texto_promociones_empleado: La casilla de promociones, redactada para el empleado.
        secciones: La politica completa.
    """

    version: str
    datos_completos: bool
    faltantes: list[str]
    aviso: str
    texto_autorizacion: str
    texto_promociones: str
    texto_autorizacion_empleado: str
    texto_promociones_empleado: str
    secciones: list[SeccionPolitica]


class EnlaceAutoregistroOut(BaseModel):
    """Estado del enlace de autorregistro (solo administrador).

    Attributes:
        existe: Si ya se genero un enlace alguna vez.
        token: Codigo del enlace (parte final de la direccion publica), o None.
        activo: Si el formulario publico esta disponible.
        actualizado_en: Fecha del ultimo cambio, o None.
        datos_completos: Si la politica tiene todos los datos del negocio (sin ellos no se puede activar).
        faltantes: Variables de configuracion sin completar.
    """

    existe: bool
    token: str | None
    activo: bool
    actualizado_en: datetime | None
    datos_completos: bool
    faltantes: list[str]


class EnlaceAutoregistroEstadoIn(BaseModel):
    """Activar o desactivar el enlace de autorregistro.

    Attributes:
        activo: True para activarlo, False para desactivarlo.
    """

    activo: bool


class AutoregistroIn(BaseModel):
    """Datos que el cliente escribe en el formulario publico de autorregistro (RF-046).

    Attributes:
        nombre: Nombre (obligatorio).
        documento: Documento (opcional).
        telefono: Solo digitos (7 a 15).
        email: Correo (opcional).
        acepta_politica: Debe ser True: acepto el aviso y la politica.
        acepta_publicidad: Autorizacion aparte (opcional) para promociones.
        sitio_web: Campo trampa para robots: una persona lo deja vacio (RF-049).
    """

    nombre: str = Field(min_length=1, max_length=150)
    documento: str | None = Field(default=None, max_length=30)
    telefono: Telefono = None
    email: Email = None
    acepta_politica: bool
    acepta_publicidad: bool = False
    sitio_web: str = Field(default="", max_length=200)

    @field_validator("nombre")
    @classmethod
    def _nombre_no_vacio(cls, valor: str) -> str:
        """Rechaza nombres formados solo por espacios."""
        valor = valor.strip()
        if not valor:
            raise ValueError("El nombre no puede quedar vacío.")
        return capitalizar_nombre(valor)

    @field_validator("documento")
    @classmethod
    def _documento_limpio(cls, valor: str | None) -> str | None:
        """Recorta el documento; vacio equivale a sin documento."""
        return _texto_o_none(valor)

    @field_validator("acepta_politica")
    @classmethod
    def _exigir_aceptacion(cls, valor: bool) -> bool:
        """Exige marcar la aceptacion del aviso y la politica."""
        if not valor:
            raise ValueError("Debe aceptar el aviso de privacidad y la política de tratamiento de datos.")
        return valor


class AutoregistroOut(BaseModel):
    """Respuesta neutra del autorregistro: igual haya o no un registro previo (RF-048).

    Attributes:
        mensaje: Agradecimiento que no revela si los datos ya existian.
    """

    mensaje: str


class SolicitudCrearIn(BaseModel):
    """Payload para registrar una solicitud de titular (`POST /solicitudes-titular`).

    Attributes:
        cliente_id: Titular que presenta la solicitud.
        tipo: consulta / actualizacion / supresion / revocatoria.
        descripcion: Detalle de lo solicitado.
    """

    cliente_id: int
    tipo: TipoSolicitudTitular
    descripcion: str | None = Field(default=None, max_length=500)

    @field_validator("descripcion")
    @classmethod
    def _descripcion_limpia(cls, valor: str | None) -> str | None:
        """Recorta la descripcion; vacia equivale a ninguna."""
        return _texto_o_none(valor)


class SolicitudActualizarIn(BaseModel):
    """Payload para avanzar una solicitud (`PATCH /solicitudes-titular/{id}`).

    Attributes:
        estado: en_tramite, resuelta o rechazada.
        respuesta: Resumen de la respuesta; obligatoria al resolver o rechazar.
    """

    estado: EstadoSolicitudTitular
    respuesta: str | None = Field(default=None, max_length=500)

    @field_validator("respuesta")
    @classmethod
    def _respuesta_limpia(cls, valor: str | None) -> str | None:
        """Recorta la respuesta; vacia equivale a ninguna."""
        return _texto_o_none(valor)

    @model_validator(mode="after")
    def _validar(self) -> "SolicitudActualizarIn":
        """No se vuelve a `recibida`; resolver o rechazar exige respuesta."""
        if self.estado == EstadoSolicitudTitular.RECIBIDA:
            raise ValueError("Una solicitud no puede volver al estado 'recibida'.")
        if self.estado in (EstadoSolicitudTitular.RESUELTA, EstadoSolicitudTitular.RECHAZADA) and not self.respuesta:
            raise ValueError("Indique la respuesta dada al titular.")
        return self


class SolicitudOut(BaseModel):
    """Solicitud de titular expuesta por la API.

    Attributes:
        id: Identificador de la solicitud.
        cliente_id: Titular.
        cliente_nombre: Nombre actual del titular (anonimizado si se suprimio).
        tipo: Tipo de solicitud.
        descripcion: Detalle, o None.
        estado: Estado actual.
        recibida_en: Fecha de recepcion.
        fecha_limite: Fecha maxima de respuesta.
        vencida: True si esta sin resolver y la fecha limite ya paso.
        resuelta_en: Fecha de la respuesta, o None.
        atendida_por: Nombre de quien respondio, o None.
        respuesta: Respuesta dada, o None.
    """

    id: int
    cliente_id: int
    cliente_nombre: str
    tipo: TipoSolicitudTitular
    descripcion: str | None
    estado: EstadoSolicitudTitular
    recibida_en: datetime
    fecha_limite: date
    vencida: bool
    resuelta_en: datetime | None
    atendida_por: str | None
    respuesta: str | None
