"""Genera el cartel de la tienda (PDF de una hoja carta) con el aviso corto, el enlace de autorregistro y su código QR.

El texto es el de la sección 3.2 de `08-politica-tratamiento-datos-borrador.md`. Todo se calcula en este PC: el enlace
lleva un código secreto, así que **no lo pegues en generadores de QR de internet**.

Requiere ``reportlab``, ``qrcode`` (con Pillow) y las fuentes Arial de Windows.

Uso (desde esta carpeta)::

    python qr_cartel.py "https://pos.demo.example.com/registro/CODIGO" cartel.pdf --nombre "Piñatería Demo" --nit "123.456.789-0"

Si se regenera el enlace en la aplicación, el anterior deja de funcionar: hay que volver a imprimir el cartel.
"""

import argparse
import io
from pathlib import Path

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

CARPETA_FUENTES = Path("C:/Windows/Fonts")
COLOR_MARCA = colors.HexColor("#7B2D8E")


def imagen_qr(enlace):
    """Devuelve el código QR del enlace como imagen lista para dibujar en el PDF (corrección de errores alta)."""
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_Q, box_size=12, border=2)
    qr.add_data(enlace)
    qr.make(fit=True)
    buffer = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buffer, format="PNG")
    buffer.seek(0)
    return ImageReader(buffer)


def lineas_ajustadas(texto, fuente, tamano, ancho):
    """Parte un texto en renglones que quepan en `ancho` puntos."""
    renglones, actual = [], ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if pdfmetrics.stringWidth(prueba, fuente, tamano) <= ancho:
            actual = prueba
        else:
            renglones.append(actual)
            actual = palabra
    renglones.append(actual)
    return renglones


def dibujar(enlace, salida, nombre, nit):
    """Dibuja el cartel: título, aviso corto, QR, enlace y responsable."""
    for apodo, archivo in (("Arial", "arial.ttf"), ("Arial-Bold", "arialbd.ttf")):
        pdfmetrics.registerFont(TTFont(apodo, str(CARPETA_FUENTES / archivo)))
    ancho, alto = letter
    c = canvas.Canvas(str(salida), pagesize=letter)
    c.setTitle("Cartel de datos personales")
    c.setFillColor(COLOR_MARCA)
    c.setFont("Arial-Bold", 44)
    c.drawCentredString(ancho / 2, alto - 4 * 28.35, "Tus datos, con respeto.")
    c.setFillColor(colors.black)
    aviso = (
        "Si te registras como cliente guardamos tu nombre y, si quieres, tu documento, teléfono y correo, "
        "solo para llevar tus compras y darte descuentos. No los vendemos ni los usamos para publicidad."
    )
    y = alto - 6.5 * 28.35
    c.setFont("Arial", 18)
    for renglon in lineas_ajustadas(aviso, "Arial", 18, ancho - 6 * 28.35):
        c.drawCentredString(ancho / 2, y, renglon)
        y -= 26
    lado = 9 * 28.35
    c.drawImage(imagen_qr(enlace), (ancho - lado) / 2, y - lado - 14, lado, lado)
    y -= lado + 40
    c.setFont("Arial-Bold", 16)
    c.drawCentredString(ancho / 2, y, "Regístrate tú mismo con la cámara de tu celular")
    y -= 24
    c.setFont("Arial", 11)
    for renglon in lineas_ajustadas(enlace, "Arial", 11, ancho - 4 * 28.35):
        c.drawCentredString(ancho / 2, y, renglon)
        y -= 15
    c.setFont("Arial", 12)
    c.drawCentredString(ancho / 2, 4 * 28.35, "Política completa disponible en la tienda.")
    c.drawCentredString(ancho / 2, 4 * 28.35 - 17, f"Responsable: {nombre}, NIT {nit}.")
    c.save()


def main():
    """Lee los argumentos y escribe el cartel."""
    parser = argparse.ArgumentParser(description="Cartel con enlace y QR de autorregistro")
    parser.add_argument("enlace", help="Enlace de autorregistro completo (https://.../registro/<código>)")
    parser.add_argument("salida", help="Archivo PDF de salida")
    parser.add_argument("--nombre", required=True, help="Nombre o razón social del responsable")
    parser.add_argument("--nit", required=True, help="NIT o cédula del responsable")
    args = parser.parse_args()
    dibujar(args.enlace, args.salida, args.nombre, args.nit)
    print(f"Listo: {args.salida}")


if __name__ == "__main__":
    main()
