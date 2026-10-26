"""Excepciones de dominio para la capa de servicios de inventario.

Se definen como excepciones explicitas (en lugar de retornar None/False o
dejar propagar excepciones genericas de SQLAlchemy) para que los routers
puedan mapearlas a codigos HTTP especificos y para evitar fallos
silenciosos en la logica de negocio critica (venta/inventario).
"""


class InventarioError(Exception):
    """Clase base para todas las excepciones de la capa de inventario."""


class ProductoNoEncontradoError(InventarioError):
    """Se lanza cuando se referencia un `producto_id` que no existe."""

    def __init__(self, producto_id: int) -> None:
        """Inicializa la excepcion con el id del producto no encontrado.

        Args:
            producto_id: Identificador del producto que no fue encontrado.
        """
        self.producto_id = producto_id
        super().__init__(f"El producto con id={producto_id} no existe.")


class StockInsuficienteError(InventarioError):
    """Se lanza cuando no hay stock propio ni componentes suficientes.

    Indica que la venta completa debe fallar (no se permiten ventas
    parciales ni stock negativo).
    """

    def __init__(self, producto_id: int, cantidad_solicitada: object, cantidad_disponible: object) -> None:
        """Inicializa la excepcion con el detalle del faltante.

        Args:
            producto_id: Identificador del producto con stock insuficiente.
            cantidad_solicitada: Cantidad que se intento consumir.
            cantidad_disponible: Cantidad realmente disponible (propia,
                sin contar componentes que tambien fallaron).
        """
        self.producto_id = producto_id
        self.cantidad_solicitada = cantidad_solicitada
        self.cantidad_disponible = cantidad_disponible
        super().__init__(
            f"Stock insuficiente para el producto id={producto_id}: "
            f"se solicitaron {cantidad_solicitada}, hay {cantidad_disponible} "
            "disponibles y no hay componentes suficientes para ensamblar el faltante."
        )


class CantidadFraccionariaError(InventarioError):
    """Se lanza cuando resolver una receta exige una cantidad no entera.

    `productos.stock_actual` es INTEGER (ver schema.sql), pero
    `producto_componentes.cantidad` es NUMERIC(10,2) para permitir
    proporciones no enteras en la receta (ej. 0.5 metros de listón por
    unidad). Si el resultado de multiplicar esa proporcion por las
    unidades faltantes no es un entero exacto, no hay forma segura de
    descontarlo del stock del componente sin inventar una regla de
    redondeo implicita — se prefiere fallar explicitamente.
    """

    def __init__(self, producto_id: int, cantidad_calculada: object) -> None:
        """Inicializa la excepcion con el detalle de la cantidad fraccionaria.

        Args:
            producto_id: Identificador del producto componente afectado.
            cantidad_calculada: Cantidad calculada (no entera) que se
                intento consumir de ese componente.
        """
        self.producto_id = producto_id
        self.cantidad_calculada = cantidad_calculada
        super().__init__(
            f"La receta exige {cantidad_calculada} unidades del producto "
            f"id={producto_id}, una cantidad no entera que no se puede "
            "descontar de un stock medido en unidades enteras."
        )


class SignoAjusteInvalidoError(InventarioError):
    """Se lanza cuando el signo de `cantidad` no corresponde al `TipoAjuste`.

    Regla (ver docstring de `AjusteInventario`): ENTRADA exige cantidad
    positiva, SALIDA y MERMA exigen cantidad negativa, CORRECCION admite
    cualquier signo (distinto de cero, ya validado por el schema).
    """

    def __init__(self, tipo: object, cantidad: int) -> None:
        """Inicializa la excepcion con el tipo y la cantidad invalidos.

        Args:
            tipo: El `TipoAjuste` del ajuste que se intento registrar.
            cantidad: La cantidad con signo invalido para ese tipo.
        """
        self.tipo = tipo
        self.cantidad = cantidad
        super().__init__(
            f"La cantidad {cantidad} no es valida para un ajuste de tipo {tipo}: "
            "ENTRADA exige cantidad positiva, SALIDA y MERMA exigen cantidad negativa."
        )


class CicloComposicionError(InventarioError):
    """Se lanza al detectar que una receta crearia un ciclo (directo o indirecto).

    El CHECK constraint de `producto_componentes` solo cubre la
    auto-referencia directa (A -> A); esta excepcion cubre los ciclos
    indirectos (A -> B -> A), que deben validarse en la capa de
    aplicacion antes de insertar/actualizar una fila.
    """

    def __init__(self, producto_padre_id: int, producto_componente_id: int) -> None:
        """Inicializa la excepcion con los productos involucrados en el ciclo.

        Args:
            producto_padre_id: Id del producto que se intenta componer.
            producto_componente_id: Id del componente que se intenta agregar
                y que, directa o indirectamente, depende de `producto_padre_id`.
        """
        self.producto_padre_id = producto_padre_id
        self.producto_componente_id = producto_componente_id
        super().__init__(
            f"No se puede agregar el producto {producto_componente_id} como "
            f"componente de {producto_padre_id}: crearia un ciclo de composicion "
            "(directo o indirecto)."
        )


class CompraError(Exception):
    """Clase base para los errores de negocio del modulo de compras."""


class CompraNoEncontradaError(CompraError):
    """Se lanza cuando se referencia un `compra_id` que no existe."""

    def __init__(self, compra_id: int) -> None:
        """Inicializa la excepcion con el id de la compra no encontrada.

        Args:
            compra_id: Identificador de la compra que no fue encontrada.
        """
        self.compra_id = compra_id
        super().__init__(f"La compra con id={compra_id} no existe.")


class EstadoCompraInvalidoError(CompraError):
    """Se lanza al intentar recibir o cancelar una compra que ya no esta pendiente."""

    def __init__(self, compra_id: int, estado_actual: object, accion: str) -> None:
        """Inicializa la excepcion con la compra, su estado y la accion rechazada.

        Args:
            compra_id: Identificador de la compra.
            estado_actual: Estado en el que se encuentra la compra.
            accion: Accion rechazada ("recibir" o "cancelar").
        """
        self.compra_id = compra_id
        self.estado_actual = estado_actual
        super().__init__(
            f"No se puede {accion} la compra id={compra_id}: ya esta {getattr(estado_actual, 'value', estado_actual)}."
        )


class ProveedorNoEncontradoError(CompraError):
    """Se lanza cuando se referencia un `proveedor_id` que no existe."""

    def __init__(self, proveedor_id: int) -> None:
        """Inicializa la excepcion con el id del proveedor no encontrado.

        Args:
            proveedor_id: Identificador del proveedor que no fue encontrado.
        """
        self.proveedor_id = proveedor_id
        super().__init__(f"El proveedor con id={proveedor_id} no existe.")



class GastoError(Exception):
    """Clase base para los errores de dominio de gastos y categorias de gasto (Adendo v3)."""


class GastoNoEncontradoError(GastoError):
    """Se lanza cuando el gasto no existe o, para un vendedor, no es suyo (no se revela cual de los dos)."""

    def __init__(self, gasto_id: int) -> None:
        """Inicializa la excepcion con el id del gasto.

        Args:
            gasto_id: Identificador del gasto que no fue encontrado.
        """
        self.gasto_id = gasto_id
        super().__init__(f"El gasto con id={gasto_id} no existe.")


class CategoriaGastoNoEncontradaError(GastoError):
    """Se lanza cuando se referencia una categoria de gasto que no existe."""

    def __init__(self, categoria_id: int) -> None:
        """Inicializa la excepcion con el id de la categoria.

        Args:
            categoria_id: Identificador de la categoria que no fue encontrada.
        """
        self.categoria_id = categoria_id
        super().__init__(f"La categoria de gasto con id={categoria_id} no existe.")


class GastoInvalidoError(GastoError):
    """Se lanza cuando los datos de un gasto no cumplen una regla de negocio (monto, plataforma, fecha, categoria)."""


class GastoSinPermisoError(GastoError):
    """Se lanza cuando el rol puede usar el endpoint pero no hacer esa operacion (por ejemplo, elegir otra fecha)."""


class GastoConflictoError(GastoError):
    """Se lanza cuando la operacion choca con el estado actual (gasto ya anulado, categoria repetida o de sistema)."""


class CajaError(Exception):
    """Clase base para los errores de dominio de la caja y el corte de caja (Adendo v3, Fase G2)."""


class CorteNoEncontradoError(CajaError):
    """Se lanza cuando el corte no existe o, para un vendedor, no lo abrio ni lo cerro el (no se revela cual)."""

    def __init__(self, corte_id: int) -> None:
        """Inicializa la excepcion con el id del corte.

        Args:
            corte_id: Identificador del corte que no fue encontrado.
        """
        self.corte_id = corte_id
        super().__init__(f"El corte de caja con id={corte_id} no existe.")


class CajaInvalidaError(CajaError):
    """Se lanza cuando un monto de la caja no cumple una regla de negocio (por ejemplo, el multiplo de $50)."""


class CajaConflictoError(CajaError):
    """Se lanza cuando la operacion choca con el estado de la caja (ya hay una abierta, o no hay ninguna abierta)."""
