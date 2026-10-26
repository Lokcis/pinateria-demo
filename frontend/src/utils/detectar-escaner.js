/**
 * Logica pura de deteccion de "rafaga de escaner" (HU-01), separada del
 * componente React para poder probarla sin simular timing real del DOM.
 */

// Umbral de rafaga: si el promedio de milisegundos entre teclas es menor
// a esto, se asume que el input vino de un lector de codigo de barras.
// Valor de partida (Documento de Arquitectura Tecnica v1.1); ajustar
// cuando el lector fisico (tarjeta #25) este conectado y se pueda medir
// su patron real.
export const UMBRAL_RAFAGA_MS = 50;

// Cantidad minima de teclas para evaluar el patron; con menos no hay
// suficiente informacion de timing para decidir.
export const LONGITUD_MINIMA_PARA_RAFAGA = 3;

/**
 * Decide si una secuencia de intervalos entre teclas corresponde a un escaneo.
 *
 * @param {number[]} deltasMs - Milisegundos transcurridos entre cada tecla
 *   consecutiva (longitud = numero de caracteres - 1).
 * @param {number} [umbralMs] - Umbral de promedio, en ms, por debajo del
 *   cual se considera rafaga de escaner.
 * @param {number} [longitudMinima] - Cantidad minima de caracteres
 *   necesaria para evaluar el patron.
 * @returns {boolean} true si el patron corresponde a un escaneo.
 */
export function esPatronDeEscaner(
  deltasMs,
  umbralMs = UMBRAL_RAFAGA_MS,
  longitudMinima = LONGITUD_MINIMA_PARA_RAFAGA
) {
  if (deltasMs.length < longitudMinima - 1) {
    return false;
  }
  const promedio = deltasMs.reduce((suma, delta) => suma + delta, 0) / deltasMs.length;
  return promedio < umbralMs;
}
