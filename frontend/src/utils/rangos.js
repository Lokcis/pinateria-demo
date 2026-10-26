/**
 * Rangos de fechas del Dashboard. Todas las fechas son textos "AAAA-MM-DD" del dia de la
 * tienda (America/Bogota); se opera con `Date.UTC` para que la zona del navegador no
 * mueva el dia.
 */

/** Rangos rapidos del selector, en el orden en que se muestran. */
export const PRESETS = [
  { id: "hoy", etiqueta: "Hoy" },
  { id: "ayer", etiqueta: "Ayer" },
  { id: "semana", etiqueta: "Semana" },
  { id: "mes", etiqueta: "Mes" },
  { id: "3meses", etiqueta: "3 meses" },
  { id: "6meses", etiqueta: "6 meses" },
  { id: "anio", etiqueta: "Año" },
];

const FORMATO_DIA_BOGOTA = new Intl.DateTimeFormat("en-CA", {
  timeZone: "America/Bogota",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

/**
 * Fecha de hoy en la zona horaria de la tienda.
 *
 * @param {Date} [ahora] - Instante a convertir (por defecto, ahora).
 * @returns {string} "AAAA-MM-DD".
 */
export function hoyEnBogota(ahora = new Date()) {
  return FORMATO_DIA_BOGOTA.format(ahora);
}

/**
 * Separa un "AAAA-MM-DD" en numeros.
 *
 * @param {string} iso
 * @returns {[number, number, number]} [anio, mes (1-12), dia].
 */
function partes(iso) {
  const [anio, mes, dia] = iso.split("-").map(Number);
  return [anio, mes, dia];
}

/**
 * Formatea año, mes (1-12) y dia como "AAAA-MM-DD".
 *
 * @param {number} anio
 * @param {number} mes
 * @param {number} dia
 * @returns {string}
 */
function armar(anio, mes, dia) {
  return `${String(anio).padStart(4, "0")}-${String(mes).padStart(2, "0")}-${String(dia).padStart(2, "0")}`;
}

/**
 * Resta dias a una fecha.
 *
 * @param {string} iso - Fecha "AAAA-MM-DD".
 * @param {number} dias - Dias a restar (puede ser negativo para sumar).
 * @returns {string} "AAAA-MM-DD".
 */
export function restarDias(iso, dias) {
  const [anio, mes, dia] = partes(iso);
  const fecha = new Date(Date.UTC(anio, mes - 1, dia - dias));
  return armar(fecha.getUTCFullYear(), fecha.getUTCMonth() + 1, fecha.getUTCDate());
}

/**
 * Resta meses a una fecha; si el dia no existe en el mes destino, usa el ultimo (31 mar - 1 mes = 28 feb).
 *
 * @param {string} iso - Fecha "AAAA-MM-DD".
 * @param {number} meses - Meses a restar.
 * @returns {string} "AAAA-MM-DD".
 */
export function restarMeses(iso, meses) {
  const [anio, mes, dia] = partes(iso);
  const indice = anio * 12 + (mes - 1) - meses;
  const anioDestino = Math.floor(indice / 12);
  const mesDestino = (indice % 12) + 1;
  const ultimoDia = new Date(Date.UTC(anioDestino, mesDestino, 0)).getUTCDate();
  return armar(anioDestino, mesDestino, Math.min(dia, ultimoDia));
}

/**
 * Calcula el rango de un rango rapido. Los rangos terminan hoy y incluyen hoy:
 * "Semana" son los ultimos 7 dias; "Mes", "3 meses", "6 meses" y "Año" van desde el
 * dia siguiente a la misma fecha de hace 1, 3, 6 o 12 meses.
 *
 * @param {string} presetId - Uno de los `id` de `PRESETS`.
 * @param {string} hoy - Fecha de hoy "AAAA-MM-DD".
 * @returns {{desde: string, hasta: string}}
 * @throws {Error} Si el id no existe.
 */
export function rangoDePreset(presetId, hoy) {
  const desdeMeses = (meses) => restarDias(restarMeses(hoy, meses), -1);
  switch (presetId) {
    case "hoy":
      return { desde: hoy, hasta: hoy };
    case "ayer": {
      const ayer = restarDias(hoy, 1);
      return { desde: ayer, hasta: ayer };
    }
    case "semana":
      return { desde: restarDias(hoy, 6), hasta: hoy };
    case "mes":
      return { desde: desdeMeses(1), hasta: hoy };
    case "3meses":
      return { desde: desdeMeses(3), hasta: hoy };
    case "6meses":
      return { desde: desdeMeses(6), hasta: hoy };
    case "anio":
      return { desde: desdeMeses(12), hasta: hoy };
    default:
      throw new Error(`Rango desconocido: ${presetId}`);
  }
}

const FORMATO_LARGO = new Intl.DateTimeFormat("es-CO", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });

/**
 * Formatea una fecha "AAAA-MM-DD" para mostrarla (ej. "25 sept 2026").
 *
 * @param {string} iso
 * @returns {string}
 */
export function formatearDia(iso) {
  const [anio, mes, dia] = partes(iso);
  return FORMATO_LARGO.format(new Date(Date.UTC(anio, mes - 1, dia)));
}

/**
 * Describe un rango en texto ("Hoy", "Ayer" o "1 sept 2026 – 25 sept 2026").
 *
 * @param {string} desde
 * @param {string} hasta
 * @param {string} hoy
 * @returns {string}
 */
export function describirRango(desde, hasta, hoy) {
  if (desde === hasta) {
    if (hasta === hoy) return "Hoy";
    if (hasta === restarDias(hoy, 1)) return "Ayer";
    return formatearDia(hasta);
  }
  return `${formatearDia(desde)} – ${formatearDia(hasta)}`;
}

/** Maximo de dias que acepta el backend en un rango. */
export const MAXIMO_DIAS_RANGO = 366;

/**
 * Valida un rango personalizado.
 *
 * @param {string} desde
 * @param {string} hasta
 * @param {string} hoy
 * @returns {string | null} Mensaje de error, o null si el rango es valido.
 */
export function validarRango(desde, hasta, hoy) {
  if (!desde || !hasta) return "Elige la fecha inicial y la final.";
  if (desde > hasta) return "La fecha inicial no puede ser posterior a la final.";
  if (hasta > hoy) return "No se pueden consultar fechas futuras.";
  const dias = (Date.parse(hasta) - Date.parse(desde)) / 86400000 + 1;
  if (dias > MAXIMO_DIAS_RANGO) return `El rango no puede superar ${MAXIMO_DIAS_RANGO} días.`;
  return null;
}
