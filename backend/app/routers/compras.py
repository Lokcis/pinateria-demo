"""Router de compras a proveedores: ordenes, recepcion de mercancia e historial (RF-010, RF-011, RF-012).

Las compras exponen costos pactados con proveedores, por lo que quedan
restringidas al rol Administrador, igual que el directorio (HU-04).
"""

from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import requerir_roles
from app.models.compra import Compra, EstadoCompra
from app.models.detalle_compra import DetalleCompra
from app.models.usuario import RolUsuario, Usuario
from app.schemas.compra import CompraIn, CompraOut, RecibirCompraIn
from app.services.compras import cancelar_compra, crear_compra, recibir_compra
from app.services.exceptions import (
    CompraNoEncontradaError,
    EstadoCompraInvalidoError,
    ProductoNoEncontradoError,
    ProveedorNoEncontradoError,
)

router = APIRouter(prefix="/compras", tags=["compras"])

TAMANO_PAGINA_MAXIMO = 100


def _consulta_completa(db: Session):
    """Consulta base de compras con proveedor y detalles precargados para serializar."""
    return db.query(Compra).options(
        joinedload(Compra.proveedor),
        joinedload(Compra.detalles).joinedload(DetalleCompra.producto),
    )


def _transicion(db: Session, compra_id: int, operacion: Callable[[Session, int], Compra]) -> Compra:
    """Ejecuta una transicion de estado de forma atomica y traduce errores a HTTP.

    Args:
        db: Sesion de base de datos.
        compra_id: Compra a transicionar.
        operacion: Funcion del servicio (`recibir_compra` o `cancelar_compra`).

    Returns:
        Compra: La compra actualizada, ya commiteada.

    Raises:
        HTTPException: 404 si la compra no existe; 409 si no esta pendiente.
    """
    try:
        operacion(db, compra_id)
        db.commit()
    except CompraNoEncontradaError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except EstadoCompraInvalidoError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _consulta_completa(db).filter(Compra.id == compra_id).one()


@router.post("", response_model=CompraOut, status_code=status.HTTP_201_CREATED)
def registrar_compra(
    payload: CompraIn,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(requerir_roles(RolUsuario.ADMINISTRADOR)),
) -> Compra:
    """Registra una orden de compra en estado `pendiente`; no mueve stock (RF-010).

    Args:
        payload: Proveedor y lineas de la orden.
        db: Sesion de base de datos inyectada.
        usuario_actual: Administrador autenticado, registrado como autor.

    Returns:
        CompraOut: La orden creada con su total calculado.

    Raises:
        HTTPException: 404 si el proveedor o algun producto no existe.
    """
    try:
        compra = crear_compra(
            db,
            proveedor_id=payload.proveedor_id,
            usuario_id=usuario_actual.id,
            lineas=[(d.producto_id, d.cantidad, d.costo_unitario) for d in payload.detalles],
        )
        db.commit()
    except (ProveedorNoEncontradoError, ProductoNoEncontradoError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _consulta_completa(db).filter(Compra.id == compra.id).one()


@router.get("", response_model=list[CompraOut])
def listar_compras(
    proveedor_id: int | None = Query(None, description="Historial de un proveedor."),
    producto_id: int | None = Query(None, description="Historial de compras que incluyen un producto."),
    estado: EstadoCompra | None = Query(None),
    pagina: int = Query(1, ge=1),
    tamano_pagina: int = Query(20, ge=1, le=TAMANO_PAGINA_MAXIMO),
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(requerir_roles(RolUsuario.ADMINISTRADOR)),
) -> list[Compra]:
    """Lista compras, de la mas reciente a la mas antigua, con filtros (RF-012).

    Args:
        proveedor_id: Filtra por proveedor (historial por proveedor).
        producto_id: Filtra compras que incluyen el producto (historial por producto).
        estado: Filtra por estado.
        pagina: Numero de pagina (base 1).
        tamano_pagina: Tamano de pagina.
        db: Sesion de base de datos inyectada.
        usuario_actual: Administrador autenticado.

    Returns:
        list[CompraOut]: Las compras de la pagina solicitada.
    """
    consulta = db.query(Compra.id)
    if proveedor_id is not None:
        consulta = consulta.filter(Compra.proveedor_id == proveedor_id)
    if producto_id is not None:
        consulta = consulta.filter(Compra.detalles.any(DetalleCompra.producto_id == producto_id))
    if estado is not None:
        consulta = consulta.filter(Compra.estado == estado)

    # Se pagina primero sobre ids y luego se cargan las compras con sus lineas:
    # el JOIN a `detalles` multiplicaria filas y LIMIT contaria lineas, no compras.
    ids = (
        consulta.order_by(Compra.fecha.desc(), Compra.id.desc())
        .offset((pagina - 1) * tamano_pagina)
        .limit(tamano_pagina)
        .all()
    )
    orden = [fila_id for (fila_id,) in ids]
    if not orden:
        return []
    compras = {c.id: c for c in _consulta_completa(db).filter(Compra.id.in_(orden)).all()}
    return [compras[compra_id] for compra_id in orden]


@router.get("/{compra_id}", response_model=CompraOut)
def obtener_compra(
    compra_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(requerir_roles(RolUsuario.ADMINISTRADOR)),
) -> Compra:
    """Devuelve una compra con sus lineas.

    Args:
        compra_id: Id de la compra.
        db: Sesion de base de datos inyectada.
        usuario_actual: Administrador autenticado.

    Returns:
        CompraOut: La compra.

    Raises:
        HTTPException: 404 si no existe.
    """
    compra = _consulta_completa(db).filter(Compra.id == compra_id).one_or_none()
    if compra is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"La compra con id={compra_id} no existe."
        )
    return compra


@router.patch("/{compra_id}/recibir", response_model=CompraOut)
def marcar_compra_recibida(
    compra_id: int,
    payload: RecibirCompraIn,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(requerir_roles(RolUsuario.ADMINISTRADOR)),
) -> Compra:
    """Marca la compra como recibida e incrementa el stock de cada producto (RF-011).

    Atomico: o se actualiza todo el stock y el estado, o nada. Pide la forma de pago de la compra (Adendo v3):
    la compra recibida cuenta como gasto en la ventana de Gastos.

    Args:
        compra_id: Compra a recibir.
        payload: Forma de pago (y plataforma si fue una transferencia).
        db: Sesion de base de datos inyectada.
        usuario_actual: Administrador autenticado.

    Returns:
        CompraOut: La compra ya recibida.

    Raises:
        HTTPException: 404 si no existe; 409 si ya fue recibida o cancelada.
    """
    return _transicion(
        db, compra_id, lambda sesion, id_compra: recibir_compra(sesion, id_compra, payload.metodo_pago, payload.plataforma)
    )


@router.patch("/{compra_id}/cancelar", response_model=CompraOut)
def marcar_compra_cancelada(
    compra_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(requerir_roles(RolUsuario.ADMINISTRADOR)),
) -> Compra:
    """Cancela una compra pendiente; no afecta el inventario.

    Args:
        compra_id: Compra a cancelar.
        db: Sesion de base de datos inyectada.
        usuario_actual: Administrador autenticado.

    Returns:
        CompraOut: La compra cancelada.

    Raises:
        HTTPException: 404 si no existe; 409 si ya fue recibida o cancelada.
    """
    return _transicion(db, compra_id, cancelar_compra)
