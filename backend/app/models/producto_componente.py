"""Modelo de ProductoComponente: relacion BOM (Bill of Materials) auto-referenciada."""

from sqlalchemy import CheckConstraint, Column, ForeignKey, Index, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class ProductoComponente(Base):
    """Representa la receta/composicion de un producto tipo paquete o ancheta.

    Cada fila indica que `producto_padre_id` requiere `cantidad` unidades
    de `producto_componente_id` para ensamblarse. La relacion es
    auto-referenciada sobre `productos` y soporta anidamiento (un
    componente puede a su vez tener sus propios componentes, ej. una
    ancheta que incluye un paquete de dulces hecho de dulces sueltos),
    lo cual se resuelve recursivamente en
    `app.services.inventario.consumir_stock`.

    Politica de borrado (ON DELETE):
        - `producto_padre_id` -> CASCADE: si se elimina el producto padre
          (la ancheta), sus filas de receta dejan de tener sentido y se
          eliminan con el.
        - `producto_componente_id` -> RESTRICT: no se puede eliminar un
          producto mientras siga siendo componente de otro, para no
          dejar recetas rotas.

    Notas de integridad:
        - El `CheckConstraint` de esta tabla solo evita la auto-referencia
          directa (producto_padre_id == producto_componente_id). Los
          ciclos indirectos (A -> B -> A) NO se pueden expresar como una
          restriccion declarativa de una sola fila y deben validarse en
          la capa de aplicacion antes de insertar/actualizar una receta
          (ver `app.services.inventario.validar_sin_ciclos`).

    Attributes:
        id: Identificador unico autoincremental.
        producto_padre_id: FK a `productos.id`, el producto compuesto.
        producto_componente_id: FK a `productos.id`, el producto que se
            consume como parte de la receta.
        cantidad: Cantidad de `producto_componente_id` requerida por cada
            unidad de `producto_padre_id`. Debe ser mayor a cero.
    """

    __tablename__ = "producto_componentes"
    __table_args__ = (
        UniqueConstraint(
            "producto_padre_id",
            "producto_componente_id",
            name="uq_producto_componente",
        ),
        CheckConstraint(
            "producto_padre_id <> producto_componente_id",
            name="ck_no_auto_referencia",
        ),
        CheckConstraint("cantidad > 0", name="producto_componentes_cantidad_check"),
        Index("ix_componentes_padre", "producto_padre_id"),
        Index("ix_componentes_hijo", "producto_componente_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    producto_padre_id = Column(
        Integer, ForeignKey("productos.id", ondelete="CASCADE"), nullable=False
    )
    producto_componente_id = Column(
        Integer, ForeignKey("productos.id", ondelete="RESTRICT"), nullable=False
    )
    cantidad = Column(Numeric(10, 2), nullable=False)

    producto_padre = relationship(
        "Producto",
        foreign_keys=[producto_padre_id],
        back_populates="componentes",
    )
    producto_componente = relationship(
        "Producto",
        foreign_keys=[producto_componente_id],
        back_populates="usado_en",
    )

    def __repr__(self) -> str:
        """Retorna una representacion legible de la receta para logs/debug."""
        return (
            f"<ProductoComponente padre={self.producto_padre_id} "
            f"componente={self.producto_componente_id} cantidad={self.cantidad}>"
        )
