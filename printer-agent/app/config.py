"""Configuracion del agente de impresion, cargada desde variables de entorno.

Todas las variables tienen el prefijo `AGENTE_` (ver `.env.example`).
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuracion del agente.

    Attributes:
        modo: `mock` escribe el ticket en consola y en un archivo de texto
            (para desarrollar sin impresora); `escpos` imprime de verdad
            en la Epson TM-T20II.
        host: Interfaz donde escucha. Debe ser `127.0.0.1`: el agente solo
            debe ser accesible desde el propio equipo POS.
        puerto: Puerto de escucha (el frontend usa `VITE_PRINTER_AGENT_URL`).
        origenes_permitidos: Origenes web autorizados por CORS, separados
            por comas (el POS en desarrollo y, en produccion, el dominio
            publico del sistema).
        nombre_negocio: Primera linea del encabezado del ticket (razon social).
        nit_negocio: Segunda linea del encabezado (NIT). Vacio para omitirla.
        direccion_negocio: Tercera linea del encabezado (direccion). Vacio
            para omitirla.
        telefono_negocio: Cuarta linea del encabezado (telefono). Vacio
            para omitirla.
        pie_ticket: Linea final del ticket.
        ancho_columnas: Caracteres por linea (48 en la TM-T20II de 80 mm
            con la fuente A; bajar a 42 si el texto se corta).
        carpeta_mock: Donde el modo `mock` guarda los tickets como .txt.
        usb_vendor_id: Vendor ID USB de la impresora (Epson = 0x04b8).
        usb_product_id: Product ID USB (TM-T20II = 0x0e15).
        impresora_windows: Nombre de la impresora instalada en Windows. Si
            se define, `escpos` imprime por el spooler de Windows (RAW) en
            vez de hablar directo por USB; es la opcion mas simple en un
            PC con Windows y el driver de Epson instalado.
        zona_horaria: Zona horaria para la fecha impresa en el ticket.
        logo_ticket: Ruta del logo en blanco y negro que se imprime arriba del ticket (relativa a la carpeta
            del agente, o absoluta). Vacio para no imprimir logo. Si el archivo falta o no se puede imprimir,
            el ticket sale igual, sin logo.
    """

    model_config = SettingsConfigDict(
        env_prefix="AGENTE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    modo: Literal["mock", "escpos"] = "mock"
    host: str = "127.0.0.1"
    puerto: int = 9100
    origenes_permitidos: str = "http://localhost:5173,http://127.0.0.1:5173"
    nombre_negocio: str = "PIÑATERIA DEMO"
    nit_negocio: str = "NIT: 900.000.000 - 0"
    direccion_negocio: str = "CALLE 123 # 45-67 BARRIO DEMO"
    telefono_negocio: str = "Tel: 3000000000"
    pie_ticket: str = "¡Gracias por tu compra!"
    ancho_columnas: int = 48
    carpeta_mock: str = "tickets_mock"
    usb_vendor_id: int = 0x04B8
    usb_product_id: int = 0x0E15
    impresora_windows: str | None = None
    zona_horaria: str = "America/Bogota"
    logo_ticket: str = "assets/logo-ticket.png"


@lru_cache
def get_settings() -> Settings:
    """Retorna la configuracion, leida una sola vez por proceso.

    Returns:
        Settings: La configuracion validada del agente.
    """
    return Settings()
