"""esquema inicial

Migracion inicial escrita a mano (no generada con --autogenerate, ya que
este entorno no tiene acceso al Postgres real). Replica exactamente
schema.sql v1.0 / Diseno de Base de Datos v1.1: tipos enumerados, las
11 tablas, sus constraints, indices (incluida la extension pg_trgm y el
indice GIN de busqueda por nombre) y la vista vw_alertas_stock_bajo.

Revision ID: 0001
Revises:
Create Date: 2026-09-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


rol_usuario = postgresql.ENUM("administrador", "vendedor", "propietario", name="rol_usuario", create_type=False)
tipo_producto = postgresql.ENUM("unidad", "paquete", "ancheta", name="tipo_producto", create_type=False)
metodo_pago = postgresql.ENUM("efectivo", "tarjeta", "transferencia", name="metodo_pago", create_type=False)
estado_compra = postgresql.ENUM("pendiente", "recibida", "cancelada", name="estado_compra", create_type=False)
tipo_ajuste = postgresql.ENUM("entrada", "salida", "merma", "correccion", name="tipo_ajuste", create_type=False)
tipo_notificacion = postgresql.ENUM("stock_bajo", "sistema", name="tipo_notificacion", create_type=False)


def upgrade() -> None:
    """Crea extension, tipos, tablas, indices y vista del esquema inicial."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Los tipos se crean aqui de forma explicita (create_type=False evita que
    # `op.create_table` intente crearlos otra vez y falle con DuplicateObject).
    bind = op.get_bind()
    rol_usuario.create(bind, checkfirst=True)
    tipo_producto.create(bind, checkfirst=True)
    metodo_pago.create(bind, checkfirst=True)
    estado_compra.create(bind, checkfirst=True)
    tipo_ajuste.create(bind, checkfirst=True)
    tipo_notificacion.create(bind, checkfirst=True)

    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("username", sa.String(60), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("rol", rol_usuario, nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "categorias",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(80), nullable=False, unique=True),
        sa.Column("descripcion", sa.String(255), nullable=True),
    )

    op.create_table(
        "productos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column("descripcion", sa.String(255), nullable=True),
        sa.Column(
            "categoria_id",
            sa.Integer(),
            sa.ForeignKey("categorias.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("codigo_barras", sa.String(50), nullable=True),
        sa.Column("tipo", tipo_producto, nullable=False, server_default="unidad"),
        sa.Column("precio_venta", sa.Numeric(10, 2), nullable=False),
        sa.Column("stock_actual", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stock_minimo", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("precio_venta >= 0", name="productos_precio_venta_check"),
        sa.CheckConstraint("stock_actual >= 0", name="productos_stock_actual_check"),
        sa.CheckConstraint("stock_minimo >= 0", name="productos_stock_minimo_check"),
    )
    op.create_index(
        "ux_productos_codigo_barras",
        "productos",
        ["codigo_barras"],
        unique=True,
        postgresql_where=sa.text("codigo_barras IS NOT NULL"),
    )
    op.create_index("ix_productos_categoria", "productos", ["categoria_id"])
    op.execute(
        "CREATE INDEX ix_productos_nombre_trgm ON productos USING gin (nombre gin_trgm_ops)"
    )

    op.create_table(
        "producto_componentes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "producto_padre_id",
            sa.Integer(),
            sa.ForeignKey("productos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "producto_componente_id",
            sa.Integer(),
            sa.ForeignKey("productos.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("cantidad", sa.Numeric(10, 2), nullable=False),
        sa.UniqueConstraint("producto_padre_id", "producto_componente_id", name="uq_producto_componente"),
        sa.CheckConstraint("producto_padre_id <> producto_componente_id", name="ck_no_auto_referencia"),
        sa.CheckConstraint("cantidad > 0", name="producto_componentes_cantidad_check"),
    )
    op.create_index("ix_componentes_padre", "producto_componentes", ["producto_padre_id"])
    op.create_index("ix_componentes_hijo", "producto_componentes", ["producto_componente_id"])

    op.create_table(
        "proveedores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre_empresa", sa.String(150), nullable=False),
        sa.Column("nombre_contacto", sa.String(120), nullable=True),
        sa.Column("telefono", sa.String(30), nullable=True),
        sa.Column("email", sa.String(120), nullable=True),
        sa.Column("direccion", sa.String(255), nullable=True),
        sa.Column("notas", sa.String(255), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "ventas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "usuario_id",
            sa.Integer(),
            sa.ForeignKey("usuarios.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("metodo_pago", metodo_pago, nullable=False, server_default="efectivo"),
        sa.Column("total", sa.Numeric(10, 2), nullable=False),
        sa.CheckConstraint("total >= 0", name="ventas_total_check"),
    )
    op.create_index("ix_ventas_fecha", "ventas", ["fecha"])
    op.create_index("ix_ventas_usuario", "ventas", ["usuario_id"])

    op.create_table(
        "detalle_ventas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("venta_id", sa.Integer(), sa.ForeignKey("ventas.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "producto_id",
            sa.Integer(),
            sa.ForeignKey("productos.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("precio_unitario", sa.Numeric(10, 2), nullable=False),
        sa.Column("subtotal", sa.Numeric(10, 2), nullable=False),
        sa.CheckConstraint("cantidad > 0", name="detalle_ventas_cantidad_check"),
        sa.CheckConstraint("precio_unitario >= 0", name="detalle_ventas_precio_unitario_check"),
        sa.CheckConstraint("subtotal >= 0", name="detalle_ventas_subtotal_check"),
    )
    op.create_index("ix_detalle_ventas_venta", "detalle_ventas", ["venta_id"])
    op.create_index("ix_detalle_ventas_producto", "detalle_ventas", ["producto_id"])

    op.create_table(
        "compras",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "proveedor_id",
            sa.Integer(),
            sa.ForeignKey("proveedores.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "usuario_id",
            sa.Integer(),
            sa.ForeignKey("usuarios.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("estado", estado_compra, nullable=False, server_default="pendiente"),
        sa.Column("total", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.CheckConstraint("total >= 0", name="compras_total_check"),
    )
    op.create_index("ix_compras_proveedor", "compras", ["proveedor_id"])
    op.create_index("ix_compras_fecha", "compras", ["fecha"])

    op.create_table(
        "detalle_compras",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("compra_id", sa.Integer(), sa.ForeignKey("compras.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "producto_id",
            sa.Integer(),
            sa.ForeignKey("productos.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("costo_unitario", sa.Numeric(10, 2), nullable=False),
        sa.Column("subtotal", sa.Numeric(10, 2), nullable=False),
        sa.CheckConstraint("cantidad > 0", name="detalle_compras_cantidad_check"),
        sa.CheckConstraint("costo_unitario >= 0", name="detalle_compras_costo_unitario_check"),
        sa.CheckConstraint("subtotal >= 0", name="detalle_compras_subtotal_check"),
    )
    op.create_index("ix_detalle_compras_compra", "detalle_compras", ["compra_id"])
    op.create_index("ix_detalle_compras_producto", "detalle_compras", ["producto_id"])

    op.create_table(
        "ajustes_inventario",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "producto_id",
            sa.Integer(),
            sa.ForeignKey("productos.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "usuario_id",
            sa.Integer(),
            sa.ForeignKey("usuarios.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("tipo", tipo_ajuste, nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("motivo", sa.String(255), nullable=False),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("cantidad <> 0", name="ajustes_inventario_cantidad_check"),
    )
    op.create_index("ix_ajustes_producto", "ajustes_inventario", ["producto_id"])
    op.create_index("ix_ajustes_fecha", "ajustes_inventario", ["fecha"])

    op.create_table(
        "notificaciones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tipo", tipo_notificacion, nullable=False, server_default="stock_bajo"),
        sa.Column(
            "producto_id",
            sa.Integer(),
            sa.ForeignKey("productos.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("mensaje", sa.String(255), nullable=False),
        sa.Column("leida", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("creada_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_notificaciones_leida", "notificaciones", ["leida"])

    op.execute(
        """
        CREATE VIEW vw_alertas_stock_bajo AS
        SELECT p.id, p.nombre, p.stock_actual, p.stock_minimo, c.nombre AS categoria
        FROM productos p
        JOIN categorias c ON c.id = p.categoria_id
        WHERE p.activo = TRUE
          AND p.stock_actual <= p.stock_minimo
        """
    )


def downgrade() -> None:
    """Revierte el esquema inicial completo, en orden inverso de dependencias."""
    op.execute("DROP VIEW IF EXISTS vw_alertas_stock_bajo")

    op.drop_table("notificaciones")
    op.drop_table("ajustes_inventario")
    op.drop_table("detalle_compras")
    op.drop_table("compras")
    op.drop_table("detalle_ventas")
    op.drop_table("ventas")
    op.drop_table("proveedores")
    op.drop_table("producto_componentes")
    op.drop_table("productos")
    op.drop_table("categorias")
    op.drop_table("usuarios")

    bind = op.get_bind()
    tipo_notificacion.drop(bind, checkfirst=True)
    tipo_ajuste.drop(bind, checkfirst=True)
    estado_compra.drop(bind, checkfirst=True)
    metodo_pago.drop(bind, checkfirst=True)
    tipo_producto.drop(bind, checkfirst=True)
    rol_usuario.drop(bind, checkfirst=True)
