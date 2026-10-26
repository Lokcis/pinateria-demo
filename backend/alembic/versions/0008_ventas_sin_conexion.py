"""ventas hechas sin conexion y envio idempotente (Fase 9)

Agrega tres columnas OPCIONALES a `ventas`:

- `uuid_cliente`: identificador que genera el POS al confirmar cada venta. Con un indice unico, reenviar
  la misma venta (porque se perdio la respuesta o porque estaba en la cola sin conexion) no la duplica.
- `sin_conexion`: marca las ventas que se hicieron sin conexion y se enviaron despues (por defecto false).
- `sincronizada_en`: momento en que el servidor recibio una venta hecha sin conexion.

NO transforma datos: las ventas anteriores quedan con `uuid_cliente` NULL, `sin_conexion` false y
`sincronizada_en` NULL. Un indice unico permite varios NULL, asi que no choca con el historial.

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agrega `uuid_cliente` (con indice unico), `sin_conexion` y `sincronizada_en` a `ventas`."""
    op.add_column("ventas", sa.Column("uuid_cliente", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column(
        "ventas",
        sa.Column("sin_conexion", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("ventas", sa.Column("sincronizada_en", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ux_ventas_uuid_cliente", "ventas", ["uuid_cliente"], unique=True)


def downgrade() -> None:
    """Quita las tres columnas (se pierde la marca de las ventas hechas sin conexion y su identificador)."""
    op.drop_index("ux_ventas_uuid_cliente", table_name="ventas")
    op.drop_column("ventas", "sincronizada_en")
    op.drop_column("ventas", "sin_conexion")
    op.drop_column("ventas", "uuid_cliente")
