/**
 * Envio de la cola de ventas sin conexion al servidor (Fase 9).
 *
 * Reglas:
 * - Se envia de la mas antigua a la mas reciente, una por una.
 * - Cada venta lleva su `uuid_cliente`: si el servidor ya la tenia (se perdio la respuesta antes), la devuelve
 *   sin duplicarla ni volver a descontar stock.
 * - Si no hay conexion (o el tunel esta caido) se detiene y se reintenta mas tarde; nada se pierde.
 * - Si la sesion vencio (401) se detiene y se pide iniciar sesion de nuevo; la cola se conserva.
 * - Si el servidor RECHAZA una venta (sin stock, topes, producto desactivado...) queda como "conflicto" con el
 *   motivo para que una persona la resuelva; no se reintenta sola ni bloquea las demas.
 */

import { crearVenta } from "../api/api-client";
import { esErrorDeConexion } from "../utils/conexion";
import { ESTADO_PENDIENTE, eliminarVenta, listarVentas, marcarConflicto } from "./cola-ventas";

/** Espera maxima por cada venta al sincronizar: con la red a medias, no se queda colgado. */
const TIEMPO_MAXIMO_ENVIO_MS = 20000;

/**
 * Envia una venta al servidor con tiempo maximo de espera.
 *
 * @param {object} payload
 * @param {string} token
 * @returns {Promise<object>}
 */
function enviarConTiempoMaximo(payload, token) {
  return crearVenta(payload, token, { tiempoMaximoMs: TIEMPO_MAXIMO_ENVIO_MS });
}

/**
 * Envia las ventas pendientes que le corresponden a quien tiene la sesion.
 *
 * @param {{
 *   token: string,
 *   usuarioId: string,
 *   esAdministrador?: boolean,
 *   enviar?: (payload: object, token: string) => Promise<object>,
 * }} opciones - Un vendedor envia solo las suyas (asi cada venta queda registrada por quien la hizo); el
 *   administrador envia las de todos. `enviar` existe para las pruebas.
 * @returns {Promise<{enviadas: number, conflictos: number, detenida: "conexion" | "sesion" | null}>}
 */
export async function sincronizarPendientes({
  token,
  usuarioId,
  esAdministrador = false,
  enviar = enviarConTiempoMaximo,
}) {
  const resultado = { enviadas: 0, conflictos: 0, detenida: null };
  const ventas = (await listarVentas()).filter(
    (venta) => venta.estado === ESTADO_PENDIENTE && (esAdministrador || venta.usuarioId === String(usuarioId))
  );

  for (const venta of ventas) {
    try {
      await enviar(venta.payload, token);
      await eliminarVenta(venta.uuid);
      resultado.enviadas += 1;
    } catch (error) {
      if (esErrorDeConexion(error)) {
        resultado.detenida = "conexion";
        break;
      }
      if (error?.status === 401) {
        resultado.detenida = "sesion";
        break;
      }
      await marcarConflicto(venta.uuid, error?.message || "El servidor rechazó la venta.");
      resultado.conflictos += 1;
    }
  }
  return resultado;
}
