import { useCallback, useEffect, useState } from "react";
import {
  cambiarEstadoEnlaceAutoregistro,
  generarEnlaceAutoregistro,
  obtenerEnlaceAutoregistro,
} from "../api/api-client";
import { useAuth } from "../context/auth-context";
import { useConfirmar } from "./dialogo-confirmacion";

/**
 * Direccion publica del formulario de autorregistro para un codigo.
 *
 * @param {string} token
 * @returns {string}
 */
export function direccionDelEnlace(token) {
  return `${window.location.origin}/registro/${token}`;
}

/**
 * Administracion del enlace de autorregistro (solo administrador; HU-07: RF-046, RF-048).
 *
 * Permite generarlo, copiarlo, desactivarlo y regenerarlo (el anterior deja de funcionar). Sin los datos
 * del negocio completos no se puede activar, para no publicar un aviso con huecos.
 *
 * @returns {JSX.Element}
 */
export function EnlaceAutoregistro() {
  const { token } = useAuth();
  const { confirmar, dialogo } = useConfirmar();
  const [enlace, setEnlace] = useState(null);
  const [error, setError] = useState(null);
  const [copiado, setCopiado] = useState(false);

  const cargar = useCallback(async () => {
    try {
      setEnlace(await obtenerEnlaceAutoregistro(token));
      setError(null);
    } catch (falla) {
      setError(falla.message || "No se pudo cargar el enlace.");
    }
  }, [token]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  /**
   * Ejecuta una accion sobre el enlace y recarga su estado.
   *
   * @param {() => Promise<object>} accion
   * @returns {Promise<void>}
   */
  async function ejecutar(accion) {
    setError(null);
    setCopiado(false);
    try {
      setEnlace(await accion());
    } catch (falla) {
      setError(falla.message || "No se pudo actualizar el enlace.");
    }
  }

  /**
   * Regenera el codigo tras confirmar: el enlace anterior deja de funcionar.
   *
   * @returns {Promise<void>}
   */
  async function regenerar() {
    const acepta = await confirmar({
      titulo: "¿Generar un enlace nuevo?",
      mensaje: "El enlace anterior dejará de funcionar de inmediato. Tendrás que compartir el nuevo.",
      textoConfirmar: "Generar nuevo",
      peligro: true,
    });
    if (acepta) await ejecutar(() => generarEnlaceAutoregistro(token));
  }

  /**
   * Copia la direccion al portapapeles.
   *
   * @returns {Promise<void>}
   */
  async function copiar() {
    try {
      await navigator.clipboard.writeText(direccionDelEnlace(enlace.token));
      setCopiado(true);
    } catch {
      setError("No se pudo copiar. Selecciona la dirección y cópiala a mano.");
    }
  }

  if (!enlace) {
    return error ? (
      <p role="alert" className="text-sm font-medium text-fucsia-osc">
        {error}
      </p>
    ) : null;
  }

  return (
    <section aria-label="Enlace de autorregistro" className="rounded-2xl border border-tinta/10 bg-white p-4">
      {dialogo}
      <h3 className="font-display text-base font-extrabold">Enlace de autorregistro</h3>
      <p className="mt-1 text-xs text-tinta/55">
        El cliente lo abre en su celular, lee el aviso y se registra solo. Comparte el enlace por WhatsApp o muéstralo en la tienda.
      </p>

      {!enlace.datos_completos && (
        <p role="note" className="mt-3 rounded-lg bg-sol/25 px-3 py-2 text-sm font-medium">
          Para publicarlo faltan datos en “Datos del negocio” (arriba): {enlace.faltantes.join(", ")}.
        </p>
      )}

      {!enlace.existe ? (
        <button
          type="button"
          onClick={() => ejecutar(() => generarEnlaceAutoregistro(token))}
          disabled={!enlace.datos_completos}
          className="mt-3 rounded-xl bg-fucsia px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
        >
          Generar enlace
        </button>
      ) : (
        <div className="mt-3 space-y-2">
          <p className="flex flex-wrap items-center gap-2 text-sm">
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-bold ${enlace.activo ? "bg-turquesa/15 text-turquesa" : "bg-fucsia/12 text-fucsia-osc"}`}
            >
              {enlace.activo ? "Activo" : "Desactivado"}
            </span>
            <code aria-label="Dirección del enlace" className="break-all rounded bg-papel px-2 py-1 text-xs">
              {direccionDelEnlace(enlace.token)}
            </code>
          </p>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={copiar} className="rounded-lg border border-tinta/20 px-3 py-1.5 text-sm font-semibold hover:bg-papel">
              {copiado ? "¡Copiado!" : "Copiar enlace"}
            </button>
            <button
              type="button"
              onClick={() => ejecutar(() => cambiarEstadoEnlaceAutoregistro(!enlace.activo, token))}
              className="rounded-lg border border-tinta/20 px-3 py-1.5 text-sm font-semibold hover:bg-papel"
            >
              {enlace.activo ? "Desactivar" : "Activar"}
            </button>
            <button
              type="button"
              onClick={regenerar}
              className="rounded-lg border border-fucsia/40 px-3 py-1.5 text-sm font-semibold text-fucsia-osc hover:bg-fucsia/10"
            >
              Generar enlace nuevo
            </button>
          </div>
        </div>
      )}

      {error && (
        <p role="alert" className="mt-2 text-sm font-medium text-fucsia-osc">
          {error}
        </p>
      )}
    </section>
  );
}
