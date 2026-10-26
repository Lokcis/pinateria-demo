"""Router de autenticacion: login y emision de JWT."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_usuario
from app.core.security import crear_access_token, hash_password, verificar_password
from app.models.usuario import Usuario
from app.schemas.auth import Token
from app.schemas.usuario import CambiarPasswordIn

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    """Autentica a un usuario por `username`/`password` y emite un access token.

    El formulario usa el contrato estandar de OAuth2 (`OAuth2PasswordRequestForm`,
    application/x-www-form-urlencoded), compatible con el boton "Authorize"
    de la documentacion interactiva (`/docs`). El campo `username` del
    formulario corresponde a `usuarios.username`.

    Args:
        form_data: Formulario con `username` y `password`.
        db: Sesion de base de datos inyectada.

    Returns:
        Token: El access token JWT, con `sub` (id de usuario) y `rol`
        como claims del payload.

    Raises:
        HTTPException: 401 si el usuario no existe, esta inactivo, o la
            contrasena no coincide.
    """
    usuario = db.query(Usuario).filter(Usuario.username == form_data.username).one_or_none()

    credenciales_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Usuario o contrasena incorrectos.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if usuario is None or not usuario.activo:
        raise credenciales_invalidas

    if not verificar_password(form_data.password, usuario.password_hash):
        raise credenciales_invalidas

    access_token = crear_access_token({"sub": str(usuario.id), "rol": usuario.rol.value})
    return Token(access_token=access_token, token_type="bearer")


@router.post("/cambiar-password", status_code=status.HTTP_204_NO_CONTENT)
def cambiar_password(
    payload: CambiarPasswordIn,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_usuario),
) -> Response:
    """Permite a cualquier usuario autenticado cambiar su propia contrasena (RF-015).

    Args:
        payload: Contrasena actual y contrasena nueva.
        db: Sesion de base de datos inyectada.
        usuario_actual: Usuario autenticado.

    Returns:
        Response: 204 sin cuerpo.

    Raises:
        HTTPException: 400 si la contrasena actual no coincide.
    """
    if not verificar_password(payload.password_actual, usuario_actual.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La contrasena actual es incorrecta.")
    usuario_actual.password_hash = hash_password(payload.password_nueva)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
