# Herramientas de documentación

Scripts para regenerar los archivos de Word y el diagrama entidad-relación a partir de los Markdown de `docs/`.

## Generar un `.docx`

Requiere Node.js. Desde esta carpeta:

```bash
npm install
node md2docx.js ../01-vision-y-alcance.md salida.docx "Piñatería Demo — Documento de Visión y Alcance v1.4 — Confidencial"
```

El tercer parámetro es el texto del pie de página. El conversor entiende encabezados, listas, tablas con barras (`|`), bloques de código, negrita, cursiva, imágenes enlazadas (`![texto](img/archivo.png)`) y una portada formada por las líneas anteriores al primer encabezado. Una tabla de dos columnas cuya segunda fila empieza en negrita se trata como tabla de ficha (sin fila de encabezado).

## Regenerar el diagrama entidad-relación

Requiere Python con Pillow y las fuentes de Windows (Arial). Escribe `../img/bd-modelo-entidad-relacion-v1_2.png`:

```bash
python er_diagrama.py
```

Si cambian las tablas de la sección 7 de `03-diseno-base-de-datos.md`, actualiza `E` en el script (las entidades y sus campos) y vuelve a generarlo.

## Regenerar las figuras de la arquitectura

Dibuja en alta resolución las seis figuras de `04-arquitectura-tecnica.md` (vista general, contenedores, tienda, flujo de venta, flujo de venta con el Adendo v2 y alertas de stock). Mismos requisitos que el diagrama ER:

```bash
python arq_figuras.py
```

## Regenerar los manuales de usuario en PDF

Genera `manual-completo.pdf` (toda la app, 9 capítulos), `manual-administrador.pdf`, `manual-propietario.pdf` y `manual-vendedor.pdf` en `../manuales/` con el diseño de la app (colores, banderines, logo y tipografías Bricolage Grotesque y Figtree), con la marca de «documento privado, prohibida su difusión» y el bloque de firma de Santiago Chávez López. Requiere `pip install reportlab pillow fonttools brotli` y `npm ci` en `frontend/` (de ahí salen las tipografías y el logo):

```bash
python manuales_pdf.py
python manuales_pdf.py --fecha-firma 14-10-2026
```

El texto de cada manual está en las funciones `contenido_*` del script. Los PDF generados no se versionan en este repositorio.

## Convertir un Markdown a PDF

Convierte un Markdown de `docs/` en un PDF para revisar o imprimir (por ejemplo, la guía de capacitación). Requiere Python con `reportlab` y las fuentes Arial de Windows:

```bash
pip install reportlab
python md2pdf.py ../09-guia-de-capacitacion.md guia-de-capacitacion.pdf
```

## Cartel con enlace y código QR

Genera el cartel de la tienda (una hoja carta) con el aviso corto, el enlace de autorregistro y su QR. Requiere `reportlab` y `qrcode[pil]`. El enlace se copia de "Datos personales" en la aplicación. El QR se calcula en el propio PC: **no pegues el enlace en generadores de QR de internet**, porque lleva un código secreto.

```bash
pip install reportlab "qrcode[pil]"
python qr_cartel.py "https://pos.demo.example.com/registro/<código>" cartel.pdf --nombre "<nombre del negocio>" --nit "<NIT o cédula>"
```

Si el enlace se regenera en la aplicación, el anterior deja de funcionar y hay que volver a generar e imprimir el cartel.
