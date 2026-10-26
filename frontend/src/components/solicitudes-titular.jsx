import { useCallback, useEffect, useState } from "react";
import { actualizarSolicitud, obtenerSolicitudes } from "../api/api-client";
import { useAuth } from "../context/auth-context";
import {
  ETIQUETA_ESTADO_SOLICITUD,
  ETIQUETA_TIPO_SOLICITUD,
  formatearDia,
  formatearFechaHora,
} from "../utils/formato";
import { useConfirmar } from "./dialogo-confirmacion";
import { DatosNegocio } from "./datos-negocio";
import { EnlaceAutoregistro } from "./enlace-autoregistro";

/** Explicacion de lo que pasa al resolver cada tipo de solicitud que cambia datos. */
const EFECTO_AL_RESOLVER = {
  supresion: "Se borrarán los datos personales del cliente (nombre, documento, teléfono, correo y descuento). Sus ventas se conservan sin datos que lo identifiquen. No se puede deshacer.",
  revocatoria: "El cliente quedará sin autorización: ya no se podrá asociar a ventas nuevas.",
};

/**
 * Una solicitud de titular con sus acciones: poner en tramite, resolver o rechazar (con la respuesta dada).
 *
 * @param {{solicitud: object, alCambiar: () => void}} props
 * @returns {JSX.Element}
 */
function TarjetaSolicitud({ solicitud, alCambiar }) {
  const { token } = useAuth();
  const { confirmar, dialogo } = useConfirmar();
  const [respondiendo, setRespondiendo] = useState(null); // null | "resuelta" | "rechazada"
  const [respuesta, setRespuesta] = useState("");
  const [error, setError] = useState(null);
  const cerrada = solicitud.estado === "resuelta" || solicitud.estado === "rechazada";

  /**
   * Cambia el estado de la solicitud; resolver una supresion o una revocatoria pide confirmar antes.
   *
   * @param {string} estado - en_tramite, resuelta o rechazada.
   * @returns {Promise<void>}
   */
  async function cambiarEstado(estado) {
    setError(null);
    const efecto = estado === "resuelta" ? EFECTO_AL_RESOLVER[solicitud.tipo] : null;
    if (efecto) {
      const acepta = await confirmar({
        titulo: `¿Resolver la ${ETIQUETA_TIPO_SOLICITUD[solicitud.tipo].toLowerCase()} de ${solicitud.cliente_nombre}?`,
        mensaje: efecto,
        textoConfirmar: "Resolver",
        peligro: true,
      });
      if (!acepta) return;
    }
    try {
      await actualizarSolicitud(solicitud.id, { estado, respuesta: respuesta.trim() || null }, token);
      setRespondiendo(null);
      setRespuesta("");
      alCambiar();
    } catch (falla) {
      setError(falla.message || "No se pudo actualizar la solicitud.");
    }
  }

  return (
    <li className="rounded-2xl border border-tinta/10 bg-white p-4 text-sm">
      {dialogo}
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-bold">
            {ETIQUETA_TIPO_SOLICITUD[solicitud.tipo]} · {solicitud.cliente_nombre}
          </p>
          <p className="text-xs text-tinta/55">
            Recibida {formatearFechaHora(solicitud.recibida_en)} · responder antes del {formatearDia(solicitud.fecha_limite)}
          </p>
        </div>
        <div className="flex flex-wrap gap-1">
          {solicitud.vencida && (
            <span className="rounded-full bg-fucsia/12 px-2 py-0.5 text-xs font-bold text-fucsia-osc">Vencida</span>
          )}
          <span className="rounded-full bg-papel-osc px-2 py-0.5 text-xs font-bold">
            {ETIQUETA_ESTADO_SOLICITUD[solicitud.estado]}
          </span>
        </div>
      </div>
      {solicitud.descripcion && <p className="mt-2 text-tinta/75">{solicitud.descripcion}</p>}
      {cerrada && (
        <p className="mt-2 text-xs text-tinta/60">
          {solicitud.atendida_por && `Atendió ${solicitud.atendida_por}`}
          {solicitud.resuelta_en && ` el ${formatearFechaHora(solicitud.resuelta_en)}`}
          {solicitud.respuesta && ` — “${solicitud.respuesta}”`}
        </p>
      )}

      {!cerrada && respondiendo === null && (
        <div className="mt-3 flex flex-wrap gap-2">
          {solicitud.estado === "recibida" && (
            <button
              type="button"
              onClick={() => cambiarEstado("en_tramite")}
              className="rounded-lg border border-tinta/20 px-3 py-1.5 font-semibold hover:bg-papel"
            >
              Poner en trámite
            </button>
          )}
          <button
            type="button"
            onClick={() => setRespondiendo("resuelta")}
            className="rounded-lg bg-fucsia px-3 py-1.5 font-bold text-white"
          >
            Resolver
          </button>
          <button
            type="button"
            onClick={() => setRespondiendo("rechazada")}
            className="rounded-lg border border-fucsia/40 px-3 py-1.5 font-semibold text-fucsia-osc hover:bg-fucsia/10"
          >
            Rechazar
          </button>
        </div>
      )}

      {!cerrada && respondiendo !== null && (
        <div className="mt-3 space-y-2">
          <label className="block">
            <span className="mb-1 block font-medium text-tinta/70">
              Respuesta dada al titular ({respondiendo === "resuelta" ? "al resolver" : "motivo del rechazo"})
            </span>
            <textarea
              value={respuesta}
              maxLength={500}
              onChange={(evento) => setRespuesta(evento.target.value)}
              rows={2}
              className="w-full rounded-lg border border-tinta/20 px-3 py-2"
            />
          </label>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={!respuesta.trim()}
              onClick={() => cambiarEstado(respondiendo)}
              className="rounded-lg bg-fucsia px-3 py-1.5 font-bold text-white disabled:opacity-50"
            >
              {respondiendo === "resuelta" ? "Confirmar resolución" : "Confirmar rechazo"}
            </button>
            <button
              type="button"
              onClick={() => setRespondiendo(null)}
              className="rounded-lg border border-tinta/20 px-3 py-1.5 font-semibold hover:bg-papel"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      {error && (
        <p role="alert" className="mt-2 font-medium text-fucsia-osc">
          {error}
        </p>
      )}
    </li>
  );
}

/**
 * Solicitudes de los titulares de los datos personales (Habeas Data, Ley 1581 de 2012; HU-07, RF-035).
 *
 * Solo el administrador. Lista primero las mas urgentes (por fecha limite legal) y marca las vencidas.
 * Las solicitudes se registran desde la ficha del cliente.
 *
 * @returns {JSX.Element}
 */
export function SolicitudesTitular() {
  const { token } = useAuth();
  const [soloPendientes, setSoloPendientes] = useState(true);
  const [solicitudes, setSolicitudes] = useState(null);
  const [error, setError] = useState(null);
  const [versionNegocio, setVersionNegocio] = useState(0);

  const cargar = useCallback(async () => {
    setError(null);
    try {
      setSolicitudes(await obtenerSolicitudes({ pendientes: soloPendientes }, token));
    } catch (falla) {
      setError(falla.message || "No se pudo cargar las solicitudes.");
      setSolicitudes([]);
    }
  }, [soloPendientes, token]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-xl font-extrabold">Datos personales</h2>
        <label className="flex items-center gap-2 text-sm font-medium">
          <input
            type="checkbox"
            checked={soloPendientes}
            onChange={(evento) => setSoloPendientes(evento.target.checked)}
          />
          Solo pendientes
        </label>
      </div>
      <DatosNegocio alGuardar={() => setVersionNegocio((v) => v + 1)} />
      <EnlaceAutoregistro key={versionNegocio} />
      <p className="text-sm text-tinta/60">
        Consultas (10 días hábiles) y reclamos de actualización, supresión o revocatoria (15 días hábiles). Se registran
        desde la ficha del cliente.
      </p>

      {error && (
        <p role="alert" className="text-sm font-medium text-fucsia-osc">
          {error}
        </p>
      )}
      {solicitudes === null && <p className="text-tinta/60">Cargando…</p>}
      {solicitudes?.length === 0 && !error && (
        <p className="text-tinta/60">{soloPendientes ? "No hay solicitudes pendientes." : "No hay solicitudes."}</p>
      )}
      <ul className="space-y-2">
        {solicitudes?.map((solicitud) => (
          <TarjetaSolicitud key={solicitud.id} solicitud={solicitud} alCambiar={cargar} />
        ))}
      </ul>
    </section>
  );
}
