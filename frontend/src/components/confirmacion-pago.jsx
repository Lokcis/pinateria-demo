import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { crearVenta, imprimirTicket, obtenerConfiguracionDescuentos, obtenerVendedores } from "../api/api-client";
import { useAuth } from "../context/auth-context";
import { useCart } from "../context/cart-context";
import { useSinConexion } from "../context/sin-conexion-context";
import { armarVentaPendiente } from "../offline/cola-ventas";
import { formatearMoneda } from "../utils/formato";
import { aCentavos, aPesos, calcularTotales, resolverDescuento, validarPagos } from "../utils/calculo-venta";
import { esErrorDeConexion, nuevoUuid } from "../utils/conexion";
import { construirTicket, construirTicketLocal } from "../utils/ticket";
import { Confeti } from "./confeti";
import { DescuentoVenta } from "./descuento-venta";
import { PagosVenta } from "./pagos-venta";
import { SelectorCliente } from "./selector-cliente";
import { SelectorVendedor } from "./selector-vendedor";

/** Un solo pago en efectivo por el total: el caso mas comun, listo para confirmar. */
const PAGOS_INICIALES = [{ id: 1, metodo: "efectivo", plataforma: null, monto: "", recibido: "", auto: true }];

/** Cada venta arranca sin descuento: el general lo aplica el vendedor solo a quien corresponda. */
const SIN_DESCUENTO = { origen: "ninguno" };

/** Cuanto se espera la respuesta del servidor al confirmar: pasado ese tiempo la venta se guarda sin conexion. */
const TIEMPO_MAXIMO_VENTA_MS = 12000;

/**
 * Renglon del desglose del total.
 *
 * @param {{etiqueta: string, valor: string}} props
 * @returns {JSX.Element}
 */
function Renglon({ etiqueta, valor }) {
  return (
    <div className="flex justify-between text-sm text-tinta/70">
      <span>{etiqueta}</span>
      <span className="tabular-nums">{valor}</span>
    </div>
  );
}

/**
 * Pantalla de confirmacion de pago (tarjeta #22; Adendo v2, HU-05 a HU-08).
 *
 * Calcula subtotal -> descuento -> redondeo a $50 -> total, recibe uno o varios pagos y no
 * deja confirmar hasta que cuadren con el total. Permite asociar un cliente (cuyo descuento propio
 * se sugiere) y elegir quien realiza la venta. El backend vuelve a calcular y validar todo.
 *
 * @returns {JSX.Element}
 */
export function ConfirmacionPago() {
  const { token, usuarioActual } = useAuth();
  const { items, total, vaciarCarrito } = useCart();
  const sinConexion = useSinConexion();
  const { enLinea, disponible } = sinConexion;
  const esAdministrador = usuarioActual?.rol === "administrador";
  const idSesion = String(usuarioActual?.sub ?? "");

  const [configuracion, setConfiguracion] = useState(null);
  const [errorConfiguracion, setErrorConfiguracion] = useState(null);
  const [eleccionDescuento, setEleccionDescuento] = useState(SIN_DESCUENTO);
  const [cliente, setCliente] = useState(null);
  const [vendedores, setVendedores] = useState([]);
  const [vendedorId, setVendedorId] = useState(idSesion);
  const [pagos, setPagos] = useState(PAGOS_INICIALES);
  const [procesando, setProcesando] = useState(false);
  const [error, setError] = useState(null);
  const [avisoImpresion, setAvisoImpresion] = useState(null);
  const [ultimaVentaId, setUltimaVentaId] = useState(null);
  const [ventaGuardada, setVentaGuardada] = useState(null);
  const [ticketPendiente, setTicketPendiente] = useState(null);
  const [reintentando, setReintentando] = useState(false);

  const { guardarEnCache, leerDeCache, reportarFalloDeConexion } = sinConexion;

  /**
   * Trae el descuento general y los topes vigentes. Sin conexion usa la ultima copia guardada en el equipo.
   *
   * @param {boolean} [reiniciarEleccion] - Si borra el descuento elegido (al abrir la pantalla o si el general cambio).
   */
  const cargarConfiguracion = useCallback(
    async (reiniciarEleccion = true) => {
      try {
        const datos = await obtenerConfiguracionDescuentos(token);
        setConfiguracion(datos);
        if (reiniciarEleccion) setEleccionDescuento(SIN_DESCUENTO);
        setErrorConfiguracion(null);
        guardarEnCache("descuentos", datos).catch(() => {});
      } catch (errorCarga) {
        if (esErrorDeConexion(errorCarga)) {
          reportarFalloDeConexion();
          const guardada = await leerDeCache("descuentos").catch(() => null);
          if (guardada) {
            setConfiguracion(guardada);
            setErrorConfiguracion(null);
            return;
          }
        }
        setErrorConfiguracion(errorCarga.message || "No se pudo cargar la configuración de descuentos.");
      }
    },
    [token, guardarEnCache, leerDeCache, reportarFalloDeConexion]
  );

  const primeraCarga = useRef(true);
  useEffect(() => {
    // Al abrir, parte limpio; al volver la conexion se refresca la configuracion sin tocar la venta en curso.
    cargarConfiguracion(primeraCarga.current);
    primeraCarga.current = false;
  }, [cargarConfiguracion, enLinea]);

  useEffect(() => {
    let activo = true;
    obtenerVendedores(token)
      .then((lista) => activo && setVendedores(lista))
      .catch(async (errorLista) => {
        // Sin la lista, la venta queda a nombre del usuario de la sesion; sin conexion se usa la guardada.
        if (!esErrorDeConexion(errorLista)) return;
        const guardada = await leerDeCache("vendedores").catch(() => null);
        if (activo && guardada) setVendedores(guardada);
      });
    return () => {
      activo = false;
    };
  }, [token, enLinea, leerDeCache]);

  const carritoVacio = items.length === 0;
  const cantidadUnidades = items.reduce((suma, item) => suma + item.cantidad, 0);

  const subtotalCentavos = aCentavos(total);
  const descuento = resolverDescuento(eleccionDescuento, configuracion, subtotalCentavos, esAdministrador, cliente);
  const totales = calcularTotales(subtotalCentavos, descuento.centavos);
  const ventaSinCobro = !carritoVacio && totales.total === 0;

  // Con un solo pago que el usuario no ha tocado, el monto sigue al total.
  const pagosVisibles = useMemo(
    () =>
      pagos.map((pago) =>
        pagos.length === 1 && pago.auto ? { ...pago, monto: String(aPesos(totales.total)) } : pago
      ),
    [pagos, totales.total]
  );
  const validacion = validarPagos(pagosVisibles, totales.total);
  const pagosCuadran =
    ventaSinCobro ||
    (validacion.errores.every((e) => !e) && validacion.faltaCentavos === 0 && validacion.sobraCentavos === 0);
  const puedeConfirmar = !carritoVacio && !procesando && !descuento.error && pagosCuadran;

  /**
   * Asocia (o quita) el cliente de la venta. El descuento propio del cliente se sugiere de una vez
   * (el vendedor puede cambiarlo o quitarlo) y reemplaza al general: nunca se suman. Sin cliente,
   * un descuento "de cliente" ya no tiene a quien pertenecer.
   *
   * @param {object | null} elegido
   */
  function cambiarCliente(elegido) {
    setCliente(elegido);
    setEleccionDescuento((actual) => {
      if (elegido?.descuento_tipo && (actual.origen === "ninguno" || actual.origen === "general")) {
        return { origen: "cliente" };
      }
      if (!elegido?.descuento_tipo && actual.origen === "cliente") {
        return SIN_DESCUENTO;
      }
      return actual;
    });
  }

  // Al volver la conexion, el aviso "se enviara sola" deja de ser cierto: la venta guardada ya salio (o aparece en la barra).
  useEffect(() => {
    if (enLinea) setVentaGuardada(null);
  }, [enLinea]);

  // Sin conexion no hay clientes: si se cae la red con un cliente elegido, se quita (y con el, su descuento propio).
  useEffect(() => {
    if (!enLinea && cliente) cambiarCliente(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enLinea]);

  /**
   * Guarda los pagos editados; un pago deja de seguir al total en cuanto se edita su monto o hay varios.
   *
   * @param {Array<object>} nuevos
   */
  function cambiarPagos(nuevos) {
    setPagos(
      nuevos.map((pago) => {
        const anterior = pagosVisibles.find((p) => p.id === pago.id);
        return { ...pago, auto: nuevos.length === 1 && Boolean(anterior?.auto) && pago.monto === anterior.monto };
      })
    );
  }

  /**
   * Envia un ticket al agente de impresion y actualiza el aviso segun el resultado.
   *
   * @param {object} ticket
   * @returns {Promise<void>}
   */
  async function intentarImprimir(ticket) {
    try {
      await imprimirTicket(ticket);
      setTicketPendiente(null);
      setAvisoImpresion(null);
    } catch (errorImpresion) {
      setTicketPendiente(ticket);
      const venta = ticket.venta_id ? `La venta #${ticket.venta_id} se registro correctamente` : `La venta ${ticket.referencia} se guardó sin conexión`;
      setAvisoImpresion(`${venta}, pero no se pudo imprimir el ticket: ${errorImpresion.message}`);
    }
  }

  /**
   * Deja la pantalla lista para la venta siguiente: sin productos, pagos, descuento ni cliente, y a nombre de la sesion.
   * Asi nadie hereda la venta de otro.
   */
  function reiniciarVenta() {
    vaciarCarrito();
    setPagos(PAGOS_INICIALES);
    setEleccionDescuento(SIN_DESCUENTO);
    setCliente(null);
    setVendedorId(idSesion);
  }

  /**
   * Guarda la venta en la cola local (Fase 9) porque no hay conexion con el servidor, e imprime su ticket con un
   * numero local ("SC-0003"). Se envia sola cuando vuelva la red; llevar `uuid_cliente` evita duplicarla.
   *
   * @param {string} uuid - Identificador de la venta.
   * @param {string | null} nombreVendedor
   * @returns {Promise<void>}
   */
  async function guardarSinConexion(uuid, nombreVendedor) {
    const entrada = armarVentaPendiente({
      uuid,
      numeroLocal: await sinConexion.siguienteNumero(),
      usuarioId: idSesion,
      creadaEn: new Date(),
      items,
      totales,
      validacionPagos: validacion,
      ventaSinCobro,
      descuentoPayload: descuento.payload,
      configuracion,
      vendedorId: vendedorId && vendedorId !== idSesion ? Number(vendedorId) : null,
      vendedorNombre: nombreVendedor,
      clienteId: cliente?.id ?? null,
    });
    await sinConexion.registrarVenta(entrada);
    setUltimaVentaId(null);
    setVentaGuardada(entrada.numeroLocal);
    reiniciarVenta();
    await intentarImprimir(construirTicketLocal(entrada));
  }

  /**
   * Confirma la venta: crea la venta en el backend y luego intenta imprimir el ticket.
   *
   * La impresion es best-effort: si falla, la venta YA quedo registrada
   * (no se revierte) y solo se avisa al vendedor para que reintente
   * manualmente o entregue el comprobante de otra forma.
   *
   * @returns {Promise<void>}
   */
  async function confirmarPago() {
    setProcesando(true);
    setError(null);
    setAvisoImpresion(null);
    setTicketPendiente(null);

    try {
      const uuid = nuevoUuid();
      const payload = {
        uuid_cliente: uuid,
        detalles: items.map((item) => ({
          producto_id: item.productoId,
          cantidad: item.cantidad,
        })),
        pagos: ventaSinCobro ? [] : validacion.payload,
        descuento: descuento.payload,
        ...(cliente && { cliente_id: cliente.id }),
        ...(vendedorId && vendedorId !== idSesion && { vendedor_id: Number(vendedorId) }),
      };
      const nombreVendedor = vendedores.find((v) => String(v.id) === (vendedorId || idSesion))?.nombre ?? null;

      if (!enLinea) {
        if (!disponible) {
          throw new Error("Sin conexión, y este navegador no puede guardar la venta. Espera a que vuelva internet.");
        }
        await guardarSinConexion(uuid, nombreVendedor);
        return;
      }

      let venta;
      try {
        venta = await crearVenta(payload, token, { tiempoMaximoMs: TIEMPO_MAXIMO_VENTA_MS });
      } catch (errorEnvio) {
        // Sin respuesta del servidor (red caida, tiempo agotado, tunel caido): la venta se guarda en el equipo y se
        // reenvia sola. Si el servidor si la habia recibido, el `uuid_cliente` evita que quede duplicada.
        if (!esErrorDeConexion(errorEnvio) || !disponible) throw errorEnvio;
        reportarFalloDeConexion();
        await guardarSinConexion(uuid, nombreVendedor);
        return;
      }
      setVentaGuardada(null);
      setUltimaVentaId(venta.id);
      reiniciarVenta();

      const nombresPorProducto = new Map(items.map((item) => [item.productoId, item.nombre]));
      await intentarImprimir(
        construirTicket(venta, (detalle) => nombresPorProducto.get(detalle.producto_id), nombreVendedor)
      );
    } catch (errorVenta) {
      setError(errorVenta.message || "No se pudo registrar la venta.");
      if (errorVenta.status === 409 && /descuento general/.test(errorVenta.message || "")) {
        // El administrador apago el descuento general mientras se hacia la venta.
        await cargarConfiguracion();
      }
    } finally {
      setProcesando(false);
    }
  }

  /**
   * Reintenta la impresion del ultimo ticket que fallo.
   *
   * @returns {Promise<void>}
   */
  async function reintentarImpresion() {
    setReintentando(true);
    await intentarImprimir(ticketPendiente);
    setReintentando(false);
  }

  return (
    <div className="confirmacion-pago">
      {errorConfiguracion && (
        <p className="mb-2 rounded-lg bg-sol/20 px-3 py-2 text-xs font-medium">
          No se pudo cargar la configuración de descuentos: {errorConfiguracion}
        </p>
      )}

      <div className={`space-y-3 ${carritoVacio || procesando ? "opacity-60" : ""}`}>
        <SelectorVendedor
          vendedores={vendedores}
          valor={vendedorId || idSesion}
          alCambiar={setVendedorId}
          deshabilitado={carritoVacio || procesando}
        />
        {enLinea ? (
          <SelectorCliente cliente={cliente} alCambiar={cambiarCliente} deshabilitado={carritoVacio || procesando} />
        ) : (
          <p className="rounded-xl border border-tinta/12 bg-white p-3 text-xs text-tinta/60">
            Sin conexión: la venta no lleva cliente (los datos de clientes no se guardan en este equipo).
          </p>
        )}
        <DescuentoVenta
          eleccion={eleccionDescuento}
          alCambiar={setEleccionDescuento}
          configuracion={configuracion}
          cliente={cliente}
          descuentoCentavos={descuento.centavos}
          error={carritoVacio ? null : descuento.error}
          esAdministrador={esAdministrador}
          deshabilitado={carritoVacio || procesando}
        />

        {ventaSinCobro ? (
          <p className="rounded-xl border border-tinta/12 bg-white p-3 text-sm text-tinta/70">
            El total es $0: la venta no lleva pagos.
          </p>
        ) : (
          <PagosVenta
            pagos={pagosVisibles}
            alCambiar={cambiarPagos}
            validacion={validacion}
            totalCentavos={totales.total}
            deshabilitado={carritoVacio || procesando}
          />
        )}
      </div>

      <div className="mt-5 border-t border-dashed border-tinta/25 pt-4">
        {!carritoVacio && (totales.descuento !== 0 || totales.ajuste !== 0) && (
          <div className="mb-2 space-y-0.5">
            <Renglon etiqueta="Subtotal" valor={formatearMoneda(aPesos(totales.subtotal))} />
            {totales.descuento !== 0 && (
              <Renglon etiqueta="Descuento" valor={`−${formatearMoneda(aPesos(totales.descuento))}`} />
            )}
            {totales.ajuste !== 0 && (
              <Renglon
                etiqueta="Ajuste por redondeo a $50"
                valor={`${totales.ajuste > 0 ? "+" : "−"}${formatearMoneda(aPesos(Math.abs(totales.ajuste)))}`}
              />
            )}
          </div>
        )}
        <div className="flex items-end justify-between">
          <div>
            <p className="text-sm font-semibold text-tinta/65">Total a pagar</p>
            <p className="text-xs text-tinta/50">
              {cantidadUnidades} {cantidadUnidades === 1 ? "unidad" : "unidades"}
            </p>
          </div>
          <p key={totales.total} className="total-a-pagar animate-pop font-display text-4xl font-extrabold tabular-nums">
            {formatearMoneda(carritoVacio ? 0 : aPesos(totales.total))}
          </p>
        </div>
      </div>

      <button
        type="button"
        onClick={confirmarPago}
        disabled={!puedeConfirmar}
        className="sombra-dura mt-4 w-full rounded-2xl border-2 border-tinta bg-fucsia px-4 py-4 font-display text-xl font-extrabold text-white transition enabled:hover:bg-fucsia-osc enabled:active:translate-x-1 enabled:active:translate-y-1 enabled:active:shadow-none disabled:cursor-not-allowed disabled:border-tinta/15 disabled:bg-tinta/10 disabled:text-tinta/40 disabled:shadow-none"
      >
        {procesando ? "Procesando…" : "Confirmar venta"}
      </button>

      <div aria-live="polite">
        {error && (
          <p className="mensaje-error mt-4 rounded-xl border border-fucsia/30 bg-fucsia/8 px-3 py-2.5 text-sm font-medium text-fucsia-osc">
            {error}
          </p>
        )}

        {ventaGuardada && !error && (
          <div
            key={ventaGuardada}
            className="mensaje-advertencia relative mt-4 animate-pop rounded-xl border border-sol/60 bg-sol/20 px-3 py-2.5 text-sm font-semibold"
          >
            Venta {ventaGuardada} guardada sin conexión. Se enviará sola cuando vuelva la red.
          </div>
        )}

        {ultimaVentaId && !error && !ventaGuardada && (
          <div
            key={ultimaVentaId}
            className="mensaje-exito relative mt-4 animate-pop rounded-xl border border-turquesa/30 bg-turquesa/10 px-3 py-2.5 text-sm font-semibold text-turquesa"
          >
            <Confeti disparo={ultimaVentaId} />
            Venta #{ultimaVentaId} registrada correctamente.
          </div>
        )}

        {avisoImpresion && (
          <div className="mensaje-advertencia mt-3 rounded-xl border border-sol/60 bg-sol/20 px-3 py-2.5 text-sm">
            <p className="font-medium">{avisoImpresion}</p>
            <button
              type="button"
              onClick={reintentarImpresion}
              disabled={reintentando}
              className="mt-2 rounded-lg border border-tinta bg-white px-3 py-1.5 text-sm font-semibold transition hover:bg-papel disabled:opacity-50"
            >
              {reintentando ? "Reintentando…" : "Reintentar impresión"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
