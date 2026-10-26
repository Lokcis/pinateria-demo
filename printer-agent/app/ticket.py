"""Composicion del ticket: convierte una venta en una lista de renglones con formato.

Es logica pura (sin hardware), asi se prueba sin impresora y el mismo
resultado sirve al modo `mock` (texto) y al modo `escpos` (con estilos).
"""

import textwrap
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal
from zoneinfo import ZoneInfo

from app.schemas import TicketIn

ETIQUETAS_METODO_PAGO = {
    "efectivo": "Efectivo",
    "tarjeta": "Tarjeta",
    "transferencia": "Transferencia",
}

ETIQUETAS_PLATAFORMA = {
    "nequi": "Nequi",
    "daviplata": "Daviplata",
}


@dataclass(frozen=True)
class Renglon:
    """Un renglon del ticket, con su estilo.

    Attributes:
        texto: Contenido ya ajustado al ancho del papel.
        alineacion: `izquierda` o `centro` (el texto ya viene relleno si
            es `izquierda`; `centro` lo centra la impresora).
        negrita: Imprimir en negrita.
        doble: Imprimir al doble de tamano (para el total).
    """

    texto: str
    alineacion: Literal["izquierda", "centro"] = "izquierda"
    negrita: bool = False
    doble: bool = False


def formatear_pesos(valor: Decimal) -> str:
    """Formatea un monto como pesos colombianos, sin decimales (ej. 25000 -> "$25.000").

    Args:
        valor: Monto a formatear.

    Returns:
        str: El monto con separador de miles `.`.
    """
    entero = int(valor.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return f"${entero:,}".replace(",", ".")


def formatear_pesos_con_signo(valor: Decimal) -> str:
    """Formatea un monto con signo explicito (ej. -20 -> "-$20", 30 -> "+$30").

    Args:
        valor: Monto a formatear.

    Returns:
        str: El monto en pesos precedido de `+` o `-`.
    """
    return ("-" if valor < 0 else "+") + formatear_pesos(abs(valor))


def _dos_columnas(izquierda: str, derecha: str, ancho: int) -> str:
    """Alinea `izquierda` a la izquierda y `derecha` al borde derecho de la linea.

    Args:
        izquierda: Texto del lado izquierdo.
        derecha: Texto del lado derecho.
        ancho: Ancho total en caracteres.

    Returns:
        str: La linea completa; si no caben ambos, se separan con un espacio.
    """
    espacios = max(1, ancho - len(izquierda) - len(derecha))
    return f"{izquierda}{' ' * espacios}{derecha}"


def construir_renglones(
    ticket: TicketIn,
    *,
    ancho: int,
    nombre_negocio: str,
    pie: str,
    zona_horaria: str,
    nit: str = "",
    direccion: str = "",
    telefono: str = "",
) -> list[Renglon]:
    """Arma el ticket completo como una lista de renglones.

    Args:
        ticket: Venta a imprimir.
        ancho: Caracteres por linea del papel.
        nombre_negocio: Nombre/razon social, primera linea del encabezado.
        pie: Mensaje final.
        zona_horaria: Zona horaria para mostrar la fecha.
        nit: NIT del negocio, segunda linea del encabezado. Si viene
            vacio, no se imprime esa linea.
        direccion: Direccion del negocio, tercera linea del encabezado.
            Si viene vacia, no se imprime esa linea.
        telefono: Telefono del negocio, cuarta linea del encabezado. Si
            viene vacio, no se imprime esa linea.

    Returns:
        list[Renglon]: Los renglones en orden de impresion.
    """
    fecha_local = ticket.fecha.astimezone(ZoneInfo(zona_horaria))
    separador = "-" * ancho
    # Una venta hecha sin conexion aun no tiene numero del servidor: se imprime su referencia local.
    etiqueta_venta = f"Venta #{ticket.venta_id}" if ticket.venta_id is not None else f"Venta {ticket.referencia}"

    renglones = [Renglon(nombre_negocio, "centro", negrita=True)]
    if nit:
        renglones.append(Renglon(nit, "centro"))
    if direccion:
        renglones.append(Renglon(direccion, "centro"))
    if telefono:
        renglones.append(Renglon(telefono, "centro"))
    renglones += [
        Renglon(separador),
        Renglon(_dos_columnas(etiqueta_venta, fecha_local.strftime("%d/%m/%Y %H:%M"), ancho)),
    ]
    if ticket.vendedor:
        for parte in textwrap.wrap(f"Atendió: {ticket.vendedor}", ancho):
            renglones.append(Renglon(parte))
    if not ticket.pagos and ticket.metodo_pago:
        # Formato anterior al Adendo v2: un solo metodo, en el encabezado.
        renglones.append(Renglon(f"Pago: {_etiqueta_metodo(ticket.metodo_pago)}"))
    renglones.append(Renglon(separador))

    for linea in ticket.lineas:
        for parte in textwrap.wrap(linea.nombre_producto, ancho) or [linea.nombre_producto]:
            renglones.append(Renglon(parte))
        detalle = f"  {linea.cantidad} x {formatear_pesos(linea.precio_unitario)}"
        renglones.append(Renglon(_dos_columnas(detalle, formatear_pesos(linea.subtotal), ancho)))

    renglones.append(Renglon(separador))

    # Orden del Adendo v2: subtotal -> descuento -> ajuste por redondeo -> total. El subtotal,
    # el descuento y el ajuste solo se anotan cuando la venta los tuvo. En el formato anterior
    # el ajuste se deduce del total menos la suma de las lineas.
    subtotal = ticket.subtotal
    if subtotal is None:
        subtotal = sum((linea.subtotal for linea in ticket.lineas), Decimal("0"))
    ajuste = ticket.ajuste_redondeo
    if ajuste is None:
        ajuste = ticket.total - subtotal + ticket.descuento_monto
    hay_descuento = _redondear(ticket.descuento_monto) != 0
    hay_ajuste = _redondear(ajuste) != 0
    if hay_descuento or hay_ajuste:
        renglones.append(Renglon(_dos_columnas("Subtotal", formatear_pesos(subtotal), ancho)))
    if hay_descuento:
        renglones.append(
            Renglon(_dos_columnas(_etiqueta_descuento(ticket), "-" + formatear_pesos(ticket.descuento_monto), ancho))
        )
    if hay_ajuste:
        renglones.append(Renglon(_dos_columnas("Ajuste por redondeo", formatear_pesos_con_signo(ajuste), ancho)))

    renglones.append(
        Renglon(_dos_columnas("TOTAL", formatear_pesos(ticket.total), ancho), negrita=True, doble=True)
    )

    if ticket.pagos:
        renglones.append(Renglon(separador))
        for pago in ticket.pagos:
            etiqueta = f"Pago: {_etiqueta_metodo(pago.metodo_pago)}"
            if pago.plataforma:
                etiqueta += f" ({ETIQUETAS_PLATAFORMA.get(pago.plataforma, pago.plataforma.capitalize())})"
            renglones.append(Renglon(_dos_columnas(etiqueta, formatear_pesos(pago.monto), ancho)))
            if pago.monto_recibido is not None:
                renglones += [
                    Renglon(_dos_columnas("  Recibido", formatear_pesos(pago.monto_recibido), ancho)),
                    Renglon(_dos_columnas("  Vueltas", formatear_pesos(pago.vueltas), ancho)),
                ]

    renglones += [
        Renglon(""),
        Renglon(pie, "centro"),
    ]
    return renglones


def _redondear(valor: Decimal) -> Decimal:
    """Redondea a pesos enteros para decidir si un monto se imprime."""
    return valor.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _etiqueta_metodo(metodo: str) -> str:
    """Etiqueta legible de un metodo de pago (ej. "efectivo" -> "Efectivo")."""
    return ETIQUETAS_METODO_PAGO.get(metodo, metodo.capitalize())


def _etiqueta_descuento(ticket: TicketIn) -> str:
    """Texto del renglon del descuento (ej. "Descuento (10 %)" o "Descuento")."""
    if ticket.descuento_tipo == "porcentaje" and ticket.descuento_valor is not None:
        porcentaje = f"{ticket.descuento_valor.normalize():f}".replace(".", ",")
        return f"Descuento ({porcentaje} %)"
    return "Descuento"


def a_texto(renglones: list[Renglon], ancho: int) -> str:
    """Renderiza los renglones como texto plano (modo `mock` y pruebas).

    Args:
        renglones: Renglones del ticket.
        ancho: Caracteres por linea, usado para centrar.

    Returns:
        str: El ticket como texto multilinea.
    """
    lineas = [r.texto.center(ancho).rstrip() if r.alineacion == "centro" else r.texto for r in renglones]
    return "\n".join(lineas) + "\n"
