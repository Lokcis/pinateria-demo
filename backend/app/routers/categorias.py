"""Router de categorias.

La consulta la usan vendedor y administrador (selector del alta de
productos, RF-016); el alta, edicion y baja (RF-017) son solo del
administrador.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import requerir_roles
from app.models.categoria import Categoria
from app.models.producto import Producto
from app.models.usuario import RolUsuario, Usuario
from app.schemas.categoria import CategoriaCrearIn, CategoriaEditarIn, CategoriaOut

router = APIRouter(prefix="/categorias", tags=["categorias"])

_MSG_CON_PRODUCTOS = "No se puede eliminar una categoria que tiene productos."


@router.get("", response_model=list[CategoriaOut])
def listar_categorias(
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(
        requerir_roles(RolUsuario.VENDEDOR, RolUsuario.ADMINISTRADOR)
    ),
) -> list[Categoria]:
    """Lista todas las categorias, ordenadas por nombre.

    Args:
        db: Sesion de base de datos inyectada.
        usuario_actual: Usuario autenticado (VENDEDOR o ADMINISTRADOR).

    Returns:
        list[CategoriaOut]: Todas las categorias del catalogo.
    """
    return db.query(Categoria).order_by(Categoria.nombre).all()


def _obtener_o_404(db: Session, categoria_id: int) -> Categoria:
    """Busca una categoria por id o lanza 404.

    Args:
        db: Sesion de base de datos.
        categoria_id: Id de la categoria.

    Returns:
        Categoria: La categoria encontrada.

    Raises:
        HTTPException: 404 si no existe.
    """
    categoria = db.query(Categoria).filter(Categoria.id == categoria_id).one_or_none()
    if categoria is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"La categoria con id={categoria_id} no existe.")
    return categoria


def _validar_nombre(db: Session, nombre: str | None, excluir_id: int | None = None) -> str:
    """Limpia el nombre y verifica que no este vacio ni lo use otra categoria (sin distinguir mayusculas).

    Args:
        db: Sesion de base de datos.
        nombre: Nombre propuesto.
        excluir_id: Categoria que se esta editando, si aplica.

    Returns:
        str: El nombre sin espacios sobrantes.

    Raises:
        HTTPException: 422 si queda vacio; 409 si ya existe.
    """
    limpio = (nombre or "").strip()
    if not limpio:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El nombre no puede quedar vacio.")
    consulta = db.query(Categoria.id).filter(func.lower(Categoria.nombre) == limpio.lower())
    if excluir_id is not None:
        consulta = consulta.filter(Categoria.id != excluir_id)
    if consulta.first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe una categoria con ese nombre.")
    return limpio


@router.post("", response_model=CategoriaOut, status_code=status.HTTP_201_CREATED)
def crear_categoria(
    payload: CategoriaCrearIn,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(requerir_roles(RolUsuario.ADMINISTRADOR)),
) -> Categoria:
    """Da de alta una categoria (RF-017). Solo administrador.

    Args:
        payload: Nombre y descripcion.
        db: Sesion de base de datos inyectada.
        usuario_actual: Administrador autenticado.

    Returns:
        CategoriaOut: La categoria creada.

    Raises:
        HTTPException: 409 si el nombre ya existe; 422 si el nombre queda vacio.
    """
    categoria = Categoria(
        nombre=_validar_nombre(db, payload.nombre),
        descripcion=(payload.descripcion or "").strip() or None,
    )
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    return categoria


@router.patch("/{categoria_id}", response_model=CategoriaOut)
def editar_categoria(
    categoria_id: int,
    payload: CategoriaEditarIn,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(requerir_roles(RolUsuario.ADMINISTRADOR)),
) -> Categoria:
    """Edita nombre y/o descripcion de una categoria (RF-017). Solo administrador.

    Args:
        categoria_id: Categoria a editar.
        payload: Campos a actualizar.
        db: Sesion de base de datos inyectada.
        usuario_actual: Administrador autenticado.

    Returns:
        CategoriaOut: La categoria actualizada.

    Raises:
        HTTPException: 404 si no existe; 409 si el nombre ya existe; 422 si el nombre queda vacio o nulo.
    """
    categoria = _obtener_o_404(db, categoria_id)
    datos = payload.model_dump(exclude_unset=True)
    if "nombre" in datos:
        categoria.nombre = _validar_nombre(db, datos["nombre"], excluir_id=categoria.id)
    if "descripcion" in datos:
        categoria.descripcion = (datos["descripcion"] or "").strip() or None
    db.commit()
    db.refresh(categoria)
    return categoria


@router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(requerir_roles(RolUsuario.ADMINISTRADOR)),
) -> Response:
    """Elimina una categoria que no tenga productos (RF-017). Solo administrador.

    Args:
        categoria_id: Categoria a eliminar.
        db: Sesion de base de datos inyectada.
        usuario_actual: Administrador autenticado.

    Returns:
        Response: 204 sin cuerpo.

    Raises:
        HTTPException: 404 si no existe; 409 si tiene productos asociados.
    """
    categoria = _obtener_o_404(db, categoria_id)
    if db.query(Producto.id).filter(Producto.categoria_id == categoria.id).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_MSG_CON_PRODUCTOS)
    try:
        db.delete(categoria)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_MSG_CON_PRODUCTOS) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
