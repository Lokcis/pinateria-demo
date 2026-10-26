/**
 * Texto de la lista de compras y enlace de WhatsApp (Adendo v2, mejora B1: RF-045).
 *
 * El sistema no envia nada por su cuenta: arma el mensaje y un enlace `wa.me` que abre
 * WhatsApp con el texto ya escrito; el usuario elige el chat y lo envia.
 */

/**
 * Largo maximo del enlace de WhatsApp. Por encima, algunos navegadores y la app de
 * WhatsApp cortan la URL, asi que solo se ofrece copiar el texto.
 */
export const LONGITUD_MAXIMA_ENLACE = 2000;

/**
 * Describe la cantidad que falta de un producto (ej. "faltan 20", "falta 1", "en el mínimo").
 *
 * @param {number} faltante - `stock_minimo - stock_actual` (0 si esta justo en el minimo).
 * @returns {string}
 */
export function describirFaltante(faltante) {
  if (faltante <= 0) {
    return "en el mínimo";
  }
  return faltante === 1 ? "falta 1" : `faltan ${faltante}`;
}

/**
 * Arma el mensaje de la lista de compras, agrupado por categoria.
 *
 * @param {Array<{nombre: string, categoria: string, stock_actual: number, stock_minimo: number,
 *   faltante: number}>} productos - Productos de la lista, ya ordenados por categoria y nombre.
 * @param {string} dia - Dia de la lista, "AAAA-MM-DD" (zona de la tienda).
 * @returns {string} El mensaje, con la categoria en negrita al estilo de WhatsApp (`*texto*`).
 */
export function armarMensajeListaCompras(productos, dia) {
  const [anio, mes, diaDelMes] = dia.split("-");
  const lineas = [`Lista de compras – Piñatería Demo (${diaDelMes}/${mes}/${anio})`];

  let categoriaActual = null;
  for (const producto of productos) {
    if (producto.categoria !== categoriaActual) {
      categoriaActual = producto.categoria;
      lineas.push("", `*${categoriaActual}*`);
    }
    lineas.push(
      `• ${producto.nombre}: ${describirFaltante(producto.faltante)} ` +
        `(hay ${producto.stock_actual}, mínimo ${producto.stock_minimo})`
    );
  }

  lineas.push("", productos.length === 1 ? "1 producto" : `${productos.length} productos`);
  return lineas.join("\n");
}

/**
 * Enlace `wa.me` que abre WhatsApp con el mensaje escrito, sin numero (el usuario elige el chat).
 *
 * @param {string} mensaje - Texto a enviar.
 * @returns {string | null} El enlace, o null si supera `LONGITUD_MAXIMA_ENLACE` (hay que copiar el texto).
 */
export function enlaceWhatsApp(mensaje) {
  const enlace = `https://wa.me/?text=${encodeURIComponent(mensaje)}`;
  return enlace.length <= LONGITUD_MAXIMA_ENLACE ? enlace : null;
}
