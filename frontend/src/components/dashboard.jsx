import { useCallback, useEffect, useState } from "react";
import { obtenerAlertasStock, obtenerNotificaciones, obtenerResumenDashboard } from "../api/api-client";
import { useAuth } from "../context/auth-context";
import { ETIQUETA_METODO_PAGO, formatearHora, formatearMoneda } from "../utils/formato";
import { agruparSerie, escalaEje, indicesConEtiqueta } from "../utils/serie";
import { PRESETS, describirRango, hoyEnBogota, rangoDePreset, validarRango } from "../utils/rangos";
import { StockBajo } from "./stock-bajo";

/** Cada cuanto se refresca el tablero solo (HU-03: "con actualizacion automatica"). */
export const INTERVALO_ACTUALIZACION_MS = 30000;

/**
 * Tarjeta con una cifra del tablero.
 *
 * @param {{titulo: string, valor: string, detalle?: string}} props
 * @returns {JSX.Element}
 */
export function Cifra({ titulo, valor, detalle }) {
  return (
    <div className="rounded-2xl border border-tinta/10 bg-white p-4">
      <p className="text-sm font-semibold text-tinta/60">{titulo}</p>
      <p className="mt-1 font-display text-3xl font-extrabold tabular-nums">{valor}</p>
      {detalle && <p className="mt-1 text-xs text-tinta/50">{detalle}</p>}
    </div>
  );
}

/**
 * Tarjeta con un titulo y un contenido libre.
 *
 * @param {{titulo: string, children: React.ReactNode}} props
 * @returns {JSX.Element}
 */
export function Tarjeta({ titulo, children }) {
  return (
    <div className="rounded-2xl border border-tinta/10 bg-white p-4">
      <h3 className="text-sm font-semibold text-tinta/60">{titulo}</h3>
      <div className="mt-2">{children}</div>
    </div>
  );
}

/**
 * Selector de rango: botones rapidos y un rango personalizado con calendario.
 *
 * @param {{preset: string, personalizado: {desde: string, hasta: string}, alElegirPreset: (id: string) => void,
 *   alAplicarPersonalizado: (rango: {desde: string, hasta: string}) => void}} props
 * @returns {JSX.Element}
 */
export function SelectorRango({ preset, personalizado, alElegirPreset, alAplicarPersonalizado }) {
  const [abierto, setAbierto] = useState(preset === "personalizado");
  const [borrador, setBorrador] = useState(personalizado);
  const [errorRango, setErrorRango] = useState(null);
  const hoy = hoyEnBogota();

  /** Valida el borrador y, si es correcto, lo aplica como rango del tablero. */
  function aplicar() {
    const mensaje = validarRango(borrador.desde, borrador.hasta, hoy);
    setErrorRango(mensaje);
    if (!mensaje) {
      alAplicarPersonalizado(borrador);
    }
  }

  const clase = (activo) =>
    `shrink-0 rounded-xl px-3.5 py-2 text-sm font-bold transition ${
      activo ? "bg-white shadow-sm" : "text-tinta/60 hover:text-tinta"
    }`;

  return (
    <div className="mt-4">
      <div role="tablist" aria-label="Rango de fechas" className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
        <div className="inline-flex rounded-2xl bg-papel-osc p-1">
          {PRESETS.map((opcion) => (
            <button
              key={opcion.id}
              type="button"
              role="tab"
              aria-selected={preset === opcion.id}
              onClick={() => {
                setAbierto(false);
                alElegirPreset(opcion.id);
              }}
              className={clase(preset === opcion.id)}
            >
              {opcion.etiqueta}
            </button>
          ))}
          <button
            type="button"
            role="tab"
            aria-selected={preset === "personalizado"}
            aria-expanded={abierto}
            onClick={() => setAbierto((valor) => !valor)}
            className={clase(preset === "personalizado")}
          >
            Personalizado
          </button>
        </div>
      </div>

      {abierto && (
        <div className="mt-3 rounded-2xl border border-tinta/10 bg-white p-4">
          <div className="flex flex-wrap items-end gap-3">
            <label className="text-sm font-semibold text-tinta/70">
              Desde
              <input
                type="date"
                value={borrador.desde}
                max={hoy}
                onChange={(evento) => setBorrador({ ...borrador, desde: evento.target.value })}
                className="mt-1 block rounded-xl border border-tinta/20 px-3 py-2 text-base text-tinta"
              />
            </label>
            <label className="text-sm font-semibold text-tinta/70">
              Hasta
              <input
                type="date"
                value={borrador.hasta}
                max={hoy}
                onChange={(evento) => setBorrador({ ...borrador, hasta: evento.target.value })}
                className="mt-1 block rounded-xl border border-tinta/20 px-3 py-2 text-base text-tinta"
              />
            </label>
            <button
              type="button"
              onClick={aplicar}
              className="rounded-xl border-2 border-tinta px-4 py-2 text-sm font-bold transition hover:bg-papel"
            >
              Aplicar
            </button>
          </div>
          {errorRango && (
            <p role="alert" className="mt-2 text-sm font-medium text-fucsia-osc">
              {errorRango}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export const UNIDAD_BARRA = { dia: "un día", semana: "una semana (lunes a domingo)", mes: "un mes" };

export const FORMATO_COMPACTO = new Intl.NumberFormat("es-CO", {
  style: "currency",
  currency: "COP",
  notation: "compact",
  maximumFractionDigits: 1,
});

/**
 * Grafico de barras del total vendido, con ejes y detalle al tocar una barra.
 *
 * Cada barra es un dia, una semana o un mes segun el largo del rango (ver `agruparSerie`);
 * el texto sobre el grafico lo dice, el eje izquierdo muestra los montos y el inferior las
 * fechas. Al tocar (o enfocar) una barra se muestra su periodo, total y numero de ventas.
 *
 * @param {{serie: Array<{fecha: string, total: string, cantidad: number}>}} props
 * @returns {JSX.Element}
 */
function GraficoVentas({ serie }) {
  const [elegida, setElegida] = useState(null);
  const { granularidad, columnas } = agruparSerie(serie);
  const { tope, marcas } = escalaEje(Math.max(...columnas.map((columna) => columna.total)));
  const conEtiqueta = indicesConEtiqueta(columnas.length);
  const detalle = elegida === null ? null : columnas[elegida];

  return (
    <Tarjeta titulo="Ventas en el tiempo">
      <p className="text-sm text-tinta/70">
        Total vendido por <strong>{granularidad === "dia" ? "día" : granularidad}</strong>: cada barra es {UNIDAD_BARRA[granularidad]}.
      </p>

      <div className="mt-3 flex gap-2">
        <div className="relative h-40 w-14 shrink-0" aria-hidden="true">
          {marcas.map((marca) => (
            <span
              key={marca}
              className="absolute right-0 -translate-y-1/2 text-xs tabular-nums text-tinta/55"
              style={{ bottom: `${(marca / tope) * 100}%` }}
            >
              {marca === 0 ? "$ 0" : FORMATO_COMPACTO.format(marca)}
            </span>
          ))}
        </div>

        <div className="min-w-0 flex-1">
          <div className="relative h-40 border-b border-l border-tinta/25">
            {marcas.slice(1).map((marca) => (
              <div
                key={marca}
                aria-hidden="true"
                className="absolute inset-x-0 border-t border-dashed border-tinta/10"
                style={{ bottom: `${(marca / tope) * 100}%` }}
              />
            ))}
            <div className="absolute inset-0 flex items-end gap-px px-px" role="group" aria-label="Ventas por período">
              {columnas.map((columna, indice) => (
                <button
                  key={columna.clave}
                  type="button"
                  onClick={() => setElegida(indice === elegida ? null : indice)}
                  aria-pressed={indice === elegida}
                  aria-label={`${columna.descripcion}: ${formatearMoneda(columna.total)}, ${columna.cantidad} ${columna.cantidad === 1 ? "venta" : "ventas"}`}
                  title={`${columna.descripcion}: ${formatearMoneda(columna.total)}`}
                  className="flex h-full min-w-px flex-1 items-end"
                >
                  <span
                    className={`block w-full rounded-t-sm ${indice === elegida ? "bg-fucsia" : "bg-fucsia/55"}`}
                    style={{ height: `${columna.total > 0 ? Math.max((columna.total / tope) * 100, 2) : 0}%` }}
                  />
                </button>
              ))}
            </div>
          </div>
          <div className="flex h-5 gap-px px-px" aria-hidden="true">
            {columnas.map((columna, indice) => (
              <div key={columna.clave} className="relative min-w-px flex-1">
                {conEtiqueta.has(indice) && (
                  <span className="absolute left-0 top-1 whitespace-nowrap text-xs text-tinta/55">{columna.etiqueta}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      <p role="status" className="mt-2 rounded-xl bg-papel px-3 py-2 text-sm">
        {detalle ? (
          <>
            <strong>{detalle.descripcion}</strong>: {formatearMoneda(detalle.total)} en {detalle.cantidad}{" "}
            {detalle.cantidad === 1 ? "venta" : "ventas"}
          </>
        ) : (
          <span className="text-tinta/60">Toca una barra para ver su fecha, total y número de ventas.</span>
        )}
      </p>
    </Tarjeta>
  );
}

/**
 * Dashboard de solo lectura del propietario (HU-03): ventas y alertas de stock bajo.
 * El boton "Stock bajo" muestra el contador de notificaciones sin leer y abre la bandeja y la
 * lista de compras (Adendo v2, mejora B1: HU-10).
 *
 * Muestra hoy por defecto y permite elegir ayer, semana, mes, 3 meses, 6 meses, año o un rango
 * personalizado. Si el rango incluye hoy, se actualiza solo cada `INTERVALO_ACTUALIZACION_MS`
 * (sin recargar la pagina); conserva los ultimos datos si una actualizacion falla.
 *
 * @returns {JSX.Element}
 */
export function Dashboard() {
  const { token } = useAuth();
  const [resumen, setResumen] = useState(null);
  const [alertas, setAlertas] = useState([]);
  const [noLeidas, setNoLeidas] = useState(0);
  const [panelAbierto, setPanelAbierto] = useState(false);
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [preset, setPreset] = useState("hoy");
  const [personalizado, setPersonalizado] = useState(() => ({ desde: hoyEnBogota(), hasta: hoyEnBogota() }));

  const cargar = useCallback(async () => {
    setCargando(true);
    try {
      const rango = preset === "personalizado" ? personalizado : rangoDePreset(preset, hoyEnBogota());
      const [datosResumen, datosAlertas, datosBandeja] = await Promise.all([
        obtenerResumenDashboard(rango, token),
        obtenerAlertasStock(token),
        // El contador es secundario: si falla, se conserva el anterior y el tablero carga igual.
        obtenerNotificaciones(token, { soloNoLeidas: true, limite: 1 }).catch(() => null),
      ]);
      setResumen(datosResumen);
      setAlertas(datosAlertas);
      if (datosBandeja) {
        setNoLeidas(datosBandeja.no_leidas);
      }
      setError(null);
    } catch (errorCarga) {
      setError(errorCarga.message || "No se pudo cargar el Dashboard.");
    } finally {
      setCargando(false);
    }
  }, [token, preset, personalizado]);

  const incluyeHoy = preset !== "personalizado" ? preset !== "ayer" : personalizado.hasta >= hoyEnBogota();

  useEffect(() => {
    cargar();
    if (!incluyeHoy) {
      return undefined;
    }
    const temporizador = setInterval(() => {
      if (document.visibilityState !== "hidden") {
        cargar();
      }
    }, INTERVALO_ACTUALIZACION_MS);
    return () => clearInterval(temporizador);
  }, [cargar, incluyeHoy]);

  if (!resumen) {
    return error ? (
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
    ) : (
      <p className="text-tinta/60">Cargando el Dashboard…</p>
    );
  }

  const metodos = Object.entries(resumen.total_por_metodo);
  const { compras } = resumen;

  return (
    <section>
      <div className="flex items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-2xl font-extrabold">Resumen</h2>
          <p className="text-sm font-semibold text-tinta/70">
            {describirRango(resumen.desde, resumen.hasta, hoyEnBogota())}
          </p>
          <p className="text-xs text-tinta/55">
            Actualizado a las {formatearHora(resumen.generado_en)}
            {incluyeHoy ? " · se refresca solo" : ""}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setPanelAbierto((abierto) => !abierto)}
            aria-expanded={panelAbierto}
            aria-label={`Notificaciones y lista de compras: ${noLeidas} sin leer`}
            className="relative rounded-xl border border-tinta/20 px-3.5 py-2 text-sm font-semibold whitespace-nowrap transition hover:border-tinta hover:bg-papel"
          >
            <span aria-hidden="true">🔔</span> Stock bajo
            {noLeidas > 0 && (
              <span
                aria-hidden="true"
                className="absolute -top-2 -right-2 grid min-w-5 place-items-center rounded-full bg-fucsia px-1.5 text-xs font-bold text-white"
              >
                {noLeidas}
              </span>
            )}
          </button>
          <button
            type="button"
            onClick={cargar}
            disabled={cargando}
            className="rounded-xl border border-tinta/20 px-3.5 py-2 text-sm font-semibold transition hover:border-tinta hover:bg-papel disabled:opacity-50"
          >
            {cargando ? "Actualizando…" : "Actualizar"}
          </button>
        </div>
      </div>

      {panelAbierto && (
        <div className="mt-4">
          <StockBajo alCambiarNoLeidas={setNoLeidas} />
        </div>
      )}

      <SelectorRango
        preset={preset}
        personalizado={personalizado}
        alElegirPreset={setPreset}
        alAplicarPersonalizado={(rango) => {
          setPersonalizado(rango);
          setPreset("personalizado");
        }}
      />

      {error && (
        <p role="alert" className="mt-3 rounded-xl bg-fucsia/8 px-3 py-2 text-sm font-medium text-fucsia-osc">
          No se pudo actualizar: {error}. Se muestran los últimos datos.
        </p>
      )}

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <Cifra titulo="Total vendido" valor={formatearMoneda(resumen.total_vendido)} />
        <Cifra
          titulo="Ventas"
          valor={String(resumen.cantidad_ventas)}
          detalle={resumen.cantidad_ventas === 1 ? "transacción" : "transacciones"}
        />
        <Cifra titulo="Ticket promedio" valor={formatearMoneda(resumen.ticket_promedio)} />
      </div>

      {resumen.ventas_por_dia.length > 1 && (
        <div className="mt-3">
          <GraficoVentas key={`${resumen.desde}-${resumen.hasta}`} serie={resumen.ventas_por_dia} />
        </div>
      )}

      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <Tarjeta titulo="Por método de pago">
          {metodos.length === 0 ? (
            <p className="text-sm text-tinta/50">Sin ventas aún</p>
          ) : (
            <div className="space-y-1">
              {metodos.map(([metodo, monto]) => (
                <div key={metodo} className="flex justify-between text-sm">
                  <span>{ETIQUETA_METODO_PAGO[metodo] || metodo}</span>
                  <span className="font-semibold tabular-nums">{formatearMoneda(monto)}</span>
                </div>
              ))}
            </div>
          )}
        </Tarjeta>

        <Tarjeta titulo="Compras a proveedores">
          <div className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span>Recibidas</span>
              <span className="font-semibold tabular-nums">
                {compras.recibidas} · {formatearMoneda(compras.total_recibido)}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Pendientes</span>
              <span className="font-semibold tabular-nums">{compras.pendientes}</span>
            </div>
          </div>
        </Tarjeta>
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-2">
        <Tarjeta titulo="Más vendidos">
          {resumen.top_productos.length === 0 ? (
            <p className="text-sm text-tinta/50">Sin ventas aún</p>
          ) : (
            <ol className="space-y-1 text-sm">
              {resumen.top_productos.map((producto) => (
                <li key={producto.producto_id} className="flex justify-between gap-3">
                  <span>{producto.nombre}</span>
                  <span className="shrink-0 font-semibold tabular-nums">
                    {producto.unidades} {producto.unidades === 1 ? "unidad" : "unidades"}
                  </span>
                </li>
              ))}
            </ol>
          )}
        </Tarjeta>

        <Tarjeta titulo={`Alertas de stock bajo ahora (${alertas.length})`}>
          {alertas.length === 0 ? (
            <p className="text-sm text-tinta/50">Todo el inventario está por encima del mínimo.</p>
          ) : (
            <ul className="space-y-1 text-sm">
              {alertas.map((alerta) => (
                <li key={alerta.id} className="flex justify-between gap-3">
                  <span>
                    {alerta.nombre} <span className="text-xs text-tinta/50">· {alerta.categoria}</span>
                  </span>
                  <span
                    className={`shrink-0 font-semibold tabular-nums ${alerta.stock_actual === 0 ? "text-fucsia-osc" : "text-mandarina"}`}
                  >
                    {alerta.stock_actual} / mín. {alerta.stock_minimo}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Tarjeta>
      </div>
    </section>
  );
}
