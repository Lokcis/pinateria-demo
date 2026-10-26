"""Esquemas Pydantic de la caja y el corte de caja (Adendo v3, Fase G2: RF-069 a RF-074, HU-13)."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.models.corte_caja import EstadoCorteCaja
from app.models.movimiento_caja import TipoMovimientoCaja
from app.schemas.tipos import TextoCapitalizado


def _pesos_enteros(valor: Decimal) -> Decimal:
    """Valida que el monto sea de pesos enteros (sin centavos)."""
    if valor != valor.to_integral_value():
        raise ValueError("El monto va en pesos enteros, sin centavos.")
    return valor


class AbrirCajaIn(BaseModel):
    """Payload de `POST /caja/abrir`.

    El multiplo de $50 se valida en `services/caja.py`, igual que en las ventas en efectivo.

    Attributes:
        base_inicial: Efectivo con que arranca la caja, en pesos enteros (0 o mas).
    """

    base_inicial: Decimal = Field(ge=0, max_digits=10, decimal_places=2)

    @field_validator("base_inicial")
    @classmethod
    def _entero(cls, valor: Decimal) -> Decimal:
        """Valida los pesos enteros."""
        return _pesos_enteros(valor)


class MovimientoCajaIn(BaseModel):
    """Payload de `POST /caja/movimientos`.

    Attributes:
        tipo: ingreso / retiro.
        monto: Pesos enteros, mayor que cero (multiplo de $50).
        motivo: Para que se hizo, obligatorio (por ejemplo, "Consignacion al banco").
    """

    tipo: TipoMovimientoCaja
    monto: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    motivo: TextoCapitalizado = Field(min_length=3, max_length=255)

    @field_validator("monto")
    @classmethod
    def _entero(cls, valor: Decimal) -> Decimal:
        """Valida los pesos enteros."""
        return _pesos_enteros(valor)


class CerrarCajaIn(BaseModel):
    """Payload de `POST /caja/cerrar`.

    Attributes:
        efectivo_contado: Lo que se conto en la caja, en pesos enteros (multiplo de $50).
        observaciones: Notas del corte, opcionales.
    """

    efectivo_contado: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    observaciones: TextoCapitalizado | None = Field(default=None, max_length=500)

    @field_validator("efectivo_contado")
    @classmethod
    def _entero(cls, valor: Decimal) -> Decimal:
        """Valida los pesos enteros."""
        return _pesos_enteros(valor)


class MovimientoCajaOut(BaseModel):
    """Un ingreso o retiro manual de la caja.

    Attributes:
        id: Identificador.
        tipo: ingreso / retiro.
        monto: Monto en pesos.
        motivo: Para que se hizo.
        usuario: Nombre de quien lo registro.
        creado_en: Hora del movimiento.
    """

    id: int
    tipo: TipoMovimientoCaja
    monto: Decimal
    motivo: str
    usuario: str
    creado_en: datetime


class CifrasCajaOut(BaseModel):
    """Las cifras de un corte: en vivo en una caja abierta, o la foto de uno cerrado.

    `efectivo_esperado = base_inicial + ventas_efectivo + ingresos - gastos_efectivo - compras_efectivo - retiros`.

    Attributes:
        base_inicial: Efectivo con que se abrio la caja.
        ventas_efectivo: Pagos en efectivo de las ventas del periodo (lo que abona a la venta; sin vueltas).
        ingresos: Ingresos manuales.
        gastos_efectivo: Gastos vigentes pagados en efectivo.
        compras_efectivo: Compras recibidas pagadas en efectivo.
        retiros: Retiros manuales.
        efectivo_esperado: Lo que deberia haber en la caja.
        ventas_tarjeta: Informativo: ventas pagadas con tarjeta, para compararlas con el datafono.
        ventas_transferencia: Informativo: ventas pagadas por transferencia (Nequi y Daviplata), para el banco.
    """

    base_inicial: Decimal
    ventas_efectivo: Decimal
    ingresos: Decimal
    gastos_efectivo: Decimal
    compras_efectivo: Decimal
    retiros: Decimal
    efectivo_esperado: Decimal
    ventas_tarjeta: Decimal
    ventas_transferencia: Decimal


class CorteCajaOut(BaseModel):
    """Una fila del historial de cortes.

    Attributes:
        id: Identificador del corte.
        estado: abierta / cerrada.
        abierta_en: Apertura.
        abierta_por: Nombre de quien abrio.
        cerrada_en: Cierre, o None si sigue abierta.
        cerrada_por: Nombre de quien cerro.
        base_inicial: Efectivo con que se abrio.
        efectivo_esperado: Foto del esperado (solo cerradas).
        efectivo_contado: Lo contado (solo cerradas).
        diferencia: contado - esperado; positiva sobra, negativa falta (solo cerradas).
    """

    id: int
    estado: EstadoCorteCaja
    abierta_en: datetime
    abierta_por: str
    cerrada_en: datetime | None
    cerrada_por: str | None
    base_inicial: Decimal
    efectivo_esperado: Decimal | None
    efectivo_contado: Decimal | None
    diferencia: Decimal | None


class VentasTardiasOut(BaseModel):
    """Ventas hechas sin conexion durante un corte, pero enviadas al servidor despues de su cierre.

    No alteran la foto del corte; se informan para que quien lo revise sepa que existen.

    Attributes:
        cantidad: Cuantas ventas.
        total: Suma de sus totales.
    """

    cantidad: int
    total: Decimal


class CorteCajaDetalleOut(CorteCajaOut):
    """Ficha de un corte cerrado: la foto de sus cifras, sus movimientos y el aviso de ventas tardias.

    Attributes:
        cifras: La foto guardada al cerrar.
        observaciones: Notas del corte.
        movimientos: Ingresos y retiros manuales del corte.
        ventas_sin_conexion_tardias: Ventas sin conexion enviadas despues del cierre.
    """

    cifras: CifrasCajaOut
    observaciones: str | None
    movimientos: list[MovimientoCajaOut]
    ventas_sin_conexion_tardias: VentasTardiasOut


class CajaActualOut(BaseModel):
    """Respuesta de `GET /caja/actual`: si la caja esta abierta y cuanto efectivo deberia haber ahora.

    Attributes:
        abierta: True si hay una caja abierta.
        corte: El corte abierto, o None.
        cifras: Cifras en vivo del corte abierto, o None.
        movimientos: Ingresos y retiros del corte abierto.
        generado_en: Momento del calculo.
    """

    abierta: bool
    corte: CorteCajaOut | None
    cifras: CifrasCajaOut | None
    movimientos: list[MovimientoCajaOut]
    generado_en: datetime
