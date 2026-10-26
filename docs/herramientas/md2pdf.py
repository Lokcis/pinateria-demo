"""Convierte un Markdown de docs/ (por ejemplo, 09-guia-de-capacitacion.md) en un PDF para revisar o imprimir.

Entiende lo que usan los documentos: encabezados (#, ##, ###), párrafos, listas con viñetas o numeradas,
casillas (`- [ ]`), citas (`>`), tablas con barras (`|`), negrita, cursiva y código en línea.

Requiere ``reportlab`` y las fuentes Arial de Windows (para las tildes, la ñ y el cuadro de las casillas).

Uso (desde esta carpeta)::

    python md2pdf.py ../09-guia-de-capacitacion.md salida.pdf
"""

import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    CondPageBreak,
    Frame,
    ListFlowable,
    ListItem,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

CARPETA_FUENTES = Path("C:/Windows/Fonts")
COLOR_MARCA = colors.HexColor("#7B2D8E")
COLOR_TEXTO = colors.HexColor("#2B2B2B")
COLOR_FILA = colors.HexColor("#F4EEF7")
PIE = "Piñatería Demo — Confidencial"


def registrar_fuentes():
    """Registra Arial (normal, negrita, cursiva) y Courier para el código en línea."""
    for nombre, archivo in (("Arial", "arial.ttf"), ("Arial-Bold", "arialbd.ttf"), ("Arial-Italic", "ariali.ttf"), ("Arial-BoldItalic", "arialbi.ttf")):
        pdfmetrics.registerFont(TTFont(nombre, str(CARPETA_FUENTES / archivo)))
    pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold", italic="Arial-Italic", boldItalic="Arial-BoldItalic")


def estilos():
    """Devuelve los estilos de párrafo del documento, por nombre."""
    base = ParagraphStyle("base", fontName="Arial", fontSize=10, leading=14, textColor=COLOR_TEXTO)
    return {
        "p": base,
        "h1": ParagraphStyle("h1", parent=base, fontName="Arial-Bold", fontSize=24, leading=28, textColor=COLOR_MARCA, spaceAfter=10),
        "h2": ParagraphStyle("h2", parent=base, fontName="Arial-Bold", fontSize=16, leading=20, textColor=COLOR_MARCA, spaceBefore=6, spaceAfter=8),
        "h3": ParagraphStyle("h3", parent=base, fontName="Arial-Bold", fontSize=12, leading=16, spaceBefore=10, spaceAfter=4),
        "cita": ParagraphStyle("cita", parent=base, leftIndent=12, borderPadding=(4, 4, 4, 8), backColor=COLOR_FILA, spaceAfter=6),
        "celda": ParagraphStyle("celda", parent=base, fontSize=8.5, leading=11),
        "celda_enc": ParagraphStyle("celda_enc", parent=base, fontSize=8.5, leading=11, fontName="Arial-Bold", textColor=colors.white),
        "centro": ParagraphStyle("centro", parent=base, alignment=TA_CENTER),
    }


def en_linea(texto):
    """Convierte el formato en línea de Markdown (negrita, cursiva, código) al mini-HTML de reportlab."""
    texto = texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    texto = re.sub(r"`([^`]+)`", r'<font name="Courier" size="9">\1</font>', texto)
    texto = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", texto)
    texto = re.sub(r"(?<![*\w])\*([^*]+)\*(?![*\w])", r"<i>\1</i>", texto)
    return texto


def tabla(filas, est):
    """Arma una tabla de reportlab a partir de las filas (listas de texto) de una tabla Markdown."""
    columnas = max(len(f) for f in filas)
    datos = []
    for i, fila in enumerate(filas):
        fila = fila + [""] * (columnas - len(fila))
        estilo = est["celda_enc"] if i == 0 else est["celda"]
        datos.append([Paragraph(en_linea(c), estilo) for c in fila])
    ancho = letter[0] - 4 * cm
    t = Table(datos, colWidths=[ancho / columnas] * columnas, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_MARCA),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_FILA]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D5C6DC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return t


def partir_fila(linea):
    """Separa una fila de tabla Markdown en sus celdas."""
    return [c.strip() for c in linea.strip().strip("|").split("|")]


def construir(lineas, est):
    """Recorre las líneas del Markdown y devuelve la lista de elementos (flowables) del PDF."""
    historia = []
    i = 0
    primera_h2 = True
    while i < len(lineas):
        linea = lineas[i].rstrip()
        if not linea.strip() or linea.strip() == "---":
            i += 1
        elif linea.startswith("# "):
            historia.append(Paragraph(en_linea(linea[2:]), est["h1"]))
            i += 1
        elif linea.startswith("## "):
            titulo = linea[3:]
            if re.match(r"[1-3]\. ", titulo):
                historia.append(PageBreak())
            elif not primera_h2:
                historia.append(CondPageBreak(7 * cm))
            primera_h2 = False
            historia.append(Paragraph(en_linea(titulo), est["h2"]))
            i += 1
        elif linea.startswith("### "):
            historia.append(CondPageBreak(4 * cm))
            historia.append(Paragraph(en_linea(linea[4:]), est["h3"]))
            i += 1
        elif linea.startswith("|"):
            filas = []
            while i < len(lineas) and lineas[i].startswith("|"):
                if not re.match(r"^\|[\s:|-]+\|?$", lineas[i].strip()):
                    filas.append(partir_fila(lineas[i]))
                i += 1
            historia += [tabla(filas, est), Spacer(1, 8)]
        elif linea.startswith(">"):
            historia.append(Paragraph(en_linea(linea.lstrip("> ").strip()), est["cita"]))
            i += 1
        elif re.match(r"^\s*(- |\* |\d+\. )", linea):
            numerada = bool(re.match(r"^\s*\d+\. ", linea))
            items = []
            while i < len(lineas) and re.match(r"^\s*(- |\* |\d+\. )", lineas[i]):
                texto = re.sub(r"^\s*(- |\* |\d+\. )", "", lineas[i].rstrip())
                texto = re.sub(r"^\[[ xX]\] ", "□  ", texto)
                items.append(ListItem(Paragraph(en_linea(texto), est["p"]), leftIndent=16))
                i += 1
            historia.append(ListFlowable(items, bulletType="1" if numerada else "bullet", start=None if not numerada else 1, bulletFontName="Arial", leftIndent=16, bulletFontSize=9))
            historia.append(Spacer(1, 6))
        else:
            parrafo = [linea.strip()]
            i += 1
            while i < len(lineas) and lineas[i].strip() and not re.match(r"^(#|\||>|\s*- |\s*\* |\s*\d+\. |---)", lineas[i]):
                parrafo.append(lineas[i].strip())
                i += 1
            historia.append(Paragraph(en_linea(" ".join(parrafo)), est["p"]))
            historia.append(Spacer(1, 6))
    return historia


def pie_de_pagina(lienzo, doc):
    """Dibuja el pie con el nombre del negocio y el número de página."""
    lienzo.saveState()
    lienzo.setFont("Arial", 8)
    lienzo.setFillColor(colors.HexColor("#777777"))
    lienzo.drawString(2 * cm, 1.2 * cm, PIE)
    lienzo.drawRightString(letter[0] - 2 * cm, 1.2 * cm, f"Página {doc.page}")
    lienzo.restoreState()


def main():
    """Punto de entrada: lee el Markdown, construye el PDF y lo escribe donde se indica."""
    if len(sys.argv) != 3:
        sys.exit("Uso: python md2pdf.py entrada.md salida.pdf")
    entrada, salida = Path(sys.argv[1]), Path(sys.argv[2])
    registrar_fuentes()
    est = estilos()
    historia = construir(entrada.read_text(encoding="utf-8").splitlines(), est)
    doc = BaseDocTemplate(str(salida), pagesize=letter, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm, title=entrada.stem, author="Piñatería Demo")
    marco = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="marco")
    doc.addPageTemplates([PageTemplate(id="p", frames=[marco], onPage=pie_de_pagina)])
    doc.build(historia)
    print(f"Listo: {salida}")


if __name__ == "__main__":
    main()
