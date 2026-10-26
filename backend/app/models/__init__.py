"""Paquete de modelos ORM.

Este modulo importa explicitamente todos los modelos para que
`Base.metadata` los conozca al momento de que Alembic autogenere
migraciones (`alembic revision --autogenerate`). Si se agrega un modelo
nuevo y no se importa aqui, Alembic no lo detectara.
"""

from app.models.ajuste_inventario import AjusteInventario, TipoAjuste
from app.models.categoria import Categoria
from app.models.categoria_gasto import CategoriaGasto
from app.models.cliente import (
    Cliente,
    EnlaceAutoregistro,
    EstadoSolicitudTitular,
    MedioAutorizacion,
    OrigenRegistro,
    SolicitudTitular,
    TipoSolicitudTitular,
)
from app.models.compra import Compra, EstadoCompra
from app.models.configuracion_negocio import ConfiguracionNegocio
from app.models.corte_caja import CorteCaja, EstadoCorteCaja
from app.models.descuento import DescuentoGeneral, OrigenDescuento, TipoDescuento, TopeDescuento
from app.models.detalle_compra import DetalleCompra
from app.models.detalle_venta import DetalleVenta
from app.models.gasto import Gasto
from app.models.movimiento_caja import MovimientoCaja, TipoMovimientoCaja
from app.models.notificacion import Notificacion, TipoNotificacion
from app.models.pago_venta import PagoVenta, PlataformaTransferencia
from app.models.producto import Producto, TipoProducto
from app.models.producto_componente import ProductoComponente
from app.models.proveedor import Proveedor
from app.models.usuario import RolUsuario, Usuario
from app.models.venta import MetodoPago, Venta

__all__ = [
    "AjusteInventario",
    "TipoAjuste",
    "Categoria",
    "CategoriaGasto",
    "Cliente",
    "ConfiguracionNegocio",
    "CorteCaja",
    "EstadoCorteCaja",
    "MovimientoCaja",
    "TipoMovimientoCaja",
    "EnlaceAutoregistro",
    "EstadoSolicitudTitular",
    "MedioAutorizacion",
    "OrigenRegistro",
    "SolicitudTitular",
    "TipoSolicitudTitular",
    "Compra",
    "EstadoCompra",
    "DetalleCompra",
    "DetalleVenta",
    "Gasto",
    "DescuentoGeneral",
    "OrigenDescuento",
    "TipoDescuento",
    "TopeDescuento",
    "Notificacion",
    "TipoNotificacion",
    "PagoVenta",
    "PlataformaTransferencia",
    "Producto",
    "TipoProducto",
    "ProductoComponente",
    "Proveedor",
    "RolUsuario",
    "Usuario",
    "MetodoPago",
    "Venta",
]
