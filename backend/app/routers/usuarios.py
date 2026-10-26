"""Router de usuarios: CRUD y roles, solo Administrador (RF-015)."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import requerir_roles
from app.core.security import hash_password
from app.models.usuario import RolUsuario, Usuario
from app.schemas.usuario import RestablecerPasswordIn, UsuarioCrearIn, UsuarioEditarIn, UsuarioOut

# Todo el router queda detras del rol Administrador: el resto recibe 403.
router = APIRouter(
    prefix="/usuarios",
    tags=["usuarios"],
    dependencies=[Depends(requerir_roles(RolUsuario.ADMINISTRADOR))],
)


def _obtener_o_404(db: Session, usuario_id: int) -> Usuario:
    """Busca un usuario por id o lanza 404.

    Args:
        db: Sesion de base de datos.
        usuario_id: Id del usuario.

    Returns:
        Usuario: El usuario encontrado.

    Raises:
        HTTPException: 404 si no existe.
    """
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).one_or_none()
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"El usuario con id={usuario_id} no existe.")
    return usuario


def _validar_username_libre(db: Session, username: str, excluir_id: int | None = None) -> None:
    """Verifica que el username no lo use otro usuario (sin distinguir mayusculas).

    Args:
        db: Sesion de base de datos.
        username: Usuario a validar.
        excluir_id: Id del usuario que se esta editando, si aplica.

    Raises:
        HTTPException: 409 si ya existe.
    """
    consulta = db.query(Usuario.id).filter(Usuario.username.ilike(username))
    if excluir_id is not None:
        consulta = consulta.filter(Usuario.id != excluir_id)
    if consulta.first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un usuario con ese nombre de usuario.")


@router.get("", response_model=list[UsuarioOut])
def listar_usuarios(db: Session = Depends(get_db)) -> list[Usuario]:
    """Lista todos los usuarios (activos e inactivos) ordenados por nombre.

    Args:
        db: Sesion de base de datos inyectada.

    Returns:
        list[UsuarioOut]: Los usuarios, sin hash de contrasena.
    """
    return db.query(Usuario).order_by(Usuario.nombre).all()


@router.post("", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def crear_usuario(payload: UsuarioCrearIn, db: Session = Depends(get_db)) -> Usuario:
    """Crea un usuario de cualquier rol con la contrasena temporal indicada.

    Args:
        payload: Datos del usuario.
        db: Sesion de base de datos inyectada.

    Returns:
        UsuarioOut: El usuario creado.

    Raises:
        HTTPException: 409 si el nombre de usuario ya existe.
    """
    _validar_username_libre(db, payload.username)
    usuario = Usuario(
        nombre=payload.nombre.strip(),
        username=payload.username,
        password_hash=hash_password(payload.password),
        rol=payload.rol,
        activo=True,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.patch("/{usuario_id}", response_model=UsuarioOut)
def editar_usuario(
    usuario_id: int,
    payload: UsuarioEditarIn,
    db: Session = Depends(get_db),
    administrador: Usuario = Depends(requerir_roles(RolUsuario.ADMINISTRADOR)),
) -> Usuario:
    """Edita nombre, usuario, rol o estado activo; desactivar nunca borra el historial.

    Un administrador no puede desactivarse ni quitarse el rol a si mismo,
    para no dejar el sistema sin administradores.

    Args:
        usuario_id: Usuario a editar.
        payload: Campos a actualizar.
        db: Sesion de base de datos inyectada.
        administrador: Administrador autenticado.

    Returns:
        UsuarioOut: El usuario actualizado.

    Raises:
        HTTPException: 404 si no existe; 403 si intenta desactivarse o cambiarse el rol;
            409 si el nuevo nombre de usuario ya existe; 422 si manda un campo en null.
    """
    usuario = _obtener_o_404(db, usuario_id)
    datos = payload.model_dump(exclude_unset=True)
    if any(valor is None for valor in datos.values()):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Los campos enviados no pueden ser nulos.")

    if usuario.id == administrador.id:
        if datos.get("activo") is False:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puede desactivar su propia cuenta.")
        if "rol" in datos and datos["rol"] != RolUsuario.ADMINISTRADOR:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puede quitarse a si mismo el rol de administrador.")

    if "username" in datos:
        _validar_username_libre(db, datos["username"], excluir_id=usuario.id)
    if "nombre" in datos:
        datos["nombre"] = datos["nombre"].strip()

    for campo, valor in datos.items():
        setattr(usuario, campo, valor)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.post("/{usuario_id}/password", status_code=status.HTTP_204_NO_CONTENT)
def restablecer_password(usuario_id: int, payload: RestablecerPasswordIn, db: Session = Depends(get_db)) -> Response:
    """Fija una contrasena temporal nueva para el usuario indicado.

    Args:
        usuario_id: Usuario al que se le restablece la contrasena.
        payload: Nueva contrasena temporal.
        db: Sesion de base de datos inyectada.

    Returns:
        Response: 204 sin cuerpo.

    Raises:
        HTTPException: 404 si el usuario no existe.
    """
    usuario = _obtener_o_404(db, usuario_id)
    usuario.password_hash = hash_password(payload.password)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
