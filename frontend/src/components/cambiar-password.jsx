import { useState } from "react";
import { cambiarMiPassword } from "../api/api-client";
import { useAuth } from "../context/auth-context";

/**
 * Boton y panel para que el usuario de la sesion cambie su propia contrasena (RF-015).
 *
 * @param {{className?: string}} props `className` reemplaza el estilo del boton (por ejemplo, para usarlo como
 *   opcion de un menu).
 * @returns {JSX.Element}
 */
export function CambiarPassword({ className }) {
  const { token } = useAuth();
  const [abierto, setAbierto] = useState(false);
  const [actual, setActual] = useState("");
  const [nueva, setNueva] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);
  const [exito, setExito] = useState(false);

  /**
   * Cierra el panel y limpia los campos.
   *
   * @returns {void}
   */
  function cerrar() {
    setAbierto(false);
    setActual("");
    setNueva("");
    setError(null);
  }

  /**
   * Envia el cambio de contrasena al backend.
   *
   * @param {React.FormEvent} evento
   * @returns {Promise<void>}
   */
  async function enviar(evento) {
    evento.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      await cambiarMiPassword(actual, nueva, token);
      cerrar();
      setExito(true);
    } catch (falla) {
      setError(falla.message || "No se pudo cambiar la contraseña.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => {
          setExito(false);
          setAbierto(true);
        }}
        className={className ?? "rounded-xl border border-tinta/20 px-3.5 py-2 text-sm font-semibold transition hover:border-tinta hover:bg-papel"}
      >
        Cambiar contraseña
      </button>
      {exito && (
        <p role="status" className="text-xs font-semibold text-tinta/70">
          Contraseña actualizada.
        </p>
      )}
      {abierto && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-tinta/40 px-4">
          <form onSubmit={enviar} role="dialog" aria-label="Cambiar contraseña" className="w-full max-w-sm space-y-3 rounded-2xl bg-white p-5 shadow-lg">
            <h3 className="font-display text-lg font-extrabold">Cambiar contraseña</h3>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-tinta/70">Contraseña actual</span>
              <input type="password" value={actual} onChange={(e) => setActual(e.target.value)} required autoComplete="current-password" className="w-full rounded-lg border border-tinta/20 px-3 py-2" />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-tinta/70">Contraseña nueva (mínimo 8)</span>
              <input type="password" value={nueva} onChange={(e) => setNueva(e.target.value)} required minLength={8} maxLength={72} autoComplete="new-password" className="w-full rounded-lg border border-tinta/20 px-3 py-2" />
            </label>
            {error && (
              <p role="alert" className="text-sm font-medium text-fucsia-osc">
                {error}
              </p>
            )}
            <div className="flex gap-2">
              <button type="submit" disabled={enviando} className="rounded-xl bg-fucsia px-4 py-2 text-sm font-bold text-white disabled:opacity-50">
                {enviando ? "Guardando…" : "Guardar"}
              </button>
              <button type="button" onClick={cerrar} className="rounded-xl border border-tinta/20 px-4 py-2 text-sm font-semibold hover:bg-papel">
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}
