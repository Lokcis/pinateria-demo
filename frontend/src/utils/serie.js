/**
 * Agrupacion de la serie de ventas por dia para el grafico del Dashboard.
 *
 * Para que cada barra se entienda, el rango se agrupa segun su largo: hasta 31 dias
 * una barra es un dia; hasta 186 dias (6 meses), una semana (lunes a domingo); mas
 * que eso, un mes calendario. Los dias son textos "AAAA-MM-DD".
 */

/** Rango maximo (en dias) que se dibuja dia por dia. */
export const MAXIMO_DIAS_POR_DIA = 31;
/** Rango maximo (en dias) que se dibuja semana por semana. */
export const MAXIMO_DIAS_POR_SEMANA = 186;

const DIAS_SEMANA = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];
const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sept", "oct", "nov", "dic"];

/**
 * Separa "AAAA-MM-DD" en un `Date` UTC (evita que la zona del navegador mueva el dia).
 *
 * @param {string} iso
 * @returns {Date}
 */
function aFecha(iso) {
  const [anio, mes, dia] = iso.split("-").map(Number);
  return new Date(Date.UTC(anio, mes - 1, dia));
}

/**
 * @param {Date} fecha - Fecha UTC.
 * @returns {string} "AAAA-MM-DD".
 */
function aIso(fecha) {
  return fecha.toISOString().slice(0, 10);
}

/**
 * Texto corto de un dia (ej. "27 oct").
 *
 * @param {string} iso
 * @returns {string}
 */
function diaMes(iso) {
  const fecha = aFecha(iso);
  return `${fecha.getUTCDate()} ${MESES[fecha.getUTCMonth()]}`;
}

/**
 * Agrupa la serie diaria en columnas de dia, semana o mes segun el largo del rango.
 *
 * Las semanas y meses de los extremos pueden quedar incompletos (solo cuentan los dias
 * del rango); `dias` indica cuantos dias tiene realmente cada columna.
 *
 * @param {Array<{fecha: string, total: string, cantidad: number}>} serie - Un elemento por dia, en orden.
 * @returns {{granularidad: "dia" | "semana" | "mes", columnas: Array<{clave: string, etiqueta: string,
 *   descripcion: string, total: number, cantidad: number, dias: number}>}}
 */
export function agruparSerie(serie) {
  const granularidad = serie.length <= MAXIMO_DIAS_POR_DIA ? "dia" : serie.length <= MAXIMO_DIAS_POR_SEMANA ? "semana" : "mes";
  const grupos = new Map();

  for (const dia of serie) {
    const fecha = aFecha(dia.fecha);
    let clave;
    if (granularidad === "dia") {
      clave = dia.fecha;
    } else if (granularidad === "semana") {
      const inicioSemana = new Date(fecha);
      inicioSemana.setUTCDate(fecha.getUTCDate() - ((fecha.getUTCDay() + 6) % 7));
      clave = aIso(inicioSemana);
    } else {
      clave = dia.fecha.slice(0, 7);
    }
    const grupo = grupos.get(clave) || { clave, total: 0, cantidad: 0, dias: 0, primero: dia.fecha, ultimo: dia.fecha };
    grupo.total += Number(dia.total);
    grupo.cantidad += dia.cantidad;
    grupo.dias += 1;
    grupo.ultimo = dia.fecha;
    grupos.set(clave, grupo);
  }

  const columnas = [...grupos.values()].map((grupo) => {
    const primera = aFecha(grupo.primero);
    if (granularidad === "dia") {
      return {
        ...grupo,
        etiqueta: `${DIAS_SEMANA[primera.getUTCDay()]} ${primera.getUTCDate()}`,
        descripcion: `${DIAS_SEMANA[primera.getUTCDay()]} ${diaMes(grupo.primero)}`,
      };
    }
    if (granularidad === "semana") {
      return {
        ...grupo,
        etiqueta: diaMes(grupo.primero),
        descripcion: `Semana del ${diaMes(grupo.primero)} al ${diaMes(grupo.ultimo)}`,
      };
    }
    const nombreMes = `${MESES[primera.getUTCMonth()]} ${primera.getUTCFullYear()}`;
    return { ...grupo, etiqueta: nombreMes, descripcion: nombreMes };
  });

  return { granularidad, columnas };
}

/**
 * Calcula una escala "redonda" para el eje vertical (4 tramos), de modo que el maximo cabe.
 *
 * @param {number} maximo - Mayor valor a dibujar.
 * @returns {{tope: number, marcas: number[]}} `marcas` de menor a mayor, de 0 a `tope`.
 */
export function escalaEje(maximo) {
  if (!(maximo > 0)) {
    return { tope: 1, marcas: [0, 1] };
  }
  const aproximado = maximo / 4;
  const magnitud = 10 ** Math.floor(Math.log10(aproximado));
  const paso = [1, 2, 2.5, 5, 10].map((factor) => factor * magnitud).find((candidato) => candidato >= aproximado);
  return { tope: paso * 4, marcas: [0, 1, 2, 3, 4].map((n) => n * paso) };
}

/**
 * Elige que columnas llevan etiqueta en el eje horizontal (maximo `limite`, siempre la primera).
 *
 * @param {number} cantidad - Numero de columnas.
 * @param {number} [limite] - Maximo de etiquetas visibles.
 * @returns {Set<number>} Indices con etiqueta.
 */
export function indicesConEtiqueta(cantidad, limite = 6) {
  const salto = Math.max(1, Math.ceil(cantidad / limite));
  const indices = new Set();
  for (let i = 0; i < cantidad; i += salto) {
    indices.add(i);
  }
  return indices;
}
