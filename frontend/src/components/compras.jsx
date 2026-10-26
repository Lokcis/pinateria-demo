import { useCallback, useEffect, useState } from "react";
import {
  cancelarCompra,
  crearCompra,
  obtenerCatalogo,
  obtenerCompras,
  obtenerProveedores,
  recibirCompra,
} from "../api/api-client";
import { Desplegable } from "./desplegable";
import { useAuth } from "../context/auth-context";
import {
  ETIQUETA_ESTADO_COMPRA,
  ETIQUETA_METODO_PAGO,
  ETIQUETA_PLATAFORMA,
  describirPago,
  esMultiploDe50,
  formatearFechaHora,
  formatearMoneda,
  redondearA50,
} from "../utils/formato";

const LINEA_VACIA = { productoId: "", cantidad: "", costo: "" };

/**
 * Formulario para registrar una orden de compra con varias lineas (RF-010).
 *
 * @param {{proveedores: Array<object>, alCrear: () => void, alCancelar: () => void}} props
 * @returns {JSX.Element}
 */
function FormularioCompra({ proveedores, alCrear, alCancelar }) {
  const { token } = useAuth();
  const [productos, setProductos] = useState([]);
  const [proveedorId, setProveedorId] = useState("");
  const [lineas, setLineas] = useState([{ ...LINEA_VACIA }]);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelado = false;
    obtenerCatalogo({ tamanoPagina: 100 }, token)
      .then((datos) => {
        if (!cancelado) setProductos(datos.productos);
      })
      .catch(() => {
        if (!cancelado) setError("No se pudo cargar el catálogo de productos.");
      });
    return () => {
      cancelado = true;
    };
  }, [token]);

  /**
   * Actualiza un campo de una linea del formulario.
   *
   * @param {number} indice - Posicion de la linea.
   * @param {string} campo - Campo a cambiar.
   * @param {string} valor - Nuevo valor.
   */
  function cambiarLinea(indice, campo, valor) {
    setLineas((actuales) => actuales.map((linea, i) => (i === indice ? { ...linea, [campo]: valor } : linea)));
  }

  const total = lineas.reduce((suma, linea) => suma + Number(linea.cantidad || 0) * Number(linea.costo || 0), 0);

  const hayRedondeo = total > 0 && !esMultiploDe50(total);

  /**
   * Envia la orden al backend.
   *
   * @param {React.FormEvent} evento
   * @returns {Promise<void>}
   */
  async function enviar(evento) {
    evento.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      await crearCompra(
        {
          proveedor_id: Number(proveedorId),
          detalles: lineas.map((linea) => ({
            producto_id: Number(linea.productoId),
            cantidad: Number(linea.cantidad),
            costo_unitario: Number(linea.costo),
          })),
        },
        token
      );
      alCrear();
    } catch (falla) {
      setError(falla.message || "No se pudo registrar la compra.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={enviar} className="space-y-3 rounded-2xl border border-tinta/10 bg-white p-4 shadow-sm">
      <h3 className="font-display text-lg font-extrabold">Nueva orden de compra</h3>
      <label className="block text-sm">
        <span className="mb-1 block font-medium text-tinta/70">Proveedor</span>
        <Desplegable
          value={proveedorId}
          onChange={(evento) => setProveedorId(evento.target.value)}
          required
          className="w-full rounded-lg border border-tinta/20 bg-white px-3 py-2"
        >
          <option value="">Selecciona…</option>
          {proveedores.map((proveedor) => (
            <option key={proveedor.id} value={proveedor.id}>
              {proveedor.nombre_empresa}
            </option>
          ))}
        </Desplegable>
      </label>

      {lineas.map((linea, indice) => (
        <div key={indice} className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_6rem_8rem_auto]">
          <Desplegable
            value={linea.productoId}
            onChange={(evento) => cambiarLinea(indice, "productoId", evento.target.value)}
            required
            aria-label={`Producto de la línea ${indice + 1}`}
            className="rounded-lg border border-tinta/20 bg-white px-3 py-2 text-sm"
          >
            <option value="">Producto…</option>
            {productos.map((producto) => (
              <option key={producto.id} value={producto.id}>
                {producto.nombre}
              </option>
            ))}
          </Desplegable>
          <input
            type="number"
            min="1"
            step="1"
            value={linea.cantidad}
            onChange={(evento) => cambiarLinea(indice, "cantidad", evento.target.value)}
            required
            placeholder="Cant."
            aria-label={`Cantidad de la línea ${indice + 1}`}
            className="rounded-lg border border-tinta/20 px-3 py-2 text-sm"
          />
          <input
            type="number"
            min="0"
            step="0.01"
            value={linea.costo}
            onChange={(evento) => cambiarLinea(indice, "costo", evento.target.value)}
            required
            placeholder="Costo unit."
            aria-label={`Costo unitario de la línea ${indice + 1}`}
            className="rounded-lg border border-tinta/20 px-3 py-2 text-sm"
          />
          <button
            type="button"
            disabled={lineas.length === 1}
            onClick={() => setLineas((actuales) => actuales.filter((_, i) => i !== indice))}
            aria-label={`Quitar línea ${indice + 1}`}
            className="rounded-lg border border-tinta/20 px-3 py-2 text-sm hover:bg-papel disabled:opacity-40"
          >
            ✕
          </button>
        </div>
      ))}

      <button
        type="button"
        onClick={() => setLineas((actuales) => [...actuales, { ...LINEA_VACIA }])}
        className="text-sm font-semibold text-fucsia-osc"
      >
        + Agregar producto
      </button>

      <p className="text-right text-sm font-bold">
        Total: {formatearMoneda(redondearA50(total))}
        {hayRedondeo && (
          <span className="block text-xs font-normal text-tinta/60">
            Redondeado a $50 (subtotal {formatearMoneda(total)})
          </span>
        )}
      </p>
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
          {enviando ? "Registrando…" : "Registrar orden"}
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
 * Pide como se pago la compra antes de recibirla (Adendo v3, RF-064): con eso la compra entra a la ventana de Gastos
 * y, si fue en efectivo, a la caja.
 *
 * @param {{compra: object, alRecibir: (pago: {metodo_pago: string, plataforma: string | null}) => Promise<void>,
 *   alCancelar: () => void}} props
 * @returns {JSX.Element}
 */
function FormularioRecepcion({ compra, alRecibir, alCancelar }) {
  const [metodoPago, setMetodoPago] = useState("efectivo");
  const [plataforma, setPlataforma] = useState("");
  const [enviando, setEnviando] = useState(false);

  /**
   * Confirma la recepcion con la forma de pago elegida.
   *
   * @param {React.FormEvent} evento
   * @returns {Promise<void>}
   */
  async function enviar(evento) {
    evento.preventDefault();
    setEnviando(true);
    await alRecibir({ metodo_pago: metodoPago, plataforma: metodoPago === "transferencia" ? plataforma : null });
    setEnviando(false);
  }

  return (
    <form onSubmit={enviar} className="mt-3 space-y-2 rounded-xl bg-papel p-3" aria-label={`Recibir la compra ${compra.id}`}>
      <p className="font-semibold">¿Cómo se pagó esta compra?</p>
      <div className="flex flex-wrap gap-2">
        <Desplegable
          value={metodoPago}
          onChange={(evento) => {
            setMetodoPago(evento.target.value);
            if (evento.target.value !== "transferencia") setPlataforma("");
          }}
          aria-label="Forma de pago de la compra"
          className="rounded-lg border border-tinta/20 bg-white px-3 py-2 text-sm"
        >
          {Object.entries(ETIQUETA_METODO_PAGO).map(([valor, etiqueta]) => (
            <option key={valor} value={valor}>
              {etiqueta}
            </option>
          ))}
        </Desplegable>
        {metodoPago === "transferencia" && (
          <Desplegable
            value={plataforma}
            onChange={(evento) => setPlataforma(evento.target.value)}
            required
            aria-label="Plataforma de la transferencia"
            className="rounded-lg border border-tinta/20 bg-white px-3 py-2 text-sm"
          >
            <option value="">Plataforma…</option>
            {Object.entries(ETIQUETA_PLATAFORMA).map(([valor, etiqueta]) => (
              <option key={valor} value={valor}>
                {etiqueta}
              </option>
            ))}
          </Desplegable>
        )}
      </div>
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={enviando}
          className="rounded-lg bg-turquesa px-3 py-1.5 font-semibold text-white disabled:opacity-50"
        >
          Confirmar recepción
        </button>
        <button type="button" onClick={alCancelar} className="rounded-lg border border-tinta/20 px-3 py-1.5 font-semibold hover:bg-papel">
          Volver
        </button>
      </div>
    </form>
  );
}

/**
 * Pantalla de compras a proveedores: ordenes, recepcion de mercancia e historial (RF-010 a RF-012).
 *
 * Solo debe montarse para el rol administrador; el backend responde 403 a los demas.
 *
 * @returns {JSX.Element}
 */
export function Compras() {
  const { token } = useAuth();
  const [compras, setCompras] = useState(null);
  const [proveedores, setProveedores] = useState([]);
  const [filtroProveedor, setFiltroProveedor] = useState("");
  const [filtroEstado, setFiltroEstado] = useState("");
  const [mostrarFormulario, setMostrarFormulario] = useState(false);
  const [recibiendoId, setRecibiendoId] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    obtenerProveedores(undefined, token)
      .then(setProveedores)
      .catch(() => setProveedores([]));
  }, [token]);

  const cargar = useCallback(async () => {
    setError(null);
    try {
      setCompras(
        await obtenerCompras(
          { proveedorId: Number(filtroProveedor) || undefined, estado: filtroEstado || undefined },
          token
        )
      );
    } catch (falla) {
      setError(falla.message || "No se pudo cargar el historial de compras.");
      setCompras([]);
    }
  }, [filtroProveedor, filtroEstado, token]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  /**
   * Recibe o cancela una compra pendiente y recarga la lista.
   *
   * @param {(id: number, token: string) => Promise<object>} accion
   * @param {number} compraId
   * @returns {Promise<void>}
   */
  async function ejecutar(accion, compraId) {
    setError(null);
    try {
      await accion(compraId, token);
      await cargar();
    } catch (falla) {
      setError(falla.message || "No se pudo actualizar la compra.");
    }
  }

  /**
   * Recibe una compra con la forma de pago elegida y recarga la lista.
   *
   * @param {number} compraId
   * @param {{metodo_pago: string, plataforma: string | null}} pago
   * @returns {Promise<void>}
   */
  async function recibir(compraId, pago) {
    setError(null);
    try {
      await recibirCompra(compraId, pago, token);
      setRecibiendoId(null);
      await cargar();
    } catch (falla) {
      setError(falla.message || "No se pudo recibir la compra.");
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-xl font-extrabold">Compras</h2>
        <div className="flex flex-wrap gap-2">
          <Desplegable
            value={filtroProveedor}
            onChange={(evento) => setFiltroProveedor(evento.target.value)}
            aria-label="Filtrar por proveedor"
            className="rounded-lg border border-tinta/20 bg-white px-3 py-2 text-sm"
          >
            <option value="">Todos los proveedores</option>
            {proveedores.map((proveedor) => (
              <option key={proveedor.id} value={proveedor.id}>
                {proveedor.nombre_empresa}
              </option>
            ))}
          </Desplegable>
          <Desplegable
            value={filtroEstado}
            onChange={(evento) => setFiltroEstado(evento.target.value)}
            aria-label="Filtrar por estado"
            className="rounded-lg border border-tinta/20 bg-white px-3 py-2 text-sm"
          >
            <option value="">Todos los estados</option>
            {Object.entries(ETIQUETA_ESTADO_COMPRA).map(([valor, etiqueta]) => (
              <option key={valor} value={valor}>
                {etiqueta}
              </option>
            ))}
          </Desplegable>
          <button
            type="button"
            onClick={() => setMostrarFormulario(true)}
            className="rounded-xl bg-fucsia px-4 py-2 text-sm font-bold text-white"
          >
            Nueva compra
          </button>
        </div>
      </div>

      {mostrarFormulario && (
        <FormularioCompra
          proveedores={proveedores}
          alCrear={() => {
            setMostrarFormulario(false);
            cargar();
          }}
          alCancelar={() => setMostrarFormulario(false)}
        />
      )}

      {error && (
        <p role="alert" className="text-sm font-medium text-fucsia-osc">
          {error}
        </p>
      )}
      {compras === null && <p className="text-tinta/60">Cargando…</p>}
      {compras?.length === 0 && !error && <p className="text-tinta/60">No hay compras registradas.</p>}

      <ul className="space-y-2">
        {compras?.map((compra) => (
          <li key={compra.id} className="rounded-2xl border border-tinta/10 bg-white p-4 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="font-bold">
                  #{compra.id} · {compra.proveedor_nombre}
                </p>
                <p className="text-tinta/60">{formatearFechaHora(compra.fecha)}</p>
                {compra.estado === "recibida" && (
                  <p className="text-tinta/60">
                    {compra.recibida_en ? `Recibida ${formatearFechaHora(compra.recibida_en)} · ` : ""}
                    {compra.metodo_pago ? `Pagada: ${describirPago(compra)}` : "Sin forma de pago registrada"}
                  </p>
                )}
              </div>
              <div className="text-right">
                <p className="font-bold">{formatearMoneda(compra.total)}</p>
                <span className="rounded-full bg-papel-osc px-2.5 py-0.5 text-xs font-bold">
                  {ETIQUETA_ESTADO_COMPRA[compra.estado]}
                </span>
              </div>
            </div>
            <ul className="mt-2 text-tinta/70">
              {compra.detalles.map((detalle) => (
                <li key={detalle.id}>
                  {detalle.cantidad} × {detalle.producto_nombre} ({formatearMoneda(detalle.costo_unitario)})
                </li>
              ))}
            </ul>
            {compra.estado === "pendiente" && recibiendoId === compra.id && (
              <FormularioRecepcion
                compra={compra}
                alRecibir={(pago) => recibir(compra.id, pago)}
                alCancelar={() => setRecibiendoId(null)}
              />
            )}
            {compra.estado === "pendiente" && recibiendoId !== compra.id && (
              <div className="mt-3 flex gap-2">
                <button
                  type="button"
                  onClick={() => setRecibiendoId(compra.id)}
                  className="rounded-lg bg-turquesa px-3 py-1.5 font-semibold text-white"
                >
                  Marcar recibida
                </button>
                <button
                  type="button"
                  onClick={() => ejecutar(cancelarCompra, compra.id)}
                  className="rounded-lg border border-tinta/20 px-3 py-1.5 font-semibold hover:bg-papel"
                >
                  Cancelar
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
