"""quien registro la venta, ademas del vendedor (Adendo v2, HU-08)

Agrega `ventas.registrada_por_id` (usuario con la sesion que registro la venta, que puede ser
distinto del vendedor elegido en el POS). Permite que el historial de un vendedor muestre tambien
lo que registro a nombre de otra persona. NO transforma datos: la columna es opcional y las ventas
anteriores quedan en NULL (se entienden registradas por su vendedor).

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agrega `ventas.registrada_por_id` (opcional, con su indice)."""
    op.add_column(
        "ventas",
        sa.Column("registrada_por_id", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True),
    )
    op.create_index("ix_ventas_registrada_por", "ventas", ["registrada_por_id"])


def downgrade() -> None:
    """Quita `ventas.registrada_por_id` (se pierde quien registro cada venta)."""
    op.drop_index("ix_ventas_registrada_por", table_name="ventas")
    op.drop_column("ventas", "registrada_por_id")
