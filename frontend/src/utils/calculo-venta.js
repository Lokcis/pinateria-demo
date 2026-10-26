/**
 * Calculo de la venta en el POS (Adendo v2, Fase A1): descuento, redondeo, topes y pagos.
 *
 * Replica `backend/app/services/calculo_venta.py` para mostrar el total y los errores antes de
 * confirmar; el backend vuelve a calcular todo y es quien decide. Se opera en centavos enteros
 * para no arrastrar errores de punto flotante.
 */

/**
 * Convierte pesos (numero o texto) a centavos enteros.
 *
 * @param {number | string} pesos
 * @returns {number}
 */
export function aCentavos(pesos) {
  return Math.round(Number(pesos) * 100);
}

/**
 * Convierte centavos a pesos.
 *
 * @param {number} centavos
 * @returns {number}
 */
export function aPesos(centavos) {
  return centavos / 100;
}

/**
 * Lee un monto escrito por el usuario (acepta "20.000", "20000" o "20000,5").
 *
 * @param {string} texto
 * @returns {number | null} El monto en pesos, o null si esta vacio o no es un numero.
 */
export function leerMonto(texto) {
  const limpio = String(texto ?? "")
    .trim()
    .replace(/\$/g, "")
    .replace(/\s/g, "");
  if (!limpio) {
    return null;
  }
  // En pesos colombianos el punto separa miles y la coma los decimales.
  const normalizado = limpio.replace(/\./g, "").replace(",", ".");
  const valor = Number(normalizado);
  return Number.isFinite(valor) ? valor : null;
}

/**
 * Lee un porcentaje escrito por el usuario (acepta "7,5" o "7.5").
 *
 * @param {string} texto
 * @returns {number | null} El porcentaje, o null si esta vacio o no es un numero.
 */
export function leerPorcentaje(texto) {
  const limpio = String(texto ?? "").trim().replace("%", "").replace(",", ".");
  if (!limpio) {
    return null;
  }
  const valor = Number(limpio);
  return Number.isFinite(valor) ? valor : null;
}

/**
 * Calcula el descuento en centavos sobre el subtotal (RF-027).
 *
 * @param {number} subtotalCentavos
 * @param {"porcentaje" | "monto"} tipo
 * @param {number | null} valor - Porcentaje (0 a 100) o pesos.
 * @returns {{centavos: number, error: string | null}}
 */
export function calcularDescuento(subtotalCentavos, tipo, valor) {
  if (valor === null || !(valor > 0)) {
    return { centavos: 0, error: "Escribe un valor mayor que cero." };
  }
  if (tipo === "porcentaje") {
    if (valor > 100) {
      return { centavos: 0, error: "Un porcentaje no puede superar el 100 %." };
    }
    const centesimas = Math.round(valor * 100);
    return { centavos: Math.round((subtotalCentavos * centesimas) / 10000), error: null };
  }
  if (!Number.isInteger(valor)) {
    return { centavos: 0, error: "Un descuento en pesos va sin centavos." };
  }
  const centavos = aCentavos(valor);
  if (centavos > subtotalCentavos) {
    return { centavos: 0, error: "El descuento no puede ser mayor que el subtotal." };
  }
  return { centavos, error: null };
}

/**
 * Aplica el descuento y despues redondea al multiplo de $50 mas cercano (la mitad sube).
 *
 * @param {number} subtotalCentavos
 * @param {number} descuentoCentavos
 * @returns {{subtotal: number, descuento: number, ajuste: number, total: number}} Todo en centavos.
 */
export function calcularTotales(subtotalCentavos, descuentoCentavos) {
  const neto = subtotalCentavos - descuentoCentavos;
  const total = Math.floor(neto / 5000 + 0.5) * 5000;
  return { subtotal: subtotalCentavos, descuento: descuentoCentavos, ajuste: total - neto, total };
}

/**
 * Indica si un descuento manual del vendedor supera los topes (RF-042). Ambos deben cumplirse.
 *
 * @param {number} subtotalCentavos
 * @param {number} descuentoCentavos
 * @param {{tope_porcentaje: string | null, tope_monto: string | null}} topes
 * @returns {boolean}
 */
export function superaTopes(subtotalCentavos, descuentoCentavos, topes) {
  if (descuentoCentavos <= 0 || !topes) {
    return false;
  }
  const porcentaje = subtotalCentavos > 0 ? (descuentoCentavos * 100) / subtotalCentavos : 0;
  const excedePorcentaje = topes.tope_porcentaje !== null && porcentaje > Number(topes.tope_porcentaje);
  const excedeMonto = topes.tope_monto !== null && descuentoCentavos > aCentavos(topes.tope_monto);
  return excedePorcentaje || excedeMonto;
}

/**
 * Resuelve el descuento elegido en la venta y su monto.
 *
 * @param {{origen: string, tipo?: string | null, valor?: string}} eleccion - Lo que eligio el usuario.
 * @param {object | null} configuracion - `GET /descuentos/configuracion`.
 * @param {number} subtotalCentavos
 * @param {boolean} esAdministrador - Los topes no aplican al administrador.
 * @param {{descuento_tipo: string | null, descuento_valor: string | null} | null} [cliente] - Cliente de la
 *   venta; su descuento propio se usa con el origen "cliente" (sin topes, como el general).
 * @returns {{centavos: number, error: string | null, payload: object}} Monto, error para mostrar y
 *   el `descuento` del payload de `POST /ventas`.
 */
export function resolverDescuento(eleccion, configuracion, subtotalCentavos, esAdministrador, cliente = null) {
  if (eleccion.origen === "cliente") {
    if (!cliente?.descuento_tipo) {
      return { centavos: 0, error: null, payload: { origen: "ninguno" } };
    }
    // Igual que el general: un descuento en pesos mayor que el subtotal se limita al subtotal.
    const centavos =
      cliente.descuento_tipo === "monto"
        ? Math.min(aCentavos(cliente.descuento_valor), subtotalCentavos)
        : calcularDescuento(subtotalCentavos, "porcentaje", Number(cliente.descuento_valor)).centavos;
    return { centavos, error: null, payload: { origen: "cliente" } };
  }

  if (eleccion.origen === "general") {
    const general = configuracion?.general;
    if (!general?.activo) {
      return { centavos: 0, error: null, payload: { origen: "ninguno" } };
    }
    // Un descuento general en pesos mayor que el subtotal se limita al subtotal (como el backend).
    const centavos =
      general.tipo === "monto"
        ? Math.min(aCentavos(general.valor), subtotalCentavos)
        : calcularDescuento(subtotalCentavos, "porcentaje", Number(general.valor)).centavos;
    return { centavos, error: null, payload: { origen: "general" } };
  }

  if (eleccion.origen === "manual") {
    if (!eleccion.tipo) {
      return { centavos: 0, error: null, payload: { origen: "manual" } };
    }
    const valor = eleccion.tipo === "porcentaje" ? leerPorcentaje(eleccion.valor) : leerMonto(eleccion.valor);
    const { centavos, error } = calcularDescuento(subtotalCentavos, eleccion.tipo, valor);
    const payload = { origen: "manual", tipo: eleccion.tipo, valor: valor === null ? null : String(valor) };
    if (error) {
      return { centavos: 0, error, payload };
    }
    if (!esAdministrador && superaTopes(subtotalCentavos, centavos, configuracion?.topes)) {
      return {
        centavos: 0,
        error: `Supera tu límite: ${configuracion.topes.descripcion}.`,
        payload,
      };
    }
    return { centavos, error: null, payload };
  }

  return { centavos: 0, error: null, payload: { origen: "ninguno" } };
}

/**
 * Valida los pagos escritos en el POS contra el total (RF-022 a RF-024).
 *
 * Un pago en efectivo sin monto recibido se toma como pago exacto (sin vueltas).
 *
 * @param {Array<{metodo: string, plataforma: string | null, monto: string, recibido: string}>} pagos
 * @param {number} totalCentavos
 * @returns {{
 *   errores: string[],
 *   sumaCentavos: number,
 *   faltaCentavos: number,
 *   sobraCentavos: number,
 *   vueltasCentavos: number[],
 *   payload: Array<object>,
 * }} Errores por pago (en el mismo orden; "" si el pago esta bien), suma, faltante, sobrante,
 *   vueltas de cada pago y la lista `pagos` del payload.
 */
export function validarPagos(pagos, totalCentavos) {
  const errores = [];
  const vueltasCentavos = [];
  const payload = [];
  let sumaCentavos = 0;

  for (const pago of pagos) {
    const monto = leerMonto(pago.monto);
    const recibidoEscrito = leerMonto(pago.recibido);
    let error = "";
    let vueltas = 0;

    if (monto === null || monto <= 0 || !Number.isInteger(monto)) {
      error = "Escribe un monto entero mayor que cero.";
    } else if (pago.metodo === "efectivo") {
      const recibido = recibidoEscrito ?? monto;
      if (monto % 50 !== 0) {
        error = "En efectivo el monto debe ser múltiplo de $50.";
      } else if (!Number.isInteger(recibido) || recibido % 50 !== 0) {
        error = "Lo recibido debe ser múltiplo de $50.";
      } else if (recibido < monto) {
        error = "Lo recibido no puede ser menor que el monto.";
      } else {
        vueltas = aCentavos(recibido - monto);
      }
    } else if (pago.metodo === "transferencia" && !pago.plataforma) {
      error = "Elige Nequi o Daviplata.";
    }

    if (monto !== null && monto > 0) {
      sumaCentavos += aCentavos(monto);
    }
    errores.push(error);
    vueltasCentavos.push(vueltas);
    payload.push({
      metodo_pago: pago.metodo,
      plataforma: pago.metodo === "transferencia" ? pago.plataforma : null,
      monto: monto === null ? null : String(monto),
      monto_recibido: pago.metodo === "efectivo" ? String(recibidoEscrito ?? monto) : null,
    });
  }

  return {
    errores,
    sumaCentavos,
    faltaCentavos: Math.max(0, totalCentavos - sumaCentavos),
    sobraCentavos: Math.max(0, sumaCentavos - totalCentavos),
    vueltasCentavos,
    payload,
  };
}
