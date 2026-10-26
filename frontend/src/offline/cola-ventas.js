/**
 * Cola local de ventas hechas sin conexion (Fase 9).
 *
 * Cada venta pendiente guarda exactamente el payload que se enviara a `POST /ventas` (con su
 * `uuid_cliente`, la hora real y los precios que vio el cliente) mas un resumen para mostrarla y
 * reimprimir su ticket sin pedirle nada al servidor.
 */

import { aCentavos, aPesos } from "../utils/calculo-venta";
import { borrar, guardar, incrementarContador, obtener, obtenerTodos } from "./almacen";

/** Estados de una venta de la cola. */
export const ESTADO_PENDIENTE = "pendiente";
export const ESTADO_CONFLICTO = "conflicto";

/**
 * Da formato de pesos con dos decimales (como llegan del backend).
 *
 * @param {number} centavos
 * @returns {string}
 */
function pesosTexto(centavos) {
  return aPesos(centavos).toFixed(2);
}

/**
 * Siguiente numero local de venta sin conexion ("SC-0001", "SC-0002"...), consecutivo por equipo.
 *
 * @returns {Promise<string>}
 */
export async function siguienteNumeroLocal() {
  const numero = await incrementarContador("consecutivo_local");
  return `SC-${String(numero).padStart(4, "0")}`;
}

/**
 * Arma la entrada de la cola para una venta confirmada sin conexion.
 *
 * El descuento general se envia con el tipo y el valor que vio el cliente (el servidor los respeta aunque
 * ya hayan cambiado); los demas orígenes se envian como estan.
 *
 * @param {{
 *   uuid: string, numeroLocal: string, usuarioId: string, creadaEn: Date,
 *   items: Array<{productoId: number, nombre: string, precioUnitario: number, cantidad: number}>,
 *   totales: {subtotal: number, descuento: number, ajuste: number, total: number},
 *   validacionPagos: {payload: Array<object>, vueltasCentavos: number[]},
 *   ventaSinCobro: boolean,
 *   descuentoPayload: object,
 *   configuracion: object | null,
 *   vendedorId?: number | null,
 *   vendedorNombre?: string | null,
 *   clienteId?: number | null,
 * }} datos - Lo calculado en la pantalla de pago; los totales y las vueltas estan en centavos.
 * @returns {object} La entrada lista para `encolarVenta`.
 */
export function armarVentaPendiente(datos) {
  const { uuid, numeroLocal, usuarioId, creadaEn, items, totales, validacionPagos, ventaSinCobro } = datos;
  const { descuentoPayload, configuracion, vendedorId = null, vendedorNombre = null, clienteId = null } = datos;

  let descuento = descuentoPayload;
  if (descuentoPayload.origen === "general" && configuracion?.general) {
    descuento = { origen: "general", tipo: configuracion.general.tipo, valor: String(configuracion.general.valor) };
  }
  const pagos = ventaSinCobro ? [] : validacionPagos.payload;

  const payload = {
    detalles: items.map((item) => ({
      producto_id: item.productoId,
      cantidad: item.cantidad,
      precio_unitario: String(item.precioUnitario),
    })),
    pagos,
    descuento,
    uuid_cliente: uuid,
    sin_conexion: { fecha: creadaEn.toISOString() },
    ...(vendedorId ? { vendedor_id: Number(vendedorId) } : {}),
    // Solo si la red se cayo justo al confirmar una venta con cliente: sin conexion desde el inicio no se elige cliente.
    ...(clienteId ? { cliente_id: Number(clienteId) } : {}),
  };

  const resumen = {
    subtotal: pesosTexto(totales.subtotal),
    descuento_tipo: descuento.tipo ?? null,
    descuento_valor: descuento.valor ?? null,
    descuento_monto: pesosTexto(totales.descuento),
    ajuste_redondeo: pesosTexto(totales.ajuste),
    total: pesosTexto(totales.total),
    vendedor: vendedorNombre,
    lineas: items.map((item) => ({
      producto_id: item.productoId,
      nombre: item.nombre,
      cantidad: item.cantidad,
      precio_unitario: pesosTexto(aCentavos(item.precioUnitario)),
      subtotal: pesosTexto(aCentavos(item.precioUnitario) * item.cantidad),
    })),
    pagos: pagos.map((pago, indice) => ({
      metodo_pago: pago.metodo_pago,
      plataforma: pago.plataforma,
      monto: pago.monto,
      monto_recibido: pago.monto_recibido,
      vueltas: pesosTexto(validacionPagos.vueltasCentavos[indice] ?? 0),
    })),
  };

  return {
    uuid,
    numeroLocal,
    usuarioId: String(usuarioId),
    creadaEn: creadaEn.toISOString(),
    estado: ESTADO_PENDIENTE,
    mensaje: null,
    intentos: 0,
    payload,
    resumen,
  };
}

/**
 * Guarda una venta en la cola.
 *
 * @param {object} entrada - Ver `armarVentaPendiente`.
 * @returns {Promise<void>}
 */
export async function encolarVenta(entrada) {
  await guardar("ventas", entrada);
}

/**
 * Lista las ventas de la cola, de la mas antigua a la mas reciente.
 *
 * @returns {Promise<Array<object>>}
 */
export async function listarVentas() {
  const ventas = await obtenerTodos("ventas");
  return ventas.sort((a, b) => a.creadaEn.localeCompare(b.creadaEn));
}

/**
 * Marca una venta como rechazada por el servidor, con el motivo, para que una persona la resuelva.
 *
 * @param {string} uuid
 * @param {string} mensaje - Lo que respondio el servidor.
 * @returns {Promise<void>}
 */
export async function marcarConflicto(uuid, mensaje) {
  const venta = await obtener("ventas", uuid);
  if (!venta) return;
  await guardar("ventas", { ...venta, estado: ESTADO_CONFLICTO, mensaje, intentos: venta.intentos + 1 });
}

/**
 * Vuelve a poner una venta en conflicto como pendiente, para reintentar su envio.
 *
 * @param {string} uuid
 * @returns {Promise<void>}
 */
export async function reabrirVenta(uuid) {
  const venta = await obtener("ventas", uuid);
  if (!venta) return;
  await guardar("ventas", { ...venta, estado: ESTADO_PENDIENTE, mensaje: null });
}

/**
 * Quita una venta de la cola (ya se envio, o la descarto una persona).
 *
 * @param {string} uuid
 * @returns {Promise<void>}
 */
export async function eliminarVenta(uuid) {
  await borrar("ventas", uuid);
}
