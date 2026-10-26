"""clientes, Habeas Data y cliente en la venta (Adendo v2, Fase A2)

Escrita a mano, como la 0001. Implementa `docs/03-diseno-base-de-datos.md`,
secciones 7.2, 7.5 a 7.7, 7.9, 7.10 y 7.12 (en el diseno se llamaba 0003; en
Alembic sigue a la 0004):

- Tipos `medio_autorizacion`, `origen_registro`, `tipo_solicitud_titular` y
  `estado_solicitud_titular`.
- Tablas `clientes` (con la autorizacion aparte para promociones), `enlace_autoregistro` y
  `solicitudes_titular`.
- Columna `ventas.cliente_id` (opcional) y su indice.
- Vista `vw_clientes_resumen` (numero de ventas, total comprado, ultima compra).

NO transforma datos: solo agrega objetos nuevos y una columna que admite
NULL. La tabla `enlace_autoregistro` queda vacia hasta que el administrador
genere el enlace de autorregistro.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


tipo_descuento = postgresql.ENUM("porcentaje", "monto", name="tipo_descuento", create_type=False)
medio_autorizacion = postgresql.ENUM(
    "escrito", "electronico", "verbal", name="medio_autorizacion", create_type=False
)
origen_registro = postgresql.ENUM("empleado", "autoregistro", name="origen_registro", create_type=False)
tipo_solicitud_titular = postgresql.ENUM(
    "consulta", "actualizacion", "supresion", "revocatoria", name="tipo_solicitud_titular", create_type=False
)
estado_solicitud_titular = postgresql.ENUM(
    "recibida", "en_tramite", "resuelta", "rechazada", name="estado_solicitud_titular", create_type=False
)

VISTA_CLIENTES_RESUMEN = """
CREATE VIEW vw_clientes_resumen AS
SELECT c.id AS cliente_id,
       COUNT(v.id)                    AS numero_ventas,
       COALESCE(SUM(v.total), 0)      AS total_comprado,
       MAX(v.fecha)                   AS ultima_compra
FROM clientes c
LEFT JOIN ventas v ON v.cliente_id = c.id
GROUP BY c.id
"""


def upgrade() -> None:
    """Crea clientes, solicitudes de titular, enlace de autorregistro, `ventas.cliente_id` y la vista de resumen."""
    bind = op.get_bind()
    for tipo in (medio_autorizacion, origen_registro, tipo_solicitud_titular, estado_solicitud_titular):
        tipo.create(bind, checkfirst=True)

    op.create_table(
        "clientes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column("documento", sa.String(30), nullable=True),
        sa.Column("telefono", sa.String(15), nullable=True),
        sa.Column("email", sa.String(120), nullable=True),
        sa.Column("descuento_tipo", tipo_descuento, nullable=True),
        sa.Column("descuento_valor", sa.Numeric(10, 2), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("acepta_publicidad", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("publicidad_fecha", sa.DateTime(timezone=True), nullable=True),
        sa.Column("autorizacion_fecha", sa.DateTime(timezone=True), nullable=False),
        sa.Column("autorizacion_medio", medio_autorizacion, nullable=False),
        sa.Column("autorizacion_version", sa.String(20), nullable=False),
        sa.Column("origen_registro", origen_registro, nullable=False, server_default="empleado"),
        sa.Column(
            "autorizacion_registrada_por",
            sa.Integer(),
            sa.ForeignKey("usuarios.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("autorizacion_revocada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("anonimizado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "(origen_registro = 'empleado') = (autorizacion_registrada_por IS NOT NULL)",
            name="ck_cliente_registrador",
        ),
        sa.CheckConstraint("(descuento_tipo IS NULL) = (descuento_valor IS NULL)", name="ck_cliente_descuento_completo"),
        sa.CheckConstraint(
            "descuento_valor IS NULL OR (descuento_valor > 0 "
            "AND (descuento_tipo <> 'porcentaje' OR descuento_valor <= 100))",
            name="ck_cliente_descuento_valor",
        ),
    )
    op.create_index(
        "ux_clientes_documento", "clientes", ["documento"], unique=True, postgresql_where=sa.text("documento IS NOT NULL")
    )
    op.create_index(
        "ix_clientes_nombre_trgm",
        "clientes",
        ["nombre"],
        postgresql_using="gin",
        postgresql_ops={"nombre": "gin_trgm_ops"},
    )
    op.create_index("ix_clientes_telefono", "clientes", ["telefono"])

    op.create_table(
        "enlace_autoregistro",
        sa.Column("id", sa.SmallInteger(), primary_key=True, server_default="1"),
        sa.Column("token", sa.String(64), nullable=False, unique=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("actualizado_por", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("id = 1", name="enlace_autoregistro_id_check"),
    )

    op.create_table(
        "solicitudes_titular",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cliente_id", sa.Integer(), sa.ForeignKey("clientes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("tipo", tipo_solicitud_titular, nullable=False),
        sa.Column("descripcion", sa.String(500), nullable=True),
        sa.Column("estado", estado_solicitud_titular, nullable=False, server_default="recibida"),
        sa.Column("recibida_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("fecha_limite", sa.Date(), nullable=False),
        sa.Column("resuelta_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("atendida_por", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("respuesta", sa.String(500), nullable=True),
    )
    op.create_index("ix_solicitudes_cliente", "solicitudes_titular", ["cliente_id"])
    op.create_index("ix_solicitudes_estado", "solicitudes_titular", ["estado"])

    op.add_column(
        "ventas",
        sa.Column("cliente_id", sa.Integer(), sa.ForeignKey("clientes.id", ondelete="RESTRICT"), nullable=True),
    )
    op.create_index("ix_ventas_cliente", "ventas", ["cliente_id"])

    op.execute(VISTA_CLIENTES_RESUMEN)


def downgrade() -> None:
    """Elimina lo creado por la 0005 (las ventas con cliente pierden la asociacion)."""
    op.execute("DROP VIEW IF EXISTS vw_clientes_resumen")
    op.drop_index("ix_ventas_cliente", table_name="ventas")
    op.drop_column("ventas", "cliente_id")
    op.drop_table("solicitudes_titular")
    op.drop_table("enlace_autoregistro")
    op.drop_table("clientes")

    bind = op.get_bind()
    for tipo in (estado_solicitud_titular, tipo_solicitud_titular, origen_registro, medio_autorizacion):
        tipo.drop(bind, checkfirst=True)
