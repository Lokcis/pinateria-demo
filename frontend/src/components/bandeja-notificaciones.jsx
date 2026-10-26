import { useCallback, useEffect, useState } from "react";
import { marcarNotificacionLeida, marcarTodasLeidas, obtenerNotificaciones } from "../api/api-client";
import { useAuth } from "../context/auth-context";
import { formatearFechaHora } from "../utils/formato";

/**
 * Bandeja de notificaciones de stock bajo (Adendo v2, mejora B1: RF-043, HU-10).
 *
 * Muestra las notificaciones de la mas reciente a la mas antigua, con el contador de no
 * leidas, y permite marcar una o todas como leidas. Se carga al montarse.
 *
 * @param {{alCambiarNoLeidas?: (noLeidas: number) => void}} props - `alCambiarNoLeidas` avisa
 *   el contador cada vez que cambia (para la insignia del Dashboard).
 * @returns {JSX.Element}
 */
export function BandejaNotificaciones({ alCambiarNoLeidas }) {
  const { token } = useAuth();
  const [bandeja, setBandeja] = useState(null);
  const [error, setError] = useState(null);
  const [ocupado, setOcupado] = useState(false);

  const cargar = useCallback(async () => {
    try {
      const datos = await obtenerNotificaciones(token);
      setBandeja(datos);
      setError(null);
      alCambiarNoLeidas?.(datos.no_leidas);
    } catch (errorCarga) {
      setError(errorCarga.message || "No se pudieron cargar las notificaciones.");
    }
  }, [token, alCambiarNoLeidas]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  /**
   * Ejecuta una accion de marcado y recarga la bandeja.
   *
   * @param {() => Promise<unknown>} accion
   */
  async function marcar(accion) {
    setOcupado(true);
    try {
      await accion();
      await cargar();
    } catch (errorMarcado) {
      setError(errorMarcado.message || "No se pudo marcar la notificación.");
    } finally {
      setOcupado(false);
    }
  }

  const noLeidas = bandeja?.no_leidas ?? 0;

  return (
    <div className="rounded-2xl border border-tinta/10 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-tinta/60">
          Notificaciones
          {bandeja && (
            <span className="font-bold text-tinta"> · {noLeidas === 1 ? "1 sin leer" : `${noLeidas} sin leer`}</span>
          )}
        </h3>
        <button
          type="button"
          onClick={() => marcar(() => marcarTodasLeidas(token))}
          disabled={ocupado || noLeidas === 0}
          className="rounded-lg border border-tinta/20 px-3 py-1.5 text-xs font-semibold transition hover:border-tinta disabled:opacity-40"
        >
          Marcar todas como leídas
        </button>
      </div>

      {error && (
        <p role="alert" className="mt-2 rounded-xl bg-fucsia/8 px-3 py-2 text-sm font-medium text-fucsia-osc">
          {error}
        </p>
      )}

      {!bandeja ? (
        !error && <p className="mt-2 text-sm text-tinta/50">Cargando notificaciones…</p>
      ) : bandeja.notificaciones.length === 0 ? (
        <p className="mt-2 text-sm text-tinta/50">No hay notificaciones.</p>
      ) : (
        <ul className="mt-2 divide-y divide-tinta/10">
          {bandeja.notificaciones.map((notificacion) => (
            <li
              key={notificacion.id}
              className={`flex items-start justify-between gap-3 py-2 text-sm ${notificacion.leida ? "text-tinta/45" : ""}`}
            >
              <div>
                <p className={notificacion.leida ? "" : "font-semibold"}>{notificacion.mensaje}</p>
                <p className="text-xs text-tinta/50">{formatearFechaHora(notificacion.creada_en)}</p>
              </div>
              {!notificacion.leida && (
                <button
                  type="button"
                  onClick={() => marcar(() => marcarNotificacionLeida(notificacion.id, token))}
                  disabled={ocupado}
                  aria-label={`Marcar como leída: ${notificacion.mensaje}`}
                  className="shrink-0 rounded-lg border border-tinta/20 px-2.5 py-1 text-xs font-semibold transition hover:border-tinta disabled:opacity-40"
                >
                  Marcar como leída
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
