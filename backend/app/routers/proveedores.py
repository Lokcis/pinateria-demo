"""Router de proveedores: directorio con CRUD completo, solo Administrador (RF-012, RF-021, HU-04)."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import requerir_roles
from app.models.proveedor import Proveedor
from app.models.usuario import RolUsuario
from app.schemas.proveedor import ProveedorCrearIn, ProveedorEditarIn, ProveedorOut

# Todo el router queda detras del rol Administrador (RF-021): un vendedor recibe 403 en cualquier ruta.
router = APIRouter(
    prefix="/proveedores",
    tags=["proveedores"],
    dependencies=[Depends(requerir_roles(RolUsuario.ADMINISTRADOR))],
)


def _obtener_o_404(db: Session, proveedor_id: int) -> Proveedor:
    """Busca un proveedor por id o lanza 404.

    Args:
        db: Sesion de base de datos.
        proveedor_id: Id del proveedor.

    Returns:
        Proveedor: El proveedor encontrado.

    Raises:
        HTTPException: 404 si no existe.
    """
    proveedor = db.query(Proveedor).filter(Proveedor.id == proveedor_id).one_or_none()
    if proveedor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El proveedor con id={proveedor_id} no existe.",
        )
    return proveedor


@router.post("", response_model=ProveedorOut, status_code=status.HTTP_201_CREATED)
def crear_proveedor(payload: ProveedorCrearIn, db: Session = Depends(get_db)) -> Proveedor:
    """Da de alta un proveedor en el directorio (RF-012).

    Args:
        payload: Datos del proveedor.
        db: Sesion de base de datos inyectada.

    Returns:
        ProveedorOut: El proveedor creado.
    """
    proveedor = Proveedor(**payload.model_dump())
    db.add(proveedor)
    db.commit()
    db.refresh(proveedor)
    return proveedor


@router.get("", response_model=list[ProveedorOut])
def listar_proveedores(
    q: str | None = Query(None, min_length=1, description="Filtro opcional por nombre de empresa o contacto."),
    db: Session = Depends(get_db),
) -> list[Proveedor]:
    """Lista el directorio de proveedores ordenado por nombre (RF-012).

    Args:
        q: Fragmento opcional del nombre de la empresa o del contacto.
        db: Sesion de base de datos inyectada.

    Returns:
        list[ProveedorOut]: Los proveedores que cumplen el filtro.
    """
    consulta = db.query(Proveedor)
    if q is not None:
        fragmento = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        consulta = consulta.filter(
            Proveedor.nombre_empresa.ilike(fragmento, escape="\\")
            | Proveedor.nombre_contacto.ilike(fragmento, escape="\\")
        )
    return consulta.order_by(Proveedor.nombre_empresa).all()


@router.get("/{proveedor_id}", response_model=ProveedorOut)
def obtener_proveedor(proveedor_id: int, db: Session = Depends(get_db)) -> Proveedor:
    """Devuelve un proveedor por id.

    Args:
        proveedor_id: Id del proveedor.
        db: Sesion de base de datos inyectada.

    Returns:
        ProveedorOut: El proveedor.

    Raises:
        HTTPException: 404 si no existe.
    """
    return _obtener_o_404(db, proveedor_id)


@router.patch("/{proveedor_id}", response_model=ProveedorOut)
def editar_proveedor(
    proveedor_id: int, payload: ProveedorEditarIn, db: Session = Depends(get_db)
) -> Proveedor:
    """Edita un proveedor; solo se actualizan los campos presentes en el payload.

    Args:
        proveedor_id: Proveedor a editar.
        payload: Campos a actualizar.
        db: Sesion de base de datos inyectada.

    Returns:
        ProveedorOut: El proveedor actualizado.

    Raises:
        HTTPException: 404 si no existe; 422 si se intenta dejar `nombre_empresa` en null.
    """
    proveedor = _obtener_o_404(db, proveedor_id)
    datos = payload.model_dump(exclude_unset=True)
    if "nombre_empresa" in datos and datos["nombre_empresa"] is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El nombre de la empresa no puede quedar vacio.",
        )
    for campo, valor in datos.items():
        setattr(proveedor, campo, valor)
    db.commit()
    db.refresh(proveedor)
    return proveedor


@router.delete("/{proveedor_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_proveedor(proveedor_id: int, db: Session = Depends(get_db)) -> Response:
    """Elimina un proveedor que nunca haya tenido una compra.

    Las compras referencian al proveedor con ON DELETE RESTRICT: si tiene
    historial no se borra, para conservar la trazabilidad de costos.

    Args:
        proveedor_id: Proveedor a eliminar.
        db: Sesion de base de datos inyectada.

    Returns:
        Response: 204 sin cuerpo.

    Raises:
        HTTPException: 404 si no existe; 409 si tiene compras registradas.
    """
    proveedor = _obtener_o_404(db, proveedor_id)
    try:
        db.delete(proveedor)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar un proveedor con compras registradas.",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
