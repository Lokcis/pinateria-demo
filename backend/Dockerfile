# Dockerfile para el Backend (FastAPI + Celery)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias del sistema útiles (como curl para healthchecks y pg_dump/libpq para respaldos)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    postgresql-client \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivo de requerimientos e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del backend
COPY . .

# Exponer el puerto del backend (FastAPI)
EXPOSE 8000
