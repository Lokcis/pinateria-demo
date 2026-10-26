"""Genera los manuales de usuario en PDF con el diseño de la app (papel crema, tinta azul, banderines,
logo y tipografías de Piñatería Demo), con aviso de documento privado y bloque de firma.

Requisitos: Python con reportlab, pillow, fonttools y brotli, y `npm ci` hecho en `frontend/` (de ahí salen las
tipografías Bricolage Grotesque y Figtree, que se convierten a TTF estático en una carpeta de caché).

    python manuales_pdf.py                      # escribe en ../manuales/
    python manuales_pdf.py --salida otra/carpeta --fecha-firma 14-10-2026

El contenido de los manuales vive en las funciones `contenido_*` de este archivo.
"""

import argparse
import datetime
import re
import tempfile
from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont as FuenteTTF
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

RAIZ = Path(__file__).resolve().parents[2]
LOGO = RAIZ / "frontend" / "public" / "logo-demo.png"
FIRMA = Path(__file__).resolve().parent / "firma.png"  # PNG transparente con la firma; no se versiona (.gitignore)
FUENTES_NPM = RAIZ / "frontend" / "node_modules" / "@fontsource-variable"

# Paleta de la app (frontend/src/app.css).
PAPEL = HexColor("#fbf6ee")
PAPEL_OSC = HexColor("#f3ead9")
TINTA = HexColor("#1f1b3a")
SUAVE = HexColor("#5e5a6e")
FUCSIA = HexColor("#d6245f")
SOL = HexColor("#ffb800")
TURQUESA = HexColor("#0b7f72")
MANDARINA = HexColor("#f26a2e")
CIELO = HexColor("#2b74e0")
BORDE = HexColor("#dccfb6")
BANDERINES = [FUCSIA, SOL, TURQUESA, MANDARINA, CIELO]

ANCHO, ALTO = 612.0, 792.0  # carta, como los manuales originales
MARGEN = 54.0
AUTOR = "Santiago Chávez López"
ROL_AUTOR = "Desarrollador del sistema"
NEGOCIO = "Piñatería Demo"
URL_APP = "https://pos.demo.example.com"
VERSION = "Versión 1.0 — 13-10-2026"
LEYENDA_PRIVADO = "Documento privado — prohibida su difusión"

# (nombre en reportlab, paquete de fontsource, archivo, peso)
FUENTES = [
    ("Figtree", "figtree", "figtree-latin-wght-normal.woff2", 400),
    ("Figtree-Bold", "figtree", "figtree-latin-wght-normal.woff2", 700),
    ("Bricolage", "bricolage-grotesque", "bricolage-grotesque-latin-wght-normal.woff2", 800),
]
_GLIFOS = set()  # caracteres que tienen las fuentes de texto (para avisar antes de que salgan cuadritos)


def preparar_fuentes(cache: Path) -> None:
    """Convierte las tipografías variables de la app a TTF estático y las registra en reportlab."""
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer

    cache.mkdir(parents=True, exist_ok=True)
    for nombre, paquete, archivo, peso in FUENTES:
        destino = cache / f"{nombre}.ttf"
        if not destino.exists():
            origen = FUENTES_NPM / paquete / "files" / archivo
            if not origen.exists():
                raise SystemExit(f"Falta {origen}: corre `npm ci` en frontend/.")
            fuente = instancer.instantiateVariableFont(TTFont(origen), {"wght": peso})
            fuente.flavor = None
            # Nombre interno único: si dos variantes comparten nombre, reportlab las confunde al incrustarlas.
            tabla_nombres = fuente["name"]
            tabla_nombres.names = [n for n in tabla_nombres.names if n.nameID not in (1, 2, 3, 4, 6, 16, 17, 21, 22, 25)]
            for id_nombre, valor in ((1, nombre), (2, "Regular"), (3, nombre), (4, nombre), (6, nombre)):
                tabla_nombres.setName(valor, id_nombre, 3, 1, 0x409)
            fuente.save(destino)
        pdfmetrics.registerFont(FuenteTTF(nombre, str(destino)))
        if nombre == "Figtree":
            _GLIFOS.update(chr(c) for c in TTFont(destino).getBestCmap())
    pdfmetrics.registerFontFamily("Figtree", normal="Figtree", bold="Figtree-Bold", italic="Figtree", boldItalic="Figtree-Bold")

    # Monoespaciada solo para direcciones y nombres de archivo.
    consolas = Path("C:/Windows/Fonts/consola.ttf")
    consolas_b = Path("C:/Windows/Fonts/consolab.ttf")
    if consolas.exists() and consolas_b.exists():
        pdfmetrics.registerFont(FuenteTTF("Mono", str(consolas)))
        pdfmetrics.registerFont(FuenteTTF("Mono-Bold", str(consolas_b)))
    else:
        from reportlab.pdfbase.pdfmetrics import Font

        pdfmetrics.registerFont(Font("Mono", "Courier", "WinAnsiEncoding"))
        pdfmetrics.registerFont(Font("Mono-Bold", "Courier-Bold", "WinAnsiEncoding"))
    pdfmetrics.registerFontFamily("Mono", normal="Mono", bold="Mono-Bold", italic="Mono", boldItalic="Mono-Bold")


def _estilo(nombre, **kw):
    base = dict(fontName="Figtree", fontSize=9.4, leading=13.4, textColor=TINTA, spaceAfter=4)
    base.update(kw)
    return ParagraphStyle(nombre, **base)


ESTILOS = {}


def crear_estilos() -> None:
    """Define los estilos de párrafo (después de registrar las fuentes)."""
    ESTILOS.update(
        cuerpo=_estilo("cuerpo"),
        titulo=_estilo("titulo", fontName="Bricolage", fontSize=31, leading=34, spaceAfter=6, spaceBefore=10),
        meta=_estilo("meta", fontSize=9.4, textColor=SUAVE, spaceAfter=10),
        h1=_estilo("h1", fontName="Bricolage", fontSize=16, leading=20, spaceBefore=11, spaceAfter=6, keepWithNext=1, leftIndent=2),
        h2=_estilo("h2", fontName="Bricolage", fontSize=12, leading=15, spaceBefore=8, spaceAfter=4, keepWithNext=1, textColor=FUCSIA),
        nota=_estilo("nota", fontSize=8.9, leading=12.6, spaceAfter=0),
        celda=_estilo("celda", fontSize=8.8, leading=12, spaceAfter=0),
        celda_cab=_estilo("celda_cab", fontName="Figtree-Bold", fontSize=8.6, leading=11, textColor=white, spaceAfter=0),
        marca=_estilo("marca", fontName="Bricolage", fontSize=21, leading=22, spaceAfter=1),
        submarca=_estilo("submarca", fontName="Figtree-Bold", fontSize=7.4, leading=10, textColor=SUAVE, spaceAfter=0),
        etiqueta=_estilo("etiqueta", fontName="Figtree-Bold", fontSize=7.6, leading=10, textColor=SUAVE, spaceAfter=2),
        url=_estilo("url", fontName="Mono-Bold", fontSize=11, leading=14, spaceAfter=0),
        aviso_t=_estilo("aviso_t", fontName="Bricolage", fontSize=12, leading=15, spaceAfter=3),
        aviso=_estilo("aviso", fontSize=8.8, leading=12.6, spaceAfter=0),
        firma=_estilo("firma", fontSize=8.4, leading=11, spaceAfter=0),
        firma_b=_estilo("firma_b", fontName="Figtree-Bold", fontSize=10, leading=13, spaceAfter=0),
    )


def P(texto, estilo="cuerpo"):
    """Párrafo con el estilo indicado; avisa si el texto trae caracteres que la fuente no tiene."""
    sin_etiquetas = re.sub(r"<[^>]+>", "", texto)
    for car in re.sub(r"&\w+;", "", sin_etiquetas):
        if car.isprintable() and car not in _GLIFOS and ord(car) > 127:
            raise ValueError(f"La fuente no tiene el carácter {car!r} (U+{ord(car):04X}) en: {texto[:50]}")
    return Paragraph(texto, ESTILOS[estilo])


def mono(texto):
    """Marca un fragmento en tipografía monoespaciada (direcciones, archivos)."""
    return f'<font name="Mono">{texto}</font>'


# ---------------------------------------------------------------------------------------------------------------------
# Elementos visuales
# ---------------------------------------------------------------------------------------------------------------------

def dibujar_banderines(c, y_superior, alto):
    """Franja de banderines (papel picado) pegada al borde superior, como en el encabezado de la app."""
    k = alto / 14.0
    paso = 24 * k
    x = 0.0
    i = 0
    while x < ANCHO:
        c.setFillColor(BANDERINES[i % 5])
        p = c.beginPath()
        p.moveTo(x, y_superior)
        p.lineTo(x + paso, y_superior)
        p.lineTo(x + paso / 2, y_superior - alto)
        p.close()
        c.drawPath(p, stroke=0, fill=1)
        x += paso
        i += 1


class Seccion(Paragraph):
    """Encabezado de sección con una barra fucsia a la izquierda."""

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFillColor(FUCSIA)
        c.roundRect(-8, 2, 4, self.height - 5, 2, stroke=0, fill=1)
        c.restoreState()
        super().draw()


class Etiqueta(Flowable):
    """Pastilla de color con texto en mayúsculas (como las etiquetas de categoría de la app)."""

    def __init__(self, texto, fondo=SOL, color=TINTA, tam=7.4, espaciado=1.1):
        super().__init__()
        self.texto, self.fondo, self.color, self.tam, self.esp = texto, fondo, color, tam, espaciado
        self.ancho = pdfmetrics.stringWidth(texto, "Figtree-Bold", tam) + espaciado * len(texto) + 18
        self.alto = tam + 9

    def wrap(self, w, h):
        return self.ancho, self.alto

    def draw(self):
        c = self.canv
        c.setFillColor(self.fondo)
        c.roundRect(0, 0, self.ancho, self.alto, self.alto / 2, stroke=0, fill=1)
        t = c.beginText(9, (self.alto - self.tam) / 2 + 1.2)
        t.setFont("Figtree-Bold", self.tam)
        t.setCharSpace(self.esp)
        t.setFillColor(self.color)
        t.textOut(self.texto)
        c.drawText(t)


class Tarjeta(Flowable):
    """Recuadro blanco con borde de tinta y sombra dura (estilo `sombra-dura` de la app)."""

    def __init__(self, contenido, relleno=white, relleno_pad=10):
        super().__init__()
        self.contenido, self.relleno, self.pad = contenido, relleno, relleno_pad

    def wrap(self, w, h):
        self.w = w - 4
        cw, ch = self.contenido.wrap(self.w - 2 * self.pad, h)
        self.h = ch + 2 * self.pad
        return w, self.h + 4

    def draw(self):
        c = self.canv
        c.setFillColor(TINTA)
        c.roundRect(4, 0, self.w, self.h, 6, stroke=0, fill=1)
        c.setFillColor(self.relleno)
        c.setStrokeColor(TINTA)
        c.setLineWidth(1.2)
        c.roundRect(0, 4, self.w, self.h, 6, stroke=1, fill=1)
        self.contenido.drawOn(c, self.pad, 4 + self.pad)


def vinetas(items):
    """Lista con viñetas fucsia."""
    return ListFlowable(
        [ListItem(P(t), leftIndent=14) for t in items],
        bulletType="bullet", start="•", bulletFontName="Figtree-Bold", bulletFontSize=11, bulletColor=FUCSIA,
        leftIndent=14, spaceAfter=4,
    )


def pasos(items):
    """Lista numerada con los números en fucsia."""
    return ListFlowable(
        [ListItem(P(t), leftIndent=18) for t in items],
        bulletType="1", bulletFormat="%s", bulletFontName="Bricolage", bulletFontSize=10, bulletColor=FUCSIA,
        leftIndent=18, spaceAfter=4,
    )


def tabla(cabecera, filas, anchos):
    """Tabla con cabecera fucsia, filas alternadas y esquinas redondeadas."""
    datos = [[P(h, "celda_cab") for h in cabecera]] + [[P(c, "celda") for c in fila] for fila in filas]
    t = Table(datos, colWidths=[a * (ANCHO - 2 * MARGEN) for a in anchos], repeatRows=1)
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), FUCSIA),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("BOX", (0, 0), (-1, -1), 0.8, BORDE),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, BORDE),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]
    for i in range(1, len(datos)):
        estilo.append(("BACKGROUND", (0, i), (-1, i), white if i % 2 else PAPEL_OSC))
    t.setStyle(TableStyle(estilo))
    return t


# ---------------------------------------------------------------------------------------------------------------------
# Páginas
# ---------------------------------------------------------------------------------------------------------------------

class LienzoNumerado(canvas.Canvas):
    """Lienzo que pone el pie de página con «Página n de N» y la leyenda de documento privado."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._estados = []

    def showPage(self):
        self._estados.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._estados)
        for estado in self._estados:
            self.__dict__.update(estado)
            self._pie(total)
            super().showPage()
        super().save()

    def _pie(self, total):
        self.setStrokeColor(BORDE)
        self.setLineWidth(0.8)
        self.line(MARGEN, 44, ANCHO - MARGEN, 44)
        self.setFont("Figtree-Bold", 7.6)
        self.setFillColor(FUCSIA)
        self.drawString(MARGEN, 31, LEYENDA_PRIVADO.upper().replace("—", "·"))
        self.setFont("Figtree", 7.6)
        self.setFillColor(SUAVE)
        self.drawRightString(ANCHO - MARGEN, 31, f"{NEGOCIO}  ·  Página {self._pageNumber} de {total}")


def fondo_pagina(titulo_corto):
    """Devuelve la función que dibuja el fondo de cada página (papel, banderines, marca de agua y cabecera)."""

    def dibujar(c, doc):
        c.saveState()
        c.setFillColor(PAPEL)
        c.rect(0, 0, ANCHO, ALTO, stroke=0, fill=1)
        # Marca de agua diagonal, muy tenue.
        c.saveState()
        c.setFillColor(FUCSIA)
        c.setFillAlpha(0.06)
        c.setFont("Bricolage", 100)
        c.translate(ANCHO / 2, ALTO / 2 - 20)
        c.rotate(35)
        c.drawCentredString(0, 0, "PRIVADO")
        c.restoreState()
        dibujar_banderines(c, ALTO, 10)
        if doc.page > 1:
            alto_logo = 24
            c.drawImage(ImageReader(str(LOGO)), MARGEN, ALTO - 24 - alto_logo, width=alto_logo * 1.0, height=alto_logo, mask="auto")
            c.setFont("Bricolage", 11.5)
            c.setFillColor(TINTA)
            c.drawString(MARGEN + alto_logo * 1.0 + 8, ALTO - 42, "Piñatería Demo")
            c.setFont("Figtree", 8.4)
            c.setFillColor(SUAVE)
            c.drawRightString(ANCHO - MARGEN, ALTO - 42, titulo_corto)
        c.restoreState()

    return dibujar


def portada(titulo, rol, version=VERSION):
    """Cabecera de la primera página: logo, nombre, etiqueta de privado, título y dirección de la app."""
    alto_logo = 54
    logo = Image(str(LOGO), width=alto_logo * 1.0, height=alto_logo)
    marca = [P("Piñatería Demo", "marca"), P("PIÑATERÍA  ·  SISTEMA DE VENTAS E INVENTARIO", "submarca")]
    cab = Table([[logo, marca]], colWidths=[alto_logo * 1.0 + 12, None])
    cab.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                             ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    cab.hAlign = "LEFT"
    return [
        Spacer(1, 6),
        cab,
        Spacer(1, 14),
        Etiqueta("DOCUMENTO PRIVADO  ·  PROHIBIDA SU DIFUSIÓN"),
        Spacer(1, 4),
        P(titulo, "titulo"),
        P(f"{rol}  ·  {version}  ·  Elaborado por {AUTOR}", "meta"),
        Tarjeta(Table([[P("DIRECCIÓN DE LA APLICACIÓN", "etiqueta")], [P(URL_APP, "url")]],
                      colWidths=[ANCHO - 2 * MARGEN - 24],
                      style=[("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                             ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)])),
        Spacer(1, 6),
    ]


def bloque_firma(fecha, firma_png=None):
    """Aviso de confidencialidad y firma del autor (la imagen `firma_png` si existe; si no, una línea en blanco)."""
    aviso = Table(
        [[P("Aviso de confidencialidad", "aviso_t")],
         [P(f"Este manual es un <b>documento privado</b>, elaborado para uso exclusivo de {NEGOCIO}. "
            "Queda prohibida su reproducción, distribución, publicación o difusión, total o parcial y por cualquier medio, "
            f"sin autorización escrita de su autor, {AUTOR}. Describe el funcionamiento interno del sistema: "
            "no lo compartas fuera del negocio ni lo publiques en redes o grupos.", "aviso")]],
        colWidths=[ANCHO - 2 * MARGEN - 24],
        style=[("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
               ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)],
    )
    ancho = ANCHO - 2 * MARGEN
    imagen_firma = ""
    if firma_png and Path(firma_png).exists():
        alto_firma = 40
        ancho_png, alto_png = ImageReader(str(firma_png)).getSize()
        imagen_firma = Image(str(firma_png), width=alto_firma * ancho_png / alto_png, height=alto_firma, hAlign="LEFT")
    firma = Table(
        [[imagen_firma, "", ""],
         [P(f"{AUTOR}", "firma_b"), "", P(fecha, "firma_b")],
         [P(f"{ROL_AUTOR}  ·  {NEGOCIO}", "firma"), "", P("Fecha de firma", "firma")]],
        colWidths=[ancho * 0.58, ancho * 0.06, ancho * 0.36], rowHeights=[42, None, None],
        style=[("LINEABOVE", (0, 1), (0, 1), 0.9, TINTA), ("LINEABOVE", (2, 1), (2, 1), 0.9, TINTA), ("VALIGN", (0, 0), (0, 0), "BOTTOM"),
               ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
               ("TOPPADDING", (0, 1), (-1, 1), 4), ("TOPPADDING", (0, 0), (-1, 0), 0),
               ("TOPPADDING", (0, 2), (-1, 2), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)],
    )
    return KeepTogether([Spacer(1, 8), Tarjeta(aviso, relleno=HexColor("#fff6dc")), Spacer(1, 6), firma])


def H(texto):
    """Encabezado de sección."""
    return Seccion(texto, ESTILOS["h1"])


def H2(texto):
    """Subtítulo dentro de una sección."""
    return Paragraph(texto, ESTILOS["h2"])


def nota(texto, tipo="aviso"):
    """Recuadro de nota: `aviso` (amarillo, cuidado) o `consejo` (verde, buena práctica)."""
    fondo, etiqueta = (HexColor("#fff6dc"), "Importante") if tipo == "aviso" else (HexColor("#e1f3ef"), "Consejo")
    return KeepTogether([Tarjeta(P(f"<b>{etiqueta}.</b> {texto}", "nota"), relleno=fondo, relleno_pad=8), Spacer(1, 4)])


# ---------------------------------------------------------------------------------------------------------------------
# Contenido de los manuales
# ---------------------------------------------------------------------------------------------------------------------

def contenido_administrador():
    """Cuerpo del manual del administrador."""
    return [
        P("El administrador puede hacer todo lo del vendedor (vender, ver las ventas de hoy, clientes e inventario) y además "
          "administra el negocio. En el computador las secciones están en el menú lateral; en el celular, en el botón "
          "<b>Más</b> de la barra inferior."),
        H("1. Dónde se hace cada tarea"),
        tabla(["Tarea", "Dónde"], [
            ["Crear usuarios, cambiar roles, restablecer contraseñas", "Negocio › <b>Usuarios</b>"],
            ["Productos, precios, recetas de anchetas, stock mínimo", "<b>Inventario</b>"],
            ["Registrar mercancía que llega (al recibirla se pregunta cómo se pagó)", "Inventario y compras › <b>Compras</b>"],
            ["Proveedores", "Inventario y compras › <b>Proveedores</b>"],
            ["Categorías", "Inventario y compras › <b>Categorías</b>"],
            ["Alertas de stock y lista de compras", "Inventario y compras › <b>Stock bajo</b>"],
            ["Costos de los productos, ganancias y ganancia neta", "Negocio › <b>Ganancias</b>"],
            ["Registrar, corregir y anular gastos; categorías de gasto; exportar (ver 12)", "Gastos y caja › <b>Gastos</b>"],
            ["Abrir, mover y cerrar la caja; historial de cortes (ver 13)", "Gastos y caja › <b>Caja</b>"],
            ["Descuento general y topes del vendedor", "Negocio › <b>Descuentos</b>"],
            ["Datos del negocio, enlace de autorregistro, solicitudes de titulares", "Clientes › <b>Datos personales</b>"],
            ["Descuento propio de un cliente", "Clientes › ficha del cliente"],
            ["Ventas hechas sin internet que necesitan revisión", "Barra del POS › <b>Ver ventas guardadas</b> (ver 11)"],
        ], [0.58, 0.42]),
        H("2. Usuarios"),
        vinetas([
            "Hay tres roles: <b>administrador</b>, <b>vendedor</b> y <b>propietario</b>.",
            "La contraseña tiene de 8 a 72 caracteres. Si alguien la olvida, la restableces desde <b>Usuarios</b>.",
            "Los usuarios no se borran: se desactivan. Un administrador no puede desactivarse a sí mismo ni quitarse el rol.",
            "Cada persona debe usar su propio usuario: la venta queda a nombre de quien tiene la sesión.",
        ]),
        H("3. Productos e inventario"),
        vinetas([
            "Los productos se pueden vender por unidad, por paquete o como <b>ancheta</b> (producto compuesto con receta). "
            "La receta lleva cantidades enteras, sin productos repetidos.",
            "Un producto no se borra: se <b>desactiva</b> (y se puede reactivar). Una categoría con productos no se puede eliminar.",
            "El <b>stock mínimo</b> de cada producto dispara la alerta de stock bajo.",
            "Las correcciones de inventario se hacen con un <b>ajuste manual</b> con su motivo; queda en el historial. "
            "Vendedor y administrador pueden hacerlo.",
            "Los nombres y textos que se registran (productos, categorías, proveedores, clientes, usuarios, descripciones, notas "
            "y motivos) quedan con la primera letra en mayúscula y el resto en minúscula. Lo que ya estaba guardado no cambia.",
        ]),
        H("4. Compras y proveedores"),
        pasos([
            "En <b>Compras</b>, crea la compra con el proveedor y los productos.",
            "Cuando llegue la mercancía, <b>recíbela</b>: solo entonces suma al stock. Al recibirla el sistema pregunta <b>cómo se pagó</b> (efectivo, tarjeta o transferencia por Nequi o Daviplata); la compra aparece en <b>Gastos</b> y, si se pagó en efectivo, resta de la caja.",
            "Una compra se puede cancelar antes de recibirla.",
            "Un proveedor que ya tiene compras no se elimina. El teléfono del proveedor lleva solo números (7 a 15).",
        ]),
        P("El total de una compra se redondea al múltiplo de $50 más cercano."),
        H("5. Stock bajo y lista de compras"),
        vinetas([
            "La bandeja avisa cuando un producto llega a su mínimo. Cada aviso sigue sin leer hasta que alguien lo marque, "
            "aunque el producto ya se haya repuesto.",
            "La <b>lista de compras</b> muestra cuánto falta de cada producto (mínimo menos stock actual). Se puede enviar "
            "por WhatsApp o copiar como texto.",
        ]),
        H("6. Costos y ganancias"),
        vinetas([
            "En <b>Ganancias</b>, escribe el costo de cada producto a mano. Para paquetes y anchetas aparece un costo "
            "sugerido a partir de sus componentes.",
            "El filtro <b>sin costo</b> muestra lo que falta cargar.",
            "Las ventas hechas antes de cargar los costos quedan “sin costo”. Usa <b>Completar costos de ventas anteriores</b> "
            "para incluirlas en la ganancia.",
            "La <b>ganancia neta</b> aparece en la misma pantalla: el margen bruto menos los <b>gastos operativos</b> (los que no son compra de mercancía: esa ya está en el costo de lo vendido, y restarla otra vez la contaría dos veces). Aparte se muestra el <b>resultado de caja</b>: lo cobrado menos <b>todos</b> los gastos, compras incluidas. Es una cifra de flujo de dinero, no una ganancia contable. Si faltan costos, avisa que la neta está incompleta.",
            "El propietario ve las ganancias en su Dashboard, solo para consultar.",
        ]),
        H("7. Descuentos"),
        vinetas([
            "<b>Descuento general:</b> lo activas o desactivas en <b>Descuentos</b>, en porcentaje o en pesos. El vendedor lo "
            "aplica a quien corresponda; no viene puesto en todas las ventas.",
            "<b>Topes:</b> fijas el máximo (porcentaje y monto) que el vendedor puede dar con un descuento escrito a mano. "
            "Mientras no los configures, no hay límite.",
            "<b>Descuento propio de un cliente:</b> lo asignas en la ficha del cliente. Se sugiere solo en la venta, reemplaza "
            "al general (no se suman) y no está sujeto a los topes.",
            "Todo descuento se calcula sobre el subtotal y el total se redondea a $50.",
        ]),
        H("8. Clientes y datos personales (Habeas Data)"),
        P("<b>Datos del negocio.</b> En <b>Datos personales</b>, sección <b>Datos del negocio</b>, completa el nombre o razón "
          "social, NIT o cédula, dirección, teléfono, correo de contacto y la fecha de la política. Mientras falte alguno, la "
          "política queda como “borrador” y no se puede generar el enlace de autorregistro."),
        P("<b>Enlace de autorregistro.</b> En <b>Datos personales</b>, sección <b>Enlace de autorregistro</b>, puedes copiar "
          "el enlace, desactivarlo o regenerarlo. Al regenerarlo, el enlace anterior deja de funcionar. Quien se registra por "
          "el enlace queda activo, sin descuento propio, y con su aceptación guardada."),
        P("<b>Autorización.</b> Un cliente no se crea sin la autorización de datos; queda guardada la fecha, el medio, la "
          "versión de la política y quién la recogió. Las promociones son una autorización aparte, desmarcada por defecto."),
        P("<b>Solicitudes de los titulares.</b> Cuando un cliente pide consultar, corregir o borrar sus datos, o retirar su "
          "autorización, regístrala en la sección de solicitudes de <b>Datos personales</b>. El sistema calcula la fecha límite:"),
        tabla(["Tipo de solicitud", "Plazo"], [
            ["Consulta", "10 días hábiles"],
            ["Actualización, supresión o revocatoria", "15 días hábiles"],
        ], [0.6, 0.4]),
        Spacer(1, 7),
        vinetas([
            "Resolver una <b>supresión</b> anonimiza al cliente (nombre “Cliente anonimizado”; documento, teléfono, correo y "
            "descuento se borran) y conserva sus ventas.",
            "Resolver una <b>revocatoria</b> impide usar al cliente en ventas nuevas.",
            "Una solicitud resuelta o rechazada no se reabre.",
            "Los formatos y la política están en el documento 08 de la documentación.",
        ]),
        H("9. Respaldos y funcionamiento"),
        vinetas([
            "Cada día a las 2:30 a. m. el sistema hace un respaldo automático de la base de datos y conserva los de los "
            "últimos 14 días.",
            "Si algo falla en la aplicación (no carga, no imprime), revisa primero el internet de la tienda y el agente de "
            "impresión del PC del POS; si sigue, avisa al desarrollador. Si solo se cayó el internet, el POS sigue vendiendo "
            "(ver 11).",
        ]),
        H("10. Errores de venta"),
        P("Una venta registrada no se borra. Si hubo un error, avisa al desarrollador para corregirlo; no hagas ajustes de "
          "inventario “a ojo” para compensarlo."),
        H("11. Ventas guardadas sin conexión"),
        P("Si se cae internet, el POS sigue vendiendo: guarda cada venta en el equipo, imprime el ticket con un número local "
          "(<b>SC-0001</b>…) y, cuando vuelve la conexión, las envía solas, de la más antigua a la más reciente. Una venta nunca "
          "se duplica ni descuenta el stock dos veces, y conserva la hora, el precio y el descuento con que se cobró."),
        vinetas([
            "Un vendedor envía solo las ventas que guardó él; <b>tú, como administrador, envías las de todos</b>. Las de otra "
            "persona esperan a que ella inicie sesión en ese equipo o a que entres tú.",
            "Mientras no se envían, las ventas <b>no aparecen en el historial ni en el Dashboard</b> del propietario. Al enviarse "
            "quedan con la hora real y el rótulo “Sin conexión”.",
            "Sin conexión no se asocian clientes: sus datos no se guardan en el navegador (Habeas Data).",
        ]),
        P("<b>Cuando una venta queda en “Necesita revisión”.</b> Lo más probable es que el servidor no tuviera stock suficiente "
          "porque el inventario no estaba al día. La venta ya ocurrió: el cliente pagó y se llevó el producto."),
        pasos([
            "El vendedor te avisa y te muestra el motivo exacto en <b>Ver ventas guardadas</b>.",
            "Corrige la causa: registra el stock que faltaba (ajuste de inventario o compra recibida), reactiva el producto o "
            "ajusta los topes de descuento.",
            "En <b>Ver ventas guardadas</b>, pulsa <b>Reintentar</b>. Si ya no tiene arreglo (por ejemplo, la venta se registró a "
            "mano), <b>Descartar</b> la borra de la cola tras confirmar; esa venta no quedará registrada en el sistema.",
        ]),
        P("<b>Límites que debes conocer:</b>"),
        vinetas([
            "No hay inicio de sesión sin conexión: si se cierra sesión o vence (8 horas) durante un corte, no se puede volver a "
            "entrar hasta que vuelva internet. Por eso el POS pide confirmar al cerrar sesión sin conexión.",
            "El stock mostrado puede estar desactualizado: sin conexión no se bloquea una venta por stock; la decide el servidor "
            "al enviarla.",
            "La cola vive en el navegador de cada equipo y no se comparte entre equipos. Usa siempre el mismo navegador (Chrome o "
            "Edge) y no una ventana privada.",
            "La hora del equipo debe estar en automático: el servidor rechaza ventas con hora futura (más de 5 minutos) o de más "
            "de 7 días.",
            "El catálogo guardado se actualiza solo con internet: abre el POS con conexión al empezar el día.",
        ]),
        H("12. Gastos"),
        P("En <b>Gastos y caja › Gastos</b> ves y registras todos los gastos del negocio; el vendedor solo ve y modifica los suyos, y el propietario solo consulta."),
        vinetas([
            "<b>Nuevo gasto:</b> categoría, qué se pagó, monto en pesos enteros, forma de pago (en efectivo, múltiplos de $50; en transferencia, Nequi o Daviplata), a quién se pagó (opcional, solo el nombre) y fecha. Tú puedes elegir una fecha anterior, nunca futura; el vendedor siempre registra con la de hoy.",
            "<b>Editar y anular:</b> puedes con cualquier gasto, también con los que ya cubre un corte de caja cerrado (el corte conserva su foto). Anular pide el motivo; el gasto no se borra: queda tachado con quién, cuándo y por qué, y deja de sumar.",
            "<b>Compras recibidas:</b> aparecen en la lista como filas de solo lectura, en la categoría de sistema <b>Compra de mercancía</b>. No se editan desde aquí (están en Compras).",
            "<b>Categorías:</b> el botón <b>Categorías</b> permite crear, renombrar y desactivar. “Compra de mercancía” es de sistema y no se toca; una categoría desactivada no se ofrece para gastos nuevos pero conserva los antiguos.",
            "Arriba de la lista ves los <b>totales</b> por categoría y por forma de pago. <b>Exportar</b> descarga un archivo que abre Excel (por defecto sin los anulados).",
            "Los gastos necesitan conexión: sin internet la pantalla lo avisa.",
        ]),
        H("13. Caja y corte de caja"),
        P("En <b>Gastos y caja › Caja</b> se abre la caja con una base, el sistema calcula cuánto efectivo debería haber y al final se hace el corte contando lo que hay. El administrador y el vendedor operan la caja; el propietario solo consulta."),
        vinetas([
            "<b>Abrir:</b> escribe la base en efectivo (múltiplos de $50). Solo puede haber una caja abierta.",
            "<b>Efectivo esperado</b> = base + ventas en efectivo + ingresos − gastos en efectivo − compras en efectivo − retiros. Las vueltas no cuentan, y los gastos anulados tampoco. Lo vendido con tarjeta y por transferencia sale aparte, solo para compararlo con el datáfono y el banco.",
            "<b>Ingresos y retiros:</b> sirven para lo que mueve efectivo sin ser venta ni gasto (cambio, consignación al banco, retiro del dueño). Piden un motivo y van en múltiplos de $50.",
            "<b>Cerrar:</b> cuenta el efectivo y escríbelo (múltiplos de $50). El sistema calcula la <b>diferencia</b> (contado − esperado: positiva sobra, negativa falta) y guarda una foto del corte que ya no se modifica. El POS no deja cerrar si ese equipo tiene ventas guardadas sin enviar (ver 11).",
            "Con el corte cerrado, el vendedor ya no puede editar ni anular los gastos que cubre; tú sí, y el corte no cambia.",
            "El <b>historial de cortes</b> muestra, para cada uno, quién lo abrió y cerró, lo esperado, lo contado y la diferencia. Su ficha avisa si después llegaron ventas hechas sin conexión durante ese corte. <b>Exportar</b> descarga los cortes del rango.",
        ]),
    ]


def contenido_propietario():
    """Cuerpo del manual del propietario."""
    return [
        H("Qué puedes hacer"),
        P("Usas el <b>Dashboard</b>, también desde el celular. Solo consultas: no vendes ni modificas datos."),
        vinetas([
            "<b>Ventas:</b> elige el rango (Hoy, Ayer, Semana, Mes, 3 meses, 6 meses, Año o personalizado). Ve el total, "
            "cuántas ventas, el desglose por forma de pago y los productos más vendidos.",
            "<b>Ganancias</b> (pestaña junto a “Ventas”): margen por período y por producto, y la tabla de costos en solo "
            "lectura. Las ventas sin costo cargado no entran en la ganancia hasta que el administrador complete los costos.",
            "<b>Ganancia neta</b> (dentro de “Ganancias”): el margen bruto menos los gastos operativos (los que no son compra de mercancía, porque esa ya está en el costo de lo vendido) y, aparte, el <b>resultado de caja</b>: lo cobrado menos todos los gastos, compras incluidas. El resultado de caja es una cifra de flujo de dinero, no una ganancia contable. Si faltan costos, avisa que la neta está incompleta.",
            "<b>Gastos</b> (pestaña junto a “Ganancias”): todos los gastos y las compras recibidas del rango, con los totales por categoría y por forma de pago, y el botón <b>Exportar</b> (archivo que abre Excel).",
            "<b>Caja</b> (pestaña junto a “Gastos”): si la caja está abierta, el efectivo esperado con su desglose; el historial de cortes con la diferencia de cada uno, su ficha y el botón <b>Exportar</b>.",
            "<b>Stock bajo</b> (botón con contador): la bandeja de alertas (marcar una o todas como leídas) y la <b>lista de "
            "compras</b>, que se puede enviar por WhatsApp o copiar como texto.",
            "<b>Instalarla en el celular:</b> abrir la dirección en Chrome › menú › “Añadir a la pantalla de inicio” "
            "(es una PWA).",
        ]),
        H("Decisiones que te tocan"),
        P("Las ejecuta el administrador: topes y descuento general, descuento propio de clientes frecuentes, y la atención "
          "de solicitudes de datos personales."),
    ]


def contenido_vendedor():
    """Cuerpo del manual del vendedor."""
    return [
        H("1.1 Antes de abrir la tienda"),
        pasos([
            "Enciende el PC del POS y la impresora (Epson TM-T20II) y entra a la dirección de la aplicación.",
            "Inicia sesión con <b>tu</b> usuario. No uses el de otra persona: la venta queda a nombre de quien tiene la sesión "
            "(se puede cambiar por venta, ver 1.4).",
            "Comprueba que el <b>agente de impresión</b> esté corriendo (su ventana minimizada; arranca solo al iniciar "
            "Windows). Si el ticket no sale, ver 1.8.",
            "Abre la aplicación <b>con internet</b> al empezar el día: así guarda los precios al día por si luego se cae la "
            "conexión (ver 1.9).",
        ]),
        H("1.2 Hacer una venta (pestaña “Nueva venta”)"),
        pasos([
            "Busca el producto por nombre, o escanea el código de barras con el lector (el cursor debe estar en el buscador).",
            "Toca el producto para agregarlo. Ajusta cantidades en el carrito; las piñatas se pueden vender por unidad, por "
            "paquete o como ancheta.",
            "(Opcional) Elige el <b>cliente</b> si la persona está registrada (ver 1.5).",
            "(Opcional) Aplica un <b>descuento</b> (ver 1.3).",
            "Elige cómo paga (ver 1.6) y pulsa <b>Confirmar venta</b>.",
            "Sale el ticket. Si no sale, la venta <b>sí quedó registrada</b>: usa <b>Reintentar impresión</b>.",
        ]),
        P("El total se redondea al múltiplo de $50 más cercano; el ticket muestra “Ajuste por redondeo”."),
        P("En el celular, el panel de la venta se abre desde la barra inferior (cantidad de artículos y total)."),
        H("1.3 Descuentos"),
        vinetas([
            "<b>General:</b> solo si el administrador lo activó. Se aplica a quien corresponde (clientes sin registro); no "
            "viene puesto por defecto.",
            "<b>Del cliente:</b> si el cliente tiene descuento propio, se sugiere solo al elegirlo. Puedes quitarlo.",
            "<b>Manual:</b> lo escribes tú (% o $), pero hay <b>topes</b> fijados por el administrador. Si te pasas, la "
            "aplicación no lo deja.",
            "El descuento se calcula sobre el subtotal y después se redondea a $50.",
        ]),
        H("1.4 Quién vendió"),
        P("El desplegable <b>Vendedor</b> trae tu nombre. Si otra persona atendió al cliente, cámbialo antes de confirmar: "
          "la venta queda a su nombre y el ticket dice “Atendió: …”. Después de cada venta vuelve a ti."),
        H("1.5 Clientes y autorización de datos personales"),
        P("Pestaña <b>Clientes</b>: busca por nombre, documento o teléfono. Para registrar a alguien nuevo:"),
        pasos([
            "Pídele sus datos (nombre; documento y teléfono si los da; correo opcional).",
            "<b>Antes de guardar, léele o muéstrale el aviso de privacidad</b> (cartel en el mostrador) y pregunta si autoriza "
            "el tratamiento de sus datos. Sin autorización <b>no se registra</b>.",
            "Marca la casilla de autorización y el medio (verbal, escrito o electrónico).",
            "La casilla de <b>promociones es aparte</b>: márcala solo si el cliente dice que sí quiere recibirlas. Por defecto "
            "está desmarcada y no debes insistir.",
            f"Alternativa: el cliente se registra solo desde su celular con el <b>enlace de autorregistro</b> que le da el "
            f"administrador ({mono('/registro/&lt;código&gt;')}); allí lee el aviso y acepta él mismo.",
        ]),
        P("Si un cliente pide ver, corregir o borrar sus datos, o retirar su autorización: <b>no lo resuelvas tú</b>; anota "
          "su nombre y teléfono y avisa al administrador (hay un procedimiento con plazos legales)."),
        H("1.6 Formas de pago"),
        vinetas([
            "<b>Efectivo:</b> escribe el monto recibido; la aplicación calcula las <b>vueltas</b> (el ticket las imprime).",
            "<b>Tarjeta.</b>",
            "<b>Transferencia:</b> elige <b>Nequi</b> o <b>Daviplata</b>; es obligatorio.",
            "<b>Pago mixto:</b> agrega varios pagos (por ejemplo, $20.000 en efectivo y el resto por Nequi). La suma debe ser "
            "<b>exactamente el total</b>; si no, no deja confirmar.",
        ]),
        H("1.7 Ventas de hoy y errores"),
        vinetas([
            "<b>Ventas de hoy</b> muestra lo que quedó hoy a tu nombre y también lo que tú registraste a nombre de otra persona "
            "(dice “Registrada por” cuando la registró alguien distinto del vendedor); desde ahí puedes <b>Reimprimir ticket</b>.",
            "Las ventas hechas sin conexión aparecen aquí, rotuladas “Sin conexión”, cuando ya se enviaron (ver 1.9).",
            "Una venta mal hecha no se borra: avisa al administrador.",
            "Si falta o sobra producto en el inventario, usa <b>Inventario</b> (ajuste manual con motivo); no vendas “a ojo” "
            "algo que no está registrado.",
        ]),
        H("1.8 Si algo falla"),
        tabla(["Síntoma", "Qué hacer"], [
            ["No sale el ticket",
             f"Revisa que la impresora tenga papel y esté encendida; pulsa <b>Reintentar impresión</b>. Si sigue, el agente no "
             f"está corriendo: abre {mono('iniciar.bat')} en la carpeta {mono('printer-agent')}."],
            ["La aplicación no carga",
             "Revisa el internet de la tienda. Si ya tenías la aplicación abierta con la sesión iniciada, <b>sigue vendiendo</b>: "
             "lee el apartado 1.9. Si no abre ni la pantalla de inicio de sesión, sin internet no hay manera de entrar: anota la "
             "venta en papel (producto, valor, forma de pago) y regístrala cuando vuelva."],
            ["“Sesión vencida”", "Vuelve a iniciar sesión (dura 8 horas)."],
            ["No encuentro un producto", "Prueba con otra palabra o el código; si no existe, avisa al administrador."],
        ], [0.3, 0.7]),
        H("1.9 Si se cae internet (modo sin conexión)"),
        P("La aplicación sigue vendiendo aunque se caiga internet. Lo que tienes que saber:"),
        vinetas([
            "Arriba aparece una barra roja: <b>“Sin conexión con el servidor. Puedes seguir vendiendo…”</b>. Vende como siempre: "
            "busca por nombre o con el lector, cobra y confirma.",
            "Al confirmar verás <b>“Venta SC-0001 guardada sin conexión”</b> y el ticket sale con ese número (no es el número "
            "definitivo de la venta). <b>No cobres dos veces ni anotes la venta en papel</b>: ya está guardada en el equipo.",
            "Sin conexión no se pueden elegir clientes ni ver “Ventas de hoy”, el inventario ni las demás pestañas: solo se vende.",
            "<b>No cierres sesión mientras no haya conexión</b>: sin internet no se puede volver a entrar. Si lo intentas, la "
            "aplicación te lo advierte.",
            "Cuando vuelva internet, las ventas se envían solas (verás “Enviando ventas guardadas…” y luego “Se enviaron N "
            "ventas”). No tienes que hacer nada; si quieres, pulsa <b>Enviar ahora</b>. Una venta nunca se duplica.",
            "Si una venta queda como <b>“Necesita revisión”</b> (por ejemplo, porque el sistema decía que no había stock), avisa "
            "al administrador y muéstrale el motivo que aparece en <b>Ver ventas guardadas</b>: él corrige el inventario y tú "
            "pulsas <b>Reintentar</b>.",
            "Si al volver internet dice <b>“Tu sesión venció”</b>, pulsa “Iniciar sesión de nuevo”: las ventas guardadas se "
            "envían al entrar. No se pierden.",
            "Un vendedor envía solo las ventas que guardó él; un administrador envía las de todos.",
        ]),
        H("1.10 Gastos"),
        vinetas([
            "Si pagaste algo con plata del negocio (domicilio, bolsas, un favor…), anótalo en <b>Gastos</b> (menú “Gastos y caja”; en el celular, <b>Más › Gastos</b>): pulsa <b>Nuevo gasto</b> y escribe la categoría, qué se pagó, el monto en pesos enteros y la forma de pago. En efectivo el monto va en <b>múltiplos de $50</b>; en transferencia, elige Nequi o Daviplata. Se guarda con la fecha de hoy.",
            "Solo ves <b>tus</b> gastos. Puedes <b>Editar</b> o <b>Anular</b> los tuyos; anular pide el motivo y el gasto no se borra (queda tachado con tu nombre). Si el gasto ya entró en un corte de caja cerrado, solo el administrador puede corregirlo.",
            "Los gastos necesitan internet: sin conexión la pantalla lo avisa. Las ventas sin conexión siguen igual.",
        ]),
        H("1.11 Caja y corte"),
        vinetas([
            "Al empezar el turno abre la caja en <b>Caja</b> (menú “Gastos y caja”; en el celular, <b>Más › Caja</b>): escribe el efectivo con que arranca, la <b>base</b>, en múltiplos de $50. Solo puede haber una caja abierta: si otra persona ya la abrió, sigues con esa.",
            "Mientras trabajas, la pantalla muestra el <b>efectivo esperado</b>: la base, más las ventas en efectivo y los ingresos, menos los gastos en efectivo, las compras pagadas en efectivo y los retiros. Las vueltas no cuentan: solo lo que abona a la venta. Lo vendido con tarjeta y por Nequi o Daviplata sale aparte, para compararlo con el datáfono y el banco.",
            "Si entra o sale plata de la caja sin ser una venta ni un gasto (cambio, consignación al banco, retiro del dueño), regístrala con <b>Registrar ingreso</b> o <b>Registrar retiro</b> y su motivo; si no, el corte saldrá descuadrado.",
            "Al terminar, <b>cuenta el efectivo</b>, pulsa <b>Cerrar caja</b> y escribe lo contado (múltiplos de $50). La pantalla muestra la diferencia: <b>sobra</b> o <b>falta</b>. El corte queda guardado y ya no se puede cambiar.",
            "<b>Antes de cerrar</b>, mira que no tengas ventas guardadas sin enviar (aviso amarillo de arriba): el POS no deja cerrar la caja mientras las haya, para que no queden por fuera del corte.",
            "Después del cierre ya no puedes editar ni anular los gastos que entraron en ese corte; si hay un error, pídele el cambio al administrador.",
            "La caja necesita internet; sin conexión la pantalla lo avisa. Las ventas sin conexión siguen igual.",
        ]),
    ]


def contenido_completo():
    """Cuerpo del manual completo de la aplicación (9 capítulos)."""
    return [
        P("Este manual recorre <b>toda la aplicación</b>, de principio a fin: qué hace cada sección, quién puede usarla y qué "
          "hacer cuando algo no sale como se espera. Cada persona tiene además un manual corto con lo que le toca "
          "(vendedor, administrador y propietario)."),
        H("Contenido"),
        tabla(["Capítulo", "Para quién"], [
            ["<b>1.</b> Conoce la aplicación", "Todos"],
            ["<b>2.</b> Vender: la pantalla “Nueva venta”", "Vendedor y administrador"],
            ["<b>3.</b> Ventas de hoy y errores de venta", "Vendedor y administrador"],
            ["<b>4.</b> Clientes y datos personales (Habeas Data)", "Vendedor y administrador"],
            ["<b>5.</b> Inventario y compras", "Vendedor (inventario) y administrador"],
            ["<b>6.</b> Gastos y caja", "Vendedor y administrador (el propietario consulta)"],
            ["<b>7.</b> Negocio: descuentos, ganancias y usuarios", "Administrador"],
            ["<b>8.</b> El Dashboard del propietario", "Propietario"],
            ["<b>9.</b> Cuando algo falla: impresora, internet y respaldos", "Todos"],
        ], [0.64, 0.36]),

        H("1. Conoce la aplicación"),
        P("Es el sistema de ventas e inventario de la piñatería: punto de venta (POS), inventario, compras, clientes, "
          "gastos, caja, ganancias y un tablero (Dashboard) para el propietario. Se abre desde el navegador, en el computador o en el celular, "
          f"en la dirección {mono(URL_APP)}."),
        H2("Quién puede hacer qué"),
        tabla(["Rol", "Qué hace", "Qué ve en el menú"], [
            ["<b>Vendedor</b>", "Vende, registra clientes con su autorización, reimprime tickets y corrige el inventario con un "
                                "ajuste manual con motivo, registra sus gastos y abre y cierra la caja.", "Nueva venta, Ventas de hoy, Clientes, Inventario, Gastos, Caja"],
            ["<b>Administrador</b>", "Todo lo del vendedor y además administra el negocio: usuarios, compras, proveedores, "
                                     "categorías, descuentos, costos, gastos, caja y datos personales.",
             "Todo, incluidos Stock bajo, Compras, Proveedores, Categorías, Gastos, Caja, Descuentos, Ganancias, Usuarios y Datos personales"],
            ["<b>Propietario</b>", "Solo consulta: ventas, ganancias (con la ganancia neta), gastos, caja y alertas de stock. No vende ni modifica datos.", "Dashboard"],
        ], [0.18, 0.46, 0.36]),
        Spacer(1, 6),
        H2("El menú"),
        vinetas([
            "<b>En el computador</b> las secciones están en el menú lateral, agrupadas en <b>Ventas</b>, <b>Clientes</b>, "
            "<b>Inventario y compras</b>, <b>Gastos y caja</b> y <b>Negocio</b>.",
            "<b>En el celular</b> las de uso diario están en la barra inferior (Vender, Hoy, Clientes, Inventario) y el resto "
            "en el botón <b>Más</b>.",
        ]),
        H2("Entrar y salir"),
        vinetas([
            "Inicia sesión con <b>tu propio usuario</b>. La venta queda a nombre de quien tiene la sesión; nadie debe usar el "
            "usuario de otra persona.",
            "La contraseña tiene de 8 a 72 caracteres. Si la olvidas, el administrador la restablece desde <b>Usuarios</b>.",
            "La sesión dura 8 horas; después aparece “Sesión vencida” y basta con volver a entrar.",
            "<b>Instalarla en el celular:</b> abre la dirección en Chrome › menú › “Añadir a la pantalla de inicio”. Queda como "
            "una aplicación más (es una PWA).",
        ]),
        nota("En cada computador del POS, abre la aplicación <b>con internet al menos una vez</b>: así descarga el catálogo que "
             "necesita para vender si se cae la conexión (ver el capítulo 9).", "consejo"),

        H("2. Vender: la pantalla “Nueva venta”"),
        H2("Antes de abrir la tienda"),
        pasos([
            "Enciende el PC del POS y la impresora (Epson TM-T20II) y entra a la dirección de la aplicación.",
            "Inicia sesión con tu usuario.",
            "Comprueba que el <b>agente de impresión</b> esté corriendo (su ventana minimizada; arranca solo al iniciar Windows).",
        ]),
        H2("Hacer una venta"),
        pasos([
            "Busca el producto por nombre, o escanea el código de barras con el lector (el cursor debe estar en el buscador).",
            "Toca el producto para agregarlo. Ajusta cantidades en el carrito; se vende por unidad, por paquete o como ancheta.",
            "(Opcional) Elige el <b>cliente</b> si la persona está registrada (capítulo 4).",
            "(Opcional) Aplica un <b>descuento</b>.",
            "Elige cómo paga y pulsa <b>Confirmar venta</b>.",
            "Sale el ticket. Si no sale, la venta <b>sí quedó registrada</b>: usa <b>Reintentar impresión</b>.",
        ]),
        P("El total se redondea al múltiplo de $50 más cercano; el ticket muestra “Ajuste por redondeo”. En el celular, el panel "
          "de la venta se abre desde la barra inferior (cantidad de artículos y total)."),
        H2("Descuentos"),
        vinetas([
            "<b>General:</b> solo si el administrador lo activó. Se aplica a quien corresponde (clientes sin registro); no viene "
            "puesto por defecto.",
            "<b>Del cliente:</b> si el cliente tiene descuento propio, se sugiere solo al elegirlo. Puedes quitarlo.",
            "<b>Manual:</b> lo escribes tú (% o $), pero hay <b>topes</b> fijados por el administrador. Si te pasas, la aplicación "
            "no lo deja.",
            "El descuento se calcula sobre el subtotal y después se redondea a $50.",
        ]),
        H2("Formas de pago"),
        vinetas([
            "<b>Efectivo:</b> escribe el monto recibido; la aplicación calcula las <b>vueltas</b> y el ticket las imprime.",
            "<b>Tarjeta.</b>",
            "<b>Transferencia:</b> elige <b>Nequi</b> o <b>Daviplata</b>; es obligatorio. Quedan registradas como transferencia, "
            "con su plataforma.",
            "<b>Pago mixto:</b> agrega varios pagos (por ejemplo, $20.000 en efectivo y el resto por Nequi). La suma debe ser "
            "<b>exactamente el total</b>; si no, no deja confirmar.",
        ]),
        H2("Quién vendió"),
        P("El desplegable <b>Vendedor</b> trae tu nombre. Si otra persona atendió al cliente, cámbialo antes de confirmar: la "
          "venta queda a su nombre y el ticket dice “Atendió: …”. Después de cada venta vuelve a ti."),

        H("3. Ventas de hoy y errores de venta"),
        vinetas([
            "<b>Ventas de hoy</b> muestra lo que quedó hoy a tu nombre y también lo que tú registraste a nombre de otra persona "
            "(dice “Registrada por” cuando la registró alguien distinto del vendedor). El “día” se cuenta en hora de Bogotá.",
            "Desde ahí puedes <b>Reimprimir ticket</b>.",
            "Las ventas hechas sin conexión aparecen rotuladas “Sin conexión” una vez que se envían.",
        ]),
        nota("<b>Una venta registrada no se borra.</b> Si hubo un error, avisa al administrador y, si hace falta, al desarrollador. "
             "No hagas ajustes de inventario “a ojo” para compensarlo."),

        H("4. Clientes y datos personales (Habeas Data)"),
        P("Pestaña <b>Clientes</b>: busca por nombre, documento o teléfono. Un cliente <b>no se crea sin su autorización</b> para "
          "tratar sus datos."),
        H2("Registrar a un cliente nuevo (vendedor)"),
        pasos([
            "Pídele sus datos (nombre; documento y teléfono si los da; correo opcional).",
            "<b>Antes de guardar, léele o muéstrale el aviso de privacidad</b> (cartel en el mostrador) y pregunta si autoriza el "
            "tratamiento de sus datos. Sin autorización <b>no se registra</b>.",
            "Marca la casilla de autorización y el medio (verbal, escrito o electrónico).",
            "La casilla de <b>promociones es aparte</b>: márcala solo si el cliente dice que sí quiere recibirlas. Por defecto está "
            "desmarcada y no debes insistir.",
            f"Alternativa: el cliente se registra solo desde su celular con el <b>enlace de autorregistro</b> "
            f"({mono('/registro/&lt;código&gt;')}); allí lee el aviso y acepta él mismo.",
        ]),
        P("Si un cliente pide ver, corregir o borrar sus datos, o retirar su autorización: <b>no lo resuelvas tú</b>; anota su "
          "nombre y teléfono y avisa al administrador."),
        H2("Lo que hace el administrador"),
        P("En <b>Clientes › Datos personales</b>:"),
        vinetas([
            "<b>Datos del negocio:</b> nombre o razón social, NIT o cédula, dirección, teléfono, correo de contacto y fecha de la "
            "política. Mientras falte alguno, la política queda como “borrador” y no se puede generar el enlace de autorregistro.",
            "<b>Enlace de autorregistro:</b> se puede copiar, desactivar o regenerar. Al regenerarlo, el enlace anterior deja de "
            "funcionar. Quien se registra por el enlace queda activo, sin descuento propio y con su aceptación guardada.",
            "<b>Descuento propio de un cliente:</b> se asigna en su ficha. Se sugiere solo en la venta, reemplaza al general (no se "
            "suman) y no está sujeto a los topes.",
        ]),
        H2("Solicitudes de los titulares"),
        P("Cuando un cliente pide consultar, corregir o borrar sus datos, o retirar su autorización, el administrador la registra "
          "en la sección de solicitudes. El sistema calcula la fecha límite:"),
        tabla(["Tipo de solicitud", "Plazo"], [
            ["Consulta", "10 días hábiles"],
            ["Actualización, supresión o revocatoria", "15 días hábiles"],
        ], [0.6, 0.4]),
        Spacer(1, 6),
        vinetas([
            "Resolver una <b>supresión</b> anonimiza al cliente (nombre “Cliente anonimizado”; documento, teléfono, correo y "
            "descuento se borran) y conserva sus ventas.",
            "Resolver una <b>revocatoria</b> impide usar al cliente en ventas nuevas.",
            "Una solicitud resuelta o rechazada no se reabre.",
        ]),

        H("5. Inventario y compras"),
        H2("Productos"),
        vinetas([
            "Los productos se pueden vender por unidad, por paquete o como <b>ancheta</b> (producto compuesto con receta). La receta "
            "lleva cantidades enteras, sin productos repetidos.",
            "Un producto no se borra: se <b>desactiva</b> (y se puede reactivar). Una categoría con productos no se puede eliminar.",
            "El <b>stock mínimo</b> de cada producto dispara la alerta de stock bajo.",
            "Los nombres y textos que se registran quedan con la primera letra en mayúscula y el resto en minúscula.",
        ]),
        H2("Corregir el inventario"),
        P("Si falta o sobra producto, usa <b>Inventario</b> con un <b>ajuste manual</b> y su motivo; queda en el historial. "
          "Vendedor y administrador pueden hacerlo. No vendas “a ojo” algo que no está registrado."),
        H2("Compras y proveedores (administrador)"),
        pasos([
            "En <b>Compras</b>, crea la compra con el proveedor y los productos.",
            "Cuando llegue la mercancía, <b>recíbela</b>: solo entonces suma al stock. Al recibirla el sistema pregunta <b>cómo se pagó</b> (efectivo, tarjeta o transferencia por Nequi o Daviplata); la compra aparece en <b>Gastos</b> y, si se pagó en efectivo, resta de la caja.",
            "Una compra se puede cancelar antes de recibirla.",
            "Un proveedor que ya tiene compras no se elimina. El teléfono del proveedor lleva solo números (7 a 15).",
        ]),
        P("El total de una compra se redondea al múltiplo de $50 más cercano. Las <b>Categorías</b> se administran en su propia "
          "sección."),
        H2("Stock bajo y lista de compras (administrador)"),
        vinetas([
            "La bandeja avisa cuando un producto llega a su mínimo. Cada aviso sigue sin leer hasta que alguien lo marque, aunque el "
            "producto ya se haya repuesto.",
            "La <b>lista de compras</b> muestra cuánto falta de cada producto (mínimo menos stock actual). Se puede enviar por "
            "WhatsApp o copiar como texto.",
        ]),

        H("6. Gastos y caja"),
        P("El menú <b>Gastos y caja</b> reúne <b>Gastos</b> y <b>Caja</b>. Los dos necesitan conexión: sin internet la pantalla lo avisa, y las ventas sin conexión siguen igual."),
        H2("Gastos"),
        vinetas([
            "Anota lo que se paga con plata del negocio: <b>Nuevo gasto</b>, categoría, qué se pagó, monto en pesos enteros y forma de pago (en efectivo, múltiplos de $50; en transferencia, Nequi o Daviplata). El vendedor lo registra siempre con la fecha de hoy; el administrador puede poner una anterior, nunca futura.",
            "El <b>vendedor</b> solo ve, edita y anula los gastos que registró él; el <b>administrador</b> ve y modifica todos; el <b>propietario</b> solo consulta.",
            "Un gasto <b>no se borra</b>: se anula con un motivo y queda tachado con quién, cuándo y por qué. Un gasto anulado deja de sumar en los totales.",
            "El administrador y el propietario ven además las <b>compras recibidas</b> (categoría “Compra de mercancía”, solo lectura), los <b>totales</b> por categoría y por forma de pago, y pueden <b>Exportar</b> un archivo que abre Excel. El administrador crea, renombra y desactiva las <b>categorías</b>.",
        ]),
        H2("Caja y corte de caja"),
        pasos([
            "<b>Abrir la caja</b> con la base en efectivo (múltiplos de $50). Solo puede haber una caja abierta.",
            "Durante el turno la pantalla muestra el <b>efectivo esperado</b>: base + ventas en efectivo + ingresos − gastos en efectivo − compras en efectivo − retiros. Las vueltas y los gastos anulados no cuentan. Lo vendido con tarjeta y por transferencia sale aparte, para compararlo con el datáfono y el banco.",
            "Si entra o sale efectivo sin ser venta ni gasto (cambio, consignación al banco, retiro del dueño), registra un <b>ingreso</b> o un <b>retiro</b> con su motivo.",
            "Al terminar, <b>cuenta el efectivo</b> y pulsa <b>Cerrar caja</b>: el sistema calcula la diferencia (contado menos esperado: si es positiva sobra, si es negativa falta) y guarda una foto del corte que ya no se modifica.",
        ]),
        vinetas([
            "El POS <b>no deja cerrar la caja</b> si ese equipo tiene ventas guardadas sin enviar (modo sin conexión); una venta hecha sin conexión que llegue después del cierre no cambia el corte y se avisa en su ficha.",
            "Con el corte cerrado, el vendedor ya no puede editar ni anular los gastos que cubre; el administrador sí, y el corte conserva su foto.",
            "El <b>historial de cortes</b> lo ven todos (el vendedor, solo los que abrió o cerró); el administrador y el propietario pueden exportarlo. El propietario no abre ni cierra la caja.",
        ]),
        nota("Antes de cerrar la caja revisa que no queden ventas guardadas sin enviar y que todos los gastos del turno estén registrados: después del cierre el vendedor ya no puede corregirlos.", "consejo"),

        H("7. Negocio: descuentos, ganancias y usuarios"),
        H2("Descuentos"),
        vinetas([
            "<b>Descuento general:</b> se activa o desactiva en <b>Descuentos</b>, en porcentaje o en pesos. El vendedor lo aplica a "
            "quien corresponda; no viene puesto en todas las ventas.",
            "<b>Topes:</b> el máximo (porcentaje y monto) que el vendedor puede dar con un descuento escrito a mano. Mientras no se "
            "configuren, no hay límite.",
            "Todo descuento se calcula sobre el subtotal y el total se redondea a $50.",
        ]),
        H2("Costos y ganancias"),
        vinetas([
            "En <b>Ganancias</b>, escribe el costo de cada producto a mano. Para paquetes y anchetas aparece un costo sugerido a "
            "partir de sus componentes.",
            "El filtro <b>sin costo</b> muestra lo que falta cargar.",
            "Las ventas hechas antes de cargar los costos quedan “sin costo”. Usa <b>Completar costos de ventas anteriores</b> para "
            "incluirlas en la ganancia.",
            "La <b>ganancia neta</b> aparece en la misma pantalla: el margen bruto menos los gastos operativos (sin la compra de mercancía, que ya está en el costo de lo vendido). Aparte se muestra el <b>resultado de caja</b>: lo cobrado menos todos los gastos, compras incluidas; es una cifra de flujo de dinero, no una ganancia contable.",
        ]),
        H2("Usuarios"),
        vinetas([
            "Hay tres roles: <b>administrador</b>, <b>vendedor</b> y <b>propietario</b>.",
            "Los usuarios no se borran: se desactivan. Un administrador no puede desactivarse a sí mismo ni quitarse el rol.",
            "Para cambiar roles o restablecer contraseñas: Negocio › <b>Usuarios</b>.",
        ]),

        H("8. El Dashboard del propietario"),
        P("El propietario usa el <b>Dashboard</b>, también desde el celular. Solo consulta: no vende ni modifica datos."),
        vinetas([
            "<b>Ventas:</b> elige el rango (Hoy, Ayer, Semana, Mes, 3 meses, 6 meses, Año o personalizado). Ve el total, cuántas "
            "ventas, el desglose por forma de pago y los productos más vendidos.",
            "<b>Ganancias</b> (pestaña junto a “Ventas”): margen por período y por producto, y la tabla de costos en solo lectura. "
            "Las ventas sin costo cargado no entran en la ganancia hasta que el administrador complete los costos.",
            "<b>Ganancia neta</b> (dentro de “Ganancias”): el margen bruto menos los gastos operativos y, aparte, el resultado de caja (lo cobrado menos todos los gastos). Avisa si está incompleta por falta de costos.",
            "<b>Gastos</b> (pestaña junto a “Ganancias”): todos los gastos y las compras recibidas del rango, con totales por categoría y por forma de pago, y <b>Exportar</b>. Solo consulta.",
            "<b>Caja</b> (pestaña junto a “Gastos”): el efectivo esperado si la caja está abierta, el historial de cortes con su diferencia y su ficha, y <b>Exportar</b>. No abre, mueve ni cierra la caja.",
            "<b>Stock bajo</b> (botón con contador): la bandeja de alertas (marcar una o todas como leídas) y la <b>lista de "
            "compras</b>, que se puede enviar por WhatsApp o copiar como texto.",
        ]),
        P("<b>Decisiones que te tocan</b> (las ejecuta el administrador): topes y descuento general, descuento propio de clientes "
          "frecuentes, y la atención de solicitudes de datos personales."),
        nota("Las ventas hechas sin conexión no aparecen en el Dashboard hasta que se envían al servidor.", "consejo"),

        H("9. Cuando algo falla: impresora, internet y respaldos"),
        tabla(["Síntoma", "Qué hacer"], [
            ["No sale el ticket",
             f"Revisa que la impresora tenga papel y esté encendida; pulsa <b>Reintentar impresión</b>. Si sigue, el agente no está "
             f"corriendo: abre {mono('iniciar.bat')} en la carpeta {mono('printer-agent')}."],
            ["La aplicación no carga",
             "Revisa el internet de la tienda. Si ya tenías la aplicación abierta con la sesión iniciada, sigue vendiendo (ver abajo). "
             "Si no abre ni la pantalla de inicio de sesión, anota la venta en papel (producto, valor, forma de pago) y regístrala "
             "cuando vuelva."],
            ["“Sesión vencida”", "Vuelve a iniciar sesión (dura 8 horas)."],
            ["No encuentro un producto", "Prueba con otra palabra o el código; si no existe, avisa al administrador."],
        ], [0.3, 0.7]),
        H2("Si se cae internet (modo sin conexión)"),
        P("La aplicación sigue vendiendo aunque se caiga internet:"),
        vinetas([
            "Arriba aparece una barra roja: <b>“Sin conexión con el servidor. Puedes seguir vendiendo…”</b>. Vende como siempre: "
            "busca por nombre o con el lector, cobra y confirma.",
            "Al confirmar verás <b>“Venta SC-0001 guardada sin conexión”</b> y el ticket sale con ese número (no es el definitivo). "
            "<b>No cobres dos veces ni anotes la venta en papel</b>: ya está guardada en el equipo.",
            "Sin conexión no se pueden elegir clientes ni ver Ventas de hoy, Inventario ni las demás pestañas: solo se vende.",
            "Cuando vuelve internet, las ventas se envían solas (“Enviando ventas guardadas…” y luego “Se enviaron N ventas”). Si "
            "quieres, pulsa <b>Enviar ahora</b>. Nunca se duplican ni descuentan el stock dos veces.",
            "Si una venta queda como <b>“Necesita revisión”</b> (por ejemplo, el sistema decía que no había stock), avisa al "
            "administrador y muéstrale el motivo en “Ver ventas guardadas”: él corrige el inventario y tú pulsas <b>Reintentar</b>.",
            "Si dice <b>“Tu sesión venció”</b>, pulsa “Iniciar sesión de nuevo”: las ventas guardadas se envían al entrar y no se "
            "pierden.",
        ]),
        nota("<b>No cierres sesión mientras no haya conexión</b>: sin internet no se puede volver a entrar. La aplicación te "
             "advierte si lo intentas. Abre la aplicación con internet al empezar el día para que tenga los precios al día."),
        H2("Respaldos"),
        P("Cada día a las 2:30 a. m. el sistema hace un respaldo automático de la base de datos y conserva los de los últimos 14 "
          "días. Si algo falla y no se resuelve con lo anterior, revisa el internet de la tienda y el agente de impresión; si "
          "sigue, avisa al desarrollador."),
        H2("Reglas de oro"),
        vinetas([
            "Cada persona usa <b>su propio usuario</b>.",
            "Una venta registrada <b>no se borra</b>; los errores se avisan.",
            "Sin autorización de datos, <b>no se registra un cliente</b>.",
            "Los ajustes de inventario llevan siempre su <b>motivo</b>.",
            "Sin conexión: se vende, <b>no se cierra sesión</b> y no se anota nada en papel.",
            "Un gasto <b>no se borra</b> (se anula con motivo) y un corte de caja cerrado <b>no se modifica</b>.",
        ]),
    ]


# Versión de cada manual; los que no aparecen aquí usarían VERSION (1.0 del 13-10-2026).
VERSIONES = {
    "manual-completo": "Versión 1.1 — 20-10-2026",
    "manual-administrador": "Versión 1.2 — 20-10-2026",
    "manual-vendedor": "Versión 1.2 — 20-10-2026",
    "manual-propietario": "Versión 1.1 — 20-10-2026",
}

MANUALES = {
    "manual-completo": ("Manual completo de la aplicación", "Todos los roles", "Manual completo de la aplicación", contenido_completo),
    "manual-administrador": ("Manual del administrador", "Rol administrador", "Manual del administrador", contenido_administrador),
    "manual-propietario": ("Manual del propietario", "Rol propietario", "Manual del propietario", contenido_propietario),
    "manual-vendedor": ("Manual del vendedor", "Rol vendedor", "Manual del vendedor", contenido_vendedor),
}


def generar(archivo: Path, titulo: str, rol: str, corto: str, contenido, fecha_firma: str, version: str = VERSION, firma_png=None) -> None:
    """Arma un manual y lo escribe en `archivo`."""
    doc = BaseDocTemplate(
        str(archivo), pagesize=(ANCHO, ALTO), title=f"{titulo} — {NEGOCIO}", author=AUTOR,
        subject=f"{NEGOCIO}: documento privado, prohibida su difusión", creator=f"{AUTOR}",
        keywords="privado, confidencial, prohibida su difusión",
        leftMargin=MARGEN, rightMargin=MARGEN, topMargin=62, bottomMargin=58,
    )
    marco = Frame(MARGEN, 58, ANCHO - 2 * MARGEN, ALTO - 62 - 58, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="manual", frames=[marco], onPage=fondo_pagina(corto))])
    historia = portada(titulo, rol, version) + contenido() + [bloque_firma(fecha_firma, firma_png)]
    doc.build(historia, canvasmaker=LienzoNumerado)


def main():
    """Punto de entrada: genera los tres manuales."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--salida", type=Path, default=Path(__file__).resolve().parents[1] / "manuales")
    ap.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "demo-fuentes-manuales")
    ap.add_argument("--firma", type=Path, default=FIRMA, help="PNG transparente con la firma (opcional)")
    ap.add_argument("--fecha-firma", default=datetime.date.today().strftime("%d-%m-%Y"))
    args = ap.parse_args()
    preparar_fuentes(args.cache)
    crear_estilos()
    args.salida.mkdir(parents=True, exist_ok=True)
    for nombre, (titulo, rol, corto, contenido) in MANUALES.items():
        destino = args.salida / f"{nombre}.pdf"
        generar(destino, titulo, rol, corto, contenido, args.fecha_firma, VERSIONES.get(nombre, VERSION), args.firma)
        print("Escrito", destino)


if __name__ == "__main__":
    main()
