import { useCallback, useEffect, useState } from "react";
import { obtenerGanancias } from "../api/api-client";
import { useAuth } from "../context/auth-context";
import { formatearMoneda } from "../utils/formato";
import { describirRango, hoyEnBogota, rangoDePreset } from "../utils/rangos";
import { agruparSerie, escalaEje, indicesConEtiqueta } from "../utils/serie";
import { Cifra, FORMATO_COMPACTO, SelectorRango, Tarjeta, UNIDAD_BARRA } from "./dashboard";

/** Productos que se muestran antes de "Ver todos". */
const PRODUCTOS_VISIBLES = 10;

/**
 * Formatea un porcentaje de margen (ej. "35,2 %") o "—" si no hay ingreso.
 *
 * @param {string | null} valor
 * @returns {string}
 */
function formatearPorcentaje(valor) {
  return valor === null ? "—" : `${Number(valor).toLocaleString("es-CO", { maximumFractionDigits: 1 })} %`;
}

/**
 * Ganancia neta y resultado de caja del rango (Adendo v3, Fase G3: RF-067).
 *
 * La neta es el margen bruto menos los gastos OPERATIVOS: las compras de mercancia ya estan en el costo de lo
 * vendido y no se restan otra vez. El resultado de caja es otra cosa: lo cobrado menos todo lo gastado, compras
 * incluidas (flujo de dinero, no una ganancia contable).
 *
 * @param {{neta: object}} props Ver `GananciaNetaOut`.
 * @returns {JSX.Element}
 */
function GananciaNeta({ neta }) {
  return (
    <section className="mt-4" aria-label="Ganancia neta">
      <h3 className="font-display text-lg font-extrabold">Ganancia neta</h3>
      {neta.incompleta && (
        <p role="note" className="mt-2 rounded-xl border border-sol/60 bg-sol/20 px-3 py-2 text-sm">
          <strong>Ganancia neta incompleta:</strong> faltan costos en algunas ventas, así que el margen bruto (y la neta) quedan por debajo
          de lo real.
        </p>
      )}
      <div className="mt-2 grid gap-3 sm:grid-cols-3">
        <Cifra
          titulo="Ganancia neta"
          valor={formatearMoneda(neta.ganancia_neta)}
          detalle={Number(neta.ganancia_neta) < 0 ? "Pérdida en el período" : "Margen bruto − gastos operativos"}
        />
        <Cifra titulo="Gastos operativos" valor={formatearMoneda(neta.gastos_operativos)} detalle="Sin la compra de mercancía" />
        <Cifra
          titulo="Resultado de caja"
          valor={formatearMoneda(neta.resultado_de_caja)}
          detalle="Cobrado − todos los gastos, compras incluidas"
        />
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <Cifra titulo="Cobrado en ventas" valor={formatearMoneda(neta.ventas_cobradas)} />
        <Cifra
          titulo="Gastos totales"
          valor={formatearMoneda(neta.gastos_totales)}
          detalle={`Incluye ${formatearMoneda(neta.compras_recibidas)} de compras recibidas`}
        />
      </div>
      <p className="mt-2 text-xs text-tinta/55">
        El resultado de caja es una cifra de flujo de dinero, útil para ver cuánto entró y cuánto salió; no es una ganancia contable.
      </p>
    </section>
  );
}

/**
 * Margen por periodo (RF-039). Cada barra es un dia, una semana o un mes segun el rango; el margen
 * positivo va hacia arriba (azul) y una perdida hacia abajo (fucsia) desde la linea de cero.
 *
 * @param {{serie: Array<{fecha: string, margen: string}>}} props
 * @returns {JSX.Element}
 */
function GraficoMargen({ serie }) {
  const [elegida, setElegida] = useState(null);
  const { granularidad, columnas } = agruparSerie(serie.map((dia) => ({ fecha: dia.fecha, total: dia.margen, cantidad: 0 })));
  // Un mismo paso para ganancias y perdidas, asi las marcas del eje quedan parejas a ambos lados del cero.
  const maximoPositivo = Math.max(0, ...columnas.map((c) => c.total));
  const maximoNegativo = Math.max(0, ...columnas.map((c) => -c.total));
  const paso = escalaEje(Math.max(maximoPositivo, maximoNegativo)).marcas[1];
  const pasosArriba = Math.max(1, Math.ceil(maximoPositivo / paso));
  const pasosAbajo = Math.ceil(maximoNegativo / paso);
  const rango = (pasosArriba + pasosAbajo) * paso;
  const cero = ((pasosAbajo * paso) / rango) * 100;
  const marcas = Array.from({ length: pasosArriba + pasosAbajo + 1 }, (_, i) => (i - pasosAbajo) * paso);
  const conEtiqueta = indicesConEtiqueta(columnas.length);
  const detalle = elegida === null ? null : columnas[elegida];

  /**
   * Posicion vertical (en % desde abajo) de un valor del eje.
   *
   * @param {number} valor
   * @returns {number}
   */
  const altura = (valor) => cero + (valor / rango) * 100;

  return (
    <Tarjeta titulo="Margen en el tiempo">
      <p className="text-sm text-tinta/70">
        Margen por <strong>{granularidad === "dia" ? "día" : granularidad}</strong>: cada barra es {UNIDAD_BARRA[granularidad]}.
      </p>

      <div className="mt-5 flex gap-2">
        <div className="relative h-40 w-14 shrink-0" aria-hidden="true">
          {marcas.map((marca) => (
            <span
              key={marca}
              className="absolute right-0 -translate-y-1/2 text-xs tabular-nums text-tinta/55"
              style={{ bottom: `${altura(marca)}%` }}
            >
              {marca === 0 ? "$ 0" : FORMATO_COMPACTO.format(marca)}
            </span>
          ))}
        </div>

        <div className="min-w-0 flex-1">
          <div className="relative h-40 border-l border-tinta/25">
            {marcas.map((marca) => (
              <div
                key={marca}
                aria-hidden="true"
                className={`absolute inset-x-0 border-t ${marca === 0 ? "border-tinta/35" : "border-dashed border-tinta/10"}`}
                style={{ bottom: `${altura(marca)}%` }}
              />
            ))}
            <div className="absolute inset-0 flex gap-[2px] px-px" role="group" aria-label="Margen por período">
              {columnas.map((columna, indice) => {
                const valor = columna.total;
                const alto = Math.abs(valor / rango) * 100;
                return (
                  <button
                    key={columna.clave}
                    type="button"
                    onClick={() => setElegida(indice === elegida ? null : indice)}
                    aria-pressed={indice === elegida}
                    aria-label={`${columna.descripcion}: margen ${formatearMoneda(valor)}`}
                    title={`${columna.descripcion}: ${formatearMoneda(valor)}`}
                    className="relative h-full min-w-px flex-1"
                  >
                    {valor !== 0 && (
                      <span
                        className={`absolute inset-x-0 block ${
                          valor > 0
                            ? `rounded-t ${indice === elegida ? "bg-cielo" : "bg-cielo/60"}`
                            : `rounded-b ${indice === elegida ? "bg-fucsia" : "bg-fucsia/60"}`
                        }`}
                        style={
                          valor > 0
                            ? { bottom: `${cero}%`, height: `${Math.max(alto, 2)}%` }
                            : { top: `${100 - cero}%`, height: `${Math.max(alto, 2)}%` }
                        }
                      />
                    )}
                  </button>
                );
              })}
            </div>
          </div>
          <div className="flex h-5 gap-[2px] px-px" aria-hidden="true">
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
            <strong>{detalle.descripcion}</strong>: margen {formatearMoneda(detalle.total)}
            {detalle.total < 0 ? " (pérdida)" : ""}
          </>
        ) : (
          <span className="text-tinta/60">Toca una barra para ver su fecha y su margen.</span>
        )}
      </p>
    </Tarjeta>
  );
}

/**
 * Margen por producto, de mayor a menor, en barras horizontales con el valor escrito (RF-038).
 * Sirve tambien como tabla: cada fila trae unidades, margen y porcentaje.
 *
 * @param {{productos: Array<object>}} props
 * @returns {JSX.Element}
 */
function MargenPorProducto({ productos }) {
  const [todos, setTodos] = useState(false);
  const visibles = todos ? productos : productos.slice(0, PRODUCTOS_VISIBLES);
  const maximo = Math.max(1, ...productos.map((p) => Math.abs(Number(p.margen))));

  return (
    <Tarjeta titulo="Margen por producto">
      {productos.length === 0 ? (
        <p className="text-sm text-tinta/50">No hay ventas con costo en este rango.</p>
      ) : (
        <>
          <ul className="space-y-2">
            {visibles.map((producto) => {
              const margen = Number(producto.margen);
              return (
                <li key={producto.producto_id} className="text-sm">
                  <div className="flex justify-between gap-3">
                    <span className="truncate">
                      {producto.nombre}{" "}
                      <span className="text-xs text-tinta/50">
                        · {producto.unidades} {producto.unidades === 1 ? "unidad" : "unidades"}
                      </span>
                    </span>
                    <span className="shrink-0 font-semibold tabular-nums">
                      {formatearMoneda(margen)}{" "}
                      <span className="text-xs font-normal text-tinta/55">({formatearPorcentaje(producto.margen_porcentaje)})</span>
                    </span>
                  </div>
                  <div className="mt-1 h-2 rounded bg-papel-osc" aria-hidden="true">
                    <div
                      className={`h-2 rounded ${margen >= 0 ? "bg-cielo" : "bg-fucsia"}`}
                      style={{ width: `${Math.max((Math.abs(margen) / maximo) * 100, 1)}%` }}
                    />
                  </div>
                </li>
              );
            })}
          </ul>
          {productos.length > PRODUCTOS_VISIBLES && (
            <button
              type="button"
              onClick={() => setTodos((valor) => !valor)}
              className="mt-3 rounded-lg border border-tinta/20 px-3 py-1.5 text-xs font-semibold hover:border-tinta"
            >
              {todos ? "Ver menos" : `Ver todos (${productos.length})`}
            </button>
          )}
        </>
      )}
    </Tarjeta>
  );
}

/**
 * Dashboard de ganancias (Adendo v2, Fase A3: HU-09, RF-038 y RF-039). Administrador y propietario.
 *
 * Muestra el margen bruto del rango elegido (ingreso neto menos costo, con los descuentos
 * repartidos), por periodo y por producto, y la ganancia neta con el resultado de caja (Adendo v3, Fase G3).
 * Las ventas sin costo se informan aparte.
 *
 * @returns {JSX.Element}
 */
export function Ganancias() {
  const { token } = useAuth();
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [preset, setPreset] = useState("mes");
  const [personalizado, setPersonalizado] = useState(() => ({ desde: hoyEnBogota(), hasta: hoyEnBogota() }));

  const cargar = useCallback(async () => {
    setCargando(true);
    try {
      const rango = preset === "personalizado" ? personalizado : rangoDePreset(preset, hoyEnBogota());
      setDatos(await obtenerGanancias(rango, token));
      setError(null);
    } catch (falla) {
      setError(falla.message || "No se pudieron cargar las ganancias.");
    } finally {
      setCargando(false);
    }
  }, [token, preset, personalizado]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  return (
    <section>
      <div className="flex items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-2xl font-extrabold">Ganancias</h2>
          {datos && (
            <p className="text-sm font-semibold text-tinta/70">{describirRango(datos.desde, datos.hasta, hoyEnBogota())}</p>
          )}
        </div>
        <button
          type="button"
          onClick={cargar}
          disabled={cargando}
          className="rounded-xl border border-tinta/20 px-3.5 py-2 text-sm font-semibold transition hover:border-tinta hover:bg-papel disabled:opacity-50"
        >
          {cargando ? "Actualizando…" : "Actualizar"}
        </button>
      </div>

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
          {error}
        </p>
      )}

      {!datos ? (
        !error && <p className="mt-4 text-tinta/60">Calculando ganancias…</p>
      ) : (
        <>
          {datos.sin_costo.lineas > 0 && (
            <p className="mt-4 rounded-xl border border-sol/60 bg-sol/20 px-3 py-2 text-sm">
              <strong>{datos.sin_costo.lineas}</strong> {datos.sin_costo.lineas === 1 ? "línea vendida" : "líneas vendidas"} sin
              costo ({formatearMoneda(datos.sin_costo.ingreso_neto)}) no {datos.sin_costo.lineas === 1 ? "entra" : "entran"} en
              el margen. Carga los costos en la tabla de costos.
            </p>
          )}

          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Cifra
              titulo="Margen bruto"
              valor={formatearMoneda(datos.resumen.margen)}
              detalle={Number(datos.resumen.margen) < 0 ? "Pérdida en el período" : undefined}
            />
            <Cifra titulo="Margen sobre lo vendido" valor={formatearPorcentaje(datos.resumen.margen_porcentaje)} />
            <Cifra titulo="Vendido (con descuentos)" valor={formatearMoneda(datos.resumen.ingreso_neto)} detalle="Solo ventas con costo" />
            <Cifra titulo="Costo" valor={formatearMoneda(datos.resumen.costo_total)} />
          </div>

          {datos.neta && <GananciaNeta neta={datos.neta} />}

          {datos.por_dia.length > 1 && (
            <div className="mt-3">
              <GraficoMargen key={`${datos.desde}-${datos.hasta}`} serie={datos.por_dia} />
            </div>
          )}

          <div className="mt-3">
            <MargenPorProducto productos={datos.por_producto} />
          </div>
        </>
      )}
    </section>
  );
}
