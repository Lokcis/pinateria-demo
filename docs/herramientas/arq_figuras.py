"""Dibuja las figuras del documento de Arquitectura Técnica (docs/04) en alta resolución con Pillow.

Escribe los PNG en ../img/. Requiere Pillow y las fuentes de Windows (Arial).
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

R = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(R, "..", "img")
FN = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 30)
FB = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 32)
FE = ImageFont.truetype("C:/Windows/Fonts/ariali.ttf", 26)
FT = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 40)

AZUL = (31, 78, 121)
AZUL_CL = (232, 240, 250)
NARANJA = (242, 140, 40)
MAG = (160, 43, 111)
MAG_CL = (253, 243, 249)
TINTA = (31, 27, 58)
BLANCO = (255, 255, 255)
GRIS = (90, 90, 100)


def lienzo(w, h):
    img = Image.new("RGB", (w, h), BLANCO)
    return img, ImageDraw.Draw(img)


def partir(d, texto, fuente, ancho):
    """Parte un texto en renglones que quepan en `ancho` píxeles."""
    renglones = []
    for parrafo in texto.split("\n"):
        actual = ""
        for palabra in parrafo.split(" "):
            prueba = (actual + " " + palabra).strip()
            if d.textlength(prueba, font=fuente) <= ancho or not actual:
                actual = prueba
            else:
                renglones.append(actual)
                actual = palabra
        renglones.append(actual)
    return renglones


def caja(d, x, y, w, h, texto, estilo="claro", titulo=None):
    """Caja redondeada con texto centrado. estilo: claro, azul, naranja, mag, mag_claro."""
    relleno, borde, color = {
        "claro": (AZUL_CL, AZUL, TINTA),
        "azul": (AZUL, AZUL, BLANCO),
        "naranja": (NARANJA, NARANJA, BLANCO),
        "mag": (MAG, MAG, BLANCO),
        "mag_claro": (MAG_CL, MAG, TINTA),
    }[estilo]
    d.rounded_rectangle([x, y, x + w, y + h], radius=26, fill=relleno, outline=borde, width=4)
    renglones = []
    if titulo:
        renglones += [(r, FB) for r in partir(d, titulo, FB, w - 40)]
    renglones += [(r, FN) for r in partir(d, texto, FN, w - 40)] if texto else []
    alto = sum(36 if f is FN else 40 for _, f in renglones)
    cy = y + (h - alto) / 2
    for r, f in renglones:
        tw = d.textlength(r, font=f)
        d.text((x + (w - tw) / 2, cy), r, fill=color, font=f)
        cy += 36 if f is FN else 40


def flecha(d, p, q, color=AZUL, ancho=5, ambos=False, punteada=False):
    (x1, y1), (x2, y2) = p, q
    if punteada:
        largo = math.hypot(x2 - x1, y2 - y1)
        pasos = int(largo // 22)
        for k in range(0, pasos, 2):
            a, b = k / pasos, min((k + 1) / pasos, 1)
            d.line([(x1 + (x2 - x1) * a, y1 + (y2 - y1) * a), (x1 + (x2 - x1) * b, y1 + (y2 - y1) * b)], fill=color, width=ancho)
    else:
        d.line([p, q], fill=color, width=ancho)

    def punta(desde, hacia):
        ang = math.atan2(hacia[1] - desde[1], hacia[0] - desde[0])
        L = 26
        pts = [hacia,
               (hacia[0] - L * math.cos(ang - 0.4), hacia[1] - L * math.sin(ang - 0.4)),
               (hacia[0] - L * math.cos(ang + 0.4), hacia[1] - L * math.sin(ang + 0.4))]
        d.polygon(pts, fill=color)

    punta(p, q)
    if ambos:
        punta(q, p)


def etiqueta(d, centro, texto, ancho_max=380):
    """Etiqueta con fondo blanco para que no se pise con las líneas."""
    renglones = partir(d, texto, FE, ancho_max)
    w = max(d.textlength(r, font=FE) for r in renglones) + 24
    h = 32 * len(renglones) + 14
    x, y = centro[0] - w / 2, centro[1] - h / 2
    d.rounded_rectangle([x, y, x + w, y + h], radius=10, fill=BLANCO, outline=(200, 200, 210), width=2)
    for i, r in enumerate(renglones):
        d.text((x + 12, y + 7 + 32 * i), r, fill=GRIS, font=FE)


def guardar(img, nombre):
    img.save(os.path.join(SALIDA, nombre), optimize=True)
    print(nombre, img.size)


def pasos(nombre, textos, columnas, ancho_caja=330, alto_caja=210, hueco_x=70, hueco_y=90, resaltados=(), titulo=None):
    """Flujo en serpiente: filas alternan sentido; las flechas conectan paso a paso."""
    filas = math.ceil(len(textos) / columnas)
    margen = 50
    w = margen * 2 + columnas * ancho_caja + (columnas - 1) * hueco_x
    top = 120 if titulo else margen
    h = top + filas * alto_caja + (filas - 1) * hueco_y + margen
    img, d = lienzo(w, h)
    if titulo:
        d.text((margen, 40), titulo, fill=TINTA, font=FT)
    pos = []
    for i in range(len(textos)):
        f, c = divmod(i, columnas)
        if f % 2 == 1:
            c = columnas - 1 - c
        pos.append((margen + c * (ancho_caja + hueco_x), top + f * (alto_caja + hueco_y)))
    for i, (txt, (x, y)) in enumerate(zip(textos, pos)):
        caja(d, x, y, ancho_caja, alto_caja, txt, "mag_claro" if i in resaltados else "claro", titulo=f"{i + 1}")
    for i in range(len(textos) - 1):
        (x1, y1), (x2, y2) = pos[i], pos[i + 1]
        if y1 == y2:
            if x2 > x1:
                flecha(d, (x1 + ancho_caja + 4, y1 + alto_caja / 2), (x2 - 4, y2 + alto_caja / 2))
            else:
                flecha(d, (x1 - 4, y1 + alto_caja / 2), (x2 + ancho_caja + 4, y2 + alto_caja / 2))
        else:
            flecha(d, (x1 + ancho_caja / 2, y1 + alto_caja + 4), (x2 + ancho_caja / 2, y2 - 4))
    guardar(img, nombre)


# ---------------------------------------------------------------- Figura 1: vista general
def vista_general():
    img, d = lienzo(1500, 900)
    caja(d, 40, 40, 560, 300, "POS Web (React) y lector USB (HID)\nAgente de impresión local\nImpresora Epson TM-T20II", "claro", titulo="Tienda (ubicación remota)")
    caja(d, 900, 40, 560, 300, "Dashboard PWA (React)\nDesde el smartphone", "claro", titulo="Propietario (remoto)")
    caja(d, 520, 400, 460, 170, "Cloudflare Edge", "naranja", titulo="Internet")
    caja(d, 360, 690, 780, 190, "Nginx · FastAPI · PostgreSQL · Redis\nCelery · Uptime Kuma · cloudflared", "azul", titulo="Servidor Ubuntu (Docker)")
    flecha(d, (320, 352), (560, 430), ambos=True)
    etiqueta(d, (400, 365), "HTTPS")
    flecha(d, (1180, 352), (940, 430), ambos=True)
    etiqueta(d, (1100, 365), "HTTPS")
    flecha(d, (750, 575), (750, 685), ambos=True)
    etiqueta(d, (1020, 630), "Túnel de salida (supera el CG-NAT del proveedor de internet)", 520)
    guardar(img, "arq-vision-general.png")


# ---------------------------------------------------------------- Figura 2: contenedores
def contenedores():
    img, d = lienzo(1500, 1280)
    c1, c2, c3 = 50, 570, 1090
    ancho, alto = 360, 150
    caja(d, c1, 40, ancho, alto, "cloudflared (túnel)", "claro")
    caja(d, c2, 40, ancho, alto, "Nginx", "azul", titulo=None)
    caja(d, c3, 40, ancho, alto, "Uptime Kuma", "claro")
    caja(d, c2, 360, ancho, 170, "FastAPI + Gunicorn / Uvicorn", "azul", titulo="Backend API")
    caja(d, c1, 700, ancho, alto, "PostgreSQL 15", "azul")
    caja(d, c3, 700, ancho, alto, "Redis", "azul")
    caja(d, c1, 1050, ancho, 160, "Alembic al arrancar", "claro", titulo="migrate")
    caja(d, c2, 1050, ancho, 160, "alertas y respaldo", "azul", titulo="Celery Worker")
    caja(d, c3, 1050, ancho, 160, "tareas programadas", "azul", titulo="Celery Beat")
    flecha(d, (c1 + ancho + 4, 115), (c2 - 4, 115))
    etiqueta(d, ((c1 + ancho + c2) / 2, 68), "puerto 8080", 160)
    flecha(d, (c2 + ancho / 2, 194), (c2 + ancho / 2, 356))
    etiqueta(d, (c2 + ancho / 2 + 10, 275), "frontend estático y /api", 380)
    flecha(d, (c3 + 60, 194), (c2 + ancho - 40, 360), punteada=True)
    etiqueta(d, (1230, 290), "healthcheck HTTP", 300)
    flecha(d, (c2 + 80, 534), (c1 + ancho - 60, 696))
    etiqueta(d, (c1 + ancho / 2 + 40, 615), "SQL (transacciones)", 340)
    flecha(d, (c2 + ancho - 80, 534), (c3 + 60, 696))
    etiqueta(d, (c3 - 40, 615), "encola tareas", 260)
    flecha(d, (c1 + ancho / 2, 1046), (c1 + ancho / 2, 854))
    etiqueta(d, (c1 + ancho / 2, 950), "migraciones", 340)
    flecha(d, (c2 + 70, 1046), (c1 + ancho - 40, 854))
    etiqueta(d, (c1 + ancho + 110, 985), "lee alertas, guarda\nnotificaciones y respaldos", 360)
    flecha(d, (c2 + ancho - 60, 1046), (c3 + 40, 854))
    etiqueta(d, (c3 - 35, 960), "toma tareas", 240)
    flecha(d, (c3 + ancho / 2, 1046), (c3 + ancho / 2, 854))
    etiqueta(d, (c3 + ancho / 2 + 30, 950), "programa tareas", 290)
    d.text((60, 1236), "Alertas de stock bajo: cada 15 minutos. Respaldo de PostgreSQL: todos los días a las 2:30 a. m. (Bogotá).", fill=GRIS, font=FE)
    guardar(img, "arq-contenedores-docker.png")


# ---------------------------------------------------------------- Figura 3: tienda
def tienda():
    img, d = lienzo(1500, 820)
    caja(d, 40, 60, 400, 190, "teclado emulado (HID)", "claro", titulo="Lector de código de barras")
    caja(d, 550, 60, 400, 190, "navegador en el PC de la tienda", "azul", titulo="POS Web (React)")
    caja(d, 1090, 60, 370, 190, "vía Cloudflare Tunnel", "naranja", titulo="Servidor")
    caja(d, 550, 520, 400, 200, "servicio local (localhost)", "claro", titulo="Agente de impresión")
    caja(d, 40, 520, 370, 200, "USB, comandos ESC/POS", "claro", titulo="Impresora Epson TM-T20II")
    flecha(d, (444, 155), (546, 155))
    etiqueta(d, (495, 118), "teclas", 120)
    flecha(d, (954, 155), (1086, 155), ambos=True)
    etiqueta(d, (1020, 112), "HTTPS", 130)
    flecha(d, (750, 254), (750, 516))
    etiqueta(d, (750, 385), "orden de impresión por localhost", 420)
    flecha(d, (546, 620), (414, 620))
    etiqueta(d, (480, 578), "ESC/POS", 130)
    d.text((40, 770), "El agente no depende de Internet; la venta sí (se confirma en el servidor antes de imprimir).", fill=GRIS, font=FE)
    guardar(img, "arq-tienda-y-agente-de-impresion.png")


if __name__ == "__main__":
    vista_general()
    contenedores()
    tienda()
    pasos("arq-flujo-de-venta.png", [
        "El vendedor escanea el código o busca por texto",
        "React agrega el producto al carrito (estado local)",
        "El vendedor confirma el pago",
        "El POS envía la venta al backend (HTTPS, Cloudflare Tunnel)",
        "El backend crea la venta y el detalle y descuenta el stock en una transacción SQL",
        "El backend responde la confirmación al POS",
        "El POS invoca al agente de impresión local (localhost)",
        "El agente envía ESC/POS a la Epson (USB): ticket impreso",
    ], columnas=4)
    pasos("arq-flujo-alertas-stock.png", [
        "Celery Beat dispara la tarea programada (cada 15 minutos)",
        "El Celery Worker consulta vw_alertas_stock_bajo en PostgreSQL",
        "Inserta una notificación por producto (si no hay una sin leer)",
        "El Dashboard lee la vista de alertas en vivo; con la mejora B1 también la bandeja",
        "El propietario ve las alertas de stock bajo en su smartphone",
    ], columnas=3, alto_caja=240, resaltados=(3,))
    pasos("arq-flujo-de-venta-adendo-v2.png", [
        "Se elige quién realiza la venta y, si aplica, el cliente",
        "El sistema sugiere el descuento (del cliente o general); el vendedor puede cambiarlo dentro de los topes",
        "El POS calcula subtotal, descuento, redondeo a $50 y total",
        "Se registran los pagos: método, plataforma, monto recibido y vueltas. La suma debe ser igual al total",
        "El POS envía la venta al backend: vendedor, cliente, descuento, líneas y pagos",
        "El backend valida todo y guarda en una transacción: venta, pagos, reparto del descuento y stock",
        "El backend confirma la venta al POS",
        "El agente imprime el ticket con pagos, descuento, recibido y vueltas",
    ], columnas=4, alto_caja=300, resaltados=(0, 1, 2, 3, 5, 7))
