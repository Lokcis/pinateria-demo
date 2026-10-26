"""Genera printer-agent/assets/logo-ticket.png: el logo en blanco y negro (1 bit) para la termica Epson TM-T20II.

Negro donde el logo es oscuro (contornos y letras) y un medio tono ordenado donde es de tono medio (las orejas),
que en papel termico se ve mucho mas limpio que un difuminado de Floyd-Steinberg.
"""
import sys
from pathlib import Path

from PIL import Image, ImageOps

origen = Path(sys.argv[1])
destino = Path(sys.argv[2])
ANCHO = 336
NEGRO, GRIS_HASTA, DENSIDAD = 90, 175, 5
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]

logo = Image.open(origen).convert("RGBA")
fondo = Image.new("RGBA", logo.size, (255, 255, 255, 255))
fondo.alpha_composite(logo)
gris = fondo.convert("L")
gris = gris.crop(ImageOps.invert(gris).getbbox())
gris = gris.resize((ANCHO, round(gris.height * ANCHO / gris.width)), Image.LANCZOS)
salida = Image.new("1", gris.size, 1)
pix, destino_pix = gris.load(), salida.load()
for y in range(gris.height):
    for x in range(gris.width):
        valor = pix[x, y]
        if valor < NEGRO or (valor < GRIS_HASTA and BAYER[y % 4][x % 4] < DENSIDAD):
            destino_pix[x, y] = 0
salida.save(destino, optimize=True)
print(destino, salida.size)
