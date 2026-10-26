import { useCallback, useEffect, useState } from "react";
import {
  crearSolicitud,
  editarCliente,
  guardarDescuentoCliente,
  obtenerFichaCliente,
} from "../api/api-client";
import { useAuth } from "../context/auth-context";
import {
  ETIQUETA_MEDIO_AUTORIZACION,
  ETIQUETA_TIPO_SOLICITUD,
  describirPago,
  formatearFechaHora,
  formatearMoneda,
} from "../utils/formato";
import { Desplegable } from "./desplegable";
import { FormularioCliente } from "./formulario-cliente";

/**
 * Insignia de estado del cliente (desactivado, autorizacion revocada, anonimizado).
 *
 * @param {{cliente: object}} props
 * @returns {JSX.Element | null}
 */
export function InsigniasCliente({ cliente }) {
  const insignias = [];
  if (cliente.anonimizado_en) insignias.push("Anonimizado");
  else if (cliente.autorizacion_revocada_en) insignias.push("Autorización revocada");
  if (!cliente.activo && !cliente.anonimizado_en) insignias.push("Desactivado");
  if (insignias.length === 0) return null;
  return (
    <span className="flex flex-wrap gap-1">
      {insignias.map((texto) => (
        <span key={texto} className="rounded-full bg-fucsia/12 px-2 py-0.5 text-xs font-bold text-fucsia-osc">
          {texto}
        </span>
      ))}
    </span>
  );
}

/**
 * Asignar o quitar el descuento propio del cliente (solo administrador, RF-025).
 *
 * @param {{cliente: object, alGuardar: (cliente: object) => void}} props
 * @returns {JSX.Element}
 */
function DescuentoPropio({ cliente, alGuardar }) {
  const { token } = useAuth();
  const [tipo, setTipo] = useState(cliente.descuento_tipo ?? "porcentaje");
  const [valor, setValor] = useState(cliente.descuento_valor ? String(Number(cliente.descuento_valor)) : "");
  const [error, setError] = useState(null);
  const [guardando, setGuardando] = useState(false);

  /**
   * Guarda el descuento; con `quitar` lo elimina.
   *
   * @param {boolean} quitar
   * @returns {Promise<void>}
   */
  async function guardar(quitar) {
    setError(null);
    setGuardando(true);
    try {
      const numero = valor.trim().replace(",", ".");
      if (!quitar && !(Number(numero) > 0)) {
        throw new Error("Escriba un valor mayor que cero.");
      }
      const actualizado = await guardarDescuentoCliente(
        cliente.id,
        quitar ? { tipo: null, valor: null } : { tipo, valor: numero },
        token
      );
      if (quitar) setValor("");
      alGuardar(actualizado);
    } catch (falla) {
      setError(falla.message || "No se pudo guardar el descuento.");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <section aria-label="Descuento propio" className="rounded-2xl border border-tinta/10 bg-white p-4">
      <h3 className="font-display text-base font-extrabold">Descuento propio</h3>
      <p className="mt-1 text-xs text-tinta/55">Se sugiere en cada venta de este cliente. Solo lo asigna el administrador.</p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Desplegable
          value={tipo}
          onChange={(evento) => setTipo(evento.target.value)}
          aria-label="Tipo de descuento del cliente"
          className="rounded-lg border border-tinta/20 bg-white px-3 py-1.5 text-sm"
        >
          <option value="porcentaje">Porcentaje (%)</option>
          <option value="monto">Monto ($)</option>
        </Desplegable>
        <input
          type="text"
          inputMode="decimal"
          value={valor}
          onChange={(evento) => setValor(evento.target.value)}
          aria-label="Valor del descuento del cliente"
          className="w-28 rounded-lg border border-tinta/20 px-3 py-1.5 text-right text-sm tabular-nums"
        />
        <button
          type="button"
          disabled={guardando}
          onClick={() => guardar(false)}
          className="rounded-xl bg-fucsia px-3 py-1.5 text-sm font-bold text-white disabled:opacity-50"
        >
          Guardar descuento
        </button>
        {cliente.descuento_tipo && (
          <button
            type="button"
            disabled={guardando}
            onClick={() => guardar(true)}
            className="rounded-xl border border-tinta/20 px-3 py-1.5 text-sm font-semibold hover:bg-papel"
          >
            Quitar descuento
          </button>
        )}
      </div>
      {error && (
        <p role="alert" className="mt-2 text-sm font-medium text-fucsia-osc">
          {error}
        </p>
      )}
    </section>
  );
}

/**
 * Registrar una solicitud del titular de los datos (solo administrador, RF-035); se atiende en "Datos personales".
 *
 * @param {{cliente: object}} props
 * @returns {JSX.Element}
 */
function NuevaSolicitud({ cliente }) {
  const { token } = useAuth();
  const [tipo, setTipo] = useState("consulta");
  const [descripcion, setDescripcion] = useState("");
  const [mensaje, setMensaje] = useState(null);
  const [error, setError] = useState(null);

  /**
   * Registra la solicitud y muestra su fecha limite legal.
   *
   * @param {React.FormEvent} evento
   * @returns {Promise<void>}
   */
  async function registrar(evento) {
    evento.preventDefault();
    setError(null);
    setMensaje(null);
    try {
      const solicitud = await crearSolicitud(
        { cliente_id: cliente.id, tipo, descripcion: descripcion.trim() || null },
        token
      );
      setDescripcion("");
      setMensaje(`Solicitud registrada. Fecha límite de respuesta: ${solicitud.fecha_limite}.`);
    } catch (falla) {
      setError(falla.message || "No se pudo registrar la solicitud.");
    }
  }

  return (
    <form onSubmit={registrar} className="rounded-2xl border border-tinta/10 bg-white p-4" aria-label="Solicitud del titular">
      <h3 className="font-display text-base font-extrabold">Solicitud del titular de los datos</h3>
      <p className="mt-1 text-xs text-tinta/55">
        Consulta, actualización, supresión o revocatoria. Se atienden en la pestaña “Datos personales”.
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Desplegable
          value={tipo}
          onChange={(evento) => setTipo(evento.target.value)}
          aria-label="Tipo de solicitud"
          className="rounded-lg border border-tinta/20 bg-white px-3 py-1.5 text-sm"
        >
          {Object.entries(ETIQUETA_TIPO_SOLICITUD).map(([valor, etiqueta]) => (
            <option key={valor} value={valor}>
              {etiqueta}
            </option>
          ))}
        </Desplegable>
        <input
          type="text"
          value={descripcion}
          maxLength={500}
          onChange={(evento) => setDescripcion(evento.target.value)}
          placeholder="Detalle (opcional)"
          aria-label="Detalle de la solicitud"
          className="min-w-48 flex-1 rounded-lg border border-tinta/20 px-3 py-1.5 text-sm"
        />
        <button type="submit" className="rounded-xl border border-tinta px-3 py-1.5 text-sm font-bold hover:bg-papel">
          Registrar solicitud
        </button>
      </div>
      {mensaje && <p className="mt-2 text-sm font-medium text-turquesa">{mensaje}</p>}
      {error && (
        <p role="alert" className="mt-2 text-sm font-medium text-fucsia-osc">
          {error}
        </p>
      )}
    </form>
  );
}

/**
 * Ficha de un cliente: datos, evidencia de la autorizacion, total comprado e historial de ventas (RF-032).
 *
 * @param {{clienteId: number, alVolver: () => void, alCambiar: () => void}} props `alCambiar` avisa al
 *   listado que el cliente cambio, para que lo recargue.
 * @returns {JSX.Element}
 */
export function FichaCliente({ clienteId, alVolver, alCambiar }) {
  const { token, usuarioActual } = useAuth();
  const esAdministrador = usuarioActual?.rol === "administrador";
  const [ficha, setFicha] = useState(null);
  const [error, setError] = useState(null);
  const [editando, setEditando] = useState(false);

  const cargar = useCallback(async () => {
    try {
      setFicha(await obtenerFichaCliente(clienteId, token));
      setError(null);
    } catch (falla) {
      setError(falla.message || "No se pudo cargar el cliente.");
    }
  }, [clienteId, token]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  /**
   * Recarga la ficha y avisa al listado tras un cambio.
   *
   * @returns {Promise<void>}
   */
  async function huboCambio() {
    await cargar();
    alCambiar();
  }

  /**
   * Da de baja o de alta al cliente.
   *
   * @returns {Promise<void>}
   */
  async function alternarActivo() {
    try {
      await editarCliente(clienteId, { activo: !ficha.activo }, token);
      await huboCambio();
    } catch (falla) {
      setError(falla.message || "No se pudo actualizar el cliente.");
    }
  }

  if (!ficha) {
    return (
      <section className="space-y-3">
        <button type="button" onClick={alVolver} className="text-sm font-semibold text-fucsia-osc">
          ← Volver a clientes
        </button>
        {error ? (
          <p role="alert" className="text-sm font-medium text-fucsia-osc">
            {error}
          </p>
        ) : (
          <p className="text-tinta/60">Cargando…</p>
        )}
      </section>
    );
  }

  const anonimizado = Boolean(ficha.anonimizado_en);

  return (
    <section className="space-y-4">
      <button type="button" onClick={alVolver} className="text-sm font-semibold text-fucsia-osc">
        ← Volver a clientes
      </button>

      <div className="rounded-2xl border border-tinta/10 bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="font-display text-xl font-extrabold">{ficha.nombre}</h2>
            <InsigniasCliente cliente={ficha} />
          </div>
          {!anonimizado && (
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setEditando((valor) => !valor)}
                className="rounded-lg border border-tinta/20 px-3 py-1.5 text-sm font-semibold hover:bg-papel"
              >
                Editar
              </button>
              <button
                type="button"
                onClick={alternarActivo}
                className="rounded-lg border border-tinta/20 px-3 py-1.5 text-sm font-semibold hover:bg-papel"
              >
                {ficha.activo ? "Desactivar" : "Activar"}
              </button>
            </div>
          )}
        </div>
        <dl className="mt-3 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
          <div>
            <dt className="inline text-tinta/55">Documento: </dt>
            <dd className="inline">{ficha.documento || "—"}</dd>
          </div>
          <div>
            <dt className="inline text-tinta/55">Teléfono: </dt>
            <dd className="inline">{ficha.telefono || "—"}</dd>
          </div>
          <div>
            <dt className="inline text-tinta/55">Correo: </dt>
            <dd className="inline">{ficha.email || "—"}</dd>
          </div>
          <div>
            <dt className="inline text-tinta/55">Descuento propio: </dt>
            <dd className="inline">
              {ficha.descuento_tipo
                ? ficha.descuento_tipo === "porcentaje"
                  ? `${Number(ficha.descuento_valor).toLocaleString("es-CO")} %`
                  : formatearMoneda(ficha.descuento_valor)
                : "Ninguno"}
            </dd>
          </div>
        </dl>
        <p className="mt-3 text-xs text-tinta/55">
          Autorización de datos: {formatearFechaHora(ficha.autorizacion_fecha)} · medio{" "}
          {(ETIQUETA_MEDIO_AUTORIZACION[ficha.autorizacion_medio] || ficha.autorizacion_medio).toLowerCase()} · política
          versión {ficha.autorizacion_version}
          {ficha.autorizacion_revocada_en && ` · revocada el ${formatearFechaHora(ficha.autorizacion_revocada_en)}`}
          {ficha.origen_registro === "autoregistro"
            ? " · se registró solo por el enlace"
            : ficha.autorizacion_recogida_por && ` · la recogió ${ficha.autorizacion_recogida_por}`}
        </p>
        <p className="mt-1 text-xs text-tinta/55">
          Promociones:{" "}
          {ficha.acepta_publicidad
            ? `autorizó el ${formatearFechaHora(ficha.publicidad_fecha)}`
            : ficha.publicidad_fecha
              ? `retiró la autorización el ${formatearFechaHora(ficha.publicidad_fecha)}`
              : "no autorizó"}
        </p>
      </div>

      {editando && !anonimizado && (
        <FormularioCliente
          cliente={ficha}
          alGuardar={async () => {
            setEditando(false);
            await huboCambio();
          }}
          alCancelar={() => setEditando(false)}
        />
      )}

      {error && (
        <p role="alert" className="text-sm font-medium text-fucsia-osc">
          {error}
        </p>
      )}

      {esAdministrador && !anonimizado && (
        <>
          <DescuentoPropio key={`${ficha.descuento_tipo}-${ficha.descuento_valor}`} cliente={ficha} alGuardar={huboCambio} />
          <NuevaSolicitud cliente={ficha} />
        </>
      )}

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-2xl border border-tinta/10 bg-white p-4">
          <p className="text-sm font-semibold text-tinta/60">Total comprado</p>
          <p className="mt-1 font-display text-2xl font-extrabold tabular-nums">{formatearMoneda(ficha.total_comprado)}</p>
        </div>
        <div className="rounded-2xl border border-tinta/10 bg-white p-4">
          <p className="text-sm font-semibold text-tinta/60">Ventas</p>
          <p className="mt-1 font-display text-2xl font-extrabold tabular-nums">{ficha.numero_ventas}</p>
          {ficha.ultima_compra && (
            <p className="mt-1 text-xs text-tinta/50">Última: {formatearFechaHora(ficha.ultima_compra)}</p>
          )}
        </div>
      </div>

      <section aria-label="Historial de ventas">
        <h3 className="mb-2 font-display text-base font-extrabold">Historial de ventas</h3>
        {ficha.ventas.length === 0 ? (
          <p className="text-sm text-tinta/60">Este cliente aún no tiene ventas.</p>
        ) : (
          <ul className="space-y-2">
            {ficha.ventas.map((venta) => (
              <li key={venta.id} className="rounded-2xl border border-tinta/10 bg-white p-3 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-semibold">
                    Venta #{venta.id} · {formatearFechaHora(venta.fecha)}
                  </span>
                  <span className="font-bold tabular-nums">{formatearMoneda(venta.total)}</span>
                </div>
                <p className="mt-0.5 text-xs text-tinta/60">
                  Atendió: {venta.vendedor} · {venta.pagos.map((pago) => describirPago(pago)).join(", ") || "Sin pagos"}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}
