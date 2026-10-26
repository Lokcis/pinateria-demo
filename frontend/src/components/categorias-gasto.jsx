import { useState } from "react";
import { crearCategoriaGasto, editarCategoriaGasto } from "../api/api-client";
import { useAuth } from "../context/auth-context";

/**
 * Una categoria de la lista: se puede renombrar y activar o desactivar; la de sistema solo se muestra.
 *
 * @param {{categoria: object, alCambiar: () => void}} props
 * @returns {JSX.Element}
 */
function FilaCategoria({ categoria, alCambiar }) {
  const { token } = useAuth();
  const [editando, setEditando] = useState(false);
  const [nombre, setNombre] = useState(categoria.nombre);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Aplica un cambio (nombre o estado) y avisa al padre para recargar.
   *
   * @param {{nombre?: string, activa?: boolean}} cambios
   * @returns {Promise<void>}
   */
  async function guardar(cambios) {
    setEnviando(true);
    setError(null);
    try {
      await editarCategoriaGasto(categoria.id, cambios, token);
      setEditando(false);
      alCambiar();
    } catch (falla) {
      setError(falla.message || "No se pudo guardar la categoría.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <li className="rounded-xl border border-tinta/10 bg-white p-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        {editando ? (
          <form
            className="flex flex-1 flex-wrap items-center gap-2"
            onSubmit={(evento) => {
              evento.preventDefault();
              guardar({ nombre: nombre.trim() });
            }}
          >
            <input
              value={nombre}
              onChange={(evento) => setNombre(evento.target.value)}
              required
              maxLength={60}
              aria-label={`Nuevo nombre de ${categoria.nombre}`}
              className="min-w-0 flex-1 rounded-lg border border-tinta/20 px-3 py-1.5"
            />
            <button type="submit" disabled={enviando} className="rounded-lg bg-fucsia px-3 py-1.5 font-bold text-white disabled:opacity-50">
              Guardar
            </button>
            <button
              type="button"
              onClick={() => {
                setEditando(false);
                setNombre(categoria.nombre);
              }}
              className="rounded-lg border border-tinta/20 px-3 py-1.5 font-semibold hover:bg-papel"
            >
              Cancelar
            </button>
          </form>
        ) : (
          <>
            <p className={`font-bold ${categoria.activa ? "" : "text-tinta/45 line-through"}`}>
              {categoria.nombre}
              {categoria.es_sistema && (
                <span className="ml-2 rounded-full bg-papel-osc px-2 py-0.5 text-xs font-bold no-underline">De sistema</span>
              )}
              {!categoria.activa && <span className="ml-2 text-xs font-semibold text-tinta/55">(desactivada)</span>}
            </p>
            {!categoria.es_sistema && (
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setEditando(true)}
                  aria-label={`Renombrar ${categoria.nombre}`}
                  className="rounded-lg border border-tinta/20 px-3 py-1 font-semibold hover:bg-papel"
                >
                  Renombrar
                </button>
                <button
                  type="button"
                  disabled={enviando}
                  onClick={() => guardar({ activa: !categoria.activa })}
                  aria-label={`${categoria.activa ? "Desactivar" : "Activar"} ${categoria.nombre}`}
                  className="rounded-lg border border-tinta/20 px-3 py-1 font-semibold hover:bg-papel disabled:opacity-50"
                >
                  {categoria.activa ? "Desactivar" : "Activar"}
                </button>
              </div>
            )}
          </>
        )}
      </div>
      {error && (
        <p role="alert" className="mt-2 font-medium text-fucsia-osc">
          {error}
        </p>
      )}
    </li>
  );
}

/**
 * Administracion de las categorias de gasto (Adendo v3, RF-060). Solo administrador.
 *
 * Crea, renombra, activa y desactiva categorias. "Compra de mercancía" es de sistema y no se modifica. Una
 * categoria desactivada no se ofrece para gastos nuevos pero conserva los antiguos.
 *
 * @param {{categorias: Array<object>, alCambiar: () => void, alCerrar: () => void}} props
 * @returns {JSX.Element}
 */
export function CategoriasGasto({ categorias, alCambiar, alCerrar }) {
  const { token } = useAuth();
  const [nombre, setNombre] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Crea la categoria escrita.
   *
   * @param {React.FormEvent} evento
   * @returns {Promise<void>}
   */
  async function crear(evento) {
    evento.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      await crearCategoriaGasto({ nombre: nombre.trim() }, token);
      setNombre("");
      alCambiar();
    } catch (falla) {
      setError(falla.message || "No se pudo crear la categoría.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section aria-label="Categorías de gasto" className="space-y-3 rounded-2xl border border-tinta/10 bg-papel p-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-display text-lg font-extrabold">Categorías de gasto</h3>
        <button type="button" onClick={alCerrar} className="rounded-lg px-2 py-1 text-sm font-semibold text-tinta/60 hover:text-tinta">
          Cerrar
        </button>
      </div>
      <form onSubmit={crear} className="flex flex-wrap gap-2">
        <input
          value={nombre}
          onChange={(evento) => setNombre(evento.target.value)}
          required
          maxLength={60}
          placeholder="Nueva categoría"
          aria-label="Nombre de la nueva categoría"
          className="min-w-0 flex-1 rounded-lg border border-tinta/20 bg-white px-3 py-2 text-sm"
        />
        <button type="submit" disabled={enviando} className="rounded-xl bg-fucsia px-4 py-2 text-sm font-bold text-white disabled:opacity-50">
          Agregar
        </button>
      </form>
      {error && (
        <p role="alert" className="text-sm font-medium text-fucsia-osc">
          {error}
        </p>
      )}
      <ul className="space-y-2">
        {categorias.map((categoria) => (
          <FilaCategoria key={`${categoria.id}-${categoria.nombre}-${categoria.activa}`} categoria={categoria} alCambiar={alCambiar} />
        ))}
      </ul>
    </section>
  );
}
