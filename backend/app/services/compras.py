"""Logica de negocio de compras a proveedores (RF-010, RF-011).

Igual que `services/inventario.py`, este modulo NO hace commit/rollback:
el router que lo invoca envuelve la llamada en la transaccion y hace
`db.rollback()` ante cualquier error de dominio, de modo que recibir una
compra sea todo o nada.
"""

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.compra import Compra, EstadoCompra
from app.models.detalle_compra import DetalleCompra
from app.models.producto import Producto
from app.models.pago_venta import PlataformaTransferencia
from app.models.proveedor import Proveedor
from app.models.venta import MetodoPago
from app.services.redondeo import redondear_a_50
from app.services.exceptions import (
    CompraNoEncontradaError,
    EstadoCompraInvalidoError,
    ProductoNoEncontradoError,
    ProveedorNoEncontradoError,
)


def crear_compra(
    db: Session,
    proveedor_id: int,
    usuario_id: int,
    lineas: list[tuple[int, int, Decimal]],
) -> Compra:
    """Crea una orden de compra en estado PENDIENTE; no toca el stock (RF-010).

    Args:
        db: Sesion activa, dentro de una transaccion del llamador.
        proveedor_id: Proveedor al que se le compra.
        usuario_id: Usuario que registra la orden.
        lineas: Tuplas `(producto_id, cantidad, costo_unitario)`.

    Returns:
        Compra: La orden creada (aun no commiteada), con `total` redondeado al multiplo de 50 mas cercano.

    Raises:
        ProveedorNoEncontradoError: Si el proveedor no existe.
        ProductoNoEncontradoError: Si algun producto no existe.
    """
    if db.query(Proveedor.id).filter(Proveedor.id == proveedor_id).one_or_none() is None:
        raise ProveedorNoEncontradoError(proveedor_id)

    compra = Compra(proveedor_id=proveedor_id, usuario_id=usuario_id, estado=EstadoCompra.PENDIENTE)
    total = Decimal("0")
    for producto_id, cantidad, costo_unitario in lineas:
        if db.query(Producto.id).filter(Producto.id == producto_id).one_or_none() is None:
            raise ProductoNoEncontradoError(producto_id)
        subtotal = (costo_unitario * cantidad).quantize(Decimal("0.01"))
        total += subtotal
        compra.detalles.append(
            DetalleCompra(
                producto_id=producto_id,
                cantidad=cantidad,
                costo_unitario=costo_unitario,
                subtotal=subtotal,
            )
        )
    compra.total = redondear_a_50(total)
    db.add(compra)
    db.flush()
    return compra


def _obtener_compra_bloqueada(db: Session, compra_id: int) -> Compra:
    """Carga una compra con `SELECT ... FOR UPDATE` para serializar cambios de estado.

    Raises:
        CompraNoEncontradaError: Si la compra no existe.
    """
    compra = db.query(Compra).filter(Compra.id == compra_id).with_for_update().one_or_none()
    if compra is None:
        raise CompraNoEncontradaError(compra_id)
    return compra


def recibir_compra(
    db: Session, compra_id: int, metodo_pago: MetodoPago, plataforma: PlataformaTransferencia | None = None
) -> Compra:
    """Marca una compra como RECIBIDA e incrementa el stock de cada producto (RF-011).

    Tambien guarda como se pago y cuando se recibio (Adendo v3, RF-063): con eso la compra entra a la lista
    de Gastos y, si fue en efectivo, a la caja (Fase G2).

    Bloquea la compra (evita recibirla dos veces en paralelo) y luego los
    productos en orden de id (evita interbloqueos entre dos recepciones
    que comparten productos). Las lineas repetidas del mismo producto se
    suman.

    Args:
        db: Sesion activa, dentro de una transaccion del llamador.
        compra_id: Compra a recibir.
        metodo_pago: Forma de pago de la compra.
        plataforma: Plataforma de la transferencia (obligatoria solo en transferencias; la valida el esquema).

    Returns:
        Compra: La compra ya en estado RECIBIDA (aun no commiteada).

    Raises:
        CompraNoEncontradaError: Si la compra no existe.
        EstadoCompraInvalidoError: Si la compra no esta PENDIENTE.
    """
    compra = _obtener_compra_bloqueada(db, compra_id)
    if compra.estado != EstadoCompra.PENDIENTE:
        raise EstadoCompraInvalidoError(compra_id, compra.estado, "recibir")

    cantidades: dict[int, int] = defaultdict(int)
    for detalle in compra.detalles:
        cantidades[detalle.producto_id] += detalle.cantidad

    for producto_id in sorted(cantidades):
        producto = db.query(Producto).filter(Producto.id == producto_id).with_for_update().one()
        producto.stock_actual += cantidades[producto_id]

    compra.estado = EstadoCompra.RECIBIDA
    compra.metodo_pago = metodo_pago
    compra.plataforma = plataforma
    compra.recibida_en = func.now()  # Reloj de la base: el mismo que usan ventas.fecha y gastos.creado_en (caja).
    return compra


def cancelar_compra(db: Session, compra_id: int) -> Compra:
    """Cancela una compra PENDIENTE sin afectar el inventario.

    Args:
        db: Sesion activa, dentro de una transaccion del llamador.
        compra_id: Compra a cancelar.

    Returns:
        Compra: La compra ya en estado CANCELADA (aun no commiteada).

    Raises:
        CompraNoEncontradaError: Si la compra no existe.
        EstadoCompraInvalidoError: Si la compra no esta PENDIENTE.
    """
    compra = _obtener_compra_bloqueada(db, compra_id)
    if compra.estado != EstadoCompra.PENDIENTE:
        raise EstadoCompraInvalidoError(compra_id, compra.estado, "cancelar")
    compra.estado = EstadoCompra.CANCELADA
    return compra
