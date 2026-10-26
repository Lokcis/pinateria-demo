"""Agente de impresion local del POS.

Corre en el equipo de la tienda (junto a la impresora USB), NUNCA en el
servidor remoto: el navegador del POS le envia el ticket por HTTP a
`127.0.0.1` y el agente lo imprime en la Epson TM-T20II.
"""

import inspect
import logging

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.impresoras import ErrorImpresion, Impresora, crear_impresora
from app.schemas import RespuestaImpresion, TicketIn
from app.ticket import construir_renglones

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

settings = get_settings()

app = FastAPI(title="Agente de impresión — Piñatería Demo", version="1.0.0")

# Starlette >= 1.0 rechaza (400) el preflight de Private Network Access salvo que se
# active `allow_private_network`; las versiones anteriores no tienen el parametro y
# se cubren con el middleware `permitir_red_privada` de abajo.
_opciones_pna = (
    {"allow_private_network": True}
    if "allow_private_network" in inspect.signature(CORSMiddleware.__init__).parameters
    else {}
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origen.strip() for origen in settings.origenes_permitidos.split(",") if origen.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    **_opciones_pna,
)


@app.middleware("http")
async def permitir_red_privada(request: Request, call_next):
    """Responde al preflight de Private Network Access de Chrome.

    Cuando el POS se sirve desde un dominio publico (HTTPS) y llama a
    `127.0.0.1`, Chrome exige `Access-Control-Allow-Private-Network: true`
    en la respuesta al preflight. Se registra despues de CORS para
    envolverlo y poder agregar el encabezado a su respuesta.

    Args:
        request: Peticion entrante.
        call_next: Siguiente manejador de la cadena.

    Returns:
        Response: La respuesta, con el encabezado extra si aplica.
    """
    respuesta = await call_next(request)
    if request.headers.get("access-control-request-private-network") == "true":
        respuesta.headers["Access-Control-Allow-Private-Network"] = "true"
    return respuesta


_impresora: Impresora | None = None


def obtener_impresora(config: Settings = Depends(get_settings)) -> Impresora:
    """Dependencia: devuelve el backend de impresion (uno por proceso).

    Args:
        config: Configuracion del agente.

    Returns:
        Impresora: El backend configurado.
    """
    global _impresora
    if _impresora is None:
        _impresora = crear_impresora(config)
    return _impresora


@app.get("/salud")
def salud(config: Settings = Depends(get_settings)) -> dict[str, str]:
    """Indica que el agente esta vivo y en que modo corre (para Uptime Kuma).

    Args:
        config: Configuracion del agente.

    Returns:
        dict[str, str]: `status` y `modo`.
    """
    return {"status": "ok", "modo": config.modo}


@app.post("/imprimir", response_model=RespuestaImpresion)
def imprimir(
    ticket: TicketIn,
    config: Settings = Depends(get_settings),
    impresora: Impresora = Depends(obtener_impresora),
) -> RespuestaImpresion:
    """Imprime el ticket de una venta ya confirmada.

    Args:
        ticket: Datos de la venta.
        config: Configuracion del agente.
        impresora: Backend de impresion.

    Returns:
        RespuestaImpresion: Confirmacion con el modo actual.

    Raises:
        HTTPException: 503 si la impresora no pudo imprimir (el mensaje llega
            al vendedor tal cual en el aviso del POS).
    """
    renglones = construir_renglones(
        ticket,
        ancho=config.ancho_columnas,
        nombre_negocio=config.nombre_negocio,
        pie=config.pie_ticket,
        zona_horaria=config.zona_horaria,
        nit=config.nit_negocio,
        direccion=config.direccion_negocio,
        telefono=config.telefono_negocio,
    )
    try:
        impresora.imprimir(ticket.identificador, renglones)
    except ErrorImpresion as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    return RespuestaImpresion(status="ok", modo=config.modo)
