"""Script de siembra de datos de DEMOSTRACION para probar el sistema a mano.

Crea datos ficticios y evidentes (nada pertenece a un negocio ni a una persona reales):

- Tres usuarios de demostracion (administrador, vendedor y propietario).
- Categorias y productos de ejemplo, con un paquete y una ancheta compuestos por receta
  (al venderlos se descuenta el stock de sus componentes).
- Dos proveedores y tres clientes con datos inventados (telefonos 300 000 00xx, correos en
  `example.com`) y su autorizacion de tratamiento de datos registrada.

Uso (con la migracion de Alembic ya aplicada):

    python -m scripts.seed_demo

Es idempotente: si algo ya existe (usuario por `username`, categoria por nombre, producto por codigo de
barras, proveedor por nombre de empresa, cliente por telefono), no lo duplica. NO usar en produccion:
las contrasenas de los usuarios de demostracion son publicas.
"""

from datetime import datetime, timezone
from decimal import Decimal

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.categoria import Categoria
from app.models.cliente import Cliente, MedioAutorizacion, OrigenRegistro
from app.models.producto import Producto, TipoProducto
from app.models.producto_componente import ProductoComponente
from app.models.proveedor import Proveedor
from app.models.usuario import RolUsuario, Usuario

CONTRASENA_DEMO = "Demo-12345"

# (username, nombre, rol)
USUARIOS = [
    ("admin", "Administrador Demo", RolUsuario.ADMINISTRADOR),
    ("vendedor", "Vendedor Demo", RolUsuario.VENDEDOR),
    ("propietario", "Propietario Demo", RolUsuario.PROPIETARIO),
]

CATEGORIAS = ["Piñatas Infantiles", "Dulces", "Decoración", "Peluches", "Anchetas"]

# (codigo_barras, nombre, categoria, tipo, precio, costo, stock)
PRODUCTOS = [
    ("7501000000001", "Piñata Mickey Mouse", "Piñatas Infantiles", TipoProducto.UNIDAD, "25000.00", "14000.00", 10),
    ("7501000000002", "Piñata Unicornio", "Piñatas Infantiles", TipoProducto.UNIDAD, "32000.00", "18000.00", 6),
    ("7501000000003", "Bolsa de dulces surtidos 1kg", "Dulces", TipoProducto.UNIDAD, "18000.00", "11000.00", 40),
    ("7501000000004", "Bolsa de confeti", "Decoración", TipoProducto.UNIDAD, "3500.00", "1500.00", 100),
    ("7501000000005", "Globos de colores x50", "Decoración", TipoProducto.UNIDAD, "9000.00", "5000.00", 30),
    ("7501000000006", "Stock bajo de prueba", "Dulces", TipoProducto.UNIDAD, "5000.00", "2500.00", 2),
    ("7501000000007", "Oso de peluche mediano", "Peluches", TipoProducto.UNIDAD, "28000.00", "16000.00", 12),
    ("7501000000008", "Caja de bombones", "Dulces", TipoProducto.UNIDAD, "15000.00", "9000.00", 25),
    # Paquete sin stock propio: al venderlo consume sus componentes.
    ("7501000000010", "Kit Fiesta Infantil", "Piñatas Infantiles", TipoProducto.PAQUETE, "60000.00", "36000.00", 0),
    # Ancheta sin stock propio: su receta mezcla productos de varias categorias.
    ("7501000000020", "Ancheta Dulce Sorpresa", "Anchetas", TipoProducto.ANCHETA, "55000.00", "33000.00", 0),
]

# (codigo del paquete o ancheta, codigo del componente, cantidad por unidad)
RECETAS = [
    ("7501000000010", "7501000000001", "1"),
    ("7501000000010", "7501000000003", "1"),
    ("7501000000010", "7501000000004", "2"),
    ("7501000000020", "7501000000007", "1"),
    ("7501000000020", "7501000000008", "2"),
    ("7501000000020", "7501000000003", "1"),
]

# (nombre_empresa, nombre_contacto, telefono, email)
PROVEEDORES = [
    ("Papeles y Fiestas Demo S.A.S.", "Contacto Uno", "3000000011", "ventas@example.com"),
    ("Dulces del Valle Demo", "Contacto Dos", "3000000012", "pedidos@example.com"),
]

# (nombre, telefono, email, acepta_publicidad)
CLIENTES = [
    ("Cliente Demo Uno", "3000000021", "cliente1@example.com", True),
    ("Cliente Demo Dos", "3000000022", "cliente2@example.com", False),
    ("Cliente Demo Tres", "3000000023", None, False),
]
VERSION_POLITICA_DEMO = "demo-1"


def _sembrar_usuarios(db) -> int:
    """Crea los usuarios de demostracion que no existan.

    Args:
        db: Sesion de base de datos.

    Returns:
        Cantidad de usuarios creados.
    """
    creados = 0
    for username, nombre, rol in USUARIOS:
        if db.query(Usuario).filter(Usuario.username == username).one_or_none() is None:
            db.add(
                Usuario(
                    nombre=nombre,
                    username=username,
                    password_hash=hash_password(CONTRASENA_DEMO),
                    rol=rol,
                    activo=True,
                )
            )
            creados += 1
    db.flush()
    return creados


def _sembrar_catalogo(db) -> tuple[int, int, int]:
    """Crea categorias, productos y recetas de demostracion si no existen.

    Args:
        db: Sesion de base de datos.

    Returns:
        Tupla (categorias, productos, lineas de receta) del catalogo de demostracion.
    """
    categorias: dict[str, Categoria] = {}
    for nombre in CATEGORIAS:
        categoria = db.query(Categoria).filter(Categoria.nombre == nombre).one_or_none()
        if categoria is None:
            categoria = Categoria(nombre=nombre)
            db.add(categoria)
            db.flush()
        categorias[nombre] = categoria

    productos: dict[str, Producto] = {}
    for codigo, nombre, nombre_categoria, tipo, precio, costo, stock in PRODUCTOS:
        producto = db.query(Producto).filter(Producto.codigo_barras == codigo).one_or_none()
        if producto is None:
            producto = Producto(
                codigo_barras=codigo,
                nombre=nombre,
                categoria_id=categorias[nombre_categoria].id,
                tipo=tipo,
                precio_venta=Decimal(precio),
                costo_unitario=Decimal(costo) if costo else None,
                stock_actual=stock,
            )
            db.add(producto)
            db.flush()
        productos[codigo] = producto

    for codigo_padre, codigo_componente, cantidad in RECETAS:
        padre, componente = productos[codigo_padre], productos[codigo_componente]
        existe = (
            db.query(ProductoComponente)
            .filter(
                ProductoComponente.producto_padre_id == padre.id,
                ProductoComponente.producto_componente_id == componente.id,
            )
            .one_or_none()
        )
        if existe is None:
            db.add(
                ProductoComponente(
                    producto_padre_id=padre.id,
                    producto_componente_id=componente.id,
                    cantidad=Decimal(cantidad),
                )
            )
    return len(categorias), len(productos), len(RECETAS)


def _sembrar_proveedores_y_clientes(db) -> tuple[int, int]:
    """Crea los proveedores y clientes ficticios que no existan.

    Args:
        db: Sesion de base de datos.

    Returns:
        Tupla (proveedores, clientes) de la demostracion.
    """
    for empresa, contacto, telefono, email in PROVEEDORES:
        if db.query(Proveedor).filter(Proveedor.nombre_empresa == empresa).one_or_none() is None:
            db.add(Proveedor(nombre_empresa=empresa, nombre_contacto=contacto, telefono=telefono, email=email))

    # Un cliente registrado por un empleado debe indicar quien recogio la autorizacion.
    admin = db.query(Usuario).filter(Usuario.username == "admin").one()
    ahora = datetime.now(timezone.utc)
    for nombre, telefono, email, acepta_publicidad in CLIENTES:
        if db.query(Cliente).filter(Cliente.telefono == telefono).one_or_none() is None:
            db.add(
                Cliente(
                    nombre=nombre,
                    telefono=telefono,
                    email=email,
                    acepta_publicidad=acepta_publicidad,
                    publicidad_fecha=ahora if acepta_publicidad else None,
                    autorizacion_fecha=ahora,
                    autorizacion_medio=MedioAutorizacion.ELECTRONICO,
                    autorizacion_version=VERSION_POLITICA_DEMO,
                    origen_registro=OrigenRegistro.EMPLEADO,
                    autorizacion_registrada_por=admin.id,
                )
            )
    return len(PROVEEDORES), len(CLIENTES)


def sembrar() -> None:
    """Crea usuarios, catalogo, proveedores y clientes de demostracion si no existen."""
    db = SessionLocal()
    try:
        usuarios = _sembrar_usuarios(db)
        categorias, productos, recetas = _sembrar_catalogo(db)
        proveedores, clientes = _sembrar_proveedores_y_clientes(db)
        db.commit()
        print(
            f"Listo: {usuarios} usuarios nuevos, {categorias} categorias, {productos} productos, "
            f"{recetas} lineas de receta, {proveedores} proveedores y {clientes} clientes de demostracion."
        )
        print(f"Usuarios de demostracion: admin, vendedor, propietario (contrasena: {CONTRASENA_DEMO}).")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    sembrar()
