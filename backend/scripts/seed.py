"""Script de siembra (seed): crea el primer usuario administrador.

Necesario porque no existe (ni esta en el alcance de las tarjetas 11-19)
un endpoint de registro publico de usuarios: la primera cuenta debe
crearse directamente contra la base de datos para poder autenticarse en
`POST /login` por primera vez.

Uso tipico (en el servidor, con la migracion de Alembic ya aplicada):

    python -m scripts.seed --username admin --nombre "Administrador Principal"

La contrasena NUNCA se pasa por argumento de linea de comandos (quedaria
en el historial de la shell y en `ps`); se pide de forma oculta con
`getpass`, o se puede pasar por la variable de entorno
`SEED_ADMIN_PASSWORD` (util para automatizar en un pipeline, pero evitar
en uso manual interactivo).

El script es idempotente: si el `username` ya existe, no lo duplica ni
sobrescribe su contrasena; informa y termina sin error.
"""

import argparse
import getpass
import os
import sys

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.usuario import RolUsuario, Usuario


def crear_usuario_inicial(
    username: str,
    nombre: str,
    password_plano: str,
    rol: RolUsuario = RolUsuario.ADMINISTRADOR,
) -> Usuario:
    """Crea un usuario si `username` no existe todavia.

    Args:
        username: Nombre de usuario para iniciar sesion. Debe ser unico.
        nombre: Nombre completo a mostrar.
        password_plano: Contrasena en texto plano; se hashea con bcrypt
            antes de persistir, nunca se guarda tal cual.
        rol: Rol a asignar. Por defecto, ADMINISTRADOR (para la primera
            cuenta del sistema).

    Returns:
        Usuario: El usuario ya existente (si `username` estaba en uso) o
        el recien creado.

    Raises:
        ValueError: Si `password_plano` esta vacia o tiene menos de 8
            caracteres (regla minima de higiene de contrasenas para una
            cuenta administradora).
    """
    if not password_plano or len(password_plano) < 8:
        raise ValueError("La contrasena debe tener al menos 8 caracteres.")

    db = SessionLocal()
    try:
        usuario_existente = db.query(Usuario).filter(Usuario.username == username).one_or_none()
        if usuario_existente is not None:
            print(f"El usuario {username!r} ya existe (id={usuario_existente.id}); no se crea de nuevo.")
            return usuario_existente

        usuario = Usuario(
            nombre=nombre,
            username=username,
            password_hash=hash_password(password_plano),
            rol=rol,
            activo=True,
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        print(f"Usuario {username!r} creado con id={usuario.id} y rol={rol.value}.")
        return usuario
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _construir_parser() -> argparse.ArgumentParser:
    """Construye el parser de argumentos de linea de comandos.

    Returns:
        argparse.ArgumentParser: Parser configurado con las opciones del
        script.
    """
    parser = argparse.ArgumentParser(
        description="Crea el primer usuario administrador del sistema."
    )
    parser.add_argument("--username", required=True, help="Nombre de usuario para login.")
    parser.add_argument("--nombre", required=True, help="Nombre completo a mostrar.")
    parser.add_argument(
        "--rol",
        choices=[rol.value for rol in RolUsuario],
        default=RolUsuario.ADMINISTRADOR.value,
        help="Rol a asignar (por defecto: administrador).",
    )
    return parser


def main() -> None:
    """Punto de entrada del script: lee argumentos, pide la contrasena y crea el usuario."""
    parser = _construir_parser()
    args = parser.parse_args()

    password_plano = os.environ.get("SEED_ADMIN_PASSWORD")
    if not password_plano:
        password_plano = getpass.getpass(f"Contrasena para {args.username!r}: ")
        confirmacion = getpass.getpass("Confirma la contrasena: ")
        if password_plano != confirmacion:
            print("Las contrasenas no coinciden.", file=sys.stderr)
            sys.exit(1)

    try:
        crear_usuario_inicial(
            username=args.username,
            nombre=args.nombre,
            password_plano=password_plano,
            rol=RolUsuario(args.rol),
        )
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
