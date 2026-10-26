"""Esquemas Pydantic de gastos y categorias de gasto (Adendo v3, Fase G1: RF-059 a RF-066, RF-075)."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.pago_venta import PlataformaTransferencia
from app.models.venta import MetodoPago
from app.schemas.tipos import NombreCapitalizado, NombreOpcionalCapitalizado, TextoCapitalizado


class CategoriaGastoIn(BaseModel):
    """Payload de `POST /categorias-gasto`.

    Attributes:
        nombre: Nombre de la categoria (hasta 60 caracteres, primera letra en mayuscula).
    """

    nombre: NombreCapitalizado = Field(min_length=1, max_length=60)


class CategoriaGastoPatch(BaseModel):
    """Payload de `PATCH /categorias-gasto/{id}`: renombrar, activar o desactivar.

    Attributes:
        nombre: Nombre nuevo, o None para dejar el actual.
        activa: True/False para activar o desactivar, o None para dejarla como esta.
    """

    nombre: NombreCapitalizado | None = Field(default=None, min_length=1, max_length=60)
    activa: bool | None = None


class CategoriaGastoOut(BaseModel):
    """Categoria de gasto tal como la expone la API.

    Attributes:
        id: Identificador.
        nombre: Nombre.
        activa: Si se ofrece para gastos nuevos.
        es_sistema: True en "Compra de mercancia": no se renombra ni se desactiva.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    activa: bool
    es_sistema: bool


def _pesos_enteros(valor: Decimal) -> Decimal:
    """Valida que el monto sea de pesos enteros (sin centavos)."""
    if valor != valor.to_integral_value():
        raise ValueError("El monto va en pesos enteros, sin centavos.")
    return valor


class GastoIn(BaseModel):
    """Payload de `POST /gastos`.

    La plataforma y el multiplo de $50 en efectivo se validan en `services/gastos.py` (dependen de la forma de pago).

    Attributes:
        categoria_id: Categoria activa del gasto.
        descripcion: Que se pago (hasta 255 caracteres).
        monto: Pesos enteros, mayor que cero.
        metodo_pago: efectivo / tarjeta / transferencia.
        plataforma: nequi / daviplata; obligatoria en transferencia y prohibida en las demas.
        beneficiario: A quien se pago, opcional; si es una persona, solo su nombre.
        fecha: Dia del gasto. El vendedor solo puede dejar la de hoy; el administrador elige una que no sea futura.
    """

    categoria_id: int
    descripcion: TextoCapitalizado = Field(min_length=1, max_length=255)
    monto: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    metodo_pago: MetodoPago
    plataforma: PlataformaTransferencia | None = None
    beneficiario: NombreOpcionalCapitalizado | None = Field(default=None, max_length=120)
    fecha: date | None = None

    @field_validator("monto")
    @classmethod
    def _monto_entero(cls, valor: Decimal) -> Decimal:
        """Valida los pesos enteros."""
        return _pesos_enteros(valor)


class GastoPatch(BaseModel):
    """Payload de `PATCH /gastos/{id}`: solo viajan los campos que cambian.

    `plataforma` y `beneficiario` se pueden mandar en null para borrarlos.

    Attributes:
        categoria_id: Categoria nueva (activa).
        descripcion: Descripcion nueva.
        monto: Monto nuevo.
        metodo_pago: Forma de pago nueva.
        plataforma: Plataforma nueva (o null).
        beneficiario: Beneficiario nuevo (o null).
        fecha: Fecha nueva; solo el administrador.
    """

    categoria_id: int | None = None
    descripcion: TextoCapitalizado | None = Field(default=None, min_length=1, max_length=255)
    monto: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    metodo_pago: MetodoPago | None = None
    plataforma: PlataformaTransferencia | None = None
    beneficiario: NombreOpcionalCapitalizado | None = Field(default=None, max_length=120)
    fecha: date | None = None

    @field_validator("monto")
    @classmethod
    def _monto_entero(cls, valor: Decimal | None) -> Decimal | None:
        """Valida los pesos enteros cuando se manda el monto."""
        return None if valor is None else _pesos_enteros(valor)


class AnularGastoIn(BaseModel):
    """Payload de `POST /gastos/{id}/anular`.

    Attributes:
        motivo: Por que se anula (obligatorio, hasta 255 caracteres).
    """

    motivo: TextoCapitalizado = Field(min_length=3, max_length=255)


class OrigenGasto(str, Enum):
    """De donde sale una fila de la lista unificada.

    Attributes:
        GASTO: Un gasto registrado en la ventana de Gastos.
        COMPRA: Una compra a proveedor ya recibida (solo lectura).
    """

    GASTO = "gasto"
    COMPRA = "compra"


class EstadoGasto(str, Enum):
    """Filtro de estado de la lista de gastos.

    Attributes:
        VIGENTE: Los que suman en los totales.
        ANULADO: Los anulados.
    """

    VIGENTE = "vigente"
    ANULADO = "anulado"


class GastoOut(BaseModel):
    """Una fila de la lista de gastos: un gasto o una compra recibida.

    Attributes:
        origen: gasto / compra.
        id: Id del gasto o de la compra (segun `origen`).
        fecha: Dia contable (hora de Bogota).
        categoria_id: Categoria (en una compra, la de sistema "Compra de mercancia", si existe).
        categoria: Nombre de la categoria.
        descripcion: Que se pago ("Compra #n — proveedor" en una compra).
        beneficiario: A quien se pago (el proveedor en una compra).
        monto: Monto en pesos.
        metodo_pago: Forma de pago; None en las compras recibidas antes del Adendo v3.
        plataforma: nequi / daviplata en una transferencia.
        registrado_por_id: Id de quien lo registro.
        registrado_por: Nombre de quien lo registro.
        creado_en: Hora real del registro (en una compra, la de recepcion).
        actualizado_en: Ultima edicion.
        actualizado_por: Quien hizo la ultima edicion.
        anulado: True si esta anulado (las compras nunca).
        anulado_en: Cuando se anulo.
        anulado_por: Quien lo anulo.
        motivo_anulacion: Por que se anulo.
        cubierto_por_corte: True si un corte de caja cerrado ya lo incluye (el vendedor no puede modificarlo).
        editable: True si quien consulta puede editarlo y anularlo.
    """

    origen: OrigenGasto
    id: int
    fecha: date
    categoria_id: int | None
    categoria: str
    descripcion: str
    beneficiario: str | None
    monto: Decimal
    metodo_pago: MetodoPago | None
    plataforma: PlataformaTransferencia | None
    registrado_por_id: int
    registrado_por: str
    creado_en: datetime
    actualizado_en: datetime | None
    actualizado_por: str | None
    anulado: bool
    anulado_en: datetime | None
    anulado_por: str | None
    motivo_anulacion: str | None
    cubierto_por_corte: bool
    editable: bool


class TotalCategoriaOut(BaseModel):
    """Total vigente de una categoria en el rango.

    Attributes:
        categoria_id: Categoria (None solo si faltara la de sistema).
        categoria: Nombre.
        cantidad: Cuantos gastos o compras.
        total: Suma de los montos vigentes.
    """

    categoria_id: int | None
    categoria: str
    cantidad: int
    total: Decimal


class TotalMetodoOut(BaseModel):
    """Total vigente por forma de pago en el rango.

    Attributes:
        metodo_pago: Forma de pago; None en las compras sin forma de pago (anteriores al Adendo v3).
        total: Suma de los montos vigentes.
    """

    metodo_pago: MetodoPago | None
    total: Decimal


class ResumenGastosOut(BaseModel):
    """Respuesta de `GET /gastos/resumen` (RF-066).

    Los gastos anulados no suman. Las compras cuentan una vez recibidas.

    Attributes:
        desde: Primer dia del rango.
        hasta: Ultimo dia del rango.
        total: Todos los gastos vigentes, incluidas las compras recibidas.
        total_compras: Solo las compras recibidas (las de la categoria de sistema).
        total_operativo: `total` sin las compras de mercancia (lo que resta la ganancia neta, Fase G3).
        por_categoria: Totales por categoria, de mayor a menor.
        por_metodo_pago: Totales por forma de pago, de mayor a menor.
    """

    desde: date
    hasta: date
    total: Decimal
    total_compras: Decimal
    total_operativo: Decimal
    por_categoria: list[TotalCategoriaOut]
    por_metodo_pago: list[TotalMetodoOut]
