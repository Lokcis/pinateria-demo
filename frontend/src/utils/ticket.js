/**
 * Construye el payload del ticket para el agente de impresion a partir de una venta.
 *
 * Sirve tanto para la venta recien confirmada (nombres tomados del carrito)
 * como para reimprimir desde el historial (nombres que ya trae el backend).
 *
 * @param {{id: number, fecha: string, subtotal: string, descuento_tipo?: string | null,
 *   descuento_valor?: string | null, descuento_monto: string, ajuste_redondeo: string, total: string,
 *   pagos: Array<object>, detalles: Array<{producto_id: number, cantidad: number,
 *   precio_unitario: string|number, subtotal: string|number}>}} venta - Venta (`VentaOut` o
 *   `VentaHistorialOut`), con sus pagos y su descuento (Adendo v2).
 * @param {(detalle: object) => string | undefined} nombreDe - Resuelve el nombre del
 *   producto de una linea; si devuelve un valor vacio se usa "Producto #id".
 * @param {string | null} [vendedor] - Nombre de quien realizo la venta (HU-08), que el ticket imprime.
 * @returns {object} El payload esperado por `POST /imprimir` del agente.
 */
export function construirTicket(venta, nombreDe, vendedor = null) {
  return {
    venta_id: venta.id,
    fecha: venta.fecha,
    vendedor: vendedor || null,
    subtotal: venta.subtotal,
    descuento_tipo: venta.descuento_tipo ?? null,
    descuento_valor: venta.descuento_valor ?? null,
    descuento_monto: venta.descuento_monto,
    ajuste_redondeo: venta.ajuste_redondeo,
    total: venta.total,
    pagos: venta.pagos.map((pago) => ({
      metodo_pago: pago.metodo_pago,
      plataforma: pago.plataforma,
      monto: pago.monto,
      monto_recibido: pago.monto_recibido,
      vueltas: pago.vueltas,
    })),
    lineas: venta.detalles.map((detalle) => ({
      nombre_producto: nombreDe(detalle) || `Producto #${detalle.producto_id}`,
      cantidad: detalle.cantidad,
      precio_unitario: detalle.precio_unitario,
      subtotal: detalle.subtotal,
    })),
  };
}

/**
 * Construye el ticket de una venta hecha sin conexion, que todavia no tiene numero del servidor.
 *
 * Se imprime con su referencia local (ej. "SC-0003") en lugar de "Venta #id"; el agente de impresion
 * (con la actualizacion de la Fase 9) la acepta en el campo `referencia`.
 *
 * @param {{numeroLocal: string, creadaEn: string, resumen: object}} entrada - Entrada de la cola local.
 * @returns {object} El payload esperado por `POST /imprimir` del agente.
 */
export function construirTicketLocal(entrada) {
  const { resumen } = entrada;
  return {
    venta_id: null,
    referencia: entrada.numeroLocal,
    fecha: entrada.creadaEn,
    vendedor: resumen.vendedor || null,
    subtotal: resumen.subtotal,
    descuento_tipo: resumen.descuento_tipo ?? null,
    descuento_valor: resumen.descuento_valor ?? null,
    descuento_monto: resumen.descuento_monto,
    ajuste_redondeo: resumen.ajuste_redondeo,
    total: resumen.total,
    pagos: resumen.pagos,
    lineas: resumen.lineas.map((linea) => ({
      nombre_producto: linea.nombre || `Producto #${linea.producto_id}`,
      cantidad: linea.cantidad,
      precio_unitario: linea.precio_unitario,
      subtotal: linea.subtotal,
    })),
  };
}
