"""Router de la bandeja de notificaciones del Dashboard (Adendo v2, mejora B1: RF-043, HU-10).

Muestra las notificaciones que la tarea programada `alertas.revisar_stock_bajo`
guarda en la tabla `notificaciones` y permite marcarlas como leidas (solo
cambia la columna `leida`; no hay cambios de esquema). Solo propietario y
administrador: el vendedor recibe 403.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, update
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import requerir_roles
from app.models.notificacion import Notificacion
from app.models.producto import Producto
from app.models.usuario import RolUsuario, Usuario
from app.schemas.notificacion import BandejaOut, LeerTodasOut, NotificacionOut

router = APIRouter(prefix="/notificaciones", tags=["notificaciones"])

LIMITE_POR_DEFECTO = 50
LIMITE_MAXIMO = 200

_propietario_o_admin = requerir_roles(RolUsuario.PROPIETARIO, RolUsuario.ADMINISTRADOR)


def _a_salida(notificacion: Notificacion, producto_nombre: str | None) -> NotificacionOut:
    """Convierte una notificacion y el nombre de su producto en el esquema de salida.

    Args:
        notificacion: La notificacion de la base de datos.
        producto_nombre: Nombre del producto asociado, o None si ya no existe.

    Returns:
        NotificacionOut: La notificacion lista para responder.
    """
    return NotificacionOut(
        id=notificacion.id,
        tipo=notificacion.tipo,
        mensaje=notificacion.mensaje,
        leida=notificacion.leida,
        creada_en=notificacion.creada_en,
        producto_id=notificacion.producto_id,
        producto_nombre=producto_nombre,
    )


@router.get("", response_model=BandejaOut)
def listar_notificaciones(
    solo_no_leidas: bool = Query(False, description="Devolver solo las que no se han leido."),
    limite: int = Query(LIMITE_POR_DEFECTO, ge=1, le=LIMITE_MAXIMO),
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(_propietario_o_admin),
) -> BandejaOut:
    """Bandeja del Dashboard: notificaciones de la mas reciente a la mas antigua y contador de no leidas.

    Args:
        solo_no_leidas: Si es True, omite las ya leidas.
        limite: Maximo de notificaciones a devolver (1 a `LIMITE_MAXIMO`).
        db: Sesion de base de datos inyectada.
        _usuario: Usuario autenticado (PROPIETARIO o ADMINISTRADOR).

    Returns:
        BandejaOut: El contador de no leidas y las notificaciones pedidas.
    """
    no_leidas = db.query(func.count(Notificacion.id)).filter(Notificacion.leida.is_(False)).scalar()

    consulta = db.query(Notificacion, Producto.nombre).outerjoin(Producto, Producto.id == Notificacion.producto_id)
    if solo_no_leidas:
        consulta = consulta.filter(Notificacion.leida.is_(False))
    filas = consulta.order_by(Notificacion.creada_en.desc(), Notificacion.id.desc()).limit(limite).all()

    return BandejaOut(
        no_leidas=no_leidas,
        notificaciones=[_a_salida(notificacion, nombre) for notificacion, nombre in filas],
    )


@router.patch("/leer-todas", response_model=LeerTodasOut)
def leer_todas(
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(_propietario_o_admin),
) -> LeerTodasOut:
    """Marca como leidas todas las notificaciones pendientes.

    Args:
        db: Sesion de base de datos inyectada.
        _usuario: Usuario autenticado (PROPIETARIO o ADMINISTRADOR).

    Returns:
        LeerTodasOut: Cuantas notificaciones se marcaron.
    """
    resultado = db.execute(
        update(Notificacion).where(Notificacion.leida.is_(False)).values(leida=True)
    )
    db.commit()
    return LeerTodasOut(marcadas=resultado.rowcount)


@router.patch("/{notificacion_id}/leida", response_model=NotificacionOut)
def marcar_leida(
    notificacion_id: int,
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(_propietario_o_admin),
) -> NotificacionOut:
    """Marca una notificacion como leida. Si ya lo estaba, no cambia nada y responde igual.

    Args:
        notificacion_id: Id de la notificacion.
        db: Sesion de base de datos inyectada.
        _usuario: Usuario autenticado (PROPIETARIO o ADMINISTRADOR).

    Returns:
        NotificacionOut: La notificacion ya marcada.

    Raises:
        HTTPException: 404 si la notificacion no existe.
    """
    notificacion = db.get(Notificacion, notificacion_id)
    if notificacion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"La notificacion con id={notificacion_id} no existe.",
        )

    if not notificacion.leida:
        notificacion.leida = True
        db.commit()
        db.refresh(notificacion)

    producto_nombre = notificacion.producto.nombre if notificacion.producto is not None else None
    return _a_salida(notificacion, producto_nombre)
