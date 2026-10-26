"""Backends de impresion: `mock` (archivo + consola) y `escpos` (Epson TM-T20II)."""

import logging
from pathlib import Path
from typing import Protocol

from app.config import Settings
from app.ticket import Renglon, a_texto

logger = logging.getLogger("printer-agent")

CARPETA_AGENTE = Path(__file__).resolve().parents[1]


def ruta_del_logo(logo_ticket: str) -> Path | None:
    """Resuelve el logo del ticket y comprueba que exista.

    Args:
        logo_ticket: Valor de `AGENTE_LOGO_TICKET` (relativo a la carpeta del agente, o absoluto; vacio = sin logo).

    Returns:
        Path | None: La ruta del archivo, o None si no hay logo configurado o el archivo no existe.
    """
    if not logo_ticket or not logo_ticket.strip():
        return None
    ruta = Path(logo_ticket.strip())
    if not ruta.is_absolute():
        ruta = CARPETA_AGENTE / ruta
    if not ruta.is_file():
        logger.warning("No se encontro el logo del ticket (%s): se imprime sin logo.", ruta)
        return None
    return ruta


class ErrorImpresion(Exception):
    """La impresora no pudo completar el trabajo (apagada, sin papel, desconectada...)."""


class Impresora(Protocol):
    """Contrato de un backend de impresion."""

    def imprimir(self, venta_id: int | str, renglones: list[Renglon]) -> None:
        """Imprime un ticket.

        Args:
            venta_id: Numero de venta, o referencia local si es una venta sin conexion (para nombrar archivos o registrar logs).
            renglones: Contenido del ticket.

        Raises:
            ErrorImpresion: Si no se pudo imprimir.
        """
        ...


class ImpresoraMock:
    """Simula la impresora: escribe el ticket en consola y en `tickets_mock/venta_N.txt`."""

    def __init__(self, carpeta: str, ancho: int, logo_ticket: str = "") -> None:
        """Crea el backend mock.

        Args:
            carpeta: Carpeta donde guardar los tickets como texto.
            ancho: Caracteres por linea.
            logo_ticket: Logo configurado; si existe, el ticket de prueba lo anota con una linea `[LOGO]`.
        """
        self._carpeta = Path(carpeta)
        self._ancho = ancho
        self._logo = ruta_del_logo(logo_ticket)

    def imprimir(self, venta_id: int | str, renglones: list[Renglon]) -> None:
        """Guarda y muestra el ticket.

        Args:
            venta_id: Numero de venta.
            renglones: Contenido del ticket.

        Raises:
            ErrorImpresion: Si no se puede escribir el archivo.
        """
        texto = a_texto(renglones, self._ancho)
        if self._logo is not None:
            texto = f"[LOGO {self._logo.name}]\n{texto}"
        try:
            self._carpeta.mkdir(parents=True, exist_ok=True)
            (self._carpeta / f"venta_{venta_id}.txt").write_text(texto, encoding="utf-8")
        except OSError as error:
            raise ErrorImpresion(f"No se pudo guardar el ticket de prueba: {error}") from error
        logger.info("Ticket (modo mock) de la venta #%s:\n%s", venta_id, texto)


class ImpresoraEscpos:
    """Imprime en una impresora termica ESC/POS (Epson TM-T20II) con `python-escpos`."""

    def __init__(self, settings: Settings) -> None:
        """Guarda la configuracion; la conexion se abre en cada impresion.

        Abrir y cerrar por trabajo evita quedarse con un handle USB muerto si
        la impresora se apaga o se desconecta entre ventas.

        Args:
            settings: Configuracion del agente.
        """
        self._settings = settings
        self._logo = ruta_del_logo(settings.logo_ticket)

    def _imprimir_logo(self, impresora) -> None:
        """Imprime el logo centrado arriba del ticket. Es best-effort: si falla, el ticket sigue sin logo.

        Args:
            impresora: La impresora ya abierta.
        """
        if self._logo is None:
            return
        try:
            impresora.set(align="center")
            impresora.image(str(self._logo), impl="bitImageRaster", center=True)
            impresora.ln(1)
        except Exception as error:  # noqa: BLE001 - un logo que falla no debe impedir el ticket
            logger.warning("No se pudo imprimir el logo del ticket (%s): sigue sin logo.", error)

    def _abrir(self):
        """Abre la conexion: spooler de Windows si se configuro un nombre, si no USB directo.

        Returns:
            escpos.escpos.Escpos: La impresora abierta.
        """
        try:
            if self._settings.impresora_windows:
                from escpos.printer import Win32Raw

                impresora = Win32Raw(self._settings.impresora_windows, profile="TM-T20II")
            else:
                from escpos.printer import Usb

                impresora = Usb(
                    self._settings.usb_vendor_id,
                    self._settings.usb_product_id,
                    profile="TM-T20II",
                )
        except ImportError as error:
            raise ErrorImpresion(
                "Falta la libreria de impresion (instala requirements.txt: python-escpos"
                " y, en Windows, pywin32)."
            ) from error
        return impresora

    def imprimir(self, venta_id: int | str, renglones: list[Renglon]) -> None:
        """Envia el ticket a la impresora y corta el papel.

        Args:
            venta_id: Numero de venta (solo para el log).
            renglones: Contenido del ticket.

        Raises:
            ErrorImpresion: Si la impresora no responde o falla al imprimir.
        """
        impresora = None
        try:
            impresora = self._abrir()
            self._imprimir_logo(impresora)
            for renglon in renglones:
                impresora.set(
                    align="center" if renglon.alineacion == "centro" else "left",
                    bold=renglon.negrita,
                    double_height=renglon.doble,
                    double_width=False,
                    font="a",
                )
                impresora.text(renglon.texto + "\n")
            impresora.ln(2)
            impresora.cut()
        except ErrorImpresion:
            raise
        except Exception as error:  # noqa: BLE001 - el hardware puede fallar de muchas formas
            raise ErrorImpresion(
                f"No se pudo imprimir en la Epson TM-T20II (¿encendida, con papel y conectada?): {error}"
            ) from error
        finally:
            if impresora is not None:
                try:
                    impresora.close()
                except Exception:  # noqa: BLE001
                    logger.warning("No se pudo cerrar limpiamente la conexion con la impresora.")
        logger.info("Ticket de la venta #%s impreso.", venta_id)


def crear_impresora(settings: Settings) -> Impresora:
    """Construye el backend de impresion segun `AGENTE_MODO`.

    Args:
        settings: Configuracion del agente.

    Returns:
        Impresora: `ImpresoraMock` o `ImpresoraEscpos`.
    """
    if settings.modo == "escpos":
        return ImpresoraEscpos(settings)
    return ImpresoraMock(settings.carpeta_mock, settings.ancho_columnas, settings.logo_ticket)
