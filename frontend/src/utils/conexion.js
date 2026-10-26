/**
 * Utilidades de conexion para el modo sin conexion (Fase 9).
 */

/** Estados HTTP con los que el tunel o Nginx dicen "el servidor no esta disponible": la venta se guarda y se reintenta. */
const ESTADOS_SIN_SERVICIO = new Set([502, 503, 504]);

/**
 * Indica si un error significa que NO se pudo hablar con el servidor (sin red, tiempo agotado o
 * servidor/tunel caido), y no que el servidor rechazo la peticion.
 *
 * Solo en estos casos una venta se guarda en la cola local; un 409 o un 422 son respuestas del
 * servidor y se muestran tal cual.
 *
 * @param {unknown} error - Lo que lanzo `fetch` o `solicitarApi`.
 * @returns {boolean} `true` si fue un fallo de conexion.
 */
export function esErrorDeConexion(error) {
  if (!error) return false;
  if (error.name === "AbortError" || error.name === "TimeoutError") return true;
  // `fetch` rechaza con TypeError cuando no hay red ("Failed to fetch", "NetworkError...").
  if (error instanceof TypeError) return true;
  const estado = Number(error.status);
  // Los 52x son los errores de Cloudflare cuando no alcanza el origen (ej. 521: servidor caido).
  return ESTADOS_SIN_SERVICIO.has(estado) || (estado >= 520 && estado <= 530);
}

/**
 * Genera un identificador unico para una venta (`uuid_cliente`). Con el, reenviar la misma venta
 * nunca la duplica en el servidor.
 *
 * @returns {string} UUID v4.
 */
export function nuevoUuid() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  // Respaldo para navegadores sin randomUUID (contextos no seguros).
  const bytes = new Uint8Array(16);
  if (typeof crypto !== "undefined" && typeof crypto.getRandomValues === "function") {
    crypto.getRandomValues(bytes);
  } else {
    for (let i = 0; i < 16; i += 1) bytes[i] = Math.floor(Math.random() * 256);
  }
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
