"""Router de solicitudes de titulares de datos (Habeas Data), solo Administrador (HU-07, RF-035).

Bitacora de consultas y reclamos con su fecha limite legal. Al resolver una
supresion se anonimiza al cliente; al resolver una revocatoria se bloquea su
uso en ventas nuevas.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import requerir_roles
from app.models.cliente import Cliente, EstadoSolicitudTitular, SolicitudTitular, TipoSolicitudTitular
from app.models.usuario import RolUsuario, Usuario
from app.schemas.cliente import SolicitudActualizarIn, SolicitudCrearIn, SolicitudOut
from app.services.habeas_data import anonimizar_cliente, fecha_limite_solicitud, revocar_autorizacion

# Todo el router queda detras del rol Administrador: el vendedor recibe 403.
router = APIRouter(
    prefix="/solicitudes-titular",
    tags=["solicitudes-titular"],
    dependencies=[Depends(requerir_roles(RolUsuario.ADMINISTRADOR))],
)

_ESTADOS_FINALES = (EstadoSolicitudTitular.RESUELTA, EstadoSolicitudTitular.RECHAZADA)


def _a_salida(solicitud: SolicitudTitular) -> SolicitudOut:
    """Convierte una solicitud ORM en su esquema de salida, calculando si esta vencida."""
    hoy = datetime.now(ZoneInfo(settings.zona_horaria)).date()
    return SolicitudOut(
        id=solicitud.id,
        cliente_id=solicitud.cliente_id,
        cliente_nombre=solicitud.cliente.nombre,
        tipo=solicitud.tipo,
        descripcion=solicitud.descripcion,
        estado=solicitud.estado,
        recibida_en=solicitud.recibida_en,
        fecha_limite=solicitud.fecha_limite,
        vencida=solicitud.estado not in _ESTADOS_FINALES and solicitud.fecha_limite < hoy,
        resuelta_en=solicitud.resuelta_en,
        atendida_por=solicitud.atendida_por_usuario.nombre if solicitud.atendida_por_usuario else None,
        respuesta=solicitud.respuesta,
    )


def _obtener_o_404(db: Session, solicitud_id: int) -> SolicitudTitular:
    """Busca una solicitud por id (con cliente y responsable) o lanza 404."""
    solicitud = (
        db.query(SolicitudTitular)
        .options(joinedload(SolicitudTitular.cliente), joinedload(SolicitudTitular.atendida_por_usuario))
        .filter(SolicitudTitular.id == solicitud_id)
        .one_or_none()
    )
    if solicitud is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"La solicitud con id={solicitud_id} no existe."
        )
    return solicitud


@router.get("", response_model=list[SolicitudOut])
def listar_solicitudes(
    estado: EstadoSolicitudTitular | None = Query(None, description="Filtra por estado."),
    cliente_id: int | None = Query(None, description="Solo las solicitudes de este cliente."),
    pendientes: bool = Query(False, description="Solo las que aun no se resuelven ni rechazan."),
    db: Session = Depends(get_db),
) -> list[SolicitudOut]:
    """Lista las solicitudes, las mas urgentes primero (por fecha limite).

    Args:
        estado: Filtro por estado.
        cliente_id: Filtro por titular.
        pendientes: Excluye las resueltas y rechazadas.
        db: Sesion de base de datos inyectada.

    Returns:
        list[SolicitudOut]: Solicitudes ordenadas por fecha limite.
    """
    consulta = db.query(SolicitudTitular).options(
        joinedload(SolicitudTitular.cliente), joinedload(SolicitudTitular.atendida_por_usuario)
    )
    if estado is not None:
        consulta = consulta.filter(SolicitudTitular.estado == estado)
    if cliente_id is not None:
        consulta = consulta.filter(SolicitudTitular.cliente_id == cliente_id)
    if pendientes:
        consulta = consulta.filter(SolicitudTitular.estado.notin_(_ESTADOS_FINALES))
    solicitudes = consulta.order_by(SolicitudTitular.fecha_limite, SolicitudTitular.id).all()
    return [_a_salida(s) for s in solicitudes]


@router.post("", response_model=SolicitudOut, status_code=status.HTTP_201_CREATED)
def crear_solicitud(payload: SolicitudCrearIn, db: Session = Depends(get_db)) -> SolicitudOut:
    """Registra una solicitud de un titular y calcula su fecha limite legal.

    Consultas: 10 dias habiles. Actualizacion, supresion y revocatoria: 15.

    Args:
        payload: Titular, tipo y detalle.
        db: Sesion de base de datos inyectada.

    Returns:
        SolicitudOut: La solicitud registrada.

    Raises:
        HTTPException: 404 si el cliente no existe; 409 si ya esta anonimizado.
    """
    cliente = db.get(Cliente, payload.cliente_id)
    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"El cliente con id={payload.cliente_id} no existe."
        )
    if cliente.anonimizado_en is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El cliente ya fue anonimizado: no admite nuevas solicitudes."
        )
    hoy = datetime.now(ZoneInfo(settings.zona_horaria)).date()
    solicitud = SolicitudTitular(
        cliente_id=cliente.id,
        tipo=payload.tipo,
        descripcion=payload.descripcion,
        fecha_limite=fecha_limite_solicitud(payload.tipo, hoy),
    )
    db.add(solicitud)
    db.commit()
    return _a_salida(_obtener_o_404(db, solicitud.id))


@router.patch("/{solicitud_id}", response_model=SolicitudOut)
def actualizar_solicitud(
    solicitud_id: int,
    payload: SolicitudActualizarIn,
    db: Session = Depends(get_db),
    administrador: Usuario = Depends(requerir_roles(RolUsuario.ADMINISTRADOR)),
) -> SolicitudOut:
    """Avanza una solicitud: la pone en tramite, la resuelve o la rechaza.

    Al RESOLVER una supresion los datos personales del cliente quedan
    anonimizados (las ventas se conservan); al resolver una revocatoria queda
    revocada su autorizacion y deja de poder asociarse a ventas nuevas. Una
    solicitud resuelta o rechazada no se vuelve a abrir.

    Args:
        solicitud_id: Solicitud a atender.
        payload: Nuevo estado y respuesta.
        db: Sesion de base de datos inyectada.
        administrador: Administrador que la atiende.

    Returns:
        SolicitudOut: La solicitud actualizada.

    Raises:
        HTTPException: 404 si no existe; 409 si ya estaba resuelta o rechazada.
    """
    solicitud = _obtener_o_404(db, solicitud_id)
    if solicitud.estado in _ESTADOS_FINALES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="La solicitud ya fue cerrada y no se puede modificar."
        )

    ahora = datetime.now(ZoneInfo("UTC"))
    solicitud.estado = payload.estado
    solicitud.atendida_por = administrador.id
    if payload.respuesta is not None:
        solicitud.respuesta = payload.respuesta
    if payload.estado in _ESTADOS_FINALES:
        solicitud.resuelta_en = ahora
    if payload.estado == EstadoSolicitudTitular.RESUELTA:
        if solicitud.tipo == TipoSolicitudTitular.SUPRESION:
            anonimizar_cliente(solicitud.cliente, ahora)
        elif solicitud.tipo == TipoSolicitudTitular.REVOCATORIA:
            revocar_autorizacion(solicitud.cliente, ahora)
    db.commit()
    return _a_salida(_obtener_o_404(db, solicitud_id))
