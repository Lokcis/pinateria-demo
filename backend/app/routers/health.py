"""Router de verificacion de salud del servicio."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/")
@router.get("/health")
@router.get("/api/health")
def health_check() -> dict[str, str]:
    """Verifica que el servicio este arriba y respondiendo.

    Returns:
        dict[str, str]: Estado del servicio, nombre y version.
    """
    return {
        "status": "ok",
        "service": "Piñatería Demo API",
        "version": "1.0.0",
    }
