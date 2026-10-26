"""vista de margen por linea de venta (Adendo v2, Fase A3)

Crea `vw_margen_detalle` (docs/03-diseno-base-de-datos.md, secciones 7.9 y
7.12): una fila por linea de venta con el ingreso neto (subtotal menos el
descuento repartido), el costo total y el margen. Las columnas
`costo_unitario` de `productos` y `detalle_ventas` ya se crearon en la 0002.
Las lineas sin costo tienen `costo_total` y `margen` en NULL: se excluyen del
margen y se informan como "sin costo". No transforma datos.

La 0003 (Fase A2, clientes) aun no existe: esta migracion sigue a la 0002.

Revision ID: 0004
Revises: 0002
Create Date: 2026-10-08
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

VISTA_MARGEN = """
CREATE VIEW vw_margen_detalle AS
SELECT d.id AS detalle_id, d.venta_id, d.producto_id, v.fecha, v.usuario_id,
       d.cantidad,
       d.subtotal - d.descuento_prorrateado             AS ingreso_neto,
       d.costo_unitario * d.cantidad                    AS costo_total,
       d.subtotal - d.descuento_prorrateado
           - d.costo_unitario * d.cantidad              AS margen
FROM detalle_ventas d
JOIN ventas v ON v.id = d.venta_id
"""


def upgrade() -> None:
    """Crea la vista `vw_margen_detalle`."""
    op.execute(VISTA_MARGEN)


def downgrade() -> None:
    """Elimina la vista `vw_margen_detalle`."""
    op.execute("DROP VIEW IF EXISTS vw_margen_detalle")
