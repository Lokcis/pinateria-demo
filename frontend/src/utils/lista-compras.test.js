import { describe, expect, it } from "vitest";

import {
  LONGITUD_MAXIMA_ENLACE,
  armarMensajeListaCompras,
  describirFaltante,
  enlaceWhatsApp,
} from "./lista-compras";

const PRODUCTOS = [
  { nombre: "Globo #9 rojo", categoria: "Globos", stock_actual: 5, stock_minimo: 25, faltante: 20 },
  { nombre: "Globo metalizado", categoria: "Globos", stock_actual: 4, stock_minimo: 5, faltante: 1 },
  { nombre: "Velas número", categoria: "Velas", stock_actual: 5, stock_minimo: 5, faltante: 0 },
];

/** HU-10 (RF-045): el mensaje de WhatsApp lleva la lista escrita; si es muy larga se copia. */
describe("lista de compras — mensaje y enlace de WhatsApp", () => {
  it("describe el faltante en singular, plural y en el mínimo", () => {
    expect(describirFaltante(20)).toBe("faltan 20");
    expect(describirFaltante(1)).toBe("falta 1");
    expect(describirFaltante(0)).toBe("en el mínimo");
  });

  it("arma el mensaje agrupado por categoría, con la fecha y el total de productos", () => {
    expect(armarMensajeListaCompras(PRODUCTOS, "2026-10-08")).toBe(
      [
        "Lista de compras – Piñatería Demo (08/10/2026)",
        "",
        "*Globos*",
        "• Globo #9 rojo: faltan 20 (hay 5, mínimo 25)",
        "• Globo metalizado: falta 1 (hay 4, mínimo 5)",
        "",
        "*Velas*",
        "• Velas número: en el mínimo (hay 5, mínimo 5)",
        "",
        "3 productos",
      ].join("\n")
    );
  });

  it("el enlace abre wa.me sin número y con el mensaje codificado", () => {
    const mensaje = armarMensajeListaCompras(PRODUCTOS, "2026-10-08");
    const enlace = enlaceWhatsApp(mensaje);

    expect(enlace.startsWith("https://wa.me/?text=")).toBe(true);
    expect(decodeURIComponent(enlace.slice("https://wa.me/?text=".length))).toBe(mensaje);
  });

  it("si la lista es muy larga no hay enlace (se ofrece copiar el texto)", () => {
    const muchos = Array.from({ length: 80 }, (_, i) => ({
      nombre: `Producto con nombre largo ${i}`,
      categoria: "Varios",
      stock_actual: 1,
      stock_minimo: 10,
      faltante: 9,
    }));
    const mensaje = armarMensajeListaCompras(muchos, "2026-10-08");

    expect(`https://wa.me/?text=${encodeURIComponent(mensaje)}`.length).toBeGreaterThan(LONGITUD_MAXIMA_ENLACE);
    expect(enlaceWhatsApp(mensaje)).toBeNull();
  });
});
