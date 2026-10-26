"""pagos mixtos, descuentos y columnas de costo (Adendo v2, Fase A1)

Escrita a mano, como la 0001. Implementa `docs/03-diseno-base-de-datos.md`,
secciones 7.2 a 7.4.1, 7.7 y 7.12:

- Tipos `plataforma_transferencia`, `tipo_descuento` y `origen_descuento`.
- Tablas `pagos_venta`, `descuento_general` y `tope_descuento`.
- Columnas `subtotal`, `descuento_*` y `ajuste_redondeo` en `ventas` y
  `descuento_prorrateado` en `detalle_ventas`.
- Columnas `costo_unitario` en `productos` y `detalle_ventas`: son de la
  Fase A3, pero se adelantan aqui (A3 aprobada) para que cada venta desde A1
  guarde el costo vigente y el margen historico quede completo. La vista
  `vw_margen_detalle` sigue en la 0004.

TRANSFORMA DATOS: calcula `subtotal` y `ajuste_redondeo` de las ventas
existentes, crea un pago por cada venta con su metodo y su total, y elimina
`ventas.metodo_pago`. Antes de aplicarla en produccion: respaldo manual y
ensayo en staging con una copia de la base.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


metodo_pago = postgresql.ENUM("efectivo", "tarjeta", "transferencia", name="metodo_pago", create_type=False)
plataforma_transferencia = postgresql.ENUM("nequi", "daviplata", name="plataforma_transferencia", create_type=False)
tipo_descuento = postgresql.ENUM("porcentaje", "monto", name="tipo_descuento", create_type=False)
origen_descuento = postgresql.ENUM(
    "ninguno", "cliente", "general", "manual", name="origen_descuento", create_type=False
)


def upgrade() -> None:
    """Crea pagos y descuentos, migra `ventas.metodo_pago` a `pagos_venta` y agrega las columnas de costo."""
    bind = op.get_bind()
    plataforma_transferencia.create(bind, checkfirst=True)
    tipo_descuento.create(bind, checkfirst=True)
    origen_descuento.create(bind, checkfirst=True)

    op.create_table(
        "pagos_venta",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("venta_id", sa.Integer(), sa.ForeignKey("ventas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metodo_pago", metodo_pago, nullable=False),
        sa.Column("plataforma", plataforma_transferencia, nullable=True),
        sa.Column("monto", sa.Numeric(10, 2), nullable=False),
        sa.Column("monto_recibido", sa.Numeric(10, 2), nullable=True),
        sa.Column("vueltas", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.CheckConstraint("monto > 0", name="pagos_venta_monto_check"),
        sa.CheckConstraint("vueltas >= 0", name="pagos_venta_vueltas_check"),
        # La plataforma solo aplica a transferencias; la aplicacion la exige en pagos
        # nuevos (las transferencias historicas migradas quedan con plataforma NULL).
        sa.CheckConstraint(
            "plataforma IS NULL OR metodo_pago = 'transferencia'", name="ck_pago_plataforma"
        ),
        sa.CheckConstraint(
            "(metodo_pago = 'efectivo' AND monto_recibido IS NOT NULL "
            "AND monto_recibido >= monto AND vueltas = monto_recibido - monto) "
            "OR (metodo_pago <> 'efectivo' AND monto_recibido IS NULL AND vueltas = 0)",
            name="ck_pago_efectivo",
        ),
    )
    op.create_index("ix_pagos_venta_venta", "pagos_venta", ["venta_id"])
    op.create_index("ix_pagos_venta_metodo", "pagos_venta", ["metodo_pago"])

    op.create_table(
        "tope_descuento",
        sa.Column("id", sa.SmallInteger(), primary_key=True, server_default="1"),
        sa.Column("tope_porcentaje", sa.Numeric(5, 2), nullable=True),
        sa.Column("tope_monto", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "actualizado_por", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True
        ),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("id = 1", name="tope_descuento_id_check"),
        sa.CheckConstraint(
            "tope_porcentaje > 0 AND tope_porcentaje <= 100", name="tope_descuento_tope_porcentaje_check"
        ),
        sa.CheckConstraint("tope_monto > 0", name="tope_descuento_tope_monto_check"),
    )

    op.create_table(
        "descuento_general",
        sa.Column("id", sa.SmallInteger(), primary_key=True, server_default="1"),
        sa.Column("tipo", tipo_descuento, nullable=False),
        sa.Column("valor", sa.Numeric(10, 2), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "actualizado_por", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True
        ),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("id = 1", name="descuento_general_id_check"),
        sa.CheckConstraint("valor > 0", name="descuento_general_valor_check"),
        sa.CheckConstraint("tipo <> 'porcentaje' OR valor <= 100", name="ck_descuento_general_porcentaje"),
    )

    # --- ventas y detalle_ventas -------------------------------------------------
    op.add_column("ventas", sa.Column("subtotal", sa.Numeric(10, 2), nullable=True))
    op.add_column(
        "ventas", sa.Column("descuento_origen", origen_descuento, nullable=False, server_default="ninguno")
    )
    op.add_column("ventas", sa.Column("descuento_tipo", tipo_descuento, nullable=True))
    op.add_column("ventas", sa.Column("descuento_valor", sa.Numeric(10, 2), nullable=True))
    op.add_column("ventas", sa.Column("descuento_monto", sa.Numeric(10, 2), nullable=False, server_default="0"))
    op.add_column("ventas", sa.Column("ajuste_redondeo", sa.Numeric(10, 2), nullable=False, server_default="0"))
    op.create_check_constraint("ventas_descuento_monto_check", "ventas", "descuento_monto >= 0")

    op.add_column(
        "detalle_ventas",
        sa.Column("descuento_prorrateado", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )
    op.create_check_constraint(
        "detalle_ventas_descuento_prorrateado_check", "detalle_ventas", "descuento_prorrateado >= 0"
    )

    # --- Costos (Fase A3, adelantados) -------------------------------------------
    op.add_column("productos", sa.Column("costo_unitario", sa.Numeric(10, 2), nullable=True))
    op.create_check_constraint("productos_costo_unitario_check", "productos", "costo_unitario >= 0")
    op.add_column("detalle_ventas", sa.Column("costo_unitario", sa.Numeric(10, 2), nullable=True))
    op.create_check_constraint("detalle_ventas_costo_unitario_check", "detalle_ventas", "costo_unitario >= 0")

    # --- Datos existentes ---------------------------------------------------------
    # subtotal = suma de las lineas; ajuste = total - subtotal (redondeo a $50 ya aplicado);
    # sin descuento. Asi se cumple total = subtotal - descuento_monto + ajuste_redondeo.
    op.execute(
        "UPDATE ventas v SET subtotal = "
        "(SELECT COALESCE(SUM(d.subtotal), 0) FROM detalle_ventas d WHERE d.venta_id = v.id)"
    )
    op.execute("UPDATE ventas SET ajuste_redondeo = total - subtotal")
    op.alter_column("ventas", "subtotal", nullable=False)
    op.create_check_constraint("ventas_subtotal_check", "ventas", "subtotal >= 0")
    op.create_check_constraint("ck_ventas_descuento", "ventas", "descuento_monto <= subtotal")
    op.create_check_constraint(
        "ck_ventas_total_coherente", "ventas", "total = subtotal - descuento_monto + ajuste_redondeo"
    )

    # Un pago por venta con su metodo y su total. En efectivo no se conocia el monto
    # recibido: se toma igual al total (vueltas 0). Las ventas en 0 no llevan pagos.
    op.execute(
        "INSERT INTO pagos_venta (venta_id, metodo_pago, monto, monto_recibido, vueltas) "
        "SELECT id, metodo_pago, total, CASE WHEN metodo_pago = 'efectivo' THEN total END, 0 "
        "FROM ventas WHERE total > 0"
    )
    op.drop_column("ventas", "metodo_pago")


def downgrade() -> None:
    """Revierte la 0002: reconstruye `ventas.metodo_pago` con el pago de mayor monto y borra lo nuevo.

    Pierde informacion: los pagos mixtos se reducen a un solo metodo, y los
    descuentos, las vueltas y los costos se descartan.
    """
    op.add_column(
        "ventas",
        sa.Column("metodo_pago", metodo_pago, nullable=False, server_default="efectivo"),
    )
    op.execute(
        "UPDATE ventas v SET metodo_pago = p.metodo_pago FROM ("
        "  SELECT DISTINCT ON (venta_id) venta_id, metodo_pago FROM pagos_venta"
        "  ORDER BY venta_id, monto DESC, id"
        ") p WHERE p.venta_id = v.id"
    )

    op.drop_constraint("detalle_ventas_costo_unitario_check", "detalle_ventas", type_="check")
    op.drop_column("detalle_ventas", "costo_unitario")
    op.drop_constraint("productos_costo_unitario_check", "productos", type_="check")
    op.drop_column("productos", "costo_unitario")

    op.drop_constraint("detalle_ventas_descuento_prorrateado_check", "detalle_ventas", type_="check")
    op.drop_column("detalle_ventas", "descuento_prorrateado")

    op.drop_constraint("ck_ventas_total_coherente", "ventas", type_="check")
    op.drop_constraint("ck_ventas_descuento", "ventas", type_="check")
    op.drop_constraint("ventas_subtotal_check", "ventas", type_="check")
    op.drop_constraint("ventas_descuento_monto_check", "ventas", type_="check")
    for columna in ("ajuste_redondeo", "descuento_monto", "descuento_valor", "descuento_tipo", "descuento_origen", "subtotal"):
        op.drop_column("ventas", columna)

    op.drop_table("descuento_general")
    op.drop_table("tope_descuento")
    op.drop_index("ix_pagos_venta_metodo", table_name="pagos_venta")
    op.drop_index("ix_pagos_venta_venta", table_name="pagos_venta")
    op.drop_table("pagos_venta")

    bind = op.get_bind()
    origen_descuento.drop(bind, checkfirst=True)
    tipo_descuento.drop(bind, checkfirst=True)
    plataforma_transferencia.drop(bind, checkfirst=True)
