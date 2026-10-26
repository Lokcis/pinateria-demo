import { useCallback, useEffect, useState } from "react";
import { guardarDatosNegocio, obtenerDatosNegocio } from "../api/api-client";
import { useAuth } from "../context/auth-context";

const CAMPOS = [
  { id: "nombre", etiqueta: "Nombre o razón social", requerido: true },
  { id: "documento", etiqueta: "NIT o cédula", requerido: true },
  { id: "direccion", etiqueta: "Dirección y ciudad", requerido: true },
  { id: "telefono", etiqueta: "Teléfono de la tienda", requerido: true, tipo: "tel" },
  { id: "correo_datos", etiqueta: "Correo para consultas y reclamos de datos", requerido: true, tipo: "email" },
  { id: "responsable_datos", etiqueta: "Quién atiende las solicitudes (opcional)" },
  { id: "politica_fecha", etiqueta: "Fecha desde la que rige la política", requerido: true, ayuda: "Ej. 12-10-2026" },
  { id: "politica_version", etiqueta: "Versión de la política", ayuda: "1.0; súbela (1.1, 2.0…) si cambia el texto" },
];

/**
 * Datos del negocio para la Politica de Tratamiento de Datos (solo administrador; HU-07).
 *
 * Con estos datos el sistema arma el aviso de privacidad y la politica que ven el POS y el formulario
 * de autorregistro. Mientras falte alguno, la politica queda como "borrador". Cualquier correo sirve
 * (no tiene que ser del dominio): es el canal por el que los titulares piden ver, corregir o borrar sus datos.
 *
 * @param {{alGuardar?: () => void}} props `alGuardar` avisa a la pantalla que los datos cambiaron.
 * @returns {JSX.Element | null}
 */
export function DatosNegocio({ alGuardar }) {
  const { token } = useAuth();
  const [valores, setValores] = useState(null);
  const [estado, setEstado] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);
  const [aviso, setAviso] = useState(null);

  const cargar = useCallback(async () => {
    try {
      const datos = await obtenerDatosNegocio(token);
      setEstado(datos);
      setValores(Object.fromEntries(CAMPOS.map(({ id }) => [id, datos[id] ?? ""])));
      setError(null);
    } catch (falla) {
      setError(falla.message || "No se pudieron cargar los datos del negocio.");
    }
  }, [token]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  /**
   * Guarda los datos y refresca el estado.
   *
   * @param {React.FormEvent} evento
   * @returns {Promise<void>}
   */
  async function guardar(evento) {
    evento.preventDefault();
    setGuardando(true);
    setError(null);
    setAviso(null);
    try {
      const datos = await guardarDatosNegocio(valores, token);
      setEstado(datos);
      setValores(Object.fromEntries(CAMPOS.map(({ id }) => [id, datos[id] ?? ""])));
      setAviso(
        datos.datos_completos
          ? `Datos guardados. Las autorizaciones nuevas quedan con la versión ${datos.version_vigente} de la política.`
          : "Datos guardados, pero aún falta completar algunos."
      );
      alGuardar?.();
    } catch (falla) {
      setError(falla.message || "No se pudieron guardar los datos del negocio.");
    } finally {
      setGuardando(false);
    }
  }

  if (!valores) {
    return error ? (
      <p role="alert" className="text-sm font-medium text-fucsia-osc">
        {error}
      </p>
    ) : null;
  }

  return (
    <form onSubmit={guardar} aria-label="Datos del negocio" className="rounded-2xl border border-tinta/10 bg-white p-4">
      <h3 className="font-display text-base font-extrabold">Datos del negocio</h3>
      <p className="mt-1 text-xs text-tinta/55">
        Aparecen en el aviso de privacidad y en la política de datos que ven los clientes. Cualquier correo sirve: es el
        canal por el que los clientes piden ver, corregir o borrar sus datos.
      </p>

      {!estado.datos_completos && (
        <p role="note" className="mt-3 rounded-lg bg-sol/25 px-3 py-2 text-sm font-medium">
          Falta: {estado.faltantes.join(", ")}. Mientras tanto la política queda como “borrador” y no se puede publicar el
          enlace de autorregistro.
        </p>
      )}

      <div className="mt-3 grid gap-2.5 sm:grid-cols-2">
        {CAMPOS.map(({ id, etiqueta, tipo, ayuda }) => (
          <label key={id} className="text-sm">
            <span className="mb-1 block font-medium text-tinta/70">{etiqueta}</span>
            <input
              type={tipo || "text"}
              value={valores[id]}
              onChange={(evento) => setValores((actual) => ({ ...actual, [id]: evento.target.value }))}
              className="w-full rounded-lg border border-tinta/20 bg-white px-3 py-2"
            />
            {ayuda && <span className="mt-0.5 block text-xs text-tinta/50">{ayuda}</span>}
          </label>
        ))}
      </div>

      {error && (
        <p role="alert" className="mt-3 text-sm font-medium text-fucsia-osc">
          {error}
        </p>
      )}
      {aviso && (
        <p role="status" className="mt-3 text-sm font-medium text-turquesa">
          {aviso}
        </p>
      )}
      <button
        type="submit"
        disabled={guardando}
        className="mt-3 rounded-xl bg-fucsia px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
      >
        {guardando ? "Guardando…" : "Guardar datos"}
      </button>
    </form>
  );
}
