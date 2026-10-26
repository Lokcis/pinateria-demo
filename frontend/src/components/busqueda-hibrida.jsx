import { useRef, useState } from "react";
import { buscarProductos } from "../api/api-client";
import { useAuth } from "../context/auth-context";
import { useCart } from "../context/cart-context";
import { useSinConexion } from "../context/sin-conexion-context";
import { esErrorDeConexion } from "../utils/conexion";
import { esPatronDeEscaner } from "../utils/detectar-escaner";
import { formatearMoneda } from "../utils/formato";

// Colores de etiqueta por categoria: se asignan de forma estable por `categoria_id`.
const COLORES_CATEGORIA = [
  "bg-fucsia/12 text-fucsia-osc",
  "bg-turquesa/12 text-turquesa",
  "bg-cielo/12 text-cielo",
  "bg-mandarina/15 text-mandarina",
  "bg-sol/25 text-tinta",
];

/**
 * Tarjeta de un producto en la lista de resultados manuales.
 *
 * @param {{producto: object, alSeleccionar: (producto: object) => void}} props
 * @returns {JSX.Element}
 */
function TarjetaProducto({ producto, alSeleccionar }) {
  const color = COLORES_CATEGORIA[producto.categoria_id % COLORES_CATEGORIA.length];
  const stockBajo = producto.stock_actual <= producto.stock_minimo;

  return (
    <li className="animate-subir">
      <button
        type="button"
        onClick={() => alSeleccionar(producto)}
        className="group flex w-full items-center gap-3 rounded-2xl border border-tinta/10 bg-white p-3 text-left transition hover:-translate-y-0.5 hover:border-tinta hover:shadow-[3px_3px_0_var(--color-tinta)] active:translate-y-0 active:shadow-none"
      >
        <span
          aria-hidden="true"
          className={`grid h-12 w-12 shrink-0 place-items-center rounded-xl font-display text-xl font-extrabold ${color}`}
        >
          {producto.nombre.trim().charAt(0).toUpperCase()}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate font-semibold">{producto.nombre}</span>
          <span
            className={`mt-0.5 inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${
              stockBajo ? "bg-sol/30 text-tinta" : "bg-tinta/6 text-tinta/65"
            }`}
          >
            {stockBajo ? `Quedan ${producto.stock_actual}` : `${producto.stock_actual} en stock`}
          </span>
        </span>
        <span className="shrink-0 font-display text-lg font-extrabold">{formatearMoneda(producto.precio_venta)}</span>
        <span
          aria-hidden="true"
          className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-fucsia text-lg font-bold leading-none text-white transition group-hover:scale-110"
        >
          +
        </span>
      </button>
    </li>
  );
}

/**
 * Input hibrido: distingue lectura por escaner de tecleo manual (HU-01).
 *
 * - Si el patron de tecleo antes de Enter es una rafaga rapida (typico de
 *   un lector de codigo de barras), busca por codigo exacto y agrega el
 *   producto al carrito automaticamente.
 * - Si el patron es tecleo humano normal, busca por nombre (fallback
 *   trigram del backend) y muestra una lista para que el vendedor elija.
 * - Sin conexion (Fase 9) busca igual en la copia del catalogo guardada en el equipo.
 *
 * @returns {JSX.Element}
 */
export function BusquedaHibrida() {
  const { token } = useAuth();
  const { agregarProducto } = useCart();
  const { enLinea, buscarLocal, reportarFalloDeConexion, catalogo } = useSinConexion();

  const [valorInput, setValorInput] = useState("");
  const [resultados, setResultados] = useState([]);
  const [buscando, setBuscando] = useState(false);
  const [mensaje, setMensaje] = useState(null);
  const [resultadosLocales, setResultadosLocales] = useState(false);

  const inputRef = useRef(null);
  const marcaTiempoUltimaTecla = useRef(null);
  const deltasEntreTeclas = useRef([]);

  /**
   * Registra el intervalo de tiempo entre esta tecla y la anterior.
   *
   * @param {React.KeyboardEvent<HTMLInputElement>} evento
   */
  function manejarKeyDown(evento) {
    if (evento.key === "Enter") {
      return;
    }
    const ahora = performance.now();
    if (marcaTiempoUltimaTecla.current !== null) {
      deltasEntreTeclas.current.push(ahora - marcaTiempoUltimaTecla.current);
    }
    marcaTiempoUltimaTecla.current = ahora;
  }

  /**
   * Reinicia el registro de timing para la proxima entrada.
   */
  function reiniciarSeguimientoDeTecleo() {
    marcaTiempoUltimaTecla.current = null;
    deltasEntreTeclas.current = [];
  }

  /**
   * Busca en el servidor o, sin conexion, en el catalogo guardado en el equipo.
   *
   * @param {string} textoConsulta
   * @returns {Promise<{productos: Array<object>, local: boolean}>}
   */
  async function buscar(textoConsulta) {
    if (enLinea) {
      try {
        return { productos: await buscarProductos(textoConsulta, token), local: false };
      } catch (error) {
        if (!esErrorDeConexion(error)) throw error;
        reportarFalloDeConexion();
      }
    }
    return { productos: await buscarLocal(textoConsulta), local: true };
  }

  /**
   * Procesa el Enter: decide si fue escaneo (auto-agregar) o tecleo manual (mostrar lista).
   *
   * @param {React.KeyboardEvent<HTMLInputElement>} evento
   * @returns {Promise<void>}
   */
  async function manejarKeyPress(evento) {
    if (evento.key !== "Enter" || valorInput.trim().length === 0) {
      return;
    }

    const textoConsulta = valorInput.trim();
    const fueEscaneado = esPatronDeEscaner(deltasEntreTeclas.current);
    reiniciarSeguimientoDeTecleo();

    setBuscando(true);
    setMensaje(null);
    try {
      const { productos, local } = await buscar(textoConsulta);
      setResultadosLocales(local);

      if (productos.length === 0) {
        setResultados([]);
        setMensaje(
          local && !catalogo
            ? "Sin conexión y sin catálogo guardado en este equipo: conéctate una vez para poder buscar productos sin conexión."
            : `No se encontro ningun producto para "${textoConsulta}".`
        );
        return;
      }

      if (fueEscaneado) {
        // Lectura por escaner: se asume codigo exacto, se agrega directo.
        agregarProducto(productos[0]);
        setValorInput("");
        setResultados([]);
        return;
      }

      // Tecleo manual: se muestra la lista para que el vendedor elija.
      setResultados(productos);
    } catch (error) {
      setMensaje(error.message || "Error al buscar el producto.");
    } finally {
      setBuscando(false);
    }
  }

  /**
   * Agrega un resultado de la lista manual al carrito y limpia la busqueda.
   *
   * @param {object} producto
   */
  function seleccionarResultado(producto) {
    agregarProducto(producto);
    setValorInput("");
    setResultados([]);
    inputRef.current?.focus();
  }

  return (
    <section className="busqueda-hibrida">
      <div className="rounded-3xl border border-tinta/10 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between gap-3">
          <label htmlFor="busqueda-producto" className="font-display text-lg font-bold">
            Escanear o buscar producto
          </label>
          {enLinea ? (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-turquesa/10 px-2.5 py-1 text-xs font-semibold text-turquesa">
              <span className="h-2 w-2 animate-pulso-suave rounded-full bg-turquesa" aria-hidden="true" />
              Listo para escanear
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-sol/30 px-2.5 py-1 text-xs font-semibold text-tinta">
              <span className="h-2 w-2 rounded-full bg-fucsia" aria-hidden="true" />
              Sin conexión · catálogo guardado
            </span>
          )}
        </div>

        <div className="relative mt-3">
          <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            className="pointer-events-none absolute left-4 top-1/2 h-6 w-6 -translate-y-1/2 text-tinta/45"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          >
            <path d="M4 7V5a1 1 0 0 1 1-1h2M17 4h2a1 1 0 0 1 1 1v2M20 17v2a1 1 0 0 1-1 1h-2M7 20H5a1 1 0 0 1-1-1v-2M8 8v8M12 8v8M16 8v8" />
          </svg>
          <input
            id="busqueda-producto"
            ref={inputRef}
            type="text"
            placeholder="Código de barras, nombre o categoría…"
            value={valorInput}
            onChange={(evento) => setValorInput(evento.target.value)}
            onKeyDown={manejarKeyDown}
            onKeyUp={manejarKeyPress}
            autoComplete="off"
            autoFocus
            className="w-full rounded-2xl border-2 border-tinta/15 bg-papel py-4 pl-13 pr-4 text-xl font-medium outline-none transition placeholder:text-tinta/40 focus:border-fucsia focus:bg-white focus:ring-4 focus:ring-fucsia/15"
          />
        </div>

        <p className="mt-2 text-sm text-tinta/60">
          Con el lector, el producto se agrega solo. Si escribes, pulsa Enter y elige de la lista.
        </p>

        {buscando && (
          <p role="status" className="mt-3 text-sm font-semibold text-tinta/70">
            Buscando…
          </p>
        )}
        {mensaje && (
          <p role="status" className="mt-3 rounded-xl bg-tinta/5 px-3 py-2 text-sm font-medium text-tinta/80">
            {mensaje}
          </p>
        )}
      </div>

      {resultados.length > 0 && resultadosLocales && (
        <p className="mt-4 text-xs font-medium text-tinta/60">
          Resultados del catálogo guardado en este equipo: el stock mostrado puede estar desactualizado.
        </p>
      )}
      {resultados.length > 0 && (
        <ul className={`${resultadosLocales ? "mt-2" : "mt-4"} grid gap-2.5 sm:grid-cols-2`}>
          {resultados.map((producto) => (
            <TarjetaProducto key={producto.id} producto={producto} alSeleccionar={seleccionarResultado} />
          ))}
        </ul>
      )}
    </section>
  );
}
