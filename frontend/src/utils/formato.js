const FORMATO_PESOS = new Intl.NumberFormat("es-CO", {
  style: "currency",
  currency: "COP",
  maximumFractionDigits: 0,
});

/**
 * Formatea un valor como pesos colombianos (ej. 25000 -> "$ 25.000").
 *
 * @param {number | string} valor - Monto numerico o su representacion en texto.
 * @returns {string}
 */
export function formatearMoneda(valor) {
  return FORMATO_PESOS.format(Number(valor));
}

/** Etiquetas legibles de los metodos de pago del backend. */
export const ETIQUETA_METODO_PAGO = {
  efectivo: "Efectivo",
  tarjeta: "Tarjeta",
  transferencia: "Transferencia",
};

/** Etiquetas legibles de las plataformas de transferencia (Adendo v2, RF-023). */
export const ETIQUETA_PLATAFORMA = {
  nequi: "Nequi",
  daviplata: "Daviplata",
};

/**
 * Describe un pago para mostrarlo (ej. "Transferencia (Nequi)").
 *
 * @param {{metodo_pago: string, plataforma?: string | null}} pago
 * @returns {string}
 */
export function describirPago(pago) {
  const metodo = ETIQUETA_METODO_PAGO[pago.metodo_pago] || pago.metodo_pago;
  return pago.plataforma ? `${metodo} (${ETIQUETA_PLATAFORMA[pago.plataforma] || pago.plataforma})` : metodo;
}

const FORMATO_HORA = new Intl.DateTimeFormat("es-CO", {
  hour: "2-digit",
  minute: "2-digit",
  hour12: true,
  timeZone: "America/Bogota",
});

/**
 * Formatea la hora de una fecha ISO en la zona horaria de la tienda (ej. "03:30 p. m.").
 *
 * @param {string} fechaIso - Fecha y hora en formato ISO 8601.
 * @returns {string}
 */
export function formatearHora(fechaIso) {
  return FORMATO_HORA.format(new Date(fechaIso));
}

const FORMATO_FECHA_HORA = new Intl.DateTimeFormat("es-CO", {
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  hour12: true,
  timeZone: "America/Bogota",
});

/**
 * Formatea fecha y hora de un ISO en la zona horaria de la tienda (ej. "25 sept, 03:30 p. m.").
 *
 * @param {string} fechaIso - Fecha y hora en formato ISO 8601.
 * @returns {string}
 */
export function formatearFechaHora(fechaIso) {
  return FORMATO_FECHA_HORA.format(new Date(fechaIso));
}

/** Etiquetas legibles de los tipos de ajuste manual de inventario (RF-009). */
export const ETIQUETA_TIPO_AJUSTE = {
  entrada: "Entrada",
  salida: "Salida",
  merma: "Merma",
  correccion: "Corrección",
};

/** Etiquetas legibles de los estados de una compra a proveedor (RF-010). */
export const ETIQUETA_ESTADO_COMPRA = {
  pendiente: "Pendiente",
  recibida: "Recibida",
  cancelada: "Cancelada",
};

/**
 * Redondea un monto al multiplo de 50 pesos mas cercano (la mitad sube), igual que el backend.
 *
 * @param {number | string} valor - Monto a redondear.
 * @returns {number}
 */
export function redondearA50(valor) {
  return Math.round(Number(valor) / 50) * 50;
}

/**
 * Indica si un monto ya es multiplo de 50 pesos (no necesita redondeo).
 *
 * @param {number | string} valor - Monto a revisar.
 * @returns {boolean}
 */
export function esMultiploDe50(valor) {
  return Math.round(Number(valor) * 100) % 5000 === 0;
}

/** Etiquetas del medio por el que un cliente autorizo el tratamiento de sus datos (HU-07). */
export const ETIQUETA_MEDIO_AUTORIZACION = {
  verbal: "Verbal",
  escrito: "Escrito",
  electronico: "Electrónico",
};

/** Etiquetas de los tipos de solicitud de un titular de datos (HU-07, RF-035). */
export const ETIQUETA_TIPO_SOLICITUD = {
  consulta: "Consulta",
  actualizacion: "Actualización",
  supresion: "Supresión",
  revocatoria: "Revocatoria",
};

/** Etiquetas de los estados de una solicitud de titular. */
export const ETIQUETA_ESTADO_SOLICITUD = {
  recibida: "Recibida",
  en_tramite: "En trámite",
  resuelta: "Resuelta",
  rechazada: "Rechazada",
};

/**
 * Formatea un dia "AAAA-MM-DD" sin desplazarlo por la zona horaria (ej. "26 oct 2026").
 *
 * @param {string} dia - Fecha calendario en formato ISO (sin hora).
 * @returns {string}
 */
export function formatearDia(dia) {
  const [anio, mes, diaDelMes] = dia.split("-").map(Number);
  return new Date(anio, mes - 1, diaDelMes).toLocaleDateString("es-CO", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}
