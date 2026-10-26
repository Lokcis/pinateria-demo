# Checklist manual — lo que las pruebas automatizadas NO cubren

Este archivo complementa `tests/test_hu01_venta.py` (backend, pytest) y
`src/**/*.test.{js,jsx}` (frontend, vitest). Lo de aquí requiere hardware
físico, un entorno desplegado, o verificación humana — no se puede
automatizar en un pipeline de CI simple.

## HU-01 — criterios que dependen de hardware

- [x] **Escaneo con el lector USB real**: confirmado en equipo de
      desarrollo (27-9-2026) — el producto se agrega al carrito de
      inmediato, sin ajustar `UMBRAL_RAFAGA_MS` (50ms).
- [x] **Impresión física en la Epson TM-T20II** (`AGENTE_MODO=escpos`):
      confirmado en equipo de desarrollo (27-9-2026) — ticket legible,
      corte de papel correcto, y la reimpresión desde "Ventas de hoy"
      también funciona.
- [ ] **Tiempo real de impresión end-to-end** ("dispare la orden de
      impresión ... en menos de 2 segundos", HU-01): pendiente cronometrar
      con reloj, desde que se confirma el pago hasta que sale el ticket
      físico, en la red real de la tienda (no en localhost/equipo de dev).
- [x] **Regla de "no ventas parciales" con stock real** (RF-004, criterio
      de HU-01): confirmado (27-9-2026) — al agotarse el stock del
      componente (piñata) de un producto compuesto, la venta del paquete
      se rechaza (409) y no descuenta nada.
- [x] **RBAC — rol `propietario` sin acceso al POS**: confirmado
      (27-9-2026) — muestra el mensaje de solo lectura en vez del punto
      de venta.

## Adendo v2 — criterios que dependen de hardware o de un entorno desplegado

- [ ] **Ticket con pagos mixtos en la Epson** (HU-05): pagos con plataforma, recibido y vueltas,
      y descuento, legibles y sin cortarse en 48 columnas.
- [ ] **Migración 0002 en staging** con una copia de la base real: las ventas anteriores
      conservan su método de pago (ver `DEPLOY.md`, paso 4).
- [ ] **WhatsApp de la lista de compras desde el celular** (HU-10): abre el chat con el mensaje.
- [ ] **Venta con pagos mixtos en menos de 2 s** contra el staging real (HU-05).
- [ ] **Aceptación** de HU-05, HU-06 (vendedor) y HU-09, HU-10 (propietario).

## Definición de Terminado (DoD) — Plan de Trabajo (`docs/05`), sección 4

- [ ] **Entorno de Staging**: el código desplegado y corriendo en el
      contenedor Docker real (Ubuntu Server), no solo en local.
- [ ] **Rendimiento POS bajo estrés básico**: repetir
      `test_venta_completa_en_menos_de_dos_segundos` contra el staging
      real, no contra el backend corriendo en localhost del desarrollador.
- [ ] **Uptime Kuma**: confirmar que el backend y el agente de impresión
      están registrados y en estado "up".
- [ ] **Respaldo de PostgreSQL**: correr el script de respaldo (Celery
      Beat) y confirmar que el `.dump` se genera correctamente.
- [ ] **Guía rápida para el vendedor**: documento (digital o impreso)
      explicando cómo escanear, buscar manual, y confirmar una venta.

## Cómo correr lo que sí está automatizado

### Backend (pytest)

```bash
cd backend
pip install -r requirements-dev.txt

# TEST_DATABASE_URL debe ser una base de PRUEBA, nunca la de produccion
export TEST_DATABASE_URL="postgresql://postgres:clave@localhost:5432/pinateria_demo_test"
pytest -v
```

### Frontend (vitest)

```bash
cd frontend
npm install
npm run test
```
