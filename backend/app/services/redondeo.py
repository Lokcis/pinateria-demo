"""Redondeo de totales a la denominacion minima de la moneda (COP: multiplos de 50 pesos)."""

from decimal import ROUND_HALF_UP, Decimal

MULTIPLO_REDONDEO = Decimal("50")


def redondear_a_50(valor: Decimal) -> Decimal:
    """Redondea un monto al multiplo de 50 pesos mas cercano (la mitad sube).

    Args:
        valor: Monto a redondear.

    Returns:
        Decimal: El multiplo de 50 mas cercano (ej. 1.024 -> 1.000, 1.025 -> 1.050).
    """
    return ((valor / MULTIPLO_REDONDEO).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * MULTIPLO_REDONDEO).quantize(
        Decimal("0.01")
    )
