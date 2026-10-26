"""Genera el logo de demostracion y los iconos de la app en `frontend/public/`.

El logo de este repositorio publico es generico (una piñata en forma de estrella con el texto "Piñatería Demo"):
se dibuja aqui mismo, sin imagenes de origen. Guarda el original en `scripts/logo/logo-demo.png` y de el salen
`frontend/public/logo-demo.png` (1024 px de ancho), los iconos de la PWA (192, 512 y "maskable"), el icono de
Apple (180) y el favicon (png e ico).

Uso (desde la raiz del repo; necesita Pillow y solo es para desarrollo):

    python scripts/generar_logos.py
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
ORIGEN = RAIZ / "scripts" / "logo" / "logo-demo.png"
DESTINO = RAIZ / "frontend" / "public"

FONDO_ICONOS = (251, 246, 238)  # papel crema de la app (--color-papel)
TINTA = (43, 33, 80)
MAGENTA = (226, 54, 140)
AMARILLO = (255, 200, 40)
CIAN = (30, 190, 220)
LADO = 1024
SUPER = 2  # se dibuja al doble y se reduce, para bordes suaves
FUENTES = ["arialbd.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"]


def fuente(tamano: int) -> ImageFont.ImageFont:
    """Devuelve una fuente en negrita disponible en el sistema (o la de Pillow si no hay ninguna).

    Args:
        tamano: Tamaño del texto en pixeles.

    Returns:
        La fuente cargada.
    """
    for nombre in FUENTES:
        try:
            return ImageFont.truetype(nombre, tamano)
        except OSError:
            continue
    return ImageFont.load_default(tamano)


def estrella(cx: float, cy: float, radio: float, interior: float, giro: float = -90.0) -> list[tuple[float, float]]:
    """Calcula los vertices de una estrella de cinco puntas.

    Args:
        cx: Centro horizontal.
        cy: Centro vertical.
        radio: Distancia del centro a cada punta.
        interior: Proporcion (0 a 1) del radio interior respecto al de las puntas.
        giro: Angulo de la primera punta, en grados (-90 apunta hacia arriba).

    Returns:
        Lista de 10 vertices (punta, valle, punta, valle...).
    """
    puntos = []
    for i in range(10):
        r = radio if i % 2 == 0 else radio * interior
        a = math.radians(giro + i * 36)
        puntos.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return puntos


def dibujar() -> Image.Image:
    """Dibuja el logo de demostracion con fondo transparente.

    Returns:
        Imagen RGBA cuadrada de 1024 px.
    """
    n = LADO * SUPER
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = n / 2, n * 0.36
    # Cordel
    d.line([(cx, n * 0.02), (cx, cy - n * 0.28)], fill=TINTA, width=10 * SUPER)
    # Flecos de papel en las puntas
    for i in range(5):
        a = math.radians(-90 + i * 72)
        px, py = cx + n * 0.29 * math.cos(a), cy + n * 0.29 * math.sin(a)
        color = (MAGENTA, AMARILLO, CIAN)[i % 3]
        for k in (-1, 0, 1):
            d.line([(px, py), (px + k * 26 * SUPER, py + 60 * SUPER)], fill=color, width=12 * SUPER)
    # Cuerpo de la piñata
    d.polygon(estrella(cx, cy, n * 0.29, 0.5), fill=MAGENTA, outline=TINTA, width=14 * SUPER)
    d.polygon(estrella(cx, cy, n * 0.19, 0.5, giro=-90 + 36), fill=AMARILLO, outline=TINTA, width=10 * SUPER)
    d.ellipse([cx - n * 0.07, cy - n * 0.07, cx + n * 0.07, cy + n * 0.07], fill=CIAN, outline=TINTA, width=10 * SUPER)
    # Texto
    for texto, y, tam, color in (("PIÑATERÍA", 0.80, 120, TINTA), ("DEMO", 0.91, 120, MAGENTA)):
        f = fuente(tam * SUPER)
        ancho = d.textlength(texto, font=f)
        d.text(((n - ancho) / 2, n * y), texto, font=f, fill=color, anchor="ls")
    return img.resize((LADO, LADO), Image.LANCZOS)


def ajustar(imagen: Image.Image, lado: int, fraccion: float, fondo: tuple[int, ...] | None) -> Image.Image:
    """Centra el logo en un lienzo cuadrado.

    Args:
        imagen: Logo con fondo transparente.
        lado: Lado del lienzo final, en pixeles.
        fraccion: Parte del lienzo que ocupa el logo (0 a 1).
        fondo: Color de fondo RGB, o None para dejarlo transparente.

    Returns:
        Imagen cuadrada lista para guardar.
    """
    lienzo = Image.new("RGBA", (lado, lado), (*fondo, 255) if fondo else (0, 0, 0, 0))
    objetivo = round(lado * fraccion)
    logo = imagen.copy()
    logo.thumbnail((objetivo, objetivo), Image.LANCZOS)
    lienzo.alpha_composite(logo, ((lado - logo.width) // 2, (lado - logo.height) // 2))
    return lienzo


def main() -> None:
    """Dibuja el logo y escribe el original, el de la app y los iconos."""
    logo = dibujar()
    ORIGEN.parent.mkdir(parents=True, exist_ok=True)
    logo.save(ORIGEN, optimize=True)
    DESTINO.mkdir(parents=True, exist_ok=True)
    logo.save(DESTINO / "logo-demo.png", optimize=True)
    ajustar(logo, 192, 0.80, FONDO_ICONOS).save(DESTINO / "pwa-192x192.png", optimize=True)
    ajustar(logo, 512, 0.80, FONDO_ICONOS).save(DESTINO / "pwa-512x512.png", optimize=True)
    ajustar(logo, 512, 0.58, FONDO_ICONOS).save(DESTINO / "maskable-icon-512x512.png", optimize=True)  # zona segura
    ajustar(logo, 180, 0.80, FONDO_ICONOS).save(DESTINO / "apple-touch-icon.png", optimize=True)
    icono = ajustar(logo, 256, 0.96, None)
    ajustar(logo, 32, 0.96, None).save(DESTINO / "favicon-32x32.png", optimize=True)
    icono.save(DESTINO / "favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])
    print("Logo de demostracion generado en", DESTINO)


if __name__ == "__main__":
    main()
