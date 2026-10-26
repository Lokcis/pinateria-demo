import { formatearMoneda } from "../utils/formato";
import { aPesos } from "../utils/calculo-venta";

/**
 * Describe un descuento (ej. "10 %" o "$2.000").
 *
 * @param {{tipo: string, valor: string}} descuento
 * @returns {string}
 */
function describirDescuento(descuento) {
  return descuento.tipo === "porcentaje"
    ? `${Number(descuento.valor).toLocaleString("es-CO")} %`
    : formatearMoneda(descuento.valor);
}

/**
 * Descuento propio del cliente de la venta, o null si no tiene (Adendo v2, HU-06 y HU-07).
 *
 * @param {object | null} cliente
 * @returns {{tipo: string, valor: string} | null}
 */
function descuentoDelCliente(cliente) {
  return cliente?.descuento_tipo ? { tipo: cliente.descuento_tipo, valor: cliente.descuento_valor } : null;
}

/**
 * Bloque de descuento de la venta (Adendo v2, HU-06: RF-026 a RF-028, RF-042).
 *
 * La venta arranca sin descuento. Si el cliente asociado tiene descuento propio, el vendedor lo
 * puede aplicar con un boton; si esta activo el descuento general, tambien (son excluyentes: se
 * aplica uno solo, nunca los dos). Tambien puede escribir un descuento manual (porcentaje o
 * monto), que queda con origen manual. Al vendedor le muestra su limite.
 *
 * @param {{
 *   eleccion: {origen: string, tipo?: string | null, valor?: string},
 *   alCambiar: (eleccion: object) => void,
 *   configuracion: object | null,
 *   cliente?: object | null,
 *   descuentoCentavos: number,
 *   error: string | null,
 *   esAdministrador: boolean,
 *   deshabilitado: boolean,
 * }} props
 * @returns {JSX.Element}
 */
export function DescuentoVenta({
  eleccion,
  alCambiar,
  configuracion,
  cliente = null,
  descuentoCentavos,
  error,
  esAdministrador,
  deshabilitado,
}) {
  const general = configuracion?.general?.activo ? configuracion.general : null;
  const propio = descuentoDelCliente(cliente);
  const editando = eleccion.origen === "manual" && Boolean(eleccion.tipo);
  const limite = configuracion?.topes?.descripcion;

  return (
    <section aria-label="Descuento" className="rounded-xl border border-tinta/12 bg-white p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold text-tinta/65">Descuento</p>
        {descuentoCentavos > 0 && (
          <p className="font-semibold tabular-nums text-turquesa">−{formatearMoneda(aPesos(descuentoCentavos))}</p>
        )}
      </div>

      {eleccion.origen === "cliente" && propio && (
        <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
          <span>
            Descuento del cliente: <strong>{describirDescuento(propio)}</strong>
          </span>
          <button
            type="button"
            disabled={deshabilitado}
            onClick={() => alCambiar({ origen: "manual", tipo: propio.tipo, valor: String(Number(propio.valor)) })}
            className="rounded-lg border border-tinta/20 px-2.5 py-1 text-xs font-semibold transition hover:border-tinta"
          >
            Cambiar
          </button>
          <button
            type="button"
            disabled={deshabilitado}
            onClick={() => alCambiar({ origen: "ninguno" })}
            className="rounded-lg border border-tinta/20 px-2.5 py-1 text-xs font-semibold transition hover:border-tinta"
          >
            Quitar
          </button>
        </div>
      )}

      {eleccion.origen === "general" && general && (
        <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
          <span>
            Descuento general: <strong>{describirDescuento(general)}</strong>
          </span>
          <button
            type="button"
            disabled={deshabilitado}
            onClick={() => alCambiar({ origen: "manual", tipo: general.tipo, valor: String(Number(general.valor)) })}
            className="rounded-lg border border-tinta/20 px-2.5 py-1 text-xs font-semibold transition hover:border-tinta"
          >
            Cambiar
          </button>
          <button
            type="button"
            disabled={deshabilitado}
            onClick={() => alCambiar({ origen: "ninguno" })}
            className="rounded-lg border border-tinta/20 px-2.5 py-1 text-xs font-semibold transition hover:border-tinta"
          >
            Quitar
          </button>
        </div>
      )}

      {editando && (
        <div className="mt-2">
          <div className="flex items-center gap-2">
            <div role="radiogroup" aria-label="Tipo de descuento" className="inline-flex rounded-lg bg-papel-osc p-0.5">
              {[
                { valor: "porcentaje", etiqueta: "%" },
                { valor: "monto", etiqueta: "$" },
              ].map((opcion) => (
                <button
                  key={opcion.valor}
                  type="button"
                  role="radio"
                  aria-checked={eleccion.tipo === opcion.valor}
                  aria-label={opcion.valor === "porcentaje" ? "Porcentaje" : "Monto en pesos"}
                  disabled={deshabilitado}
                  onClick={() => alCambiar({ ...eleccion, tipo: opcion.valor })}
                  className={`w-9 rounded-md py-1 text-sm font-bold ${eleccion.tipo === opcion.valor ? "bg-white shadow-sm" : "text-tinta/60"}`}
                >
                  {opcion.etiqueta}
                </button>
              ))}
            </div>
            <input
              type="text"
              inputMode="decimal"
              aria-label={eleccion.tipo === "porcentaje" ? "Porcentaje de descuento" : "Descuento en pesos"}
              value={eleccion.valor ?? ""}
              disabled={deshabilitado}
              onChange={(evento) => alCambiar({ ...eleccion, valor: evento.target.value })}
              className="w-28 rounded-lg border border-tinta/20 px-2 py-1 text-right tabular-nums"
            />
            <button
              type="button"
              disabled={deshabilitado}
              onClick={() => alCambiar({ origen: "ninguno" })}
              className="rounded-lg border border-tinta/20 px-2.5 py-1 text-xs font-semibold transition hover:border-tinta"
            >
              Quitar
            </button>
          </div>
          {!esAdministrador && limite && limite !== "sin límite" && (
            <p className="mt-1 text-xs text-tinta/55">Tu límite: {limite}.</p>
          )}
        </div>
      )}

      {!editando && eleccion.origen !== "general" && eleccion.origen !== "cliente" && (
        <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
          <span className="text-tinta/55">Sin descuento</span>
          <button
            type="button"
            disabled={deshabilitado}
            onClick={() => alCambiar({ origen: "manual", tipo: "porcentaje", valor: "" })}
            className="rounded-lg border border-tinta/20 px-2.5 py-1 text-xs font-semibold transition hover:border-tinta"
          >
            Agregar descuento
          </button>
          {propio && (
            <button
              type="button"
              disabled={deshabilitado}
              onClick={() => alCambiar({ origen: "cliente" })}
              className="rounded-lg border border-turquesa/50 px-2.5 py-1 text-xs font-semibold text-turquesa transition hover:border-turquesa"
            >
              Aplicar descuento del cliente ({describirDescuento(propio)})
            </button>
          )}
          {general && (
            <button
              type="button"
              disabled={deshabilitado}
              onClick={() => alCambiar({ origen: "general" })}
              className="rounded-lg border border-tinta/20 px-2.5 py-1 text-xs font-semibold transition hover:border-tinta"
            >
              Aplicar descuento general ({describirDescuento(general)})
            </button>
          )}
        </div>
      )}

      {error && (
        <p role="alert" className="mt-2 text-xs font-medium text-fucsia-osc">
          {error}
        </p>
      )}
    </section>
  );
}
