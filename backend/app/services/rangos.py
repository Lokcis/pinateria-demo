"""Rango de dias en la zona horaria del negocio, compartido por el Dashboard y Ganancias."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status

from app.core.config import settings

MAXIMO_DIAS_RANGO = 366


def rango_de_fechas(desde: date | None, hasta: date | None) -> tuple:
    """Valida el rango pedido y devuelve (desde, hasta, inicio, fin) en la zona del negocio.

    Sin parametros el rango es solo hoy. `desde` y `hasta` son inclusivos;
    `inicio`/`fin` son el intervalo semiabierto [inicio, fin) para filtrar.

    Args:
        desde: Primer dia del rango, o None para usar `hasta` (o hoy).
        hasta: Ultimo dia del rango, o None para usar hoy.

    Returns:
        tuple: (desde, hasta, inicio, fin).

    Raises:
        HTTPException: 422 si el rango esta invertido, llega al futuro o supera
            `MAXIMO_DIAS_RANGO` dias.
    """
    zona = ZoneInfo(settings.zona_horaria)
    hoy = datetime.now(zona).date()
    hasta = hasta or hoy
    desde = desde or hasta
    if desde > hasta:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "La fecha inicial no puede ser posterior a la final.")
    if hasta > hoy:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No se pueden consultar fechas futuras.")
    if (hasta - desde).days + 1 > MAXIMO_DIAS_RANGO:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"El rango no puede superar {MAXIMO_DIAS_RANGO} dias."
        )
    inicio = datetime.combine(desde, time.min, tzinfo=zona)
    fin = datetime.combine(hasta + timedelta(days=1), time.min, tzinfo=zona)
    return desde, hasta, inicio, fin
