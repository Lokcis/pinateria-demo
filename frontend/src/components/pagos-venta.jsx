import { ETIQUETA_METODO_PAGO, ETIQUETA_PLATAFORMA, formatearMoneda } from "../utils/formato";
import { aPesos } from "../utils/calculo-venta";

const METODOS = Object.entries(ETIQUETA_METODO_PAGO).map(([valor, etiqueta]) => ({ valor, etiqueta }));
const PLATAFORMAS = Object.entries(ETIQUETA_PLATAFORMA).map(([valor, etiqueta]) => ({ valor, etiqueta }));

/**
 * Grupo de botones de una sola eleccion (en lugar de un <select> nativo).
 *
 * @param {{etiqueta: string, opciones: Array<{valor: string, etiqueta: string}>, valor: string | null,
 *   alElegir: (valor: string) => void, deshabilitado: boolean}} props
 * @returns {JSX.Element}
 */
function Opciones({ etiqueta, opciones, valor, alElegir, deshabilitado }) {
  return (
    <div role="radiogroup" aria-label={etiqueta} className="flex flex-wrap gap-1.5">
      {opciones.map((opcion) => (
        <button
          key={opcion.valor}
          type="button"
          role="radio"
          aria-checked={valor === opcion.valor}
          disabled={deshabilitado}
          onClick={() => alElegir(opcion.valor)}
          className={`rounded-lg border px-2.5 py-1.5 text-sm font-semibold transition ${
            valor === opcion.valor ? "border-tinta bg-tinta text-white" : "border-tinta/15 bg-white hover:border-tinta"
          }`}
        >
          {opcion.etiqueta}
        </button>
      ))}
    </div>
  );
}

/**
 * Pagos de la venta (Adendo v2, HU-05: RF-022 a RF-024).
 *
 * Uno o varios pagos con metodo y monto; en transferencia se elige Nequi o Daviplata y en
 * efectivo se escribe lo recibido para ver las vueltas (vacio = pago exacto). Muestra cuanto
 * falta o sobra para llegar al total.
 *
 * @param {{
 *   pagos: Array<{id: number, metodo: string, plataforma: string | null, monto: string, recibido: string}>,
 *   alCambiar: (pagos: Array<object>) => void,
 *   validacion: ReturnType<typeof import("../utils/calculo-venta").validarPagos>,
 *   totalCentavos: number,
 *   deshabilitado: boolean,
 * }} props
 * @returns {JSX.Element}
 */
export function PagosVenta({ pagos, alCambiar, validacion, totalCentavos, deshabilitado }) {
  /**
   * Cambia campos de un pago.
   *
   * @param {number} indice
   * @param {object} cambios
   */
  function cambiar(indice, cambios) {
    alCambiar(pagos.map((pago, i) => (i === indice ? { ...pago, ...cambios } : pago)));
  }

  /** Agrega un pago con lo que falta para llegar al total. */
  function agregar() {
    const siguienteId = Math.max(0, ...pagos.map((p) => p.id)) + 1;
    const falta = validacion.faltaCentavos > 0 ? String(aPesos(validacion.faltaCentavos)) : "";
    alCambiar([...pagos, { id: siguienteId, metodo: "transferencia", plataforma: null, monto: falta, recibido: "" }]);
  }

  return (
    <section aria-label="Pagos" className="space-y-2">
      {pagos.map((pago, indice) => {
        const etiqueta = pagos.length > 1 ? `Pago ${indice + 1}` : "Pago";
        const error = validacion.errores[indice];
        const vueltas = validacion.vueltasCentavos[indice];
        return (
          <fieldset key={pago.id} className="min-w-0 rounded-xl border border-tinta/12 bg-white p-3">
            <legend className="sr-only">{etiqueta}</legend>
            <div className="flex items-start justify-between gap-2">
              <Opciones
                etiqueta={`Método del ${etiqueta.toLowerCase()}`}
                opciones={METODOS}
                valor={pago.metodo}
                deshabilitado={deshabilitado}
                alElegir={(metodo) => cambiar(indice, { metodo, plataforma: metodo === "transferencia" ? pago.plataforma : null })}
              />
              {pagos.length > 1 && (
                <button
                  type="button"
                  disabled={deshabilitado}
                  onClick={() => alCambiar(pagos.filter((_, i) => i !== indice))}
                  aria-label={`Quitar ${etiqueta.toLowerCase()}`}
                  className="rounded-lg px-2 py-1 text-sm font-bold text-tinta/50 hover:text-fucsia-osc"
                >
                  ✕
                </button>
              )}
            </div>

            {pago.metodo === "transferencia" && (
              <div className="mt-2">
                <Opciones
                  etiqueta={`Plataforma del ${etiqueta.toLowerCase()}`}
                  opciones={PLATAFORMAS}
                  valor={pago.plataforma}
                  deshabilitado={deshabilitado}
                  alElegir={(plataforma) => cambiar(indice, { plataforma })}
                />
              </div>
            )}

            <div className="mt-2 flex flex-wrap items-end gap-3">
              <label className="text-xs font-semibold text-tinta/60">
                Monto
                <input
                  type="text"
                  inputMode="numeric"
                  value={pago.monto}
                  disabled={deshabilitado}
                  onChange={(evento) => cambiar(indice, { monto: evento.target.value })}
                  aria-label={`Monto del ${etiqueta.toLowerCase()}`}
                  className="mt-0.5 block w-32 rounded-lg border border-tinta/20 px-2 py-1.5 text-right text-base tabular-nums text-tinta"
                />
              </label>
              {pago.metodo === "efectivo" && (
                <>
                  <label className="text-xs font-semibold text-tinta/60">
                    Recibido
                    <input
                      type="text"
                      inputMode="numeric"
                      value={pago.recibido}
                      placeholder="Exacto"
                      disabled={deshabilitado}
                      onChange={(evento) => cambiar(indice, { recibido: evento.target.value })}
                      aria-label={`Recibido en el ${etiqueta.toLowerCase()}`}
                      className="mt-0.5 block w-32 rounded-lg border border-tinta/20 px-2 py-1.5 text-right text-base tabular-nums text-tinta"
                    />
                  </label>
                  {!error && (
                    <p className="pb-1.5 text-sm">
                      Vueltas: <strong className="tabular-nums">{formatearMoneda(aPesos(vueltas))}</strong>
                    </p>
                  )}
                </>
              )}
            </div>

            {error && (
              <p role="alert" className="mt-1.5 text-xs font-medium text-fucsia-osc">
                {error}
              </p>
            )}
          </fieldset>
        );
      })}

      <div className="flex flex-wrap items-center justify-between gap-2">
        <button
          type="button"
          disabled={deshabilitado || pagos.length >= 10}
          onClick={agregar}
          className="rounded-lg border border-dashed border-tinta/40 px-3 py-1.5 text-sm font-semibold transition hover:border-tinta"
        >
          + Agregar pago
        </button>
        <p role="status" className="text-sm font-semibold tabular-nums">
          {validacion.faltaCentavos > 0 && (
            <span className="text-fucsia-osc">Falta {formatearMoneda(aPesos(validacion.faltaCentavos))}</span>
          )}
          {validacion.sobraCentavos > 0 && (
            <span className="text-fucsia-osc">Sobra {formatearMoneda(aPesos(validacion.sobraCentavos))}</span>
          )}
          {validacion.faltaCentavos === 0 && validacion.sobraCentavos === 0 && totalCentavos > 0 && (
            <span className="text-turquesa">Pagos completos</span>
          )}
        </p>
      </div>
    </section>
  );
}
