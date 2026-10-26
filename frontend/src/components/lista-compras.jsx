import { useCallback, useEffect, useState } from "react";
import { obtenerListaCompras } from "../api/api-client";
import { useAuth } from "../context/auth-context";
import { armarMensajeListaCompras, describirFaltante, enlaceWhatsApp } from "../utils/lista-compras";
import { hoyEnBogota } from "../utils/rangos";

/**
 * Lista de compras con lo que falta para llegar al stock minimo (Adendo v2, mejora B1: RF-044, RF-045).
 *
 * Se calcula al abrirla (y con "Actualizar"). Permite abrir WhatsApp con la lista escrita
 * (enlace `wa.me`, el usuario elige el chat y la envia) o copiarla como texto.
 *
 * @returns {JSX.Element}
 */
export function ListaCompras() {
  const { token } = useAuth();
  const [productos, setProductos] = useState(null);
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [avisoCopia, setAvisoCopia] = useState(null);
  const [copiaManual, setCopiaManual] = useState(false);

  const cargar = useCallback(async () => {
    setCargando(true);
    setAvisoCopia(null);
    setCopiaManual(false);
    try {
      const datos = await obtenerListaCompras(token);
      setProductos(datos.productos);
      setError(null);
    } catch (errorCarga) {
      setError(errorCarga.message || "No se pudo cargar la lista de compras.");
    } finally {
      setCargando(false);
    }
  }, [token]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  const mensaje = productos && productos.length > 0 ? armarMensajeListaCompras(productos, hoyEnBogota()) : null;
  const enlace = mensaje ? enlaceWhatsApp(mensaje) : null;

  /** Copia el mensaje al portapapeles; si el navegador no lo permite, muestra el texto para copiarlo a mano. */
  async function copiar() {
    try {
      await navigator.clipboard.writeText(mensaje);
      setAvisoCopia("Lista copiada. Pégala en el chat que quieras.");
      setCopiaManual(false);
    } catch {
      setAvisoCopia("No se pudo copiar automáticamente: selecciona el texto y cópialo.");
      setCopiaManual(true);
    }
  }

  return (
    <div className="rounded-2xl border border-tinta/10 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-tinta/60">
          Lista de compras{productos ? ` (${productos.length})` : ""}
        </h3>
        <button
          type="button"
          onClick={cargar}
          disabled={cargando}
          className="rounded-lg border border-tinta/20 px-3 py-1.5 text-xs font-semibold transition hover:border-tinta disabled:opacity-40"
        >
          {cargando ? "Actualizando…" : "Actualizar"}
        </button>
      </div>

      {error && (
        <p role="alert" className="mt-2 rounded-xl bg-fucsia/8 px-3 py-2 text-sm font-medium text-fucsia-osc">
          {error}
        </p>
      )}

      {!productos ? (
        !error && <p className="mt-2 text-sm text-tinta/50">Calculando la lista…</p>
      ) : productos.length === 0 ? (
        <p className="mt-2 text-sm text-tinta/50">No hay productos en stock bajo. No hace falta comprar nada.</p>
      ) : (
        <>
          <table className="mt-2 w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-tinta/50">
                <th className="py-1 font-semibold">Producto</th>
                <th className="py-1 pl-3 text-right font-semibold">Hay</th>
                <th className="py-1 pl-3 text-right font-semibold">Mín.</th>
                <th className="py-1 pl-3 text-right font-semibold">Faltan</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-tinta/10">
              {productos.map((producto) => (
                <tr key={producto.producto_id}>
                  <td className="py-1.5">
                    {producto.nombre} <span className="text-xs text-tinta/50">· {producto.categoria}</span>
                  </td>
                  <td className="py-1.5 pl-3 text-right tabular-nums">{producto.stock_actual}</td>
                  <td className="py-1.5 pl-3 text-right tabular-nums">{producto.stock_minimo}</td>
                  <td className="py-1.5 pl-3 text-right font-semibold tabular-nums">
                    {producto.faltante > 0 ? (
                      producto.faltante
                    ) : (
                      <span className="text-xs font-normal whitespace-nowrap text-tinta/60">{describirFaltante(0)}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="mt-3 flex flex-wrap gap-2">
            {enlace ? (
              <a
                href={enlace}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-xl bg-turquesa px-3.5 py-2 text-sm font-bold text-white transition hover:opacity-90"
              >
                Enviar por WhatsApp
              </a>
            ) : (
              <p className="w-full text-xs text-tinta/60">
                La lista es muy larga para abrirla en WhatsApp: cópiala y pégala en el chat.
              </p>
            )}
            <button
              type="button"
              onClick={copiar}
              className="rounded-xl border border-tinta/20 px-3.5 py-2 text-sm font-semibold transition hover:border-tinta"
            >
              Copiar texto
            </button>
          </div>
          {avisoCopia && (
            <p role="status" className="mt-2 text-xs font-medium text-tinta/70">
              {avisoCopia}
            </p>
          )}
          {copiaManual && (
            <textarea
              readOnly
              value={mensaje}
              aria-label="Texto de la lista de compras"
              onFocus={(evento) => evento.target.select()}
              rows={6}
              className="mt-2 w-full rounded-xl border border-tinta/20 p-2 text-xs"
            />
          )}
        </>
      )}
    </div>
  );
}
