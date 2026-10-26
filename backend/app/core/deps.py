"""Dependencias de FastAPI para autenticacion y control de acceso por rol (RBAC).

`get_current_usuario` decodifica el JWT del header `Authorization` y
carga el `Usuario` correspondiente. `requerir_roles` es una fabrica de
dependencias: cada router pasa los roles permitidos para ese endpoint,
y FastAPI resuelve el chequeo antes de ejecutar la logica del endpoint
(patron de dependency injection, no un middleware global, para poder
variar los roles permitidos por ruta).
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import TokenInvalidoError, decodificar_access_token
from app.models.usuario import RolUsuario, Usuario

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def get_current_usuario(
    token: str = Depends(_oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """Resuelve el usuario autenticado a partir del token JWT de la request.

    Args:
        token: Token JWT extraido del header `Authorization: Bearer <token>`.
        db: Sesion de base de datos inyectada.

    Returns:
        Usuario: El usuario autenticado y activo.

    Raises:
        HTTPException: 401 si el token es invalido/expiro, si el `sub`
            del payload no corresponde a un usuario existente, o si el
            usuario esta inactivo.
    """
    credenciales_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar la sesion.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decodificar_access_token(token)
    except TokenInvalidoError as exc:
        raise credenciales_invalidas from exc

    usuario_id_str = payload.get("sub")
    if usuario_id_str is None:
        raise credenciales_invalidas

    try:
        usuario_id = int(usuario_id_str)
    except (TypeError, ValueError) as exc:
        raise credenciales_invalidas from exc

    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).one_or_none()
    if usuario is None or not usuario.activo:
        raise credenciales_invalidas

    return usuario


def requerir_roles(*roles_permitidos: RolUsuario):
    """Crea una dependencia que exige que el usuario autenticado tenga uno de los roles dados.

    Args:
        *roles_permitidos: Uno o mas `RolUsuario` autorizados para el
            endpoint que usa esta dependencia.

    Returns:
        Callable: Una dependencia de FastAPI que retorna el `Usuario`
        autenticado si su rol esta permitido, o lanza 403 en caso
        contrario.
    """

    def _verificar_rol(usuario_actual: Usuario = Depends(get_current_usuario)) -> Usuario:
        """Verifica que el rol del usuario autenticado este en la lista permitida.

        Args:
            usuario_actual: Usuario resuelto por `get_current_usuario`.

        Returns:
            Usuario: El mismo usuario, si su rol esta autorizado.

        Raises:
            HTTPException: 403 si el rol del usuario no esta en
                `roles_permitidos`.
        """
        if usuario_actual.rol not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para realizar esta operacion.",
            )
        return usuario_actual

    return _verificar_rol
