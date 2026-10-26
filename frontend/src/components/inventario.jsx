import { useCallback, useEffect, useState } from "react";
import {
  actualizarStockMinimo,
  crearProducto,
  desactivarProducto,
  editarProducto,
  obtenerAjustesInventario,
  obtenerCatalogo,
  obtenerCategorias,
  obtenerProductosQueLoUsan,
  reactivarProducto,
  registrarAjusteInventario,
} from "../api/api-client";
import { Desplegable } from "./desplegable";
import { useAuth } from "../context/auth-context";
import { useConfirmar } from "./dialogo-confirmacion";
import { ComposicionProducto, EditorReceta, recetaDesdeProducto, recetaParaApi } from "./editor-receta";
import { ETIQUETA_TIPO_AJUSTE, formatearFechaHora, formatearMoneda } from "../utils/formato";

const TAMANO_PAGINA = 20;

const TIPOS_SALIDA = new Set(["salida", "merma"]);

/**
 * Calcula la cantidad con signo que espera el backend a partir de una
 * magnitud positiva ingresada por el usuario y el tipo de ajuste elegido.
 *
 * ENTRADA siempre suma, SALIDA/MERMA siempre restan; solo CORRECCION
 * necesita que el usuario elija la direccion (puede corregir hacia
 * arriba o hacia abajo).
 *
 * @param {string} tipo - Tipo de ajuste (entrada/salida/merma/correccion).
 * @param {number} magnitud - Cantidad positiva ingresada por el usuario.
 * @param {"+"|"-"} signoCorreccion - Direccion elegida, solo para CORRECCION.
 * @returns {number} La cantidad con signo a enviar al backend.
 */
function calcularCantidadConSigno(tipo, magnitud, signoCorreccion) {
  if (tipo === "entrada") return magnitud;
  if (TIPOS_SALIDA.has(tipo)) return -magnitud;
  return signoCorreccion === "+" ? magnitud : -magnitud;
}

/**
 * Formulario para registrar un ajuste manual de inventario (RF-009).
 *
 * @param {{productoId: number, alRegistrar: (producto: object) => void}} props
 * @returns {JSX.Element}
 */
function FormularioAjuste({ productoId, alRegistrar }) {
  const { token } = useAuth();
  const [tipo, setTipo] = useState("entrada");
  const [magnitud, setMagnitud] = useState("");
  const [signoCorreccion, setSignoCorreccion] = useState("+");
  const [motivo, setMotivo] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [mensaje, setMensaje] = useState(null);

  /**
   * Envia el ajuste al backend y limpia el formulario si sale bien.
   *
   * @param {React.FormEvent} evento
   * @returns {Promise<void>}
   */
  async function enviar(evento) {
    evento.preventDefault();
    const magnitudNumerica = Number(magnitud);
    if (!magnitudNumerica || magnitudNumerica <= 0) {
      setMensaje({ tipo: "error", texto: "La cantidad debe ser mayor a cero." });
      return;
    }

    setEnviando(true);
    setMensaje(null);
    try {
      await registrarAjusteInventario(
        productoId,
        {
          tipo,
          cantidad: calcularCantidadConSigno(tipo, magnitudNumerica, signoCorreccion),
          motivo,
        },
        token
      );
      setMensaje({ tipo: "ok", texto: "Ajuste registrado." });
      setMagnitud("");
      setMotivo("");
      alRegistrar();
    } catch (error) {
      setMensaje({ tipo: "error", texto: error.message || "No se pudo registrar el ajuste." });
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={enviar} className="mt-3 space-y-2.5 rounded-2xl border border-tinta/10 bg-papel p-3.5">
      <p className="text-sm font-semibold text-tinta/70">Registrar ajuste manual</p>
      <div className="grid gap-2.5 sm:grid-cols-2">
        <label className="text-sm">
          <span className="mb-1 block font-medium text-tinta/70">Tipo</span>
          <Desplegable
            value={tipo}
            onChange={(evento) => setTipo(evento.target.value)}
            className="w-full rounded-lg border border-tinta/20 bg-white px-3 py-2"
          >
            {Object.entries(ETIQUETA_TIPO_AJUSTE).map(([valor, etiqueta]) => (
              <option key={valor} value={valor}>
                {etiqueta}
              </option>
            ))}
          </Desplegable>
        </label>
        <label className="text-sm">
          <span className="mb-1 block font-medium text-tinta/70">Cantidad</span>
          <div className="flex gap-2">
            {tipo === "correccion" && (
              <Desplegable
                value={signoCorreccion}
                onChange={(evento) => setSignoCorreccion(evento.target.value)}
                className="rounded-lg border border-tinta/20 bg-white px-2 py-2"
                aria-label="Dirección de la corrección"
              >
                <option value="+">Sube (+)</option>
                <option value="-">Baja (−)</option>
              </Desplegable>
            )}
            <input
              type="number"
              min="1"
              step="1"
              value={magnitud}
              onChange={(evento) => setMagnitud(evento.target.value)}
              placeholder="0"
              required
              className="w-full rounded-lg border border-tinta/20 bg-white px-3 py-2"
            />
          </div>
        </label>
      </div>
      <label className="block text-sm">
        <span className="mb-1 block font-medium text-tinta/70">Motivo</span>
        <input
          type="text"
          value={motivo}
          onChange={(evento) => setMotivo(evento.target.value)}
          placeholder="Ej. conteo físico, piñatas dañadas, muestra…"
          required
          maxLength={255}
          className="w-full rounded-lg border border-tinta/20 bg-white px-3 py-2"
        />
      </label>
      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={enviando}
          className="rounded-lg bg-fucsia px-3.5 py-2 text-sm font-semibold text-white transition hover:bg-fucsia-osc disabled:opacity-50"
        >
          {enviando ? "Registrando…" : "Registrar ajuste"}
        </button>
        {mensaje && (
          <span className={`text-sm font-medium ${mensaje.tipo === "error" ? "text-fucsia-osc" : "text-turquesa"}`}>
            {mensaje.texto}
          </span>
        )}
      </div>
    </form>
  );
}

/**
 * Historial de ajustes de un producto, cargado bajo demanda al expandir la fila.
 *
 * @param {{productoId: number, recarga: number}} props - `recarga` cambia para forzar un refetch.
 * @returns {JSX.Element}
 */
function HistorialAjustes({ productoId, recarga }) {
  const { token } = useAuth();
  const [ajustes, setAjustes] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelado = false;
    setError(null);
    obtenerAjustesInventario(productoId, token)
      .then((datos) => {
        if (!cancelado) setAjustes(datos);
      })
      .catch((errorCarga) => {
        if (!cancelado) setError(errorCarga.message || "No se pudo cargar el historial.");
      });
    return () => {
      cancelado = true;
    };
  }, [productoId, token, recarga]);

  if (error) {
    return <p className="mt-3 text-sm text-fucsia-osc">{error}</p>;
  }
  if (ajustes === null) {
    return <p className="mt-3 text-sm text-tinta/50">Cargando historial…</p>;
  }
  if (ajustes.length === 0) {
    return <p className="mt-3 text-sm text-tinta/50">Sin ajustes registrados todavía.</p>;
  }

  return (
    <ul className="mt-3 space-y-1.5">
      {ajustes.map((ajuste) => (
        <li key={ajuste.id} className="flex flex-wrap items-baseline justify-between gap-2 text-sm">
          <span>
            <span className="font-semibold">{ETIQUETA_TIPO_AJUSTE[ajuste.tipo] || ajuste.tipo}</span>{" "}
            <span className={`font-semibold tabular-nums ${ajuste.cantidad < 0 ? "text-fucsia-osc" : "text-turquesa"}`}>
              {ajuste.cantidad > 0 ? `+${ajuste.cantidad}` : ajuste.cantidad}
            </span>{" "}
            — {ajuste.motivo}
          </span>
          <span className="shrink-0 text-xs text-tinta/50">{formatearFechaHora(ajuste.fecha)}</span>
        </li>
      ))}
    </ul>
  );
}

const ETIQUETA_TIPO_COMPUESTO = { paquete: "Paquete", ancheta: "Ancheta" };

/**
 * Casilla "producto compuesto" con el tipo (paquete/ancheta) y el editor de su receta.
 *
 * @param {{
 *   compuesto: boolean, tipo: string, receta: Array<object>, excluirId?: number,
 *   alCambiarCompuesto: (compuesto: boolean) => void, alCambiarTipo: (tipo: string) => void,
 *   alCambiarReceta: (receta: Array<object>) => void
 * }} props
 * @returns {JSX.Element}
 */
function SeccionCompuesto({ compuesto, tipo, receta, excluirId, alCambiarCompuesto, alCambiarTipo, alCambiarReceta }) {
  return (
    <div className="space-y-2.5">
      <div className="flex flex-wrap items-center gap-4 text-sm">
        <label className="flex items-center gap-2 font-medium">
          <input type="checkbox" checked={compuesto} onChange={(evento) => alCambiarCompuesto(evento.target.checked)} />
          Producto compuesto (se arma con otros artículos)
        </label>
        {compuesto && (
          <label className="flex items-center gap-2">
            <span className="font-medium text-tinta/70">Tipo de compuesto</span>
            <Desplegable
              value={tipo}
              onChange={(evento) => alCambiarTipo(evento.target.value)}
              className="rounded-lg border border-tinta/20 bg-white px-3 py-1.5"
            >
              {Object.entries(ETIQUETA_TIPO_COMPUESTO).map(([valor, etiqueta]) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </Desplegable>
          </label>
        )}
      </div>
      {compuesto && <EditorReceta receta={receta} alCambiar={alCambiarReceta} excluirId={excluirId} />}
    </div>
  );
}

/**
 * Formulario para editar los datos generales de un producto (RF-016).
 *
 * @param {{producto: object, alGuardar: (producto: object) => void, alCancelar: () => void}} props
 * @returns {JSX.Element}
 */
function FormularioEditarProducto({ producto, alGuardar, alCancelar }) {
  const { token } = useAuth();
  const [categorias, setCategorias] = useState([]);
  const [valores, setValores] = useState({
    nombre: producto.nombre,
    descripcion: producto.descripcion ?? "",
    categoriaId: String(producto.categoria_id),
    codigoBarras: producto.codigo_barras ?? "",
    precioVenta: String(Number(producto.precio_venta)),
  });
  const [compuesto, setCompuesto] = useState(producto.tipo !== "unidad");
  const [tipoCompuesto, setTipoCompuesto] = useState(producto.tipo === "unidad" ? "ancheta" : producto.tipo);
  const [receta, setReceta] = useState(recetaDesdeProducto(producto.componentes));
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelado = false;
    obtenerCategorias(token)
      .then((datos) => !cancelado && setCategorias(datos))
      .catch(() => {});
    return () => {
      cancelado = true;
    };
  }, [token]);

  const cambiar = (campo) => (evento) => setValores((actual) => ({ ...actual, [campo]: evento.target.value }));

  /**
   * Envia los cambios; descripcion y codigo vacios se mandan como null.
   *
   * @param {React.FormEvent} evento
   * @returns {Promise<void>}
   */
  async function enviar(evento) {
    evento.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      const cambios = {
        nombre: valores.nombre.trim(),
        descripcion: valores.descripcion.trim() || null,
        categoria_id: Number(valores.categoriaId),
        codigo_barras: valores.codigoBarras.trim() || null,
        precio_venta: Number(valores.precioVenta),
      };
      if (compuesto) {
        cambios.tipo = tipoCompuesto;
        cambios.componentes = recetaParaApi(receta);
      } else if (producto.tipo !== "unidad") {
        cambios.tipo = "unidad";
        cambios.componentes = [];
      }
      const actualizado = await editarProducto(producto.id, cambios, token);
      alGuardar(actualizado);
    } catch (falla) {
      setError(falla.message || "No se pudo guardar el producto.");
    } finally {
      setEnviando(false);
    }
  }

  const clase = "w-full rounded-lg border border-tinta/20 bg-white px-3 py-2";
  return (
    <form onSubmit={enviar} className="mb-4 space-y-3 rounded-xl border border-tinta/10 bg-papel/50 p-3">
      <div className="grid gap-2.5 sm:grid-cols-2">
        <label className="text-sm">
          <span className="mb-1 block font-medium text-tinta/70">Nombre del producto</span>
          <input value={valores.nombre} onChange={cambiar("nombre")} required maxLength={150} className={clase} />
        </label>
        <label className="text-sm">
          <span className="mb-1 block font-medium text-tinta/70">Categoría del producto</span>
          <Desplegable value={valores.categoriaId} onChange={cambiar("categoriaId")} required className={clase}>
            {categorias.map((categoria) => (
              <option key={categoria.id} value={categoria.id}>
                {categoria.nombre}
              </option>
            ))}
          </Desplegable>
        </label>
        <label className="text-sm">
          <span className="mb-1 block font-medium text-tinta/70">Precio de venta</span>
          <input type="number" min="0" step="1" value={valores.precioVenta} onChange={cambiar("precioVenta")} required className={clase} />
        </label>
        <label className="text-sm">
          <span className="mb-1 block font-medium text-tinta/70">Código de barras</span>
          <input value={valores.codigoBarras} onChange={cambiar("codigoBarras")} maxLength={50} className={clase} />
        </label>
        <label className="text-sm sm:col-span-2">
          <span className="mb-1 block font-medium text-tinta/70">Descripción</span>
          <input value={valores.descripcion} onChange={cambiar("descripcion")} maxLength={255} className={clase} />
        </label>
      </div>
      <SeccionCompuesto
        compuesto={compuesto}
        tipo={tipoCompuesto}
        receta={receta}
        excluirId={producto.id}
        alCambiarCompuesto={setCompuesto}
        alCambiarTipo={setTipoCompuesto}
        alCambiarReceta={setReceta}
      />
      {error && (
        <p role="alert" className="text-sm font-medium text-fucsia-osc">
          {error}
        </p>
      )}
      <div className="flex gap-2">
        <button type="submit" disabled={enviando} className="rounded-lg bg-fucsia px-3 py-1.5 text-sm font-bold text-white disabled:opacity-50">
          {enviando ? "Guardando…" : "Guardar cambios"}
        </button>
        <button type="button" onClick={alCancelar} className="rounded-lg border border-tinta/20 px-3 py-1.5 text-sm font-semibold hover:bg-papel">
          Cancelar
        </button>
      </div>
    </form>
  );
}

/**
 * Una fila del catalogo: resumen siempre visible, detalle desplegable con
 * edicion de stock minimo (solo administrador), registro de ajustes y su historial.
 *
 * @param {{producto: object, esAdministrador: boolean, alActualizarProducto: (producto: object) => void}} props
 * @returns {JSX.Element}
 */
function FilaProducto({ producto, esAdministrador, alActualizarProducto }) {
  const { token } = useAuth();
  const { confirmar, dialogo } = useConfirmar();
  const [abierta, setAbierta] = useState(false);
  const [recargaHistorial, setRecargaHistorial] = useState(0);
  const [stockMinimoEditado, setStockMinimoEditado] = useState(String(producto.stock_minimo));
  const [guardandoStockMinimo, setGuardandoStockMinimo] = useState(false);
  const [mensajeStockMinimo, setMensajeStockMinimo] = useState(null);
  const [editando, setEditando] = useState(false);
  const [errorEstado, setErrorEstado] = useState(null);

  const stockBajo = producto.stock_actual <= producto.stock_minimo;

  /**
   * Guarda el nuevo stock minimo del producto.
   *
   * @param {React.FormEvent} evento
   * @returns {Promise<void>}
   */
  async function guardarStockMinimo(evento) {
    evento.preventDefault();
    setGuardandoStockMinimo(true);
    setMensajeStockMinimo(null);
    try {
      const actualizado = await actualizarStockMinimo(producto.id, Number(stockMinimoEditado), token);
      alActualizarProducto(actualizado);
      setMensajeStockMinimo({ tipo: "ok", texto: "Guardado." });
    } catch (error) {
      setMensajeStockMinimo({ tipo: "error", texto: error.message || "No se pudo guardar." });
    } finally {
      setGuardandoStockMinimo(false);
    }
  }

  /**
   * Desactiva o reactiva el producto tras confirmar; recarga la lista porque cambia de filtro.
   *
   * @returns {Promise<void>}
   */
  async function alternarActivo() {
    const accion = producto.activo ? "desactivar" : "reactivar";
    setErrorEstado(null);
    let aviso = "";
    if (producto.activo) {
      try {
        const compuestos = await obtenerProductosQueLoUsan(producto.id, token);
        if (compuestos.length > 0) {
          const nombres = compuestos.map((compuesto) => compuesto.nombre).join(", ");
          aviso =
            `Este producto es parte de: ${nombres}. ` +
            "Seguirá en esas recetas y su stock se seguirá descontando al armarlas.";
        }
      } catch {
        // Si no se pudo consultar, se confirma sin el aviso.
      }
    }
    const acepta = await confirmar({
      titulo: `¿Quieres ${accion} ${producto.nombre}?`,
      mensaje: producto.activo
        ? "Dejará de aparecer en el POS y en el catálogo por defecto."
        : "Volverá a estar disponible para la venta.",
      aviso,
      textoConfirmar: producto.activo ? "Desactivar" : "Reactivar",
      peligro: producto.activo,
    });
    if (!acepta) return;
    try {
      await (producto.activo ? desactivarProducto(producto.id, token) : reactivarProducto(producto.id, token));
      alActualizarProducto(null);
    } catch (falla) {
      setErrorEstado(falla.message || "No se pudo cambiar el estado del producto.");
    }
  }

  return (
    <li className="rounded-2xl border border-tinta/10 bg-white">
      {dialogo}
      <button
        type="button"
        onClick={() => setAbierta((valor) => !valor)}
        aria-expanded={abierta}
        className="flex w-full flex-wrap items-center gap-3 p-4 text-left"
      >
        <span className="font-display text-lg font-extrabold">{producto.nombre}</span>
        <span className="rounded-full bg-cielo/12 px-2.5 py-0.5 text-xs font-semibold text-cielo">
          {producto.categoria_nombre}
        </span>
        {stockBajo && (
          <span className="rounded-full bg-fucsia/15 px-2.5 py-0.5 text-xs font-bold text-fucsia-osc">
            Stock bajo
          </span>
        )}
        {ETIQUETA_TIPO_COMPUESTO[producto.tipo] && (
          <span className="rounded-full bg-turquesa/15 px-2.5 py-0.5 text-xs font-bold text-turquesa">
            {ETIQUETA_TIPO_COMPUESTO[producto.tipo]}
          </span>
        )}
        {!producto.activo && (
          <span className="rounded-full bg-tinta/10 px-2.5 py-0.5 text-xs font-semibold text-tinta/60">Inactivo</span>
        )}
        <span className="ml-auto flex items-center gap-4 text-sm">
          <span className="tabular-nums text-tinta/60">
            Stock: <strong className="text-tinta">{producto.stock_actual}</strong> / mín. {producto.stock_minimo}
          </span>
          <span className="font-display text-lg font-extrabold tabular-nums">{formatearMoneda(producto.precio_venta)}</span>
        </span>
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          className={`h-5 w-5 shrink-0 text-tinta/45 transition-transform ${abierta ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          strokeWidth="2.4"
          strokeLinecap="round"
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>

      {abierta && (
        <div className="border-t border-dashed border-tinta/20 px-4 pb-4 pt-3.5">
          <ComposicionProducto componentes={producto.componentes} />
          {esAdministrador && (
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => setEditando((valor) => !valor)}
                className="rounded-lg border border-tinta/20 px-3 py-1.5 text-sm font-semibold hover:bg-papel"
              >
                {editando ? "Cerrar edición" : "Editar datos"}
              </button>
              <button
                type="button"
                onClick={alternarActivo}
                className="rounded-lg border border-fucsia/40 px-3 py-1.5 text-sm font-semibold text-fucsia-osc hover:bg-fucsia/10"
              >
                {producto.activo ? "Desactivar producto" : "Reactivar producto"}
              </button>
              {errorEstado && (
                <span role="alert" className="text-sm font-medium text-fucsia-osc">
                  {errorEstado}
                </span>
              )}
            </div>
          )}
          {esAdministrador && editando && (
            <FormularioEditarProducto
              producto={producto}
              alGuardar={(actualizado) => {
                alActualizarProducto(actualizado);
                setEditando(false);
              }}
              alCancelar={() => setEditando(false)}
            />
          )}
          {esAdministrador && (
            <form onSubmit={guardarStockMinimo} className="flex flex-wrap items-center gap-2.5">
              <label className="text-sm">
                <span className="mr-2 font-medium text-tinta/70">Stock mínimo</span>
                <input
                  type="number"
                  min="0"
                  step="1"
                  value={stockMinimoEditado}
                  onChange={(evento) => setStockMinimoEditado(evento.target.value)}
                  className="w-24 rounded-lg border border-tinta/20 px-3 py-1.5"
                />
              </label>
              <button
                type="submit"
                disabled={guardandoStockMinimo}
                className="rounded-lg border border-tinta px-3 py-1.5 text-sm font-semibold transition hover:bg-papel disabled:opacity-50"
              >
                {guardandoStockMinimo ? "Guardando…" : "Guardar"}
              </button>
              {mensajeStockMinimo && (
                <span
                  className={`text-sm font-medium ${
                    mensajeStockMinimo.tipo === "error" ? "text-fucsia-osc" : "text-turquesa"
                  }`}
                >
                  {mensajeStockMinimo.texto}
                </span>
              )}
            </form>
          )}

          <FormularioAjuste
            productoId={producto.id}
            alRegistrar={() => {
              alActualizarProducto(null);
              setRecargaHistorial((valor) => valor + 1);
            }}
          />

          <p className="mt-4 text-sm font-semibold text-tinta/70">Historial de ajustes</p>
          <HistorialAjustes productoId={producto.id} recarga={recargaHistorial} />
        </div>
      )}
    </li>
  );
}

const VALORES_INICIALES_ALTA = {
  nombre: "",
  categoriaId: "",
  codigoBarras: "",
  precioVenta: "",
  stockInicial: "",
};

const TIPO_COMPUESTO_INICIAL = "ancheta";

/**
 * Formulario de alta de un producto nuevo (HU-02, RF-016). Solo administrador.
 *
 * `codigo_barras` es opcional (HU-02: anchetas, mermas o mercancia
 * artesanal sin etiqueta de fabrica).
 *
 * @param {{alCrear: (producto: object) => void, alCancelar: () => void}} props
 * @returns {JSX.Element}
 */
function FormularioAltaProducto({ alCrear, alCancelar }) {
  const { token } = useAuth();
  const [categorias, setCategorias] = useState(null);
  const [valores, setValores] = useState(VALORES_INICIALES_ALTA);
  const [compuesto, setCompuesto] = useState(false);
  const [tipoCompuesto, setTipoCompuesto] = useState(TIPO_COMPUESTO_INICIAL);
  const [receta, setReceta] = useState([]);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelado = false;
    obtenerCategorias(token)
      .then((datos) => {
        if (!cancelado) setCategorias(datos);
      })
      .catch(() => {
        if (!cancelado) setCategorias([]);
      });
    return () => {
      cancelado = true;
    };
  }, [token]);

  /**
   * Actualiza un campo del formulario por su nombre.
   *
   * @param {string} campo
   * @returns {(evento: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => void}
   */
  function cambiar(campo) {
    return (evento) => setValores((actual) => ({ ...actual, [campo]: evento.target.value }));
  }

  /**
   * Envia el alta del producto.
   *
   * @param {React.FormEvent} evento
   * @returns {Promise<void>}
   */
  async function enviar(evento) {
    evento.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      const producto = await crearProducto(
        {
          nombre: valores.nombre,
          categoria_id: Number(valores.categoriaId),
          codigo_barras: valores.codigoBarras.trim() ? valores.codigoBarras.trim() : null,
          precio_venta: Number(valores.precioVenta),
          stock_inicial: Number(valores.stockInicial),
          ...(compuesto ? { tipo: tipoCompuesto, componentes: recetaParaApi(receta) } : {}),
        },
        token
      );
      alCrear(producto);
    } catch (errorCreacion) {
      setError(errorCreacion.message || "No se pudo crear el producto.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={enviar} className="mt-4 space-y-3 rounded-2xl border border-tinta/10 bg-white p-4">
      <p className="font-display text-lg font-extrabold">Nuevo producto</p>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-sm">
          <span className="mb-1 block font-medium text-tinta/70">Nombre</span>
          <input
            type="text"
            value={valores.nombre}
            onChange={cambiar("nombre")}
            required
            maxLength={150}
            className="w-full rounded-lg border border-tinta/20 px-3 py-2"
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block font-medium text-tinta/70">Categoría</span>
          <Desplegable
            value={valores.categoriaId}
            onChange={cambiar("categoriaId")}
            required
            className="w-full rounded-lg border border-tinta/20 bg-white px-3 py-2"
          >
            <option value="" disabled>
              Selecciona una categoría…
            </option>
            {(categorias || []).map((categoria) => (
              <option key={categoria.id} value={categoria.id}>
                {categoria.nombre}
              </option>
            ))}
          </Desplegable>
        </label>
        <label className="text-sm">
          <span className="mb-1 block font-medium text-tinta/70">Código de barras (opcional)</span>
          <input
            type="text"
            value={valores.codigoBarras}
            onChange={cambiar("codigoBarras")}
            placeholder="Vacío si no tiene etiqueta de fábrica"
            maxLength={50}
            className="w-full rounded-lg border border-tinta/20 px-3 py-2"
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block font-medium text-tinta/70">Precio de venta</span>
          <input
            type="number"
            min="0"
            step="1"
            value={valores.precioVenta}
            onChange={cambiar("precioVenta")}
            required
            className="w-full rounded-lg border border-tinta/20 px-3 py-2"
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block font-medium text-tinta/70">Stock inicial</span>
          <input
            type="number"
            min="0"
            step="1"
            value={valores.stockInicial}
            onChange={cambiar("stockInicial")}
            required
            className="w-full rounded-lg border border-tinta/20 px-3 py-2"
          />
        </label>
      </div>
      <SeccionCompuesto
        compuesto={compuesto}
        tipo={tipoCompuesto}
        receta={receta}
        alCambiarCompuesto={setCompuesto}
        alCambiarTipo={setTipoCompuesto}
        alCambiarReceta={setReceta}
      />
      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={enviando || categorias === null}
          className="rounded-lg bg-fucsia px-3.5 py-2 text-sm font-semibold text-white transition hover:bg-fucsia-osc disabled:opacity-50"
        >
          {enviando ? "Creando…" : "Crear producto"}
        </button>
        <button
          type="button"
          onClick={alCancelar}
          className="rounded-lg border border-tinta/20 px-3.5 py-2 text-sm font-semibold transition hover:bg-papel"
        >
          Cancelar
        </button>
        {error && <span className="text-sm font-medium text-fucsia-osc">{error}</span>}
      </div>
    </form>
  );
}

/**
 * Pantalla de Inventario: catalogo con filtro y paginacion, edicion de stock
 * minimo (RF-007), alta de productos (HU-02, RF-016) y ajustes manuales con
 * su historial (RF-009).
 *
 * @returns {JSX.Element}
 */
export function Inventario() {
  const { token, usuarioActual } = useAuth();
  const esAdministrador = usuarioActual?.rol === "administrador";

  const [terminoBusqueda, setTerminoBusqueda] = useState("");
  const [filtroAplicado, setFiltroAplicado] = useState("");
  const [pagina, setPagina] = useState(1);
  const [catalogo, setCatalogo] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [mostrarAlta, setMostrarAlta] = useState(false);
  const [verInactivos, setVerInactivos] = useState(false);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      setCatalogo(await obtenerCatalogo(
          { q: filtroAplicado || undefined, pagina, tamanoPagina: TAMANO_PAGINA, activo: !verInactivos },
          token
        ));
    } catch (errorCarga) {
      setError(errorCarga.message || "No se pudo cargar el catálogo.");
    } finally {
      setCargando(false);
    }
  }, [token, filtroAplicado, pagina, verInactivos]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  /**
   * Actualiza (o refresca) un producto puntual dentro de la lista ya cargada,
   * sin recargar todo el catalogo. `null` fuerza una recarga completa (ej.
   * despues de un ajuste, que cambia `stock_actual` pero el backend no
   * devuelve el producto completo en esa respuesta).
   *
   * @param {object | null} productoActualizado
   */
  function actualizarProductoEnLista(productoActualizado) {
    if (productoActualizado === null) {
      cargar();
      return;
    }
    setCatalogo((actual) => ({
      ...actual,
      productos: actual.productos.map((p) => (p.id === productoActualizado.id ? productoActualizado : p)),
    }));
  }

  /**
   * Aplica el termino de busqueda escrito y vuelve a la primera pagina.
   *
   * @param {React.FormEvent} evento
   */
  function buscar(evento) {
    evento.preventDefault();
    setPagina(1);
    setFiltroAplicado(terminoBusqueda.trim());
  }

  if (error) {
    return (
      <div role="alert" className="rounded-2xl border border-fucsia/30 bg-fucsia/8 p-5 text-fucsia-osc">
        <p className="font-medium">{error}</p>
        <button
          type="button"
          onClick={cargar}
          className="mt-3 rounded-lg border border-tinta bg-white px-3 py-1.5 text-sm font-semibold text-tinta"
        >
          Reintentar
        </button>
      </div>
    );
  }

  return (
    <section>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 className="font-display text-2xl font-extrabold">Inventario</h2>
        <div className="flex flex-wrap gap-2">
          <form onSubmit={buscar} className="flex gap-2">
            <input
              type="search"
              value={terminoBusqueda}
              onChange={(evento) => setTerminoBusqueda(evento.target.value)}
              placeholder="Buscar por nombre…"
              className="w-56 rounded-xl border border-tinta/20 bg-white px-3.5 py-2 text-sm"
            />
            <button
              type="submit"
              className="rounded-xl border border-tinta/20 px-3.5 py-2 text-sm font-semibold transition hover:border-tinta hover:bg-papel"
            >
              Buscar
            </button>
          </form>
          {esAdministrador && (
            <Desplegable
              aria-label="Estado de los productos"
              value={verInactivos ? "inactivos" : "activos"}
              onChange={(evento) => {
                setVerInactivos(evento.target.value === "inactivos");
                setPagina(1);
              }}
              className="rounded-xl border border-tinta/20 bg-white px-3 py-2 text-sm font-semibold"
            >
              <option value="activos">Activos</option>
              <option value="inactivos">Inactivos</option>
            </Desplegable>
          )}
          {esAdministrador && (
            <button
              type="button"
              onClick={() => setMostrarAlta((valor) => !valor)}
              className="rounded-xl bg-fucsia px-3.5 py-2 text-sm font-semibold text-white transition hover:bg-fucsia-osc"
            >
              {mostrarAlta ? "Cancelar" : "+ Nuevo producto"}
            </button>
          )}
        </div>
      </div>

      {mostrarAlta && esAdministrador && (
        <FormularioAltaProducto
          alCancelar={() => setMostrarAlta(false)}
          alCrear={() => {
            setMostrarAlta(false);
            setPagina(1);
            cargar();
          }}
        />
      )}

      {!catalogo ? (
        <p className="mt-6 text-tinta/60">{cargando ? "Cargando catálogo…" : ""}</p>
      ) : catalogo.productos.length === 0 ? (
        <p className="mt-6 rounded-2xl border border-dashed border-tinta/25 p-8 text-center text-tinta/60">
          No se encontraron productos.
        </p>
      ) : (
        <>
          <ul className="mt-5 space-y-2.5">
            {catalogo.productos.map((producto) => (
              <FilaProducto
                key={producto.id}
                producto={producto}
                esAdministrador={esAdministrador}
                alActualizarProducto={actualizarProductoEnLista}
              />
            ))}
          </ul>

          <div className="mt-4 flex items-center justify-between text-sm text-tinta/60">
            <span>
              Página {pagina} — {catalogo.total} {catalogo.total === 1 ? "producto" : "productos"} en total
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setPagina((valor) => Math.max(1, valor - 1))}
                disabled={pagina <= 1 || cargando}
                className="rounded-lg border border-tinta/20 px-3 py-1.5 font-semibold transition hover:border-tinta hover:bg-papel disabled:opacity-40"
              >
                Anterior
              </button>
              <button
                type="button"
                onClick={() => setPagina((valor) => valor + 1)}
                disabled={pagina * TAMANO_PAGINA >= catalogo.total || cargando}
                className="rounded-lg border border-tinta/20 px-3 py-1.5 font-semibold transition hover:border-tinta hover:bg-papel disabled:opacity-40"
              >
                Siguiente
              </button>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
