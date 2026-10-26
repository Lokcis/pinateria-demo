# Agente de impresión — Piñatería Demo

Servicio local que imprime el ticket de venta en la **Epson TM-T20II** (RF-020).
Corre en el **equipo POS de la tienda**, junto a la impresora USB, y nunca en el
servidor remoto: el navegador del POS le envía el ticket a `http://127.0.0.1:9100`.

```
Navegador (POS) ──POST /imprimir──▶ Agente (127.0.0.1:9100) ──USB/ESC-POS──▶ Epson TM-T20II
```

La impresión es *best-effort*: si falla, la venta ya quedó registrada en el
backend y el POS muestra el aviso con un botón **Reintentar impresión**.

## Instalación en el PC del POS (Windows)

Hay cuatro scripts en esta carpeta; se usan con doble clic. Requisitos: Python 3 (con "Add python.exe to PATH") y Git.

| Script | Para qué |
|---|---|
| `instalar.bat` | Una sola vez: crea `.venv`, instala las dependencias y deja `.env` a partir de `.env.example`. Repetirlo no daña nada. |
| `iniciar.bat` | Arranca el agente en `http://127.0.0.1:9100`. No cierres su ventana. |
| `actualizar.bat` | `git pull --ff-only` y dependencias nuevas. Después hay que reiniciar el agente (cerrar su ventana y abrir `iniciar.bat`). |
| `inicio-automatico.bat` | Hace que el agente arranque solo (minimizado) al iniciar sesión en Windows. `inicio-automatico.bat quitar` lo desactiva. |

Después de `instalar.bat`, edita `.env` (Bloc de notas) para el uso real:

```
AGENTE_MODO=escpos
AGENTE_IMPRESORA_WINDOWS=EPSON TM-T20II Receipt
AGENTE_ORIGENES_PERMITIDOS=https://pos.demo.example.com,http://localhost:5173
```

Sin el dominio público en `AGENTE_ORIGENES_PERMITIDOS`, el navegador bloquea las llamadas del POS al agente: **los tickets
no se imprimen** (las ventas sí se registran). El agente lee `.env` al arrancar: reinícialo tras cambiarlo.

Los scripts son archivos de texto: se pueden leer antes de ejecutarlos. No se distribuye un `.exe` (los empaquetados con
PyInstaller suelen disparar al antivirus y complican `pywin32` y `python-escpos`).

### Instalación manual (desarrollo, Linux o macOS)

```bash
cd printer-agent
python -m venv .venv
.venv\Scripts\activate          # Windows (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
cp .env.example .env
python run.py
```

Comprueba que responde: `http://127.0.0.1:9100/salud` → `{"status":"ok","modo":"mock"}`.

## Logo en el ticket

El ticket imprime arriba el logo de Piñatería Demo (`assets/logo-ticket.png`, en blanco y negro de 1 bit y 336 puntos de ancho, para que se vea limpio en papel térmico). Se controla con `AGENTE_LOGO_TICKET` en `.env`: vacío = sin logo. Si el archivo falta o la impresora no logra imprimirlo, el ticket sale igual, sin logo (el aviso queda en el log del agente). Para cambiar el logo:

```
python tools/generar_logo.py ruta/del/logo-a-color.png assets/logo-ticket.png
```

Al actualizar el PC del POS (`actualizar.bat`) hay que reiniciar el agente; si `.env` ya existía, no hace falta tocarlo (el logo viene activado por defecto).

## Modos

| `AGENTE_MODO` | Qué hace |
|---|---|
| `mock` (por defecto) | No imprime. Guarda cada ticket en `tickets_mock/venta_N.txt` y lo muestra en consola. Sirve para desarrollar sin impresora. |
| `escpos` | Imprime en la Epson TM-T20II y corta el papel. |

## Conectar la impresora real (`AGENTE_MODO=escpos`)

**Opción A — spooler de Windows (la más simple).** Instala el driver de Epson,
mira el nombre exacto en *Configuración → Impresoras y escáneres* y ponlo en `.env`:

```
AGENTE_MODO=escpos
AGENTE_IMPRESORA_WINDOWS=EPSON TM-T20II Receipt
```

**Opción B — USB directo.** Deja `AGENTE_IMPRESORA_WINDOWS` vacío. Usa los IDs
por defecto de la TM-T20II (`0x04b8` / `0x0e15`, configurables con
`AGENTE_USB_VENDOR_ID` / `AGENTE_USB_PRODUCT_ID`). En Windows requiere asociar
la impresora al driver **WinUSB** (con Zadig) y tener `libusb`; en Linux, una
regla `udev` para el usuario que corre el agente.

Si el texto se corta o sobra margen, ajusta `AGENTE_ANCHO_COLUMNAS` (48 → 42).

## API

- `GET /salud` — estado del agente y modo (para Uptime Kuma).
- `POST /imprimir` — imprime un ticket. Devuelve `503` con un mensaje legible si
  la impresora falla (apagada, sin papel, desconectada). Formato del Adendo v2
  (pagos mixtos, recibido, vueltas y descuento):

```json
{
  "venta_id": 9,
  "fecha": "2026-10-08T20:30:00Z",
  "vendedor": "Laura Gómez",
  "subtotal": "30600.00",
  "descuento_tipo": "porcentaje",
  "descuento_valor": "10.00",
  "descuento_monto": "3060.00",
  "ajuste_redondeo": "10.00",
  "total": "27550.00",
  "pagos": [
    {"metodo_pago": "efectivo", "monto": "20000.00", "monto_recibido": "50000.00", "vueltas": "30000.00"},
    {"metodo_pago": "transferencia", "plataforma": "nequi", "monto": "7550.00"}
  ],
  "lineas": [
    {"nombre_producto": "Piñata", "cantidad": 1, "precio_unitario": "30600.00", "subtotal": "30600.00"}
  ]
}
```

  El ticket imprime subtotal, descuento y ajuste por redondeo (solo si los hubo), el total y
  cada pago con su plataforma; en efectivo, lo recibido y las vueltas. Si trae `vendedor` (opcional),
  imprime "Atendió: nombre" bajo el número de venta. El agente **también
  acepta el formato anterior** (`metodo_pago` en lugar de `pagos`, sin `subtotal` ni
  descuento), para poder actualizarlo antes que el servidor.

  **Ventas hechas sin conexión (Fase 9).** Una venta que aún no llegó al servidor no tiene número de venta: el
  POS manda `"venta_id": null` y una `"referencia"` local (letras, números y guion, hasta 30 caracteres; por
  ejemplo `"SC-0003"`). El ticket imprime `Venta SC-0003` en lugar de `Venta #12`, y el modo `mock` guarda el
  archivo como `venta_SC-0003.txt`. Hace falta `venta_id` o `referencia`. **Actualiza este agente antes de usar el
  modo sin conexión**; los tickets de ventas normales funcionan con la versión anterior y con esta.

## CORS y producción

`AGENTE_ORIGENES_PERMITIDOS` debe incluir el dominio desde el que se abre el POS
(en producción, el de Cloudflare Tunnel). El agente responde también al
preflight de *Private Network Access* de Chrome, necesario cuando una página
pública llama a `127.0.0.1`.

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest
```

Cubren el formato del ticket y los endpoints sin hardware. **Lo que requiere la
impresora física** (legibilidad, corte de papel, tiempo de impresión < 2 s) está en
el checklist de `backend/tests/README_pruebas.md`.

## Actualizar

Ejecuta `actualizar.bat` (o, a mano: `git pull`, activar `.venv` y `pip install -r requirements.txt`). Después reinicia el
agente: cierra su ventana y abre `iniciar.bat` (o reinicia el PC, si arranca con Windows). Cuando cambia el formato del
ticket, se actualiza el agente **antes** que el servidor (ver `DEPLOY.md`). `git pull` trae la rama que tenga el PC
(normalmente la misma que sigue el servidor).

## Arranque automático

En el PC de la tienda conviene que el agente inicie con Windows para que el vendedor no tenga que abrirlo:
ejecuta `inicio-automatico.bat` (deja un acceso en la carpeta de Inicio del usuario; no pide permisos de administrador).
Si mueves la carpeta `printer-agent`, ejecútalo de nuevo. Para comprobar que está activo, abre
`http://127.0.0.1:9100/salud` en el navegador del PC: debe responder `{"status":"ok","modo":"escpos"}`.
