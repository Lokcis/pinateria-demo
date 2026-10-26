"""Entrypoint de la aplicacion.

Expone dos objetos, mismo contrato que ya usa `docker-compose.yml`:
    - `app`: instancia de FastAPI, usada por `gunicorn main:app`.
    - `celery`: instancia de Celery, usada por `celery -A main.celery worker`
      y `celery -A main.celery beat`.

Este archivo debe permanecer delgado: la configuracion vive en
`app/core/config.py`, los modelos en `app/models/`, y los endpoints en
`app/routers/`. No agregar logica de negocio aqui.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.celery_app import celery
from app.core.config import settings
from app.routers import (
    auth,
    autoregistro,
    caja,
    categorias,
    clientes,
    compras,
    dashboard,
    descuentos,
    ganancias,
    gastos,
    health,
    negocio,
    notificaciones,
    productos,
    proveedores,
    solicitudes_titular,
    usuarios,
    ventas,
)

app = FastAPI(
    title="Piñatería Demo API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origen.strip() for origen in settings.cors_origins.split(",") if origen.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],  # el navegador lee el nombre del archivo que descarga (CSV)
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(categorias.router)
app.include_router(productos.router)
app.include_router(ventas.router)
app.include_router(descuentos.router)
app.include_router(clientes.router)
app.include_router(negocio.router)
app.include_router(autoregistro.admin)
app.include_router(autoregistro.publico)
app.include_router(solicitudes_titular.router)
app.include_router(ganancias.router)
app.include_router(gastos.router)
app.include_router(caja.router)
app.include_router(proveedores.router)
app.include_router(compras.router)
app.include_router(dashboard.router)
app.include_router(notificaciones.router)
app.include_router(usuarios.router)

__all__ = ["app", "celery"]
