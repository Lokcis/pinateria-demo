"""Router de la caja y el corte de caja (Adendo v3, Fase G2: RF-069 a RF-074, HU-13).

Permisos (docs/12, seccion 4): el administrador y el vendedor abren, mueven y cierran la caja; el propietario solo
consulta. El historial de cortes lo ven todos, pero un vendedor solo los que abrio o cerro el; exportarlo es del
administrador y el propietario. Las reglas del efectivo esperado y de la foto del corte viven en
`services/caja.py`; aqui se valida el rol de cada ruta.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import requerir_roles
from app.models.usuario import RolUsuario, Usuario
from app.schemas.caja import (
    AbrirCajaIn,
    CajaActualOut,
    CerrarCajaIn,
    CorteCajaDetalleOut,
    CorteCajaOut,
    MovimientoCajaIn,
)
from app.services import caja as servicio
from app.services.exceptions import CajaConflictoError, CajaInvalidaError, CorteNoEncontradoError

router = APIRouter(prefix="/caja", tags=["caja"])

TAMANO_PAGINA_MAXIMO = 200

_todos = requerir_roles(RolUsuario.ADMINISTRADOR, RolUsuario.VENDEDOR, RolUsuario.PROPIETARIO)
_escritura = requerir_roles(RolUsuario.ADMINISTRADOR, RolUsuario.VENDEDOR)
_consulta_del_negocio = requerir_roles(RolUsuario.ADMINISTRADOR, RolUsuario.PROPIETARIO)

_ESTADO_HTTP = {
    CorteNoEncontradoError: status.HTTP_404_NOT_FOUND,
    CajaInvalidaError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    CajaConflictoError: status.HTTP_409_CONFLICT,
}


@contextmanager
def _errores_de_dominio(db: Session) -> Iterator[None]:
    """Revierte la transaccion y traduce los errores de dominio de la caja a su codigo HTTP.

    Args:
        db: Sesion cuya transaccion se revierte ante un error.

    Raises:
        HTTPException: 404 (corte inexistente o ajeno), 409 (estado de la caja) o 422 (monto invalido).
    """
    try:
        yield
    except tuple(_ESTADO_HTTP) as exc:
        db.rollback()
        raise HTTPException(status_code=_ESTADO_HTTP[type(exc)], detail=str(exc)) from exc


def _validar_rango(desde: date | None, hasta: date | None) -> None:
    """Valida que el rango del historial no este invertido.

    Raises:
        HTTPException: 422 si `desde` es posterior a `hasta`.
    """
    if desde is not None and hasta is not None and desde > hasta:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "La fecha inicial no puede ser posterior a la final.")


@router.get("/actual", response_model=CajaActualOut)
def caja_actual(
    db: Session = Depends(get_db),
    _usuario: Usuario = Depends(_todos),
):
    """Estado de la caja y, si esta abierta, el efectivo esperado en vivo con su desglose (RF-070).

    Args:
        db: Sesion de base de datos inyectada.
        _usuario: Administrador, vendedor o propietario.

    Returns:
        CajaActualOut: Estado, cifras y movimientos del corte abierto.
    """
    return servicio.caja_actual(db)


@router.post("/abrir", response_model=CajaActualOut, status_code=status.HTTP_201_CREATED)
def abrir_caja(
    payload: AbrirCajaIn,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(_escritura),
):
    """Abre la caja con la base indicada (RF-069). Administrador y vendedor; el propietario recibe 403.

    Args:
        payload: Base inicial (multiplo de $50).
        db: Sesion de base de datos inyectada.
        usuario_actual: Administrador o vendedor, registrado como quien la abre.

    Returns:
        CajaActualOut: La caja ya abierta.

    Raises:
        HTTPException: 409 si ya hay una caja abierta; 422 si la base no es multiplo de $50.
    """
    with _errores_de_dominio(db):
        servicio.abrir_caja(db, usuario_actual, payload.base_inicial)
    db.commit()
    return servicio.caja_actual(db)


@router.post("/movimientos", response_model=CajaActualOut, status_code=status.HTTP_201_CREATED)
def registrar_movimiento(
    payload: MovimientoCajaIn,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(_escritura),
):
    """Registra un ingreso o retiro manual en la caja abierta (RF-071). Administrador y vendedor.

    Args:
        payload: Tipo, monto (multiplo de $50) y motivo.
        db: Sesion de base de datos inyectada.
        usuario_actual: Administrador o vendedor.

    Returns:
        CajaActualOut: La caja con el efectivo esperado ya actualizado.

    Raises:
        HTTPException: 409 si no hay una caja abierta; 422 si el monto no es multiplo de $50.
    """
    with _errores_de_dominio(db):
        servicio.registrar_movimiento(db, usuario_actual, payload)
    db.commit()
    return servicio.caja_actual(db)


@router.post("/cerrar", response_model=CorteCajaDetalleOut)
def cerrar_caja(
    payload: CerrarCajaIn,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(_escritura),
):
    """Cierra la caja: calcula la diferencia con lo contado y guarda la foto del corte (RF-072).

    Administrador y vendedor. El cierre no se repite ni se edita. El POS no deja cerrar si el equipo tiene
    ventas guardadas sin enviar (lo valida la pantalla).

    Args:
        payload: Efectivo contado (multiplo de $50) y observaciones.
        db: Sesion de base de datos inyectada.
        usuario_actual: Administrador o vendedor, registrado como quien la cierra.

    Returns:
        CorteCajaDetalleOut: La ficha del corte recien cerrado.

    Raises:
        HTTPException: 409 si no hay una caja abierta; 422 si lo contado no es multiplo de $50.
    """
    with _errores_de_dominio(db):
        corte = servicio.cerrar_caja(db, usuario_actual, payload)
    db.commit()
    return servicio.obtener_corte(db, usuario_actual, corte.id)


@router.get("/cortes", response_model=list[CorteCajaOut])
def listar_cortes(
    desde: date | None = Query(None, description="Primer dia (por fecha de apertura)."),
    hasta: date | None = Query(None, description="Ultimo dia (por fecha de apertura)."),
    pagina: int = Query(1, ge=1),
    tamano_pagina: int = Query(30, ge=1, le=TAMANO_PAGINA_MAXIMO),
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(_todos),
):
    """Historial de cortes, del mas reciente al mas antiguo (RF-073).

    Un vendedor solo ve los cortes que abrio o cerro el.

    Args:
        desde: Primer dia del rango.
        hasta: Ultimo dia del rango.
        pagina: Numero de pagina (base 1).
        tamano_pagina: Tamano de pagina.
        db: Sesion de base de datos inyectada.
        usuario_actual: Usuario autenticado.

    Returns:
        list[CorteCajaOut]: Las filas de la pagina.

    Raises:
        HTTPException: 422 si el rango esta invertido.
    """
    _validar_rango(desde, hasta)
    return servicio.listar_cortes(
        db, usuario_actual, desde, hasta, limite=tamano_pagina, desplazamiento=(pagina - 1) * tamano_pagina
    )


@router.get("/cortes/exportar")
def exportar_cortes(
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(_consulta_del_negocio),
) -> Response:
    """Descarga un CSV (abre en Excel) con una fila por corte cerrado del rango (RF-073).

    Administrador y propietario; el vendedor recibe 403. Va ANTES de `/cortes/{corte_id}` para que
    "exportar" no se lea como un id.

    Args:
        desde: Primer dia del rango (por apertura).
        hasta: Ultimo dia del rango (por apertura).
        db: Sesion de base de datos inyectada.
        usuario_actual: Administrador o propietario.

    Returns:
        Response: El archivo CSV (UTF-8 con BOM, separado por punto y coma).

    Raises:
        HTTPException: 422 si el rango esta invertido.
    """
    _validar_rango(desde, hasta)
    contenido = servicio.exportar_cortes_csv(db, usuario_actual, desde, hasta)
    if desde is not None and hasta is not None:
        nombre = f"cortes_de_caja_{desde.isoformat()}_a_{hasta.isoformat()}.csv"
    else:
        nombre = "cortes_de_caja.csv"
    return Response(
        content=contenido.encode("utf-8"),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/cortes/{corte_id}", response_model=CorteCajaDetalleOut)
def obtener_corte(
    corte_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(_todos),
):
    """Ficha de un corte: la foto de sus cifras, sus movimientos y el aviso de ventas enviadas despues del cierre.

    Args:
        corte_id: Id del corte.
        db: Sesion de base de datos inyectada.
        usuario_actual: Usuario autenticado; un vendedor solo ve los suyos.

    Returns:
        CorteCajaDetalleOut: La ficha.

    Raises:
        HTTPException: 404 si no existe o, para un vendedor, no lo abrio ni lo cerro el.
    """
    with _errores_de_dominio(db):
        return servicio.obtener_corte(db, usuario_actual, corte_id)
