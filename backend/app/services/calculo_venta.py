"""Calculo de una venta del Adendo v2 (Fase A1): descuento, topes, redondeo, prorrateo y pagos.

Orden de calculo (docs/03, seccion 7.8): subtotal (suma de las lineas) ->
descuento sobre el subtotal -> redondeo a multiplo de $50 -> total. La suma
de los pagos debe ser igual al total. Todo se calcula aqui, en el backend;
del cliente solo se toman el tipo y el valor del descuento y los montos de
los pagos.

Las funciones son puras (sin base de datos) y lanzan `ValueError` con un
mensaje para el usuario; el router lo convierte en una respuesta HTTP.
"""

from dataclasses import dataclass
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from app.models.descuento import TipoDescuento
from app.models.pago_venta import PlataformaTransferencia
from app.models.venta import MetodoPago
from app.services.redondeo import MULTIPLO_REDONDEO, redondear_a_50

CENTAVOS = Decimal("0.01")
CIEN = Decimal("100")


def formatear_pesos(valor: Decimal) -> str:
    """Formatea un monto como pesos para los mensajes de error (ej. 25000 -> "$25.000").

    Args:
        valor: Monto.

    Returns:
        str: El monto con separador de miles y sin decimales si son cero.
    """
    entero = valor.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    texto = f"{entero:,.0f}" if entero == valor else f"{valor:,.2f}"
    return "$" + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def _formatear_porcentaje(valor: Decimal) -> str:
    """Formatea un porcentaje sin ceros sobrantes (ej. 10.00 -> "10 %", 7.50 -> "7,5 %")."""
    texto = f"{valor.normalize():f}".replace(".", ",")
    return f"{texto} %"


def es_entero(valor: Decimal) -> bool:
    """Indica si un monto no tiene centavos.

    Args:
        valor: Monto a revisar.

    Returns:
        bool: True si es un numero entero de pesos.
    """
    return valor == valor.to_integral_value()


def calcular_monto_descuento(subtotal: Decimal, tipo: TipoDescuento, valor: Decimal) -> Decimal:
    """Calcula el descuento en pesos sobre el subtotal (RF-027).

    Args:
        subtotal: Subtotal de la venta.
        tipo: Porcentaje o monto fijo.
        valor: Porcentaje (0 a 100) o pesos.

    Returns:
        Decimal: El descuento en pesos, redondeado al centavo (la mitad sube).

    Raises:
        ValueError: Si el valor no es positivo, un porcentaje supera 100, un
            monto tiene centavos o el descuento supera el subtotal.
    """
    if valor <= 0:
        raise ValueError("El valor del descuento debe ser mayor que cero.")
    if tipo == TipoDescuento.PORCENTAJE:
        if valor > CIEN:
            raise ValueError("Un descuento en porcentaje no puede superar el 100 %.")
        return (subtotal * valor / CIEN).quantize(CENTAVOS, rounding=ROUND_HALF_UP)

    if not es_entero(valor):
        raise ValueError("Un descuento en pesos debe ser un valor entero, sin centavos.")
    if valor > subtotal:
        raise ValueError(
            f"El descuento ({formatear_pesos(valor)}) no puede ser mayor que el subtotal "
            f"({formatear_pesos(subtotal)})."
        )
    return valor.quantize(CENTAVOS)


def validar_topes(
    subtotal: Decimal,
    monto_descuento: Decimal,
    tope_porcentaje: Decimal | None,
    tope_monto: Decimal | None,
) -> None:
    """Verifica que un descuento manual del vendedor cumpla los dos topes (RF-042).

    Se deben cumplir ambos; un tope en None no limita. El porcentaje se mide
    sobre el subtotal, sea cual sea la forma en que se escribio el descuento.

    Args:
        subtotal: Subtotal de la venta.
        monto_descuento: Descuento en pesos ya calculado.
        tope_porcentaje: Porcentaje maximo, o None.
        tope_monto: Monto maximo en pesos, o None.

    Raises:
        ValueError: Con el limite vigente, si se supera cualquiera de los topes.
    """
    if monto_descuento <= 0:
        return
    porcentaje = monto_descuento * CIEN / subtotal if subtotal > 0 else Decimal("0")
    excede_porcentaje = tope_porcentaje is not None and porcentaje > tope_porcentaje
    excede_monto = tope_monto is not None and monto_descuento > tope_monto
    if excede_porcentaje or excede_monto:
        raise ValueError(f"El descuento supera el límite permitido: {describir_topes(tope_porcentaje, tope_monto)}.")


def describir_topes(tope_porcentaje: Decimal | None, tope_monto: Decimal | None) -> str:
    """Describe los topes vigentes para mostrarlos al vendedor.

    Args:
        tope_porcentaje: Porcentaje maximo, o None.
        tope_monto: Monto maximo en pesos, o None.

    Returns:
        str: Ej. "hasta 10 % y hasta $5.000", o "sin límite".
    """
    partes = []
    if tope_porcentaje is not None:
        partes.append(f"hasta {_formatear_porcentaje(tope_porcentaje)} del subtotal")
    if tope_monto is not None:
        partes.append(f"hasta {formatear_pesos(tope_monto)}")
    return " y ".join(partes) if partes else "sin límite"


@dataclass(frozen=True)
class Totales:
    """Resultado del calculo del total de una venta.

    Attributes:
        subtotal: Suma de las lineas.
        descuento_monto: Descuento en pesos.
        ajuste_redondeo: Ajuste a multiplo de $50 (puede ser negativo).
        total: `subtotal - descuento_monto + ajuste_redondeo`.
    """

    subtotal: Decimal
    descuento_monto: Decimal
    ajuste_redondeo: Decimal
    total: Decimal


def calcular_totales(subtotal: Decimal, descuento_monto: Decimal) -> Totales:
    """Aplica el descuento y luego el redondeo a multiplo de $50.

    Args:
        subtotal: Suma de las lineas.
        descuento_monto: Descuento en pesos (0 a `subtotal`).

    Returns:
        Totales: Subtotal, descuento, ajuste por redondeo y total.
    """
    neto = subtotal - descuento_monto
    total = redondear_a_50(neto)
    return Totales(
        subtotal=subtotal.quantize(CENTAVOS),
        descuento_monto=descuento_monto.quantize(CENTAVOS),
        ajuste_redondeo=(total - neto).quantize(CENTAVOS),
        total=total,
    )


def prorratear_descuento(subtotales: list[Decimal], descuento_monto: Decimal) -> list[Decimal]:
    """Reparte el descuento entre las lineas en proporcion a su subtotal (docs/03, 7.8).

    Cada linea recibe su parte truncada al centavo y el resto de centavos va a
    la ultima linea con subtotal mayor que cero, para que la suma sea exacta
    y ninguna linea gratuita reciba descuento.

    Args:
        subtotales: Subtotal de cada linea, en el orden de la venta.
        descuento_monto: Descuento total de la venta.

    Returns:
        list[Decimal]: Descuento de cada linea; suman `descuento_monto`.
    """
    total = sum(subtotales, Decimal("0"))
    if descuento_monto <= 0 or total <= 0:
        return [Decimal("0.00") for _ in subtotales]

    partes = [(descuento_monto * s / total).quantize(CENTAVOS, rounding=ROUND_DOWN) for s in subtotales]
    ultima_con_valor = max(i for i, s in enumerate(subtotales) if s > 0)
    partes[ultima_con_valor] += descuento_monto - sum(partes, Decimal("0"))
    return partes


@dataclass(frozen=True)
class PagoCalculado:
    """Un pago validado, listo para guardarse.

    Attributes:
        metodo_pago: Metodo del pago.
        plataforma: Plataforma (solo transferencia).
        monto: Lo que abona al total.
        monto_recibido: Lo entregado en efectivo, o None.
        vueltas: Cambio a devolver (0 si no es efectivo).
    """

    metodo_pago: MetodoPago
    plataforma: PlataformaTransferencia | None
    monto: Decimal
    monto_recibido: Decimal | None
    vueltas: Decimal


def validar_pagos(
    pagos: list[tuple[MetodoPago, PlataformaTransferencia | None, Decimal, Decimal | None]],
    total: Decimal,
) -> list[PagoCalculado]:
    """Valida los pagos de una venta y calcula las vueltas (RF-022 a RF-024).

    Reglas: montos en pesos enteros y mayores que cero; en efectivo, monto y
    monto recibido multiplos de $50 y recibido >= monto; en transferencia, la
    plataforma es obligatoria; tarjeta y transferencia no llevan monto
    recibido; la suma de los montos es igual al total; una venta en $0 no
    lleva pagos.

    Args:
        pagos: Tuplas (metodo, plataforma, monto, monto_recibido) en el orden recibido.
        total: Total de la venta ya redondeado.

    Returns:
        list[PagoCalculado]: Los pagos con sus vueltas.

    Raises:
        ValueError: Con un mensaje para el usuario si alguna regla no se cumple.
    """
    if total == 0:
        if pagos:
            raise ValueError("Una venta con total $0 no lleva pagos.")
        return []
    if not pagos:
        raise ValueError("Agregue al menos un pago.")

    calculados = []
    for metodo, plataforma, monto, recibido in pagos:
        if monto <= 0 or not es_entero(monto):
            raise ValueError("El monto de cada pago debe ser un valor entero mayor que cero.")

        if metodo == MetodoPago.EFECTIVO:
            if monto % MULTIPLO_REDONDEO != 0:
                raise ValueError(
                    f"Un pago en efectivo debe ser múltiplo de $50 ({formatear_pesos(monto)} no lo es)."
                )
            if recibido is None:
                raise ValueError("En un pago en efectivo indique el monto recibido.")
            if recibido % MULTIPLO_REDONDEO != 0:
                raise ValueError("El monto recibido en efectivo debe ser múltiplo de $50.")
            if recibido < monto:
                raise ValueError(
                    f"El monto recibido ({formatear_pesos(recibido)}) no puede ser menor que el pago "
                    f"en efectivo ({formatear_pesos(monto)})."
                )
            if plataforma is not None:
                raise ValueError("La plataforma solo aplica a pagos por transferencia.")
            vueltas = recibido - monto
        else:
            if recibido is not None:
                raise ValueError("El monto recibido solo aplica a pagos en efectivo.")
            if metodo == MetodoPago.TRANSFERENCIA and plataforma is None:
                raise ValueError("En un pago por transferencia elija la plataforma: Nequi o Daviplata.")
            if metodo != MetodoPago.TRANSFERENCIA and plataforma is not None:
                raise ValueError("La plataforma solo aplica a pagos por transferencia.")
            vueltas = Decimal("0")

        calculados.append(
            PagoCalculado(
                metodo_pago=metodo,
                plataforma=plataforma,
                monto=monto.quantize(CENTAVOS),
                monto_recibido=recibido.quantize(CENTAVOS) if recibido is not None else None,
                vueltas=vueltas.quantize(CENTAVOS),
            )
        )

    suma = sum((p.monto for p in calculados), Decimal("0"))
    if suma < total:
        raise ValueError(
            f"Los pagos suman {formatear_pesos(suma)} y el total es {formatear_pesos(total)}: "
            f"faltan {formatear_pesos(total - suma)}."
        )
    if suma > total:
        raise ValueError(
            f"Los pagos suman {formatear_pesos(suma)} y el total es {formatear_pesos(total)}: "
            f"sobran {formatear_pesos(suma - total)}."
        )
    return calculados
