"""Alertas automaticas de stock bajo (Celery Beat, RF-008).

Revisa periodicamente la vista `vw_alertas_stock_bajo` (productos activos
con `stock_actual <= stock_minimo`) y crea una `Notificacion` por
producto. No duplica avisos: si el producto ya tiene una notificacion de
tipo STOCK_BAJO sin leer, no crea otra (evita reenviar la misma alerta en
cada corrida mientras el propietario no la marque como leida).
"""

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.celery_app import celery
from app.core.database import SessionLocal
from app.models.notificacion import Notificacion, TipoNotificacion

logger = logging.getLogger(__name__)

_CONSULTA_ALERTAS = text(
    "SELECT id, nombre, stock_actual, stock_minimo FROM vw_alertas_stock_bajo"
)


def revisar_stock_bajo_impl(db: Session) -> int:
    """Crea notificaciones de stock bajo para los productos que las necesiten.

    Args:
        db: Sesion de SQLAlchemy activa.

    Returns:
        int: Cantidad de notificaciones nuevas creadas.
    """
    productos_en_alerta = db.execute(_CONSULTA_ALERTAS).all()

    creadas = 0
    for producto_id, nombre, stock_actual, stock_minimo in productos_en_alerta:
        ya_notificado = (
            db.query(Notificacion.id)
            .filter(
                Notificacion.producto_id == producto_id,
                Notificacion.tipo == TipoNotificacion.STOCK_BAJO,
                Notificacion.leida.is_(False),
            )
            .first()
        )
        if ya_notificado is not None:
            continue

        db.add(
            Notificacion(
                tipo=TipoNotificacion.STOCK_BAJO,
                producto_id=producto_id,
                mensaje=(
                    f"Stock bajo: {nombre} tiene {stock_actual} unidades "
                    f"(minimo configurado: {stock_minimo})."
                ),
            )
        )
        creadas += 1

    db.commit()
    return creadas


@celery.task(name="alertas.revisar_stock_bajo")
def revisar_stock_bajo() -> int:
    """Punto de entrada de Celery: abre su propia sesion y delega en `revisar_stock_bajo_impl`.

    Returns:
        int: Cantidad de notificaciones nuevas creadas.
    """
    db = SessionLocal()
    try:
        creadas = revisar_stock_bajo_impl(db)
        logger.info("Revision de stock bajo: %d notificacion(es) nueva(s).", creadas)
        return creadas
    finally:
        db.close()
