"""Router de descuentos: descuento general y topes del descuento manual (Adendo v2, Fase A1, HU-06).

La configuracion la leen vendedor y administrador (el POS sugiere el descuento
general y muestra el limite vigente); solo el administrador la modifica
(RF-026, RF-042). El vendedor recibe 403 al intentar modificarla.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import requerir_roles
from app.models.descuento import DescuentoGeneral, TopeDescuento
from app.models.usuario import RolUsuario, Usuario
from app.schemas.descuento import (
    ConfiguracionDescuentosOut,
    DescuentoGeneralIn,
    DescuentoGeneralOut,
    TopesDescuentoIn,
    TopesDescuentoOut,
)
from app.services.calculo_venta import describir_topes

router = APIRouter(prefix="/descuentos", tags=["descuentos"])

_solo_administrador = requerir_roles(RolUsuario.ADMINISTRADOR)


def _configuracion(db: Session) -> ConfiguracionDescuentosOut:
    """Arma la configuracion vigente a partir de las tablas de una sola fila.

    Args:
        db: Sesion de base de datos.

    Returns:
        ConfiguracionDescuentosOut: Descuento general (o None) y topes (None = sin tope).
    """
    general = db.get(DescuentoGeneral, 1)
    topes = db.get(TopeDescuento, 1)
    tope_porcentaje = topes.tope_porcentaje if topes else None
    tope_monto = topes.tope_monto if topes else None
    return ConfiguracionDescuentosOut(
        general=(
            DescuentoGeneralOut(tipo=general.tipo, valor=general.valor, activo=general.activo) if general else None
        ),
        topes=TopesDescuentoOut(
            tope_porcentaje=tope_porcentaje,
            tope_monto=tope_monto,
            descripcion=describir_topes(tope_porcentaje, tope_monto),
        ),
    )


@router.get("/configuracion", response_model=ConfiguracionDescuentosOut)
def obtener_configuracion(
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(requerir_roles(RolUsuario.VENDEDOR, RolUsuario.ADMINISTRADOR)),
) -> ConfiguracionDescuentosOut:
    """Descuento general y topes del descuento manual vigentes.

    Args:
        db: Sesion de base de datos inyectada.
        _usuario: Usuario autenticado (VENDEDOR o ADMINISTRADOR).

    Returns:
        ConfiguracionDescuentosOut: La configuracion vigente.
    """
    return _configuracion(db)


@router.put("/general", response_model=ConfiguracionDescuentosOut)
def guardar_descuento_general(
    payload: DescuentoGeneralIn,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(_solo_administrador),
) -> ConfiguracionDescuentosOut:
    """Crea o modifica el descuento general (RF-026).

    Args:
        payload: Tipo, valor y si esta activo.
        db: Sesion de base de datos inyectada.
        usuario_actual: Administrador autenticado.

    Returns:
        ConfiguracionDescuentosOut: La configuracion ya actualizada.
    """
    general = db.get(DescuentoGeneral, 1) or DescuentoGeneral(id=1)
    general.tipo = payload.tipo
    general.valor = payload.valor
    general.activo = payload.activo
    general.actualizado_por = usuario_actual.id
    db.add(general)
    db.commit()
    return _configuracion(db)


@router.put("/topes", response_model=ConfiguracionDescuentosOut)
def guardar_topes(
    payload: TopesDescuentoIn,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(_solo_administrador),
) -> ConfiguracionDescuentosOut:
    """Crea o modifica los topes del descuento manual del vendedor (RF-042).

    Args:
        payload: Porcentaje maximo y monto maximo; None quita ese tope.
        db: Sesion de base de datos inyectada.
        usuario_actual: Administrador autenticado.

    Returns:
        ConfiguracionDescuentosOut: La configuracion ya actualizada.
    """
    topes = db.get(TopeDescuento, 1) or TopeDescuento(id=1)
    topes.tope_porcentaje = payload.tope_porcentaje
    topes.tope_monto = payload.tope_monto
    topes.actualizado_por = usuario_actual.id
    db.add(topes)
    db.commit()
    return _configuracion(db)
