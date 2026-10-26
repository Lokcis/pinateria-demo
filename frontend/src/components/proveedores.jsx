import { useCallback, useEffect, useState } from "react";
import {
  crearProveedor,
  editarProveedor,
  eliminarProveedor,
  obtenerProveedores,
} from "../api/api-client";
import { useAuth } from "../context/auth-context";
import { useConfirmar } from "./dialogo-confirmacion";

const CAMPOS = [
  { id: "nombre_empresa", etiqueta: "Empresa", requerido: true },
  { id: "nombre_contacto", etiqueta: "Contacto" },
  { id: "telefono", etiqueta: "Teléfono", tipo: "tel", soloNumeros: true },
  { id: "email", etiqueta: "Correo", tipo: "email" },
  { id: "direccion", etiqueta: "Dirección" },
  { id: "notas", etiqueta: "Notas" },
];

/**
 * Formulario de alta/edicion de un proveedor (RF-012).
 *
 * @param {{proveedor?: object, alGuardar: () => void, alCancelar: () => void}} props
 *   `proveedor` presente indica edicion; ausente, alta.
 * @returns {JSX.Element}
 */
function FormularioProveedor({ proveedor, alGuardar, alCancelar }) {
  const { token } = useAuth();
  const [valores, setValores] = useState(() =>
    Object.fromEntries(CAMPOS.map(({ id }) => [id, proveedor?.[id] ?? ""]))
  );
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Envia el formulario; los campos vacios opcionales se mandan como null.
   *
   * @param {React.FormEvent} evento
   * @returns {Promise<void>}
   */
  async function enviar(evento) {
    evento.preventDefault();
    if (valores.telefono && valores.telefono.length < 7) {
      setError("El teléfono debe tener al menos 7 dígitos.");
      return;
    }
    setEnviando(true);
    setError(null);
    const payload = Object.fromEntries(
      Object.entries(valores).map(([campo, valor]) => [campo, valor.trim() || null])
    );
    try {
      if (proveedor) {
        await editarProveedor(proveedor.id, payload, token);
      } else {
        await crearProveedor(payload, token);
      }
      alGuardar();
    } catch (falla) {
      setError(falla.message || "No se pudo guardar el proveedor.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={enviar} className="space-y-3 rounded-2xl border border-tinta/10 bg-white p-4 shadow-sm">
      <h3 className="font-display text-lg font-extrabold">
        {proveedor ? "Editar proveedor" : "Nuevo proveedor"}
      </h3>
      <div className="grid gap-2.5 sm:grid-cols-2">
        {CAMPOS.map(({ id, etiqueta, requerido, tipo, soloNumeros }) => (
          <label key={id} className="text-sm">
            <span className="mb-1 block font-medium text-tinta/70">{etiqueta}</span>
            <input
              type={tipo || "text"}
              inputMode={soloNumeros ? "numeric" : undefined}
              maxLength={soloNumeros ? 15 : undefined}
              value={valores[id]}
              required={requerido}
              onChange={(evento) => {
                const valor = soloNumeros ? evento.target.value.replace(/\D/g, "") : evento.target.value;
                setValores((actual) => ({ ...actual, [id]: valor }));
              }}
              className="w-full rounded-lg border border-tinta/20 bg-white px-3 py-2"
            />
          </label>
        ))}
      </div>
      {error && (
        <p role="alert" className="text-sm font-medium text-fucsia-osc">
          {error}
        </p>
      )}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={enviando}
          className="rounded-xl bg-fucsia px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
        >
          {enviando ? "Guardando…" : "Guardar"}
        </button>
        <button
          type="button"
          onClick={alCancelar}
          className="rounded-xl border border-tinta/20 px-4 py-2 text-sm font-semibold hover:bg-papel"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}

/**
 * Directorio de proveedores con CRUD completo (RF-012, RF-021, HU-04).
 *
 * Solo debe montarse para el rol administrador; el backend ademas responde
 * 403 a cualquier otro rol, asi que esto es solo la capa de interfaz.
 *
 * @returns {JSX.Element}
 */
export function Proveedores() {
  const { token } = useAuth();
  const { confirmar, dialogo } = useConfirmar();
  const [proveedores, setProveedores] = useState(null);
  const [q, setQ] = useState("");
  const [formulario, setFormulario] = useState(null); // null | "nuevo" | objeto proveedor
  const [error, setError] = useState(null);

  const cargar = useCallback(async () => {
    setError(null);
    try {
      setProveedores(await obtenerProveedores(q.trim() || undefined, token));
    } catch (falla) {
      setError(falla.message || "No se pudo cargar el directorio.");
      setProveedores([]);
    }
  }, [q, token]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  /**
   * Elimina un proveedor tras confirmar; el backend rechaza (409) los que tienen compras.
   *
   * @param {object} proveedor
   * @returns {Promise<void>}
   */
  async function eliminar(proveedor) {
    const acepta = await confirmar({
      titulo: `¿Eliminar a ${proveedor.nombre_empresa}?`,
      mensaje: "Esta acción no se puede deshacer.",
      textoConfirmar: "Eliminar",
      peligro: true,
    });
    if (!acepta) return;
    try {
      await eliminarProveedor(proveedor.id, token);
      await cargar();
    } catch (falla) {
      setError(falla.message || "No se pudo eliminar el proveedor.");
    }
  }

  return (
    <section className="space-y-4">
      {dialogo}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-xl font-extrabold">Proveedores</h2>
        <div className="flex gap-2">
          <input
            type="search"
            value={q}
            onChange={(evento) => setQ(evento.target.value)}
            placeholder="Buscar empresa o contacto…"
            aria-label="Buscar proveedor"
            className="rounded-lg border border-tinta/20 bg-white px-3 py-2 text-sm"
          />
          <button
            type="button"
            onClick={() => setFormulario("nuevo")}
            className="rounded-xl bg-fucsia px-4 py-2 text-sm font-bold text-white"
          >
            Nuevo proveedor
          </button>
        </div>
      </div>

      {formulario && (
        <FormularioProveedor
          proveedor={formulario === "nuevo" ? undefined : formulario}
          alGuardar={() => {
            setFormulario(null);
            cargar();
          }}
          alCancelar={() => setFormulario(null)}
        />
      )}

      {error && (
        <p role="alert" className="text-sm font-medium text-fucsia-osc">
          {error}
        </p>
      )}
      {proveedores === null && <p className="text-tinta/60">Cargando…</p>}
      {proveedores?.length === 0 && !error && <p className="text-tinta/60">No hay proveedores registrados.</p>}

      <ul className="space-y-2">
        {proveedores?.map((proveedor) => (
          <li
            key={proveedor.id}
            className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-tinta/10 bg-white p-4"
          >
            <div className="min-w-0 text-sm">
              <p className="font-bold">{proveedor.nombre_empresa}</p>
              <p className="text-tinta/70">
                {[proveedor.nombre_contacto, proveedor.telefono, proveedor.email].filter(Boolean).join(" · ") ||
                  "Sin datos de contacto"}
              </p>
              {proveedor.direccion && <p className="text-tinta/60">{proveedor.direccion}</p>}
              {proveedor.notas && <p className="text-tinta/60 italic">{proveedor.notas}</p>}
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setFormulario(proveedor)}
                className="rounded-lg border border-tinta/20 px-3 py-1.5 text-sm font-semibold hover:bg-papel"
              >
                Editar
              </button>
              <button
                type="button"
                onClick={() => eliminar(proveedor)}
                className="rounded-lg border border-fucsia/40 px-3 py-1.5 text-sm font-semibold text-fucsia-osc hover:bg-fucsia/10"
              >
                Eliminar
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
