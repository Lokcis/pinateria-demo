"""caja y corte de caja (Adendo v3, Fase G2)

Crea los tipos `estado_corte_caja` y `tipo_movimiento_caja` y las tablas `cortes_caja` y `movimientos_caja`
con sus indices (docs/03-diseno-base-de-datos.md, capitulo 8; docs/12-gastos-y-corte-de-caja.md).

NO transforma datos: solo agrega tablas nuevas. Aun asi, antes de aplicarla en produccion: respaldo manual
y aprobacion en `MIGRACIONES_APROBADAS`.

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

estado_corte_caja = postgresql.ENUM("abierta", "cerrada", name="estado_corte_caja", create_type=False)
tipo_movimiento_caja = postgresql.ENUM("ingreso", "retiro", name="tipo_movimiento_caja", create_type=False)


def upgrade() -> None:
    """Crea los tipos, `cortes_caja` (una sola caja abierta a la vez) y `movimientos_caja`."""
    estado_corte_caja.create(op.get_bind(), checkfirst=True)
    tipo_movimiento_caja.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "cortes_caja",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("estado", estado_corte_caja, nullable=False, server_default="abierta"),
        sa.Column("abierta_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("abierta_por_id", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("base_inicial", sa.Numeric(10, 2), nullable=False),
        sa.Column("cerrada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cerrada_por_id", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("ventas_efectivo", sa.Numeric(10, 2), nullable=True),
        sa.Column("ingresos_caja", sa.Numeric(10, 2), nullable=True),
        sa.Column("gastos_efectivo", sa.Numeric(10, 2), nullable=True),
        sa.Column("compras_efectivo", sa.Numeric(10, 2), nullable=True),
        sa.Column("retiros_caja", sa.Numeric(10, 2), nullable=True),
        sa.Column("efectivo_esperado", sa.Numeric(10, 2), nullable=True),
        sa.Column("efectivo_contado", sa.Numeric(10, 2), nullable=True),
        sa.Column("diferencia", sa.Numeric(10, 2), nullable=True),
        sa.Column("ventas_tarjeta", sa.Numeric(10, 2), nullable=True),
        sa.Column("ventas_transferencia", sa.Numeric(10, 2), nullable=True),
        sa.Column("observaciones", sa.String(500), nullable=True),
        sa.CheckConstraint("base_inicial >= 0", name="cortes_caja_base_check"),
        sa.CheckConstraint("efectivo_contado IS NULL OR efectivo_contado >= 0", name="cortes_caja_contado_check"),
        sa.CheckConstraint(
            "(estado = 'abierta' AND cerrada_en IS NULL AND cerrada_por_id IS NULL AND efectivo_esperado IS NULL "
            "AND efectivo_contado IS NULL AND diferencia IS NULL) "
            "OR (estado = 'cerrada' AND cerrada_en IS NOT NULL AND cerrada_por_id IS NOT NULL "
            "AND efectivo_esperado IS NOT NULL AND efectivo_contado IS NOT NULL AND diferencia IS NOT NULL)",
            name="ck_corte_caja_estado",
        ),
    )
    # Una sola caja abierta a la vez: indice unico parcial sobre una expresion constante.
    op.execute("CREATE UNIQUE INDEX ux_cortes_caja_abierta ON cortes_caja ((true)) WHERE estado = 'abierta'")
    op.create_index("ix_cortes_caja_abierta_en", "cortes_caja", ["abierta_en"])

    op.create_table(
        "movimientos_caja",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("corte_id", sa.Integer(), sa.ForeignKey("cortes_caja.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("tipo", tipo_movimiento_caja, nullable=False),
        sa.Column("monto", sa.Numeric(10, 2), nullable=False),
        sa.Column("motivo", sa.String(255), nullable=False),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("monto > 0", name="movimientos_caja_monto_check"),
    )
    op.create_index("ix_movimientos_caja_corte", "movimientos_caja", ["corte_id"])


def downgrade() -> None:
    """Revierte la 0010: se pierden los cortes de caja y sus movimientos."""
    op.drop_index("ix_movimientos_caja_corte", table_name="movimientos_caja")
    op.drop_table("movimientos_caja")
    op.drop_index("ix_cortes_caja_abierta_en", table_name="cortes_caja")
    op.execute("DROP INDEX IF EXISTS ux_cortes_caja_abierta")
    op.drop_table("cortes_caja")
    tipo_movimiento_caja.drop(op.get_bind(), checkfirst=True)
    estado_corte_caja.drop(op.get_bind(), checkfirst=True)
