"""Logica de negocio de inventario: consumo de stock (BOM) y validacion de recetas.

Este modulo NO gestiona transacciones (commit/rollback): quien llama a
`consumir_stock` (tipicamente el router de `POST /ventas`) es responsable
de envolver la llamada en una transaccion y hacer `db.rollback()` si se
lanza cualquier `InventarioError`, para garantizar que una venta fallida
no deje descuentos parciales de inventario.
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.ajuste_inventario import AjusteInventario, TipoAjuste
from app.models.producto import Producto
from app.models.producto_componente import ProductoComponente
from app.services.exceptions import (
    CantidadFraccionariaError,
    CicloComposicionError,
    ProductoNoEncontradoError,
    SignoAjusteInvalidoError,
    StockInsuficienteError,
)

_TIPOS_SIGNO_POSITIVO = {TipoAjuste.ENTRADA}
_TIPOS_SIGNO_NEGATIVO = {TipoAjuste.SALIDA, TipoAjuste.MERMA}


def _a_entero_exacto(producto_id: int, valor: Decimal) -> int:
    """Convierte una cantidad calculada a entero, exigiendo que sea exacta.

    `productos.stock_actual` es INTEGER; `producto_componentes.cantidad`
    es NUMERIC(10,2). Multiplicar una proporcion de receta por unidades
    faltantes puede producir un resultado fraccionario, que no se puede
    descontar de un stock entero sin una regla de redondeo implicita.

    Args:
        producto_id: Identificador del producto componente, para el
            mensaje de error.
        valor: Cantidad calculada (puede tener decimales).

    Returns:
        int: El valor convertido a entero, solo si es exacto.

    Raises:
        CantidadFraccionariaError: Si `valor` no es un entero exacto.
    """
    entero = int(valor)
    if Decimal(entero) != valor:
        raise CantidadFraccionariaError(producto_id, valor)
    return entero


def consumir_stock(db: Session, producto_id: int, cantidad: int) -> None:
    """Descuenta stock de un producto, resolviendo composicion (BOM) si es necesario.

    Regla de consumo (Diseño de Base de Datos v1.1, sección 3.10):
        1. Bloquea la fila del producto (`SELECT ... FOR UPDATE`) para
           evitar condiciones de carrera entre ventas simultaneas.
        2. Descuenta primero de `stock_actual` propio (lo ya armado).
        3. Si el stock propio no alcanza, resuelve el faltante
           recursivamente contra `producto_componentes`: por cada
           componente de la receta, calcula la cantidad requerida
           (`cantidad_receta * unidades_faltantes`) y vuelve a llamar a
           `consumir_stock` sobre ese componente. La recursion soporta
           composicion anidada sin logica adicional.
        4. Si en cualquier nivel no hay stock ni componentes suficientes,
           lanza `StockInsuficienteError` de inmediato. El llamador debe
           hacer `db.rollback()` ante esta excepcion (o cualquier
           `InventarioError`) para deshacer los cambios ya aplicados en
           la sesion: la venta completa debe fallar, nunca una venta
           parcial ni dejar stock en negativo.

    Args:
        db: Sesion de SQLAlchemy activa, dentro de una transaccion
            controlada por el llamador.
        producto_id: Identificador del producto a descontar.
        cantidad: Cantidad entera a consumir. Debe ser mayor a cero.

    Raises:
        ProductoNoEncontradoError: Si `producto_id` no existe.
        StockInsuficienteError: Si no hay stock propio ni componentes
            suficientes para cubrir `cantidad`.
        CantidadFraccionariaError: Si la receta exige una cantidad no
            entera de algun componente.
        ValueError: Si `cantidad` no es mayor a cero.
    """
    if cantidad <= 0:
        raise ValueError("La cantidad a consumir debe ser mayor a cero.")

    producto = (
        db.query(Producto)
        .filter(Producto.id == producto_id)
        .with_for_update()
        .one_or_none()
    )
    if producto is None:
        raise ProductoNoEncontradoError(producto_id)

    if producto.stock_actual >= cantidad:
        producto.stock_actual -= cantidad
        return

    faltante = cantidad - producto.stock_actual
    componentes = (
        db.query(ProductoComponente)
        .filter(ProductoComponente.producto_padre_id == producto_id)
        .all()
    )

    if not componentes:
        raise StockInsuficienteError(
            producto_id=producto_id,
            cantidad_solicitada=cantidad,
            cantidad_disponible=producto.stock_actual,
        )

    stock_propio_original = producto.stock_actual
    producto.stock_actual = 0

    try:
        for componente in componentes:
            cantidad_requerida = _a_entero_exacto(
                componente.producto_componente_id,
                componente.cantidad * Decimal(faltante),
            )
            consumir_stock(db, componente.producto_componente_id, cantidad_requerida)
    except (StockInsuficienteError, CantidadFraccionariaError, ProductoNoEncontradoError):
        # Revierte el descuento tentativo del stock propio antes de propagar,
        # para que el estado en memoria de este objeto sea consistente si el
        # llamador decide inspeccionarlo antes de hacer rollback().
        producto.stock_actual = stock_propio_original
        raise


def aplicar_ajuste_inventario(
    db: Session,
    producto_id: int,
    usuario_id: int,
    tipo: TipoAjuste,
    cantidad: int,
    motivo: str,
) -> AjusteInventario:
    """Registra un ajuste manual de inventario y actualiza el stock del producto (RF-009).

    Args:
        db: Sesion de SQLAlchemy activa, dentro de una transaccion
            controlada por el llamador.
        producto_id: Identificador del producto a ajustar.
        usuario_id: Identificador del usuario que registra el ajuste.
        tipo: Tipo de ajuste (entrada/salida/merma/correccion).
        cantidad: Magnitud con signo del ajuste. Debe ser distinta de
            cero y coincidir con el signo esperado para `tipo`
            (ENTRADA positiva, SALIDA/MERMA negativa; CORRECCION admite
            cualquier signo).
        motivo: Justificacion textual obligatoria del ajuste.

    Returns:
        AjusteInventario: El ajuste registrado (aun no commiteado).

    Raises:
        ProductoNoEncontradoError: Si `producto_id` no existe.
        SignoAjusteInvalidoError: Si el signo de `cantidad` no
            corresponde al `tipo` dado.
        StockInsuficienteError: Si aplicar el ajuste dejaria
            `stock_actual` en negativo.
    """
    if tipo in _TIPOS_SIGNO_POSITIVO and cantidad <= 0:
        raise SignoAjusteInvalidoError(tipo, cantidad)
    if tipo in _TIPOS_SIGNO_NEGATIVO and cantidad >= 0:
        raise SignoAjusteInvalidoError(tipo, cantidad)

    producto = (
        db.query(Producto)
        .filter(Producto.id == producto_id)
        .with_for_update()
        .one_or_none()
    )
    if producto is None:
        raise ProductoNoEncontradoError(producto_id)

    nuevo_stock = producto.stock_actual + cantidad
    if nuevo_stock < 0:
        raise StockInsuficienteError(
            producto_id=producto_id,
            cantidad_solicitada=-cantidad,
            cantidad_disponible=producto.stock_actual,
        )

    producto.stock_actual = nuevo_stock

    ajuste = AjusteInventario(
        producto_id=producto_id,
        usuario_id=usuario_id,
        tipo=tipo,
        cantidad=cantidad,
        motivo=motivo,
    )
    db.add(ajuste)
    return ajuste


def validar_sin_ciclos(db: Session, producto_padre_id: int, producto_componente_id: int) -> None:
    """Valida que agregar una receta no genere un ciclo directo o indirecto.

    El `CheckConstraint` `ck_no_auto_referencia` de `producto_componentes`
    solo impide la auto-referencia directa
    (`producto_padre_id == producto_componente_id`). Esta funcion cubre
    el caso general: recorre el grafo de dependencias a partir de
    `producto_componente_id` y falla si en algun punto se llega de
    vuelta a `producto_padre_id`.

    Args:
        db: Sesion de SQLAlchemy activa.
        producto_padre_id: Id del producto que se intenta componer.
        producto_componente_id: Id del componente que se quiere agregar
            a la receta de `producto_padre_id`.

    Raises:
        CicloComposicionError: Si agregar la relacion crearia un ciclo
            (incluye el caso de auto-referencia directa, validado aqui
            tambien para dar un mensaje de error consistente antes de
            tocar la base de datos).
    """
    if producto_padre_id == producto_componente_id:
        raise CicloComposicionError(producto_padre_id, producto_componente_id)

    visitados: set[int] = set()
    pendientes = [producto_componente_id]

    while pendientes:
        actual = pendientes.pop()
        if actual == producto_padre_id:
            raise CicloComposicionError(producto_padre_id, producto_componente_id)
        if actual in visitados:
            continue
        visitados.add(actual)

        hijos = (
            db.query(ProductoComponente.producto_componente_id)
            .filter(ProductoComponente.producto_padre_id == actual)
            .all()
        )
        pendientes.extend(hijo_id for (hijo_id,) in hijos)
