"""Arranca el agente con la configuracion de `.env` (host y puerto)."""

import uvicorn

from app.config import get_settings

if __name__ == "__main__":
    config = get_settings()
    uvicorn.run("app.main:app", host=config.host, port=config.puerto)
