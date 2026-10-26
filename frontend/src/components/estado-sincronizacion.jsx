import { useState } from "react";
import { imprimirTicket } from "../api/api-client";
import { useAuth } from "../context/auth-context";
import { useSinConexion } from "../context/sin-conexion-context";
import { ESTADO_CONFLICTO } from "../offline/cola-ventas";
import { describirPago, formatearFechaHora, formatearMoneda } from "../utils/formato";
import { construirTicketLocal } from "../utils/ticket";
import { useConfirmar } from "./dialogo-confirmacion";

/**
 * Dice hace cuanto se guardo el catalogo ("hace 5 min", "hace 2 h").
 *
 * @param {string} guardadoEn - Fecha ISO.
 * @returns {string}
 */
function haceCuanto(guardadoEn) {
  const minutos = Math.max(0, Math.round((Date.now() - new Date(guardadoEn).getTime()) / 60000));
  if (minutos < 1) return "hace un momento";
  if (minutos < 60) return `hace ${minutos} min`;
  const horas = Math.round(minutos / 60);
  return horas < 24 ? `hace ${horas} h` : `hace ${Math.round(horas / 24)} d`;
}

/**
 * Una venta de la cola: resumen, estado y acciones.
 *
 * @param {{venta: object}} props
 * @returns {JSX.Element}
 */
function FilaVentaGuardada({ venta }) {
  const { reintentarVenta, descartarVenta } = useSinConexion();
  const { confirmar, dialogo } = useConfirmar();
  const [aviso, setAviso] = useState(null);
  const enConflicto = venta.estado === ESTADO_CONFLICTO;

  async function reimprimir() {
    setAviso("Imprimiendo…");
    try {
      await imprimirTicket(construirTicketLocal(venta));
      setAviso("Ticket enviado a la impresora.");
    } catch (error) {
      setAviso(`No se pudo imprimir: ${error.message}`);
    }
  }

  async function descartar() {
    const seguro = await confirmar({
      titulo: `¿Descartar la venta ${venta.numeroLocal}?`,
      mensaje: "La venta se borra de este equipo y NO quedará registrada en el sistema.",
      aviso: `Fue por ${formatearMoneda(venta.resumen.total)}. Hazlo solo si ya la registraste a mano o si no se llegó a cobrar.`,
      textoConfirmar: "Descartar venta",
      peligro: true,
    });
    if (seguro) await descartarVenta(venta.uuid);
  }

  return (
    <li className="rounded-2xl border border-tinta/12 bg-white p-3.5 text-sm">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="font-display text-base font-extrabold">{venta.numeroLocal}</span>
        <span className="text-tinta/60">{formatearFechaHora(venta.creadaEn)}</span>
        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${
            enConflicto ? "bg-fucsia/12 text-fucsia-osc" : "bg-sol/30 text-tinta"
          }`}
        >
          {enConflicto ? "Necesita revisión" : "Por enviar"}
        </span>
        <span className="ml-auto font-display text-base font-extrabold tabular-nums">
          {formatearMoneda(venta.resumen.total)}
        </span>
      </div>
      <p className="mt-1 text-tinta/70">
        {venta.resumen.lineas.map((linea) => `${linea.cantidad} × ${linea.nombre}`).join(", ")}
      </p>
      <p className="text-xs text-tinta/55">
        {venta.resumen.pagos.length > 0 ? venta.resumen.pagos.map(describirPago).join(" + ") : "Sin cobro"}
      </p>
      {enConflicto && (
        <p role="alert" className="mt-2 rounded-lg bg-fucsia/8 px-3 py-2 text-xs font-medium text-fucsia-osc">
          El servidor no la aceptó: {venta.mensaje} Corrige eso (por ejemplo, registra el stock que falta) y pulsa
          “Reintentar”.
        </p>
      )}
      <div className="mt-2.5 flex flex-wrap items-center gap-2">
        {enConflicto && (
          <button
            type="button"
            onClick={() => reintentarVenta(venta.uuid)}
            className="rounded-lg border border-tinta bg-white px-3 py-1.5 text-xs font-bold transition hover:bg-papel"
          >
            Reintentar
          </button>
        )}
        <button
          type="button"
          onClick={reimprimir}
          className="rounded-lg border border-tinta/25 bg-white px-3 py-1.5 text-xs font-semibold transition hover:bg-papel"
        >
          Reimprimir ticket
        </button>
        {enConflicto && (
          <button
            type="button"
            onClick={descartar}
            className="rounded-lg px-3 py-1.5 text-xs font-semibold text-fucsia-osc transition hover:bg-fucsia/10"
          >
            Descartar
          </button>
        )}
        {aviso && (
          <span role="status" className="text-xs text-tinta/65">
            {aviso}
          </span>
        )}
      </div>
      {dialogo}
    </li>
  );
}

/**
 * Barra del modo sin conexion (Fase 9): avisa si no hay conexion, cuantas ventas esperan para enviarse, cuales
 * necesitan revision, y deja verlas, reintentarlas, reimprimirlas o descartarlas.
 *
 * No muestra nada cuando todo esta en orden (hay conexion y no hay ventas guardadas).
 *
 * @returns {JSX.Element | null}
 */
export function EstadoSincronizacion() {
  const { cerrarSesion } = useAuth();
  const sc = useSinConexion();
  const [abierta, setAbierta] = useState(false);

  if (!sc.activo) return null;

  // El aviso de "se enviaron" solo tiene sentido con conexion; si vuelve a caer, ya no aplica.
  const ultimoEnvio = sc.enLinea ? sc.ultimoEnvio : null;
  const hayAlgo = !sc.disponible || !sc.enLinea || sc.ventas.length > 0 || sc.sesionVencida || Boolean(ultimoEnvio);
  if (!hayAlgo) return null;

  const catalogo = sc.catalogo;
  const texto = {
    conexion: `Puedes seguir vendiendo: las ventas se guardan en este equipo y se envían solas al volver la red.`,
    catalogo: catalogo
      ? `Catálogo guardado: ${catalogo.cantidad} productos, ${haceCuanto(catalogo.guardadoEn)}.`
      : "Todavía no hay catálogo guardado en este equipo: conéctate una vez para poder buscar productos sin conexión.",
  };

  return (
    <section aria-label="Estado de la conexión" className="mx-auto max-w-[90rem] space-y-2 px-4 pt-3 sm:px-6">
      {!sc.disponible && (
        <p role="alert" className="rounded-2xl border border-sol/60 bg-sol/20 px-4 py-2.5 text-sm font-medium">
          Este navegador no permite guardar datos en el equipo: si se cae internet no se podrá vender. Usa Chrome o Edge
          en el equipo de la tienda.
        </p>
      )}

      {!sc.enLinea && (
        <div role="alert" className="rounded-2xl bg-fucsia px-4 py-3 text-sm text-white">
          <p className="font-extrabold">Sin conexión con el servidor.</p>
          <p className="mt-0.5 font-medium">{texto.conexion}</p>
          <p className="mt-0.5 text-xs font-medium text-white/85">{texto.catalogo}</p>
          <p className="mt-0.5 text-xs font-medium text-white/85">
            No cierres sesión: sin conexión no se puede volver a entrar. Sin conexión no hay clientes, historial ni
            inventario; solo se vende.
          </p>
        </div>
      )}

      {sc.enLinea && sc.sesionVencida && sc.misPendientes > 0 && (
        <div role="alert" className="rounded-2xl border border-fucsia/40 bg-fucsia/8 px-4 py-3 text-sm">
          <p className="font-bold text-fucsia-osc">Tu sesión venció.</p>
          <p className="mt-0.5">
            Hay {sc.misPendientes} {sc.misPendientes === 1 ? "venta guardada" : "ventas guardadas"} sin enviar. Inicia
            sesión de nuevo y se envían solas; no se pierden.
          </p>
          <button
            type="button"
            onClick={cerrarSesion}
            className="mt-2 rounded-lg border border-tinta bg-white px-3 py-1.5 text-xs font-bold transition hover:bg-papel"
          >
            Iniciar sesión de nuevo
          </button>
        </div>
      )}

      {sc.enLinea && !sc.sesionVencida && sc.misPendientes > 0 && (
        <div role="status" className="flex flex-wrap items-center gap-3 rounded-2xl border border-sol/60 bg-sol/20 px-4 py-2.5 text-sm">
          <p className="font-semibold">
            {sc.sincronizando
              ? "Enviando ventas guardadas…"
              : `${sc.misPendientes} ${sc.misPendientes === 1 ? "venta guardada" : "ventas guardadas"} sin conexión por enviar.`}
          </p>
          {!sc.sincronizando && (
            <button
              type="button"
              onClick={sc.sincronizar}
              className="rounded-lg border border-tinta bg-white px-3 py-1 text-xs font-bold transition hover:bg-papel"
            >
              Enviar ahora
            </button>
          )}
        </div>
      )}

      {sc.pendientesDeOtros > 0 && (
        <p role="status" className="rounded-2xl border border-tinta/15 bg-white px-4 py-2.5 text-sm">
          Hay {sc.pendientesDeOtros} {sc.pendientesDeOtros === 1 ? "venta guardada" : "ventas guardadas"} por otra
          persona: se envían cuando ella inicie sesión en este equipo, o si entra un administrador.
        </p>
      )}

      {sc.conflictos > 0 && (
        <p role="alert" className="rounded-2xl border border-fucsia/40 bg-fucsia/8 px-4 py-2.5 text-sm font-semibold text-fucsia-osc">
          {sc.conflictos} {sc.conflictos === 1 ? "venta no se pudo registrar" : "ventas no se pudieron registrar"} y
          necesitan revisión. Ábrelas abajo para ver el motivo.
        </p>
      )}

      {ultimoEnvio && (
        <div role="status" className="flex flex-wrap items-center gap-3 rounded-2xl border border-turquesa/30 bg-turquesa/10 px-4 py-2.5 text-sm font-semibold text-turquesa">
          <p>
            {ultimoEnvio.enviadas > 0
              ? `Se ${ultimoEnvio.enviadas === 1 ? "envió 1 venta guardada" : `enviaron ${ultimoEnvio.enviadas} ventas guardadas`} sin conexión.`
              : "Ninguna venta se pudo registrar."}
            {ultimoEnvio.conflictos > 0 &&
              ` ${ultimoEnvio.conflictos} ${ultimoEnvio.conflictos === 1 ? "necesita" : "necesitan"} revisión.`}
          </p>
          <button
            type="button"
            onClick={sc.descartarAviso}
            className="rounded-lg border border-turquesa/40 bg-white px-3 py-1 text-xs font-bold transition hover:bg-papel"
          >
            Entendido
          </button>
        </div>
      )}

      {sc.ventas.length > 0 && (
        <div>
          <button
            type="button"
            aria-expanded={abierta}
            onClick={() => setAbierta((valor) => !valor)}
            className="text-sm font-bold text-fucsia-osc underline-offset-2 hover:underline"
          >
            {abierta ? "Ocultar ventas guardadas" : `Ver ventas guardadas (${sc.ventas.length})`}
          </button>
          {abierta && (
            <ul aria-label="Ventas guardadas sin conexión" className="mt-2 grid gap-2.5 md:grid-cols-2">
              {sc.ventas.map((venta) => (
                <FilaVentaGuardada key={venta.uuid} venta={venta} />
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}
