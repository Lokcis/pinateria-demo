"""Utilidades de seguridad: hashing de contrasenas y manejo de JWT.

Usa passlib (bcrypt) para el hashing de contrasenas y python-jose para
la emision y verificacion de tokens JWT.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenInvalidoError(Exception):
    """Se lanza cuando un token JWT es invalido, esta mal formado o expiro."""


def hash_password(password_plano: str) -> str:
    """Genera el hash bcrypt de una contrasena en texto plano.

    Args:
        password_plano: Contrasena en texto plano ingresada por el usuario.

    Returns:
        str: Hash bcrypt listo para almacenar en `usuarios.password_hash`.
    """
    return _pwd_context.hash(password_plano)


def verificar_password(password_plano: str, password_hash: str) -> bool:
    """Verifica una contrasena en texto plano contra su hash almacenado.

    Args:
        password_plano: Contrasena en texto plano ingresada por el usuario.
        password_hash: Hash bcrypt almacenado en la base de datos.

    Returns:
        bool: True si la contrasena coincide con el hash, False en caso
            contrario. Nunca lanza excepcion ante un hash malformado;
            retorna False de forma segura.
    """
    try:
        return _pwd_context.verify(password_plano, password_hash)
    except ValueError:
        return False


def crear_access_token(datos: dict[str, Any], expiracion: timedelta | None = None) -> str:
    """Crea un access token JWT firmado.

    Args:
        datos: Claims a incluir en el payload (por ejemplo, `sub` con el
            id del usuario y `rol` con su rol).
        expiracion: Tiempo de vigencia del token. Si no se especifica,
            usa `settings.access_token_expire_minutes`.

    Returns:
        str: El token JWT codificado.
    """
    payload = datos.copy()
    expira_en = datetime.now(timezone.utc) + (
        expiracion or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload.update({"exp": expira_en})
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decodificar_access_token(token: str) -> dict[str, Any]:
    """Decodifica y valida un access token JWT.

    Args:
        token: Token JWT recibido en la cabecera Authorization.

    Returns:
        dict[str, Any]: El payload decodificado del token.

    Raises:
        TokenInvalidoError: Si el token esta mal formado, la firma no es
            valida, o el token ha expirado.
    """
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise TokenInvalidoError("El token es invalido o ha expirado.") from exc
