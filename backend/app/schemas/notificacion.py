"""Esquemas Pydantic de la bandeja de notificaciones (Adendo v2, mejora B1: RF-043, HU-10)."""

from datetime import datetime

from pydantic import BaseModel

from app.models.notificacion import TipoNotificacion


class NotificacionOut(BaseModel):
    """Una notificacion de la bandeja del Dashboard.

    Attributes:
        id: Id de la notificacion.
        tipo: Categoria de la notificacion.
        mensaje: Texto guardado al crearla (stock y minimo de ese momento).
        leida: Si ya se marco como leida.
        creada_en: Momento de creacion.
        producto_id: Producto que la origino, o None si se elimino.
        producto_nombre: Nombre actual del producto, o None si se elimino.
    """

    id: int
    tipo: TipoNotificacion
    mensaje: str
    leida: bool
    creada_en: datetime
    producto_id: int | None
    producto_nombre: str | None


class BandejaOut(BaseModel):
    """Respuesta de `GET /notificaciones`.

    Attributes:
        no_leidas: Total de notificaciones sin leer (no depende del limite ni del filtro).
        notificaciones: Las notificaciones pedidas, de la mas reciente a la mas antigua.
    """

    no_leidas: int
    notificaciones: list[NotificacionOut]


class LeerTodasOut(BaseModel):
    """Respuesta de `PATCH /notificaciones/leer-todas`.

    Attributes:
        marcadas: Cuantas notificaciones pasaron de no leidas a leidas.
    """

    marcadas: int
