import { useState } from "react";
import { buscarProductos } from "../api/api-client";
import { useAuth } from "../context/auth-context";

/**
 * Convierte la receta del backend (`ProductoOut.componentes`) al estado del editor.
 *
 * @param {Array<{producto_id: number, nombre: string, cantidad: number}>} [componentes]
 * @returns {Array<{producto_id: number, nombre: string, cantidad: number}>}
 */
export function recetaDesdeProducto(componentes) {
  return (componentes || []).map(({ producto_id, nombre, cantidad }) => ({ producto_id, nombre, cantidad }));
}

/**
 * Convierte el estado del editor al payload que espera la API.
 *
 * @param {Array<{producto_id: number, cantidad: number}>} receta
 * @returns {Array<{producto_id: number, cantidad: number}>}
 */
export function recetaParaApi(receta) {
  return receta.map(({ producto_id, cantidad }) => ({ producto_id, cantidad: Number(cantidad) }));
}

/**
 * Editor de la receta de un producto compuesto (paquete o ancheta): busca
 * productos, los agrega con su cantidad y permite quitarlos.
 *
 * Es un componente controlado: `receta` es la lista actual y `alCambiar`
 * recibe la lista nueva. No puede contener el propio producto (`excluirId`).
 *
 * @param {{
 *   receta: Array<{producto_id: number, nombre: string, cantidad: number|string}>,
 *   alCambiar: (receta: Array<object>) => void,
 *   excluirId?: number
 * }} props
 * @returns {JSX.Element}
 */
export function EditorReceta({ receta, alCambiar, excluirId }) {
  const { token } = useAuth();
  const [texto, setTexto] = useState("");
  const [resultados, setResultados] = useState([]);
  const [buscando, setBuscando] = useState(false);
  const [mensaje, setMensaje] = useState(null);

  /**
   * Busca productos por nombre o código para agregarlos a la receta.
   *
   * @returns {Promise<void>}
   */
  async function buscar() {
    const consulta = texto.trim();
    if (!consulta) return;
    setBuscando(true);
    setMensaje(null);
    try {
      const encontrados = await buscarProductos(consulta, token);
      setResultados(encontrados.filter((producto) => producto.id !== excluirId));
      if (encontrados.length === 0) setMensaje("No se encontraron productos.");
    } catch (falla) {
      setMensaje(falla.message || "No se pudo buscar.");
    } finally {
      setBuscando(false);
    }
  }

  /**
   * Agrega un producto a la receta; si ya estaba, suma una unidad.
   *
   * @param {{id: number, nombre: string}} producto
   * @returns {void}
   */
  function agregar(producto) {
    const existente = receta.find((linea) => linea.producto_id === producto.id);
    if (existente) {
      alCambiar(
        receta.map((linea) =>
          linea.producto_id === producto.id ? { ...linea, cantidad: Number(linea.cantidad) + 1 } : linea
        )
      );
    } else {
      alCambiar([...receta, { producto_id: producto.id, nombre: producto.nombre, cantidad: 1 }]);
    }
    setResultados([]);
    setTexto("");
  }

  const cambiarCantidad = (productoId, cantidad) =>
    alCambiar(receta.map((linea) => (linea.producto_id === productoId ? { ...linea, cantidad } : linea)));
  const quitar = (productoId) => alCambiar(receta.filter((linea) => linea.producto_id !== productoId));

  return (
    <fieldset className="space-y-2.5 rounded-xl border border-tinta/10 bg-papel/50 p-3">
      <legend className="px-1 text-sm font-semibold text-tinta/70">Artículos que lo componen</legend>

      {receta.length === 0 ? (
        <p className="text-sm text-tinta/50">Aún no tiene artículos: busca y agrega los que lleva.</p>
      ) : (
        <ul className="space-y-1.5">
          {receta.map((linea) => (
            <li key={linea.producto_id} className="flex items-center gap-2 text-sm">
              <input
                type="number"
                min="1"
                step="1"
                required
                aria-label={`Cantidad de ${linea.nombre}`}
                value={linea.cantidad}
                onChange={(evento) => cambiarCantidad(linea.producto_id, evento.target.value)}
                className="w-20 rounded-lg border border-tinta/20 bg-white px-2 py-1"
              />
              <span className="flex-1 font-medium">{linea.nombre}</span>
              <button
                type="button"
                onClick={() => quitar(linea.producto_id)}
                aria-label={`Quitar ${linea.nombre}`}
                className="rounded-lg border border-tinta/20 px-2 py-1 text-xs font-semibold text-fucsia-osc hover:bg-fucsia/10"
              >
                Quitar
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="flex gap-2">
        <input
          type="text"
          value={texto}
          onChange={(evento) => setTexto(evento.target.value)}
          onKeyDown={(evento) => {
            if (evento.key === "Enter") {
              evento.preventDefault();
              buscar();
            }
          }}
          aria-label="Buscar componente"
          placeholder="Buscar por nombre o código…"
          className="flex-1 rounded-lg border border-tinta/20 bg-white px-3 py-1.5 text-sm"
        />
        <button
          type="button"
          onClick={buscar}
          disabled={buscando}
          className="rounded-lg border border-tinta px-3 py-1.5 text-sm font-semibold hover:bg-white disabled:opacity-50"
        >
          {buscando ? "Buscando…" : "Buscar artículo"}
        </button>
      </div>
      {mensaje && <p className="text-sm text-tinta/60">{mensaje}</p>}
      {resultados.length > 0 && (
        <ul className="flex flex-wrap gap-1.5">
          {resultados.map((producto) => (
            <li key={producto.id}>
              <button
                type="button"
                onClick={() => agregar(producto)}
                title="Agregar a la receta"
                className="rounded-full border border-tinta/15 bg-white px-3 py-1 text-sm hover:bg-papel"
              >
                {producto.nombre}
              </button>
            </li>
          ))}
        </ul>
      )}
    </fieldset>
  );
}

/**
 * Lista de solo lectura de los artículos de un producto compuesto (para la tarjeta).
 *
 * @param {{componentes: Array<{producto_id: number, nombre: string, cantidad: number, activo: boolean}>}} props
 * @returns {JSX.Element | null}
 */
export function ComposicionProducto({ componentes }) {
  if (!componentes || componentes.length === 0) return null;
  return (
    <div className="mb-4">
      <p className="text-sm font-semibold text-tinta/70">Compuesto por</p>
      <ul className="mt-1.5 space-y-1 text-sm">
        {componentes.map((componente) => (
          <li key={componente.producto_id}>
            <span className="font-semibold tabular-nums">{componente.cantidad} ×</span> {componente.nombre}
            {!componente.activo && (
              <span className="ml-2 rounded-full bg-tinta/10 px-2 py-0.5 text-xs font-semibold text-tinta/60">
                Inactivo
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
