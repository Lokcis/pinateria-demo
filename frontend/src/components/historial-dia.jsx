import { useCallback, useEffect, useState } from "react";
import { imprimirTicket, obtenerHistorialHoy } from "../api/api-client";
import { useAuth } from "../context/auth-context";
import { ETIQUETA_METODO_PAGO, describirPago, formatearHora, formatearMoneda } from "../utils/formato";
import { construirTicket } from "../utils/ticket";

const COLOR_METODO = {
  efectivo: "bg-turquesa/12 text-turquesa",
  tarjeta: "bg-cielo/12 text-cielo",
  transferencia: "bg-mandarina/15 text-mandarina",
};

/**
 * Tarjeta de una cifra del resumen del dia.
 *
 * @param {{titulo: string, valor: string, detalle?: string}} props
 * @returns {JSX.Element}
 */
function CifraResumen({ titulo, valor, detalle }) {
  return (
    <div className="rounded-2xl border border-tinta/10 bg-white p-4">
      <p className="text-sm font-semibold text-tinta/60">{titulo}</p>
      <p className="mt-1 font-display text-3xl font-extrabold tabular-nums">{valor}</p>
      {detalle && <p className="mt-1 text-xs text-tinta/50">{detalle}</p>}
    </div>
  );
}

/**
 * Una venta del historial: resumen en una fila y detalle desplegable con reimpresion.
 *
 * @param {{venta: object}} props
 * @returns {JSX.Element}
 */
function FilaVenta({ venta }) {
  const [abierta, setAbierta] = useState(false);
  const [estadoImpresion, setEstadoImpresion] = useState(null);

  /**
   * Reenvia el ticket de esta venta al agente de impresion.
   *
   * @returns {Promise<void>}
   */
  async function reimprimir() {
    setEstadoImpresion({ tipo: "info", texto: "Imprimiendo…" });
    try {
      await imprimirTicket(construirTicket(venta, (detalle) => detalle.nombre_producto, venta.vendedor));
      setEstadoImpresion({ tipo: "ok", texto: "Ticket enviado a la impresora." });
    } catch (error) {
      setEstadoImpresion({ tipo: "error", texto: `No se pudo imprimir: ${error.message}` });
    }
  }

  return (
    <li className="animate-subir rounded-2xl border border-tinta/10 bg-white">
      <button
        type="button"
        onClick={() => setAbierta((valor) => !valor)}
        aria-expanded={abierta}
        className="flex w-full flex-wrap items-center gap-x-3 gap-y-1.5 p-4 text-left"
      >
        <span className="shrink-0 text-sm font-semibold tabular-nums text-tinta/65 sm:w-24">{formatearHora(venta.fecha)}</span>
        <span className="font-display text-lg font-extrabold">Venta #{venta.id}</span>
        {venta.sin_conexion && (
          <span
            title="Se hizo sin conexión y se envió después; la hora es la de la tienda"
            className="rounded-full bg-sol/30 px-2.5 py-0.5 text-xs font-semibold"
          >
            Sin conexión
          </span>
        )}
        <span className="flex flex-wrap gap-1">
          {venta.pagos.map((pago, indice) => (
            <span
              key={indice}
              className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${COLOR_METODO[pago.metodo_pago] || "bg-tinta/8"}`}
            >
              {describirPago(pago)}
            </span>
          ))}
          {venta.pagos.length === 0 && (
            <span className="rounded-full bg-tinta/8 px-2.5 py-0.5 text-xs font-semibold">Sin cobro</span>
          )}
        </span>
        <span className="ml-auto font-display text-lg font-extrabold tabular-nums">{formatearMoneda(venta.total)}</span>
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          className={`h-5 w-5 shrink-0 text-tinta/45 transition-transform ${abierta ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          strokeWidth="2.4"
          strokeLinecap="round"
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>

      {abierta && (
        <div className="border-t border-dashed border-tinta/20 px-4 pb-4 pt-3">
          {venta.detalles.map((detalle) => (
            <div key={detalle.producto_id} className="flex justify-between gap-3 py-1 text-sm">
              <span>
                {detalle.cantidad} × {detalle.nombre_producto}
              </span>
              <span className="font-semibold tabular-nums">{formatearMoneda(detalle.subtotal)}</span>
            </div>
          ))}
          {Number(venta.descuento_monto) > 0 && (
            <div className="flex justify-between gap-3 py-1 text-sm text-turquesa">
              <span>Descuento{venta.descuento_origen === "general" ? " general" : ""}</span>
              <span className="font-semibold tabular-nums">−{formatearMoneda(venta.descuento_monto)}</span>
            </div>
          )}
          {venta.pagos.length > 1 &&
            venta.pagos.map((pago, indice) => (
              <div key={indice} className="flex justify-between gap-3 py-0.5 text-xs text-tinta/60">
                <span>{describirPago(pago)}</span>
                <span className="tabular-nums">{formatearMoneda(pago.monto)}</span>
              </div>
            ))}
          {venta.pagos
            .filter((pago) => Number(pago.vueltas) > 0)
            .map((pago, indice) => (
              <p key={indice} className="text-xs text-tinta/60">
                Recibido {formatearMoneda(pago.monto_recibido)} · vueltas {formatearMoneda(pago.vueltas)}
              </p>
            ))}
          <p className="mt-2 text-xs text-tinta/55">
            Atendió: {venta.vendedor}
            {venta.registrada_por && ` · Registrada por: ${venta.registrada_por}`}
            {venta.cliente && ` · Cliente: ${venta.cliente}`}
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={reimprimir}
              className="rounded-lg border border-tinta bg-white px-3 py-1.5 text-sm font-semibold transition hover:bg-papel"
            >
              Reimprimir ticket
            </button>
            {estadoImpresion && (
              <span
                role="status"
                className={`text-sm font-medium ${estadoImpresion.tipo === "error" ? "text-fucsia-osc" : "text-tinta/70"}`}
              >
                {estadoImpresion.texto}
              </span>
            )}
          </div>
        </div>
      )}
    </li>
  );
}

/**
 * Historial de ventas del dia (RF-018): resumen, ventas del dia y reimpresion de tickets.
 *
 * @returns {JSX.Element}
 */
export function HistorialDia() {
  const { token } = useAuth();
  const [historial, setHistorial] = useState(null);
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(true);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      setHistorial(await obtenerHistorialHoy(token));
    } catch (errorCarga) {
      setError(errorCarga.message || "No se pudo cargar el historial.");
    } finally {
      setCargando(false);
    }
  }, [token]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  if (error) {
    return (
      <div role="alert" className="rounded-2xl border border-fucsia/30 bg-fucsia/8 p-5 text-fucsia-osc">
        <p className="font-medium">{error}</p>
        <button
          type="button"
          onClick={cargar}
          className="mt-3 rounded-lg border border-tinta bg-white px-3 py-1.5 text-sm font-semibold text-tinta"
        >
          Reintentar
        </button>
      </div>
    );
  }

  if (!historial) {
    return <p className="text-tinta/60">{cargando ? "Cargando ventas de hoy…" : ""}</p>;
  }

  const metodos = Object.entries(historial.total_por_metodo);

  return (
    <section>
      <div className="flex items-end justify-between gap-3">
        <h2 className="font-display text-2xl font-extrabold">Ventas de hoy</h2>
        <button
          type="button"
          onClick={cargar}
          disabled={cargando}
          className="rounded-xl border border-tinta/20 px-3.5 py-2 text-sm font-semibold transition hover:border-tinta hover:bg-papel disabled:opacity-50"
        >
          {cargando ? "Actualizando…" : "Actualizar"}
        </button>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <CifraResumen titulo="Total vendido" valor={formatearMoneda(historial.total_vendido)} />
        <CifraResumen
          titulo="Ventas"
          valor={String(historial.cantidad_ventas)}
          detalle={historial.cantidad_ventas === 1 ? "transacción" : "transacciones"}
        />
        <div className="rounded-2xl border border-tinta/10 bg-white p-4">
          <p className="text-sm font-semibold text-tinta/60">Por método de pago</p>
          {metodos.length === 0 ? (
            <p className="mt-2 text-sm text-tinta/50">Sin ventas aún</p>
          ) : (
            <div className="mt-2 space-y-1">
              {metodos.map(([metodo, monto]) => (
                <div key={metodo} className="flex justify-between text-sm">
                  <span>{ETIQUETA_METODO_PAGO[metodo] || metodo}</span>
                  <span className="font-semibold tabular-nums">{formatearMoneda(monto)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {historial.ventas.length === 0 ? (
        <p className="mt-6 rounded-2xl border border-dashed border-tinta/25 p-8 text-center text-tinta/60">
          Todavía no hay ventas registradas hoy.
        </p>
      ) : (
        <ul className="mt-5 space-y-2.5">
          {historial.ventas.map((venta) => (
            <FilaVenta key={venta.id} venta={venta} />
          ))}
        </ul>
      )}
    </section>
  );
}
