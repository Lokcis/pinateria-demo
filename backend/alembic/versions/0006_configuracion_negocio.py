"""datos del negocio configurables desde la aplicacion (Adendo v2, Fase A2)

Crea `configuracion_negocio`, una tabla de una sola fila con los datos del responsable del
tratamiento (nombre, NIT o cedula, direccion, telefono, correo de contacto, version y fecha de
la politica). Reemplaza las variables `NEGOCIO_*` del `.env`: el administrador las edita en
"Datos personales > Datos del negocio". NO transforma datos: solo agrega una tabla vacia.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crea la tabla `configuracion_negocio` (vacia: la fila se crea al guardar los datos por primera vez)."""
    op.create_table(
        "configuracion_negocio",
        sa.Column("id", sa.SmallInteger(), primary_key=True, server_default="1"),
        sa.Column("nombre", sa.String(150), nullable=False, server_default=""),
        sa.Column("documento", sa.String(40), nullable=False, server_default=""),
        sa.Column("direccion", sa.String(200), nullable=False, server_default=""),
        sa.Column("telefono", sa.String(40), nullable=False, server_default=""),
        sa.Column("correo_datos", sa.String(120), nullable=False, server_default=""),
        sa.Column("responsable_datos", sa.String(150), nullable=False, server_default=""),
        sa.Column("politica_version", sa.String(20), nullable=False, server_default="1.0"),
        sa.Column("politica_fecha", sa.String(40), nullable=False, server_default=""),
        sa.Column("actualizado_por", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("id = 1", name="configuracion_negocio_id_check"),
    )


def downgrade() -> None:
    """Elimina `configuracion_negocio` (se pierden los datos del negocio guardados)."""
    op.drop_table("configuracion_negocio")
