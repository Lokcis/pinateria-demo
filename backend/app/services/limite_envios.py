"""Limite de envios por visitante para el formulario publico de autorregistro (RF-049).

Vive en memoria del proceso y no guarda direcciones IP: de cada visitante solo se conserva un resumen
(hash) de su identificador y la hora de sus ultimos intentos, que se descartan al vencer la ventana.
Es la segunda barrera: la primera es el limite de peticiones de Nginx (`limit_req`) sobre `/api/publico/`.
Cada proceso del backend lleva su propia cuenta, asi que con varios procesos el limite efectivo es
mayor; por eso Nginx es el limite principal.
"""

import hashlib
import time
from collections import deque

MAX_INTENTOS = 5
VENTANA_SEGUNDOS = 600

_intentos: dict[str, deque[float]] = {}


def _clave(identificador: str) -> str:
    """Resumen no reversible del identificador del visitante."""
    return hashlib.sha256(identificador.encode("utf-8")).hexdigest()


def registrar_intento(identificador: str, ahora: float | None = None) -> bool:
    """Cuenta un intento de envio y dice si el visitante aun esta dentro del limite.

    Args:
        identificador: Identificador del visitante (por ejemplo, su direccion de red).
        ahora: Momento del intento en segundos (solo para pruebas); por defecto, la hora actual.

    Returns:
        bool: True si el intento esta permitido; False si ya supero `MAX_INTENTOS` en la ventana.
    """
    ahora = time.monotonic() if ahora is None else ahora
    corte = ahora - VENTANA_SEGUNDOS

    # Descarta a los visitantes cuyos intentos ya vencieron, para que el diccionario no crezca sin limite.
    for clave in [c for c, fechas in _intentos.items() if not fechas or fechas[-1] < corte]:
        del _intentos[clave]

    fechas = _intentos.setdefault(_clave(identificador), deque())
    while fechas and fechas[0] < corte:
        fechas.popleft()
    if len(fechas) >= MAX_INTENTOS:
        return False
    fechas.append(ahora)
    return True


def reiniciar() -> None:
    """Borra todos los intentos (pruebas)."""
    _intentos.clear()
