"""Instancia de Celery, separada del entrypoint de FastAPI.

Mantener esta instancia en su propio modulo permite que main.py exponga
`celery` (para `celery -A main.celery worker`) sin acoplar la
configuracion de tareas asincronas a la definicion de la app FastAPI.
"""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery = Celery(
    "pinateria_demo",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.respaldos", "app.tasks.alertas"],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Bogota",
    enable_utc=True,
    beat_schedule={
        # Respaldo diario de PostgreSQL, 2:30 a. m. hora de Bogota (fuera del horario de la tienda).
        "respaldo-diario": {
            "task": "respaldos.respaldar_base_de_datos",
            "schedule": crontab(hour=2, minute=30),
        },
        # Revision de stock bajo (RF-008), cada 15 minutos.
        "alertas-stock-bajo": {
            "task": "alertas.revisar_stock_bajo",
            "schedule": crontab(minute="*/15"),
        },
    },
)
