import { useCallback, useEffect, useState } from "react";
import { crearCategoria, editarCategoria, eliminarCategoria, obtenerCategorias } from "../api/api-client";
import { useAuth } from "../context/auth-context";
import { useConfirmar } from "./dialogo-confirmacion";

/**
 * Formulario de alta/edicion de una categoria (RF-017).
 *
 * @param {{categoria?: object, alGuardar: () => void, alCancelar: () => void}} props
 *   `categoria` presente indica edicion; ausente, alta.
 * @returns {JSX.Element}
 */
function FormularioCategoria({ categoria, alGuardar, alCancelar }) {
  const { token } = useAuth();
  const [nombre, setNombre] = useState(categoria?.nombre ?? "");
  const [descripcion, setDescripcion] = useState(categoria?.descripcion ?? "");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Envia el formulario; la descripcion vacia se manda como null.
   *
   * @param {React.FormEvent} evento
   * @returns {Promise<void>}
   */
  async function enviar(evento) {
    evento.preventDefault();
    setEnviando(true);
    setError(null);
    const payload = { nombre: nombre.trim(), descripcion: descripcion.trim() || null };
    try {
      if (categoria) {
        await editarCategoria(categoria.id, payload, token);
      } else {
        await crearCategoria(payload, token);
      }
      alGuardar();
    } catch (falla) {
      setError(falla.message || "No se pudo guardar la categoría.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={enviar} className="space-y-3 rounded-2xl border border-tinta/10 bg-white p-4 shadow-sm">
      <h3 className="font-display text-lg font-extrabold">{categoria ? "Editar categoría" : "Nueva categoría"}</h3>
      <div className="grid gap-2.5 sm:grid-cols-2">
        <label className="text-sm">
          <span className="mb-1 block font-medium text-tinta/70">Nombre</span>
          <input value={nombre} onChange={(e) => setNombre(e.target.value)} required maxLength={80} className="w-full rounded-lg border border-tinta/20 bg-white px-3 py-2" />
        </label>
        <label className="text-sm">
          <span className="mb-1 block font-medium text-tinta/70">Descripción</span>
          <input value={descripcion} onChange={(e) => setDescripcion(e.target.value)} maxLength={255} className="w-full rounded-lg border border-tinta/20 bg-white px-3 py-2" />
        </label>
      </div>
      {error && (
        <p role="alert" className="text-sm font-medium text-fucsia-osc">
          {error}
        </p>
      )}
      <div className="flex gap-2">
        <button type="submit" disabled={enviando} className="rounded-xl bg-fucsia px-4 py-2 text-sm font-bold text-white disabled:opacity-50">
          {enviando ? "Guardando…" : "Guardar"}
        </button>
        <button type="button" onClick={alCancelar} className="rounded-xl border border-tinta/20 px-4 py-2 text-sm font-semibold hover:bg-papel">
          Cancelar
        </button>
      </div>
    </form>
  );
}

/**
 * Gestion de categorias de productos (RF-017). Solo administrador.
 *
 * El backend rechaza (409) eliminar una categoria con productos.
 *
 * @returns {JSX.Element}
 */
export function Categorias() {
  const { token } = useAuth();
  const { confirmar, dialogo } = useConfirmar();
  const [categorias, setCategorias] = useState(null);
  const [formulario, setFormulario] = useState(null); // null | "nueva" | objeto categoria
  const [error, setError] = useState(null);

  const cargar = useCallback(async () => {
    setError(null);
    try {
      setCategorias(await obtenerCategorias(token));
    } catch (falla) {
      setError(falla.message || "No se pudieron cargar las categorías.");
      setCategorias([]);
    }
  }, [token]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  /**
   * Elimina una categoria tras confirmar.
   *
   * @param {object} categoria
   * @returns {Promise<void>}
   */
  async function eliminar(categoria) {
    const acepta = await confirmar({
      titulo: `¿Eliminar la categoría ${categoria.nombre}?`,
      mensaje: "Esta acción no se puede deshacer.",
      textoConfirmar: "Eliminar",
      peligro: true,
    });
    if (!acepta) return;
    setError(null);
    try {
      await eliminarCategoria(categoria.id, token);
      await cargar();
    } catch (falla) {
      setError(falla.message || "No se pudo eliminar la categoría.");
    }
  }

  return (
    <section className="space-y-4">
      {dialogo}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-xl font-extrabold">Categorías</h2>
        <button type="button" onClick={() => setFormulario("nueva")} className="rounded-xl bg-fucsia px-4 py-2 text-sm font-bold text-white">
          Nueva categoría
        </button>
      </div>

      {formulario && (
        <FormularioCategoria
          key={formulario === "nueva" ? "nueva" : formulario.id}
          categoria={formulario === "nueva" ? undefined : formulario}
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
      {categorias === null && <p className="text-tinta/60">Cargando…</p>}
      {categorias?.length === 0 && !error && <p className="text-tinta/60">No hay categorías registradas.</p>}

      <ul className="space-y-2">
        {categorias?.map((categoria) => (
          <li key={categoria.id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-tinta/10 bg-white p-4">
            <div className="min-w-0 text-sm">
              <p className="font-bold">{categoria.nombre}</p>
              {categoria.descripcion && <p className="text-tinta/60">{categoria.descripcion}</p>}
            </div>
            <div className="flex gap-2">
              <button type="button" onClick={() => setFormulario(categoria)} aria-label={`Editar ${categoria.nombre}`} className="rounded-lg border border-tinta/20 px-3 py-1.5 text-sm font-semibold hover:bg-papel">
                Editar
              </button>
              <button type="button" onClick={() => eliminar(categoria)} aria-label={`Eliminar ${categoria.nombre}`} className="rounded-lg border border-fucsia/40 px-3 py-1.5 text-sm font-semibold text-fucsia-osc hover:bg-fucsia/10">
                Eliminar
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
