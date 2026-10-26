"""gastos, categorias de gasto y compras con forma de pago (Adendo v3, Fase G1)

Crea `categorias_gasto` (con la siembra de las categorias iniciales) y `gastos`, agrega tres columnas
OPCIONALES a `compras` (`metodo_pago`, `plataforma`, `recibida_en`) y crea la vista `vw_gastos_unificados`
(docs/03-diseno-base-de-datos.md, capitulo 8; docs/12-gastos-y-corte-de-caja.md).

NO transforma datos: las compras anteriores quedan con las tres columnas en NULL (suman en los gastos,
pero no afectan la caja) y los tipos `metodo_pago` y `plataforma_transferencia` ya existen. Aun asi,
antes de aplicarla en produccion: respaldo manual y aprobacion en `MIGRACIONES_APROBADAS`.

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

metodo_pago = postgresql.ENUM("efectivo", "tarjeta", "transferencia", name="metodo_pago", create_type=False)
plataforma_transferencia = postgresql.ENUM("nequi", "daviplata", name="plataforma_transferencia", create_type=False)

CATEGORIAS_INICIALES = [
    ("Compra de mercancía", True),
    ("Arriendo", False),
    ("Servicios públicos", False),
    ("Nómina", False),
    ("Transporte", False),
    ("Publicidad", False),
    ("Mantenimiento", False),
    ("Impuestos", False),
    ("Otros", False),
]

VISTA_GASTOS_UNIFICADOS = """
CREATE VIEW vw_gastos_unificados AS
SELECT 'gasto'::text AS origen, g.id AS origen_id, g.fecha, g.categoria_id, c.nombre AS categoria,
       g.descripcion, g.beneficiario, g.monto, g.metodo_pago, g.plataforma, g.registrado_por_id,
       (g.anulado_en IS NOT NULL) AS anulado, g.creado_en
FROM gastos g
JOIN categorias_gasto c ON c.id = g.categoria_id
UNION ALL
SELECT 'compra'::text, k.id,
       (COALESCE(k.recibida_en, k.fecha) AT TIME ZONE 'America/Bogota')::date,
       s.id, COALESCE(s.nombre, 'Compra de mercancía'),
       'Compra #' || k.id || ' — ' || p.nombre_empresa, p.nombre_empresa, k.total, k.metodo_pago, k.plataforma,
       k.usuario_id, FALSE, COALESCE(k.recibida_en, k.fecha)
FROM compras k
JOIN proveedores p ON p.id = k.proveedor_id
LEFT JOIN categorias_gasto s ON s.es_sistema
WHERE k.estado = 'recibida'
"""


def upgrade() -> None:
    """Crea las categorias y los gastos, siembra las categorias, extiende `compras` y crea la vista unificada."""
    categorias = op.create_table(
        "categorias_gasto",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(60), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("es_sistema", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("creada_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.execute("CREATE UNIQUE INDEX ux_categorias_gasto_nombre ON categorias_gasto (lower(nombre))")
    op.create_index(
        "ux_categorias_gasto_sistema",
        "categorias_gasto",
        ["es_sistema"],
        unique=True,
        postgresql_where=sa.text("es_sistema"),
    )
    op.bulk_insert(categorias, [{"nombre": nombre, "es_sistema": es_sistema} for nombre, es_sistema in CATEGORIAS_INICIALES])

    op.create_table(
        "gastos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "fecha",
            sa.Date(),
            nullable=False,
            server_default=sa.text("((now() AT TIME ZONE 'America/Bogota')::date)"),
        ),
        sa.Column(
            "categoria_id", sa.Integer(), sa.ForeignKey("categorias_gasto.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("descripcion", sa.String(255), nullable=False),
        sa.Column("beneficiario", sa.String(120), nullable=True),
        sa.Column("monto", sa.Numeric(10, 2), nullable=False),
        sa.Column("metodo_pago", metodo_pago, nullable=False),
        sa.Column("plataforma", plataforma_transferencia, nullable=True),
        sa.Column(
            "registrado_por_id", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "actualizado_por_id", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True
        ),
        sa.Column("anulado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("anulado_por_id", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("motivo_anulacion", sa.String(255), nullable=True),
        sa.CheckConstraint("monto > 0", name="gastos_monto_check"),
        sa.CheckConstraint("plataforma IS NULL OR metodo_pago = 'transferencia'", name="ck_gasto_plataforma"),
        sa.CheckConstraint(
            "(anulado_en IS NULL AND anulado_por_id IS NULL AND motivo_anulacion IS NULL) "
            "OR (anulado_en IS NOT NULL AND anulado_por_id IS NOT NULL AND motivo_anulacion IS NOT NULL)",
            name="ck_gasto_anulacion",
        ),
    )
    op.create_index("ix_gastos_fecha", "gastos", ["fecha", "categoria_id"])
    op.create_index("ix_gastos_registrado_por", "gastos", ["registrado_por_id", "creado_en"])
    op.create_index("ix_gastos_creado_en", "gastos", ["creado_en"])

    op.add_column("compras", sa.Column("metodo_pago", metodo_pago, nullable=True))
    op.add_column("compras", sa.Column("plataforma", plataforma_transferencia, nullable=True))
    op.add_column("compras", sa.Column("recibida_en", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint("ck_compra_plataforma", "compras", "plataforma IS NULL OR metodo_pago = 'transferencia'")

    op.execute(VISTA_GASTOS_UNIFICADOS)


def downgrade() -> None:
    """Revierte la 0009: se pierden los gastos, las categorias y la forma de pago de las compras."""
    op.execute("DROP VIEW IF EXISTS vw_gastos_unificados")
    op.drop_constraint("ck_compra_plataforma", "compras", type_="check")
    op.drop_column("compras", "recibida_en")
    op.drop_column("compras", "plataforma")
    op.drop_column("compras", "metodo_pago")
    op.drop_index("ix_gastos_creado_en", table_name="gastos")
    op.drop_index("ix_gastos_registrado_por", table_name="gastos")
    op.drop_index("ix_gastos_fecha", table_name="gastos")
    op.drop_table("gastos")
    op.drop_index("ux_categorias_gasto_sistema", table_name="categorias_gasto")
    op.execute("DROP INDEX IF EXISTS ux_categorias_gasto_nombre")
    op.drop_table("categorias_gasto")
