"""Autorregistro de clientes por enlace publico (HU-07: RF-046 a RF-049).

Dos routers:

- `admin`: el administrador consulta, genera (o regenera), activa y desactiva el enlace.
- `publico`: los endpoints SIN sesion que usa el cliente desde su celular. Son los unicos de la API
  que no exigen JWT; los protege un codigo aleatorio, el limite de envios (Nginx y backend), un campo
  trampa y respuestas neutras que no revelan si el cliente ya existia.
"""

import secrets
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import requerir_roles
from app.models.cliente import Cliente, EnlaceAutoregistro, MedioAutorizacion, OrigenRegistro
from app.models.usuario import RolUsuario, Usuario
from app.schemas.cliente import (
    AutoregistroIn,
    AutoregistroOut,
    EnlaceAutoregistroEstadoIn,
    EnlaceAutoregistroOut,
    PoliticaOut,
)
from app.services import limite_envios
from app.services.politica_datos import (
    cargar_datos_negocio,
    construir_politica,
    datos_completos,
    faltantes,
    version_vigente,
)

admin = APIRouter(
    prefix="/autoregistro",
    tags=["autoregistro"],
    dependencies=[Depends(requerir_roles(RolUsuario.ADMINISTRADOR))],
)
publico = APIRouter(prefix="/publico", tags=["publico"])

_MSG_NO_DISPONIBLE = "Este enlace no está disponible. Pide uno nuevo en la tienda."
_MSG_GRACIAS = "Recibimos tu registro. ¡Gracias!"


def _a_salida(db: Session, enlace: EnlaceAutoregistro | None) -> EnlaceAutoregistroOut:
    """Convierte la fila del enlace (o su ausencia) en el esquema de salida."""
    datos = cargar_datos_negocio(db)
    return EnlaceAutoregistroOut(
        existe=enlace is not None,
        token=enlace.token if enlace else None,
        activo=bool(enlace.activo) if enlace else False,
        actualizado_en=enlace.actualizado_en if enlace else None,
        datos_completos=datos_completos(datos),
        faltantes=faltantes(datos),
    )


def _exigir_datos_completos(db: Session) -> None:
    """Lanza 409 si faltan datos del negocio: sin ellos el aviso de privacidad quedaria con huecos."""
    pendientes = faltantes(cargar_datos_negocio(db))
    if pendientes:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Faltan datos del negocio para publicar la política de datos: " + ", ".join(pendientes)
            + ". Complételos en \"Datos del negocio\".",
        )


@admin.get("/enlace", response_model=EnlaceAutoregistroOut)
def consultar_enlace(db: Session = Depends(get_db)) -> EnlaceAutoregistroOut:
    """Devuelve el estado del enlace de autorregistro (administrador).

    Args:
        db: Sesion de base de datos inyectada.

    Returns:
        EnlaceAutoregistroOut: Codigo, si esta activo y si la politica tiene todos sus datos.
    """
    return _a_salida(db, db.get(EnlaceAutoregistro, 1))


@admin.post("/enlace", response_model=EnlaceAutoregistroOut)
def generar_enlace(
    db: Session = Depends(get_db),
    administrador: Usuario = Depends(requerir_roles(RolUsuario.ADMINISTRADOR)),
) -> EnlaceAutoregistroOut:
    """Genera el enlace o lo regenera con un codigo nuevo y lo deja activo (RF-048).

    El enlace anterior deja de funcionar de inmediato.

    Args:
        db: Sesion de base de datos inyectada.
        administrador: Administrador que lo genera.

    Returns:
        EnlaceAutoregistroOut: El enlace nuevo.

    Raises:
        HTTPException: 409 si faltan datos del negocio en la politica.
    """
    _exigir_datos_completos(db)
    enlace = db.get(EnlaceAutoregistro, 1)
    if enlace is None:
        enlace = EnlaceAutoregistro(id=1)
        db.add(enlace)
    enlace.token = secrets.token_urlsafe(24)
    enlace.activo = True
    enlace.actualizado_por = administrador.id
    db.commit()
    db.refresh(enlace)
    return _a_salida(db, enlace)


@admin.patch("/enlace", response_model=EnlaceAutoregistroOut)
def cambiar_estado_enlace(
    payload: EnlaceAutoregistroEstadoIn,
    db: Session = Depends(get_db),
    administrador: Usuario = Depends(requerir_roles(RolUsuario.ADMINISTRADOR)),
) -> EnlaceAutoregistroOut:
    """Activa o desactiva el enlace sin cambiar su codigo (RF-048).

    Args:
        payload: Nuevo estado.
        db: Sesion de base de datos inyectada.
        administrador: Administrador que lo cambia.

    Returns:
        EnlaceAutoregistroOut: El enlace actualizado.

    Raises:
        HTTPException: 404 si aun no se genero; 409 si se quiere activar y faltan datos del negocio.
    """
    enlace = db.get(EnlaceAutoregistro, 1)
    if enlace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todavía no se ha generado el enlace.")
    if payload.activo:
        _exigir_datos_completos(db)
    enlace.activo = payload.activo
    enlace.actualizado_por = administrador.id
    db.commit()
    db.refresh(enlace)
    return _a_salida(db, enlace)


def _enlace_vigente(db: Session, token: str) -> EnlaceAutoregistro:
    """Busca el enlace por su codigo y verifica que se pueda usar.

    Args:
        db: Sesion de base de datos.
        token: Codigo recibido en la direccion publica.

    Returns:
        EnlaceAutoregistro: El enlace, si coincide, esta activo y la politica esta completa.

    Raises:
        HTTPException: 404 con un mensaje claro si el enlace no existe, esta desactivado,
            fue regenerado o la politica no esta completa.
    """
    enlace = db.get(EnlaceAutoregistro, 1)
    coincide = enlace is not None and secrets.compare_digest(enlace.token.encode(), token.encode())
    if not coincide or not enlace.activo or not datos_completos(cargar_datos_negocio(db)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_MSG_NO_DISPONIBLE)
    return enlace


def _identificador_visitante(solicitud: Request) -> str:
    """Identificador transitorio para el limite de envios (detras de Cloudflare y Nginx).

    Se usa solo en memoria y como hash; nunca se guarda con el cliente.
    """
    cabeceras = solicitud.headers
    return (
        cabeceras.get("cf-connecting-ip")
        or cabeceras.get("x-real-ip")
        or (solicitud.client.host if solicitud.client else "desconocido")
    )


@publico.get("/autoregistro/{token}", response_model=PoliticaOut)
def formulario_publico(token: str, db: Session = Depends(get_db)) -> dict:
    """Devuelve el aviso y la politica vigentes para mostrar en el formulario publico (sin sesion).

    Args:
        token: Codigo del enlace.
        db: Sesion de base de datos inyectada.

    Returns:
        PoliticaOut: Aviso de privacidad, casillas y politica completa.

    Raises:
        HTTPException: 404 si el enlace no esta disponible.
    """
    _enlace_vigente(db, token)
    return construir_politica(cargar_datos_negocio(db))


@publico.post("/autoregistro/{token}", response_model=AutoregistroOut, status_code=status.HTTP_201_CREATED)
def enviar_autoregistro(
    token: str, payload: AutoregistroIn, solicitud: Request, db: Session = Depends(get_db)
) -> AutoregistroOut:
    """Registra al cliente que llena el formulario publico (sin sesion).

    El cliente queda activo, sin descuento propio, con origen `autoregistro`, medio `electronico`, la fecha
    y la version de la politica vigente. No se guarda su direccion IP. La respuesta es la misma si ya existia
    un cliente con ese documento o telefono y no se revela ni modifica nada; lo mismo si llenaron el campo
    trampa (un robot).

    Args:
        token: Codigo del enlace.
        payload: Datos y aceptacion del cliente.
        solicitud: Peticion HTTP (solo para el limite de envios).
        db: Sesion de base de datos inyectada.

    Returns:
        AutoregistroOut: Mensaje neutro de agradecimiento.

    Raises:
        HTTPException: 429 si supero el limite de envios; 404 si el enlace no esta disponible.
    """
    if not limite_envios.registrar_intento(_identificador_visitante(solicitud)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Demasiados intentos. Inténtalo de nuevo más tarde."
        )
    _enlace_vigente(db, token)

    neutral = AutoregistroOut(mensaje=_MSG_GRACIAS)
    if payload.sitio_web.strip():
        return neutral  # un robot llenó el campo trampa: se ignora sin avisarle

    existentes = []
    if payload.documento:
        existentes.append(Cliente.documento == payload.documento)
    if payload.telefono:
        existentes.append(Cliente.telefono == payload.telefono)
    if existentes and db.query(Cliente.id).filter(or_(*existentes)).first() is not None:
        return neutral

    ahora = datetime.now(ZoneInfo("UTC"))
    db.add(
        Cliente(
            nombre=payload.nombre,
            documento=payload.documento,
            telefono=payload.telefono,
            email=payload.email,
            autorizacion_fecha=ahora,
            autorizacion_medio=MedioAutorizacion.ELECTRONICO,
            autorizacion_version=version_vigente(cargar_datos_negocio(db)),
            origen_registro=OrigenRegistro.AUTOREGISTRO,
            autorizacion_registrada_por=None,
            acepta_publicidad=payload.acepta_publicidad,
            publicidad_fecha=ahora if payload.acepta_publicidad else None,
        )
    )
    try:
        db.commit()
    except IntegrityError:  # dos envios simultaneos con el mismo documento
        db.rollback()
    return neutral
