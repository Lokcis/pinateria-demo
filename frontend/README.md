# Frontend POS — Piñatería Demo

Cubre las tarjetas Trello **20, 21 y 22** de Fase 1:
- Input híbrido código de barras / búsqueda manual (HU-01).
- Carrito de compras (agregar, quitar, modificar cantidades).
- Pantalla de confirmación de pago (método de pago, resumen, confirmar venta).

## Requisitos

- Node.js 20.19+ o 22.12+ (Vite 8 y Vitest 5) y npm.
- El backend (`backend/`) corriendo y accesible.
- El agente de impresión (`printer-agent/`) corriendo en `localhost` del
  equipo POS (modo mock o escpos, según disponibilidad de hardware).

## Ejecutar en desarrollo

```bash
npm install
cp .env.example .env.local
npm run dev
```

Ajusta `.env.local`:
- `VITE_API_BASE_URL` → URL del backend (en desarrollo, `http://localhost:8000`;
  en producción, la URL del túnel de Cloudflare).
- `VITE_PRINTER_AGENT_URL` → siempre `http://127.0.0.1:9100` (el agente
  corre en la misma máquina que el navegador del POS).

## Compilar para producción

```bash
npm run build
```

Genera `dist/`, listo para servir con Nginx en el mismo contenedor/servidor
o para copiar a `frontend/dist/` del `docker-compose.yml` existente.

## Notas de implementación

- **Autenticación**: el JWT se guarda en `localStorage` (clave `mm_pos_token`)
  y se decodifica en el cliente solo para mostrar el rol en la UI — la
  validación real de firma/expiración la hace siempre el backend en cada
  request.
- **RBAC en la UI**: solo `vendedor` y `administrador` ven la pantalla de
  venta; `propietario` recibe un mensaje de solo lectura (su UI real es el
  Dashboard PWA, tarjetas de Fase 4, aún no construido).
- **Detección de escáner**: el umbral de ráfaga (50ms promedio entre teclas)
  está en `src/components/busqueda-hibrida.jsx` como constante
  `UMBRAL_RAFAGA_MS`. Es un valor de partida (Documento de Arquitectura
  Técnica v1.1); ajústalo una vez el lector físico esté conectado
  (tarjeta #25) y se pueda medir su patrón real.
- **Impresión best-effort**: si `POST /ventas` tiene éxito pero el agente de
  impresión falla (impresora apagada, agente no corriendo), la venta
  **no se revierte** — ya quedó registrada en el backend. Se le avisa al
  vendedor para que reintente o entregue el comprobante de otra forma.

## Verificación realizada

Todos los archivos fueron validados con `esbuild` (transformación JSX +
resolución de imports entre módulos) sin errores. **No se instalaron las
dependencias de npm ni se ejecutó `npm run dev` real**, porque este
entorno no tiene acceso a la red para descargarlas — se recomienda correr
`npm install && npm run dev` en tu máquina antes de darlo por probado.
