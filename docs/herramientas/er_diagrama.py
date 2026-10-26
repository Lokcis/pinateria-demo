"""Dibuja el diagrama entidad-relación v1.2 (esquema original + Adendo v2) con Pillow."""
import os
from PIL import Image, ImageDraw, ImageFont

R = os.path.dirname(os.path.abspath(__file__))
FN = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 23)
FB = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 25)
FS = ImageFont.truetype("C:/Windows/Fonts/ariali.ttf", 21)

AZUL, AZUL_CL = (31, 78, 121), (255, 255, 255)
MAG, MAG_CL = (160, 43, 111), (253, 243, 249)
TINTA = (31, 27, 58)
LINEA = (60, 90, 140)
LINEA_N = (160, 43, 111)

W, H = 1340, 1910
BW = 380
LH = 31   # alto de cada campo
HH = 40   # alto del encabezado
X0, X1, X2 = 30, 480, 930

# nombre: (x, y, nuevo, campos)
E = {
    "categorias": (X0, 40, False, ["PK id", "nombre", "descripcion"]),
    "usuarios": (X0, 210, False, ["PK id", "nombre", "username", "password_hash", "rol", "activo"]),
    "clientes": (X0, 470, True, ["PK id", "nombre", "documento (único)", "telefono", "email",
                                 "descuento_tipo / descuento_valor", "activo", "origen_registro", "autorizacion_* (6 campos)", "anonimizado_en"]),
    "solicitudes_titular": (X0, 880, True, ["PK id", "FK cliente_id", "tipo", "estado", "fecha_limite", "FK atendida_por"]),
    "proveedores": (X0, 1190, False, ["PK id", "nombre_empresa", "nombre_contacto", "telefono", "email"]),
    "productos": (X1, 40, False, ["PK id", "FK categoria_id", "nombre", "codigo_barras (null)", "tipo", "precio_venta",
                                  "costo_unitario (null) *", "stock_actual", "stock_minimo", "activo"]),
    "ventas": (X1, 420, False, ["PK id", "FK usuario_id (vendedor)", "FK cliente_id (null)", "fecha", "subtotal",
                                "descuento_origen / _tipo / _valor", "descuento_monto", "ajuste_redondeo", "total"]),
    "pagos_venta": (X1, 770, True, ["PK id", "FK venta_id", "metodo_pago", "plataforma (null)", "monto",
                                    "monto_recibido (null)", "vueltas"]),
    "descuento_general": (X1, 1040, True, ["PK id (= 1)", "tipo", "valor", "activo", "FK actualizado_por"]),
    "compras": (X1, 1250, False, ["PK id", "FK proveedor_id", "FK usuario_id", "fecha", "estado", "total"]),
    "enlace_autoregistro": (X0, 1430, True, ["PK id (= 1)", "token (único)", "activo", "FK actualizado_por"]),
    "tope_descuento": (X2, 1020, True, ["PK id (= 1)", "tope_porcentaje (null)", "tope_monto (null)", "FK actualizado_por"]),
    "notificaciones": (X2, 40, False, ["PK id", "FK producto_id (null)", "tipo", "mensaje", "leida"]),
    "ajustes_inventario": (X2, 250, False, ["PK id", "FK producto_id", "FK usuario_id", "tipo", "cantidad", "motivo"]),
    "detalle_ventas": (X2, 500, False, ["PK id", "FK venta_id", "FK producto_id", "cantidad", "precio_unitario", "subtotal",
                                        "descuento_prorrateado", "costo_unitario (null) *"]),
    "producto_componentes": (X2, 830, False, ["PK id", "FK producto_padre_id", "FK producto_componente_id", "cantidad"]),
    "detalle_compras": (X2, 1250, False, ["PK id", "FK compra_id", "FK producto_id", "cantidad", "costo_unitario", "subtotal"]),
}


def caja(n):
    x, y, _, campos = E[n]
    return x, y, BW, HH + LH * len(campos) + 8


def fila_y(n, texto):
    x, y, _, campos = E[n]
    i = next(k for k, c in enumerate(campos) if c.startswith(texto))
    return y + HH + LH * i + LH // 2


img = Image.new("RGB", (W, H), (255, 255, 255))
d = ImageDraw.Draw(img)

# ---------- relaciones (polilíneas ortogonales por canales verticales)
def relacion(a, lado_a, ya, b, lado_b, yb, canal, etiq_a="", etiq_b="", discontinua=False, color=LINEA):
    xa, _, wa, _ = caja(a)
    xb, _, wb, _ = caja(b)
    pa = xa + (wa if lado_a == "r" else 0)
    pb = xb + (wb if lado_b == "r" else 0)
    puntos = [(pa, ya), (canal, ya), (canal, yb), (pb, yb)]
    for (p, q) in zip(puntos, puntos[1:]):
        if discontinua:
            largo = abs(q[0] - p[0]) + abs(q[1] - p[1])
            pasos = int(largo // 14)
            for k in range(0, pasos, 2):
                t0, t1 = k / max(pasos, 1), min((k + 1) / max(pasos, 1), 1)
                d.line([(p[0] + (q[0] - p[0]) * t0, p[1] + (q[1] - p[1]) * t0), (p[0] + (q[0] - p[0]) * t1, p[1] + (q[1] - p[1]) * t1)], fill=color, width=3)
        else:
            d.line([p, q], fill=color, width=3)
    for (px, py, lado, txt) in ((pa, ya, lado_a, etiq_a), (pb, yb, lado_b, etiq_b)):
        if txt:
            tx = px + 6 if lado == "r" else px - 6 - d.textlength(txt, font=FS)
            d.text((tx, py - 28), txt, fill=TINTA, font=FS)


NEW = LINEA_N
# categorias - productos
relacion("categorias", "r", fila_y("categorias", "PK"), "productos", "l", fila_y("productos", "FK categoria"), 455, "1", "N")
# usuarios - ventas / compras
relacion("usuarios", "r", fila_y("usuarios", "nombre"), "ventas", "l", fila_y("ventas", "FK usuario"), 440, "1", "N")
relacion("usuarios", "r", fila_y("usuarios", "rol"), "compras", "l", fila_y("compras", "FK usuario"), 420, "1", "N")
# clientes - ventas
relacion("clientes", "r", fila_y("clientes", "nombre"), "ventas", "l", fila_y("ventas", "FK cliente"), 460, "1", "N", color=NEW)
# proveedores - compras
relacion("proveedores", "r", fila_y("proveedores", "PK"), "compras", "l", fila_y("compras", "FK proveedor"), 445, "1", "N")
# clientes - solicitudes (vertical)
d.line([(X0 + 190, caja("clientes")[1] + caja("clientes")[3]), (X0 + 190, E["solicitudes_titular"][1])], fill=NEW, width=3)
d.text((X0 + 198, caja("clientes")[1] + caja("clientes")[3] + 4), "1        N", fill=TINTA, font=FS)
# ventas - pagos_venta (vertical)
d.line([(X1 + 190, caja("ventas")[1] + caja("ventas")[3]), (X1 + 190, E["pagos_venta"][1])], fill=NEW, width=3)
d.text((X1 + 198, caja("ventas")[1] + caja("ventas")[3] + 4), "1        N", fill=TINTA, font=FS)
# productos - detalle_ventas / detalle_compras / ajustes / notificaciones / componentes
relacion("productos", "r", fila_y("productos", "nombre"), "notificaciones", "l", fila_y("notificaciones", "FK producto"), 905, "1", "0..N", discontinua=True)
relacion("productos", "r", fila_y("productos", "codigo"), "ajustes_inventario", "l", fila_y("ajustes_inventario", "FK producto"), 915, "1", "N")
relacion("productos", "r", fila_y("productos", "tipo"), "detalle_ventas", "l", fila_y("detalle_ventas", "FK producto"), 925, "1", "N")
relacion("productos", "r", fila_y("productos", "precio"), "producto_componentes", "l", fila_y("producto_componentes", "FK producto_padre"), 935, "1", "N")
relacion("productos", "r", fila_y("productos", "stock_actual"), "producto_componentes", "l", fila_y("producto_componentes", "FK producto_componente"), 895, "1", "N")
relacion("productos", "r", fila_y("productos", "activo"), "detalle_compras", "l", fila_y("detalle_compras", "FK producto"), 885, "1", "N")
# ventas - detalle_ventas
relacion("ventas", "r", fila_y("ventas", "PK"), "detalle_ventas", "l", fila_y("detalle_ventas", "FK venta"), 945, "1", "N")
# compras - detalle_compras
relacion("compras", "r", fila_y("compras", "PK"), "detalle_compras", "l", fila_y("detalle_compras", "FK compra"), 905, "1", "N")

# ---------- cajas
for n, (x, y, nuevo, campos) in E.items():
    _, _, w, h = caja(n)
    cab, fondo = (MAG, MAG_CL) if nuevo else (AZUL, AZUL_CL)
    d.rectangle([x, y, x + w, y + h], fill=fondo, outline=cab, width=3)
    d.rectangle([x, y, x + w, y + HH], fill=cab)
    tw = d.textlength(n, font=FB)
    d.text((x + (w - tw) / 2, y + 6), n, fill=(255, 255, 255), font=FB)
    for i, c in enumerate(campos):
        color = TINTA
        d.text((x + 12, y + HH + LH * i + 2), c, fill=color, font=FN)

# ---------- leyenda
ly = H - 110
d.rectangle([30, ly, 52, ly + 22], fill=AZUL)
d.text((62, ly - 2), "Esquema original (v1.1)", fill=TINTA, font=FN)
d.rectangle([380, ly, 402, ly + 22], fill=MAG)
d.text((412, ly - 2), "Adendo v2 (tablas nuevas)", fill=TINTA, font=FN)
d.text((30, ly + 36), "* Campo de la Fase A3 (opcional).  ventas.metodo_pago se elimina: pasa a pagos_venta.", fill=TINTA, font=FS)
d.text((30, ly + 64), "Se omiten las líneas hacia usuarios desde clientes, descuento_general, tope_descuento,", fill=TINTA, font=FS)
d.text((30, ly + 90), "solicitudes_titular, enlace_autoregistro y ajustes_inventario (se indican como campos FK).", fill=TINTA, font=FS)

img.save(os.path.join(R, "..", "img", "bd-modelo-entidad-relacion-v1_2.png"), optimize=True)
print("er_v12.png", img.size)
