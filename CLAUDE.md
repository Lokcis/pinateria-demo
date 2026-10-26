# Piñatería Demo — contexto del proyecto

Sistema de ventas e inventario (POS + inventario + compras + gastos + caja + dashboard PWA) para una piñatería.
Documentación (visión, historias, base de datos, arquitectura, plan, estado, adendos) en `docs/`; empieza por `docs/README.md`.

## Estructura

- `backend/` — FastAPI + SQLAlchemy + Alembic + Celery (respaldos). Tests: `pytest` (necesita `TEST_DATABASE_URL`).
- `frontend/` — React + Vite + Tailwind v4. Tests: `npm test`. Build: `npm run build`.
- `printer-agent/` — agente local de impresión (Epson TM-T20II). Corre en el PC del POS, nunca en el servidor.
- `nginx/nginx.conf`, `docker-compose.yml`, `DEPLOY.md`, `deploy/` — infraestructura y guía de despliegue de referencia.

## Flujo de Git

`rama de trabajo → PR → dev → PR → main`, con merge commit y el CI en verde.

## Convenciones

- Código y comentarios en español. Docstrings en todas las funciones públicas.
- Formas de pago: `efectivo`, `tarjeta`, `transferencia` (Nequi/Daviplata son transferencia con su `plataforma`). Una venta puede tener varios pagos (`pagos_venta`) cuya suma es el total.
- Zona horaria del negocio: `America/Bogota` (el "día" del historial se calcula ahí, no en UTC).
- Modo sin conexión (`docs/11-modo-sin-conexion.md`): toda venta del POS lleva `uuid_cliente` (reenviarla no la duplica); la cola y el catálogo guardado viven en `frontend/src/offline/` (IndexedDB). No se guardan datos de clientes en el navegador.
- Gastos y corte de caja (`docs/12-gastos-y-corte-de-caja.md`): el vendedor solo ve y modifica sus propios gastos (filtro en el servidor); un corte cerrado es una foto inmutable; la caja usa el reloj de la base (`now()`).
- Migraciones: no transforman datos sin aprobación previa y respaldo.
- Los datos de este repositorio son de demostración; no agregues datos reales de ningún negocio ni de personas.
