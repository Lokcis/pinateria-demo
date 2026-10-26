import { useCallback, useEffect, useState } from "react";
import { completarCostosVentas, guardarCosto, obtenerCostos } from "../api/api-client";
import { useAuth } from "../context/auth-context";
import { formatearMoneda } from "../utils/formato";
import { useConfirmar } from "./dialogo-confirmacion";

const ETIQUETA_TIPO = { unidad: "Unidad", paquete: "Paquete", ancheta: "Ancheta" };

/**
 * Lee un costo escrito por el usuario ("1.500", "1500" o "1500,50").
 *
 * @param {string} texto
 * @returns {number | null | undefined} El costo, null si esta vacio (sin costo) o undefined si no es valido.
 */
function leerCosto(texto) {
  const limpio = String(texto ?? "").trim().replace(/\$/g, "").replace(/\s/g, "");
  if (!limpio) {
    return null;
  }
  const normalizado = limpio.replace(/\./g, "").replace(",", ".");
  // Pesos con hasta dos decimales; nada de negativos ni otros caracteres.
  if (!/^\d+(\.\d{1,2})?$/.test(normalizado)) {
    return undefined;
  }
  return Number(normalizado);
}

/**
 * Texto editable de un costo, con coma decimal (ej. "1500.50" -> "1500,5"; null -> "").
 *
 * @param {string | null} costo
 * @returns {string}
 */
function costoATexto(costo) {
  return costo === null ? "" : String(Number(costo)).replace(".", ",");
}

/**
 * Margen por unidad con el costo actual, en porcentaje del precio (ej. "42 %").
 *
 * @param {string} precio
 * @param {string | null} costo
 * @returns {string}
 */
function margenUnitario(precio, costo) {
  if (costo === null || !(Number(precio) > 0)) {
    return "—";
  }
  const porcentaje = ((Number(precio) - Number(costo)) * 100) / Number(precio);
  return `${porcentaje.toLocaleString("es-CO", { maximumFractionDigits: 0 })} %`;
}

/**
 * Fila editable de la tabla de costos.
 *
 * @param {{producto: object, editable: boolean, alGuardar: (fila: object) => void}} props
 * @returns {JSX.Element}
 */
function FilaCosto({ producto, editable, alGuardar }) {
  const { token } = useAuth();
  const actual = costoATexto(producto.costo_unitario);
  const [texto, setTexto] = useState(actual);
  const [estado, setEstado] = useState(null);
  const cambiado = texto.trim() !== actual;

  /**
   * Guarda el costo escrito (o el sugerido, si se pasa).
   *
   * @param {string} [valorTexto]
   * @returns {Promise<void>}
   */
  async function guardar(valorTexto = texto) {
    const valor = leerCosto(valorTexto);
    if (valor === undefined) {
      setEstado({ tipo: "error", texto: "Costo no válido." });
      return;
    }
    setEstado({ tipo: "info", texto: "Guardando…" });
    try {
      const fila = await guardarCosto(producto.producto_id, valor === null ? null : String(valor), token);
      setTexto(costoATexto(fila.costo_unitario));
      setEstado(null);
      alGuardar(fila);
    } catch (falla) {
      setEstado({ tipo: "error", texto: falla.message || "No se pudo guardar." });
    }
  }

  return (
    <tr className="align-top">
      <td className="py-2 pr-3">
        <p className="font-medium">{producto.nombre}</p>
        <p className="text-xs text-tinta/55">
          {producto.categoria} · {ETIQUETA_TIPO[producto.tipo] || producto.tipo}
        </p>
      </td>
      <td className="py-2 pr-3 text-right tabular-nums">{formatearMoneda(producto.precio_venta)}</td>
      <td className="py-2 pr-3">
        {editable ? (
          <form
            onSubmit={(evento) => {
              evento.preventDefault();
              guardar();
            }}
            className="flex items-center justify-end gap-1.5"
          >
            <input
              value={texto}
              onChange={(evento) => setTexto(evento.target.value)}
              inputMode="decimal"
              placeholder="Sin costo"
              aria-label={`Costo de ${producto.nombre}`}
              className="w-28 rounded-lg border border-tinta/20 px-2 py-1 text-right tabular-nums"
            />
            {cambiado && (
              <button type="submit" className="rounded-lg bg-fucsia px-2.5 py-1 text-xs font-bold text-white">
                Guardar
              </button>
            )}
          </form>
        ) : (
          <p className="text-right tabular-nums">
            {producto.costo_unitario === null ? <span className="text-tinta/50">Sin costo</span> : formatearMoneda(producto.costo_unitario)}
          </p>
        )}
        {estado && (
          <p
            role={estado.tipo === "error" ? "alert" : "status"}
            className={`mt-1 text-right text-xs ${estado.tipo === "error" ? "text-fucsia-osc" : "text-tinta/60"}`}
          >
            {estado.texto}
          </p>
        )}
      </td>
      <td className="py-2 pr-3 text-right text-sm">
        {producto.costo_sugerido !== null ? (
          <span className="inline-flex items-center gap-1.5">
            <span className="tabular-nums">{formatearMoneda(producto.costo_sugerido)}</span>
            {editable && producto.costo_unitario !== producto.costo_sugerido && (
              <button
                type="button"
                onClick={() => guardar(costoATexto(producto.costo_sugerido))}
                aria-label={`Usar el costo sugerido para ${producto.nombre}`}
                className="rounded-lg border border-tinta/20 px-2 py-0.5 text-xs font-semibold hover:border-tinta"
              >
                Usar
              </button>
            )}
          </span>
        ) : producto.sugerido_incompleto ? (
          <span className="text-xs text-tinta/55">Faltan costos de componentes</span>
        ) : (
          <span className="text-tinta/35">—</span>
        )}
      </td>
      <td className="py-2 text-right tabular-nums">{margenUnitario(producto.precio_venta, producto.costo_unitario)}</td>
    </tr>
  );
}

/**
 * Tabla de costos (Adendo v2, Fase A3: RF-037). El administrador la edita; el propietario solo la ve.
 *
 * Cada producto tiene su costo editable en la fila; los paquetes y anchetas muestran un costo
 * sugerido (suma de sus componentes). El administrador puede completar, con el costo actual, las
 * lineas de ventas pasadas que quedaron sin costo.
 *
 * @param {{editable: boolean}} props
 * @returns {JSX.Element}
 */
export function Costos({ editable }) {
  const { token } = useAuth();
  const { confirmar, dialogo } = useConfirmar();
  const [tabla, setTabla] = useState(null);
  const [soloSinCosto, setSoloSinCosto] = useState(false);
  const [error, setError] = useState(null);
  const [aviso, setAviso] = useState(null);

  const cargar = useCallback(async () => {
    try {
      setTabla(await obtenerCostos(token, { soloSinCosto }));
      setError(null);
    } catch (falla) {
      setError(falla.message || "No se pudieron cargar los costos.");
    }
  }, [token, soloSinCosto]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  /** Completa los costos de las ventas pasadas, tras confirmar. */
  async function completar() {
    const acepta = await confirmar({
      titulo: "¿Completar los costos de ventas anteriores?",
      mensaje:
        `Se llenarán ${tabla.lineas_por_completar} líneas vendidas sin costo con el costo actual de su producto. ` +
        "Es una aproximación: las líneas que ya tienen costo no se tocan. No se puede deshacer.",
      textoConfirmar: "Completar",
    });
    if (!acepta) return;
    try {
      const { lineas_completadas: lineas } = await completarCostosVentas(token);
      setAviso(`Se completaron ${lineas} ${lineas === 1 ? "línea" : "líneas"}.`);
      await cargar();
    } catch (falla) {
      setError(falla.message || "No se pudieron completar los costos.");
    }
  }

  return (
    <section className="space-y-3">
      {dialogo}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="font-display text-lg font-extrabold">Costos de los productos</h3>
          <p className="text-sm text-tinta/60">
            {editable
              ? "Escribe el costo de compra de cada producto. Cada venta guarda el costo del momento."
              : "Costo de compra de cada producto. Solo el administrador lo modifica."}
          </p>
        </div>
        <label className="flex items-center gap-2 text-sm font-medium">
          <input type="checkbox" checked={soloSinCosto} onChange={(e) => setSoloSinCosto(e.target.checked)} className="h-4 w-4" />
          Solo sin costo
        </label>
      </div>

      {error && (
        <p role="alert" className="rounded-xl bg-fucsia/8 px-3 py-2 text-sm font-medium text-fucsia-osc">
          {error}
        </p>
      )}
      {aviso && (
        <p role="status" className="rounded-xl bg-turquesa/10 px-3 py-2 text-sm font-medium text-turquesa">
          {aviso}
        </p>
      )}

      {editable && tabla?.lineas_por_completar > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-sol/60 bg-sol/20 px-3 py-2 text-sm">
          <span>
            Hay <strong>{tabla.lineas_por_completar}</strong> líneas de ventas anteriores sin costo cuyo producto ya tiene costo.
          </span>
          <button
            type="button"
            onClick={completar}
            className="rounded-lg border border-tinta bg-white px-3 py-1.5 text-xs font-semibold hover:bg-papel"
          >
            Completar costos de ventas anteriores
          </button>
        </div>
      )}

      {!tabla ? (
        !error && <p className="text-tinta/60">Cargando costos…</p>
      ) : tabla.productos.length === 0 ? (
        <p className="text-sm text-tinta/60">{soloSinCosto ? "Todos los productos tienen costo." : "No hay productos."}</p>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-tinta/10 bg-white p-3">
          <table className="w-full min-w-[34rem] text-sm">
            <thead>
              <tr className="text-left text-xs text-tinta/55">
                <th className="pb-2 font-semibold">Producto</th>
                <th className="pb-2 pr-3 text-right font-semibold">Precio</th>
                <th className="pb-2 pr-3 text-right font-semibold">Costo</th>
                <th className="pb-2 pr-3 text-right font-semibold">Sugerido</th>
                <th className="pb-2 text-right font-semibold">Margen</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-tinta/10">
              {tabla.productos.map((producto) => (
                <FilaCosto
                  key={`${producto.producto_id}-${producto.costo_unitario}`}
                  producto={producto}
                  editable={editable}
                  alGuardar={() => cargar()}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
