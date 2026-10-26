import { useCallback, useEffect, useState } from "react";
import {
  abrirCaja,
  cerrarCaja,
  exportarCortes,
  obtenerCajaActual,
  obtenerCorte,
  obtenerCortes,
  registrarMovimientoCaja,
} from "../api/api-client";
import { useAuth } from "../context/auth-context";
import { useSinConexion } from "../context/sin-conexion-context";
import { useEnLinea } from "../hooks/use-en-linea";
import { descargarArchivo } from "../utils/descarga";
import { esMultiploDe50, formatearFechaHora, formatearMoneda } from "../utils/formato";
import { describirRango, hoyEnBogota, rangoDePreset } from "../utils/rangos";
import { SelectorRango, Tarjeta } from "./dashboard";

/** Cortes que se piden por pagina del historial. */
const TAMANO_PAGINA = 30;

const CLASE_CAMPO = "w-full rounded-lg border border-tinta/20 bg-white px-3 py-2";

/**
 * Dice en palabras la diferencia de un corte (positiva: sobra; negativa: falta).
 *
 * @param {number | string} diferencia - Contado menos esperado.
 * @returns {string}
 */
function describirDiferencia(diferencia) {
  const valor = Number(diferencia);
  if (valor === 0) return "La caja cuadra";
  return valor > 0 ? `Sobran ${formatearMoneda(valor)}` : `Faltan ${formatearMoneda(-valor)}`;
}

/**
 * Valida un monto en efectivo: pesos enteros, multiplo de $50 (igual que las ventas).
 *
 * @param {string} texto - Lo que escribio la persona.
 * @param {{permitirCero?: boolean, nombre: string}} opciones
 * @returns {string | null} Mensaje de error, o null si esta bien.
 */
function validarEfectivo(texto, { permitirCero = false, nombre }) {
  const pesos = Number(texto);
  if (texto.trim() === "" || !Number.isInteger(pesos) || pesos < 0 || (pesos === 0 && !permitirCero)) {
    return `${nombre} va en pesos enteros${permitirCero ? "" : ", mayor que cero"}.`;
  }
  if (!esMultiploDe50(pesos)) return `${nombre} debe ser múltiplo de $50.`;
  return null;
}

/**
 * Una linea del desglose del efectivo esperado.
 *
 * @param {{etiqueta: string, valor: number | string, signo?: "+" | "-"}} props
 * @returns {JSX.Element}
 */
function LineaDesglose({ etiqueta, valor, signo }) {
  return (
    <li className="flex justify-between gap-3">
      <span>
        {signo && <span className="mr-1.5 inline-block w-3 text-center font-bold text-tinta/50">{signo === "-" ? "−" : "+"}</span>}
        {etiqueta}
      </span>
      <span className="font-semibold tabular-nums">{formatearMoneda(valor)}</span>
    </li>
  );
}

/**
 * El efectivo esperado con su desglose y, aparte, lo cobrado por tarjeta y transferencia (solo informativo).
 *
 * @param {{cifras: object}} props Ver `CifrasCajaOut`.
 * @returns {JSX.Element}
 */
function DesgloseDeCifras({ cifras }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <Tarjeta titulo="Cómo se calcula">
        <ul className="space-y-1 text-sm">
          <LineaDesglose etiqueta="Base con que se abrió" valor={cifras.base_inicial} />
          <LineaDesglose etiqueta="Ventas en efectivo" valor={cifras.ventas_efectivo} signo="+" />
          <LineaDesglose etiqueta="Ingresos" valor={cifras.ingresos} signo="+" />
          <LineaDesglose etiqueta="Gastos en efectivo" valor={cifras.gastos_efectivo} signo="-" />
          <LineaDesglose etiqueta="Compras en efectivo" valor={cifras.compras_efectivo} signo="-" />
          <LineaDesglose etiqueta="Retiros" valor={cifras.retiros} signo="-" />
          <li className="flex justify-between gap-3 border-t border-tinta/15 pt-1.5 font-bold">
            <span>Efectivo esperado</span>
            <span className="tabular-nums">{formatearMoneda(cifras.efectivo_esperado)}</span>
          </li>
        </ul>
      </Tarjeta>
      <Tarjeta titulo="Para comparar con el datáfono y el banco">
        <ul className="space-y-1 text-sm">
          <LineaDesglose etiqueta="Ventas con tarjeta" valor={cifras.ventas_tarjeta} />
          <LineaDesglose etiqueta="Ventas por transferencia (Nequi y Daviplata)" valor={cifras.ventas_transferencia} />
        </ul>
        <p className="mt-2 text-xs text-tinta/55">No suman al efectivo de la caja.</p>
      </Tarjeta>
    </div>
  );
}

/**
 * Lista de ingresos y retiros manuales de un corte.
 *
 * @param {{movimientos: Array<object>}} props Ver `MovimientoCajaOut`.
 * @returns {JSX.Element}
 */
function ListaMovimientos({ movimientos }) {
  if (movimientos.length === 0) return <p className="text-sm text-tinta/50">Sin ingresos ni retiros.</p>;
  return (
    <ul className="space-y-1.5 text-sm">
      {movimientos.map((movimiento) => (
        <li key={movimiento.id} className="flex flex-wrap justify-between gap-x-3">
          <span>
            <strong>{movimiento.tipo === "ingreso" ? "Ingreso" : "Retiro"}</strong> · {movimiento.motivo}
            <span className="text-xs text-tinta/55">
              {" "}
              · {movimiento.usuario}, {formatearFechaHora(movimiento.creado_en)}
            </span>
          </span>
          <span className={`font-semibold tabular-nums ${movimiento.tipo === "ingreso" ? "" : "text-fucsia-osc"}`}>
            {movimiento.tipo === "ingreso" ? "+" : "−"}
            {formatearMoneda(movimiento.monto)}
          </span>
        </li>
      ))}
    </ul>
  );
}

/**
 * Formulario para abrir la caja con la base (RF-069).
 *
 * @param {{alAbrir: () => void}} props
 * @returns {JSX.Element}
 */
function FormularioApertura({ alAbrir }) {
  const { token } = useAuth();
  const [base, setBase] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Abre la caja con la base escrita.
   *
   * @param {React.FormEvent} evento
   * @returns {Promise<void>}
   */
  async function enviar(evento) {
    evento.preventDefault();
    const mensaje = validarEfectivo(base, { permitirCero: true, nombre: "La base" });
    if (mensaje) {
      setError(mensaje);
      return;
    }
    setEnviando(true);
    setError(null);
    try {
      await abrirCaja(Number(base), token);
      alAbrir();
    } catch (falla) {
      setError(falla.message || "No se pudo abrir la caja.");
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={enviar} className="space-y-3 rounded-2xl border border-tinta/10 bg-white p-4 shadow-sm">
      <h3 className="font-display text-lg font-extrabold">Abrir la caja</h3>
      <p className="text-sm text-tinta/70">
        Escribe el efectivo con que arranca la caja (la base). El sistema irá sumando las ventas en efectivo y restando los gastos desde ahora.
      </p>
      <label className="block max-w-xs text-sm">
        <span className="mb-1 block font-medium text-tinta/70">Base en efectivo</span>
        <input
          type="number"
          inputMode="numeric"
          min="0"
          step="1"
          value={base}
          onChange={(evento) => setBase(evento.target.value)}
          required
          placeholder="$"
          className={CLASE_CAMPO}
        />
      </label>
      {error && (
        <p role="alert" className="text-sm font-medium text-fucsia-osc">
          {error}
        </p>
      )}
      <button type="submit" disabled={enviando} className="rounded-xl bg-fucsia px-4 py-2 text-sm font-bold text-white disabled:opacity-50">
        {enviando ? "Abriendo…" : "Abrir caja"}
      </button>
    </form>
  );
}

/**
 * Formulario de un ingreso o retiro manual (RF-071).
 *
 * @param {{tipo: "ingreso" | "retiro", alGuardar: () => void, alCancelar: () => void}} props
 * @returns {JSX.Element}
 */
function FormularioMovimiento({ tipo, alGuardar, alCancelar }) {
  const { token } = useAuth();
  const [monto, setMonto] = useState("");
  const [motivo, setMotivo] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);
  const esIngreso = tipo === "ingreso";

  /**
   * Registra el movimiento.
   *
   * @param {React.FormEvent} evento
   * @returns {Promise<void>}
   */
  async function enviar(evento) {
    evento.preventDefault();
    const mensaje = validarEfectivo(monto, { nombre: "El monto" });
    if (mensaje) {
      setError(mensaje);
      return;
    }
    if (motivo.trim().length < 3) {
      setError("Escribe el motivo.");
      return;
    }
    setEnviando(true);
    setError(null);
    try {
      await registrarMovimientoCaja({ tipo, monto: Number(monto), motivo: motivo.trim() }, token);
      alGuardar();
    } catch (falla) {
      setError(falla.message || "No se pudo registrar el movimiento.");
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={enviar} className="space-y-3 rounded-2xl border border-tinta/10 bg-white p-4 shadow-sm">
      <h3 className="font-display text-lg font-extrabold">{esIngreso ? "Ingreso de efectivo" : "Retiro de efectivo"}</h3>
      <div className="grid gap-2.5 sm:grid-cols-2">
        <label className="text-sm">
          <span className="mb-1 block font-medium text-tinta/70">Monto</span>
          <input
            type="number"
            inputMode="numeric"
            min="50"
            step="1"
            value={monto}
            onChange={(evento) => setMonto(evento.target.value)}
            required
            placeholder="$"
            className={CLASE_CAMPO}
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block font-medium text-tinta/70">Motivo</span>
          <input
            value={motivo}
            onChange={(evento) => setMotivo(evento.target.value)}
            required
            maxLength={255}
            placeholder={esIngreso ? "Por ejemplo, cambio para la caja" : "Por ejemplo, consignación al banco"}
            className={CLASE_CAMPO}
          />
        </label>
      </div>
      {error && (
        <p role="alert" className="text-sm font-medium text-fucsia-osc">
          {error}
        </p>
      )}
      <div className="flex gap-2">
        <button type="submit" disabled={enviando} className="rounded-xl bg-fucsia px-4 py-2 text-sm font-bold text-white disabled:opacity-50">
          {enviando ? "Guardando…" : esIngreso ? "Registrar ingreso" : "Registrar retiro"}
        </button>
        <button type="button" onClick={alCancelar} className="rounded-xl border border-tinta/20 px-4 py-2 text-sm font-semibold hover:bg-papel">
          Cancelar
        </button>
      </div>
    </form>
  );
}

/**
 * Formulario del corte: se cuenta el efectivo y se calcula la diferencia con lo esperado (RF-072).
 *
 * El POS no deja cerrar si este equipo tiene ventas guardadas sin enviar: una venta hecha sin conexion que se
 * envie despues del cierre no entra en el corte.
 *
 * @param {{esperado: number | string, ventasSinEnviar: number, alCerrar: (corte: object) => void,
 *   alCancelar: () => void}} props
 * @returns {JSX.Element}
 */
function FormularioCierre({ esperado, ventasSinEnviar, alCerrar, alCancelar }) {
  const { token } = useAuth();
  const [contado, setContado] = useState("");
  const [observaciones, setObservaciones] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);
  const bloqueado = ventasSinEnviar > 0;
  const hayConteo = contado.trim() !== "" && Number.isInteger(Number(contado)) && Number(contado) >= 0;

  /**
   * Cierra la caja con el efectivo contado.
   *
   * @param {React.FormEvent} evento
   * @returns {Promise<void>}
   */
  async function enviar(evento) {
    evento.preventDefault();
    const mensaje = validarEfectivo(contado, { permitirCero: true, nombre: "El efectivo contado" });
    if (mensaje) {
      setError(mensaje);
      return;
    }
    setEnviando(true);
    setError(null);
    try {
      alCerrar(await cerrarCaja({ efectivoContado: Number(contado), observaciones: observaciones.trim() }, token));
    } catch (falla) {
      setError(falla.message || "No se pudo cerrar la caja.");
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={enviar} className="space-y-3 rounded-2xl border border-tinta/10 bg-white p-4 shadow-sm">
      <h3 className="font-display text-lg font-extrabold">Cerrar la caja</h3>
      {bloqueado && (
        <p role="alert" className="rounded-xl border border-sol/60 bg-sol/20 px-3 py-2 text-sm">
          Este equipo tiene {ventasSinEnviar} {ventasSinEnviar === 1 ? "venta guardada" : "ventas guardadas"} sin enviar. Espera a que
          se envíen (o revísalas en el aviso de arriba) antes de cerrar la caja: si no, no quedarían en el corte.
        </p>
      )}
      <p className="text-sm text-tinta/70">Cuenta el efectivo que hay en la caja y escríbelo. El sistema lo compara con lo esperado.</p>
      <div className="grid gap-2.5 sm:grid-cols-2">
        <label className="text-sm">
          <span className="mb-1 block font-medium text-tinta/70">Efectivo contado</span>
          <input
            type="number"
            inputMode="numeric"
            min="0"
            step="1"
            value={contado}
            onChange={(evento) => setContado(evento.target.value)}
            required
            placeholder="$"
            className={CLASE_CAMPO}
          />
        </label>
        <div className="text-sm">
          <span className="mb-1 block font-medium text-tinta/70">Efectivo esperado</span>
          <p className="rounded-lg bg-papel px-3 py-2 font-bold tabular-nums">{formatearMoneda(esperado)}</p>
        </div>
        <label className="text-sm sm:col-span-2">
          <span className="mb-1 block font-medium text-tinta/70">Observaciones (opcional)</span>
          <textarea
            value={observaciones}
            onChange={(evento) => setObservaciones(evento.target.value)}
            maxLength={500}
            rows={2}
            className={CLASE_CAMPO}
          />
        </label>
      </div>
      {hayConteo && (
        <p role="status" className="rounded-xl bg-papel px-3 py-2 text-sm font-semibold">
          {describirDiferencia(Number(contado) - Number(esperado))}
        </p>
      )}
      {error && (
        <p role="alert" className="text-sm font-medium text-fucsia-osc">
          {error}
        </p>
      )}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={enviando || bloqueado}
          className="rounded-xl bg-fucsia px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
        >
          {enviando ? "Cerrando…" : "Cerrar caja"}
        </button>
        <button type="button" onClick={alCancelar} className="rounded-xl border border-tinta/20 px-4 py-2 text-sm font-semibold hover:bg-papel">
          Cancelar
        </button>
      </div>
    </form>
  );
}

/**
 * Ficha de un corte: quien lo abrio y cerro, la foto de sus cifras, sus movimientos y el aviso de ventas sin
 * conexion enviadas despues del cierre.
 *
 * @param {{corte: object, alCerrarFicha?: () => void}} props Ver `CorteCajaDetalleOut`.
 * @returns {JSX.Element}
 */
function FichaCorte({ corte, alCerrarFicha }) {
  const cerrado = corte.estado === "cerrada";
  const tardias = corte.ventas_sin_conexion_tardias;
  return (
    <div className="space-y-3 rounded-2xl border border-tinta/10 bg-papel/60 p-4" aria-label={`Corte ${corte.id}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="text-sm">
          <p className="font-display text-lg font-extrabold">Corte #{corte.id}</p>
          <p className="text-tinta/70">
            Abrió {corte.abierta_por} · {formatearFechaHora(corte.abierta_en)}
          </p>
          {cerrado && (
            <p className="text-tinta/70">
              Cerró {corte.cerrada_por} · {formatearFechaHora(corte.cerrada_en)}
            </p>
          )}
        </div>
        {alCerrarFicha && (
          <button type="button" onClick={alCerrarFicha} className="rounded-lg border border-tinta/20 px-3 py-1.5 text-sm font-semibold hover:bg-white">
            Cerrar ficha
          </button>
        )}
      </div>

      {cerrado && (
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-2xl border border-tinta/10 bg-white p-3">
            <p className="text-xs font-semibold text-tinta/60">Esperado</p>
            <p className="font-display text-xl font-extrabold tabular-nums">{formatearMoneda(corte.efectivo_esperado)}</p>
          </div>
          <div className="rounded-2xl border border-tinta/10 bg-white p-3">
            <p className="text-xs font-semibold text-tinta/60">Contado</p>
            <p className="font-display text-xl font-extrabold tabular-nums">{formatearMoneda(corte.efectivo_contado)}</p>
          </div>
          <div className="rounded-2xl border border-tinta/10 bg-white p-3">
            <p className="text-xs font-semibold text-tinta/60">Diferencia</p>
            <p className={`font-display text-xl font-extrabold tabular-nums ${Number(corte.diferencia) < 0 ? "text-fucsia-osc" : ""}`}>
              {formatearMoneda(corte.diferencia)}
            </p>
            <p className="text-xs text-tinta/60">{describirDiferencia(corte.diferencia)}</p>
          </div>
        </div>
      )}

      <DesgloseDeCifras cifras={corte.cifras} />

      {tardias.cantidad > 0 && (
        <p role="note" className="rounded-xl border border-sol/60 bg-sol/20 px-3 py-2 text-sm">
          Ventas sin conexión enviadas después del cierre: <strong>{tardias.cantidad}</strong> por {formatearMoneda(tardias.total)}. No
          están en las cifras de este corte, que se guardó tal cual al cerrarse.
        </p>
      )}

      <Tarjeta titulo="Ingresos y retiros">
        <ListaMovimientos movimientos={corte.movimientos} />
      </Tarjeta>
      {corte.observaciones && (
        <p className="text-sm">
          <strong>Observaciones:</strong> {corte.observaciones}
        </p>
      )}
    </div>
  );
}

/**
 * Historial de cortes del rango, con su ficha y (para administrador y propietario) la exportacion a CSV.
 *
 * @param {{puedeExportar: boolean, version: number, sinRed: boolean}} props `version` cambia cuando se cierra una
 *   caja, para recargar la lista.
 * @returns {JSX.Element}
 */
function HistorialDeCortes({ puedeExportar, version, sinRed }) {
  const { token } = useAuth();
  const [preset, setPreset] = useState("mes");
  const [personalizado, setPersonalizado] = useState(() => ({ desde: hoyEnBogota(), hasta: hoyEnBogota() }));
  const [cortes, setCortes] = useState(null);
  const [hayMas, setHayMas] = useState(false);
  const [ficha, setFicha] = useState(null);
  const [exportando, setExportando] = useState(false);
  const [error, setError] = useState(null);

  const rango = preset === "personalizado" ? personalizado : rangoDePreset(preset, hoyEnBogota());

  const cargar = useCallback(async () => {
    setError(null);
    const { desde, hasta } = preset === "personalizado" ? personalizado : rangoDePreset(preset, hoyEnBogota());
    try {
      const filas = await obtenerCortes({ desde, hasta, pagina: 1, tamanoPagina: TAMANO_PAGINA }, token);
      setCortes(filas);
      setHayMas(filas.length === TAMANO_PAGINA);
    } catch (falla) {
      setError(falla.message || "No se pudo cargar el historial de cortes.");
      setCortes((actuales) => actuales ?? []);
    }
  }, [token, preset, personalizado]);

  useEffect(() => {
    cargar();
  }, [cargar, version, sinRed]);

  /**
   * Trae la siguiente pagina y la agrega al final de la lista.
   *
   * @returns {Promise<void>}
   */
  async function verMas() {
    setError(null);
    try {
      const pagina = Math.floor(cortes.length / TAMANO_PAGINA) + 1;
      const filas = await obtenerCortes({ ...rango, pagina, tamanoPagina: TAMANO_PAGINA }, token);
      setCortes((actuales) => [...actuales, ...filas]);
      setHayMas(filas.length === TAMANO_PAGINA);
    } catch (falla) {
      setError(falla.message || "No se pudieron cargar más cortes.");
    }
  }

  /**
   * Abre la ficha de un corte (o la cierra si ya estaba abierta).
   *
   * @param {number} corteId
   * @returns {Promise<void>}
   */
  async function verFicha(corteId) {
    if (ficha?.id === corteId) {
      setFicha(null);
      return;
    }
    setError(null);
    try {
      setFicha(await obtenerCorte(corteId, token));
    } catch (falla) {
      setError(falla.message || "No se pudo abrir el corte.");
    }
  }

  /**
   * Descarga el CSV de los cortes cerrados del rango.
   *
   * @returns {Promise<void>}
   */
  async function exportar() {
    setExportando(true);
    setError(null);
    try {
      const { contenido, nombre } = await exportarCortes(rango, token);
      descargarArchivo(contenido, nombre);
    } catch (falla) {
      setError(falla.message || "No se pudo exportar los cortes.");
    } finally {
      setExportando(false);
    }
  }

  return (
    <section className="space-y-3" aria-label="Historial de cortes">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="font-display text-xl font-extrabold">Historial de cortes</h3>
        {puedeExportar && (
          <button
            type="button"
            onClick={exportar}
            disabled={exportando || sinRed}
            className="rounded-xl border border-tinta/20 px-3.5 py-2 text-sm font-semibold hover:bg-papel disabled:opacity-50"
          >
            {exportando ? "Exportando…" : "Exportar"}
          </button>
        )}
      </div>

      <SelectorRango
        preset={preset}
        personalizado={personalizado}
        alElegirPreset={setPreset}
        alAplicarPersonalizado={(nuevo) => {
          setPersonalizado(nuevo);
          setPreset("personalizado");
        }}
      />
      <p className="text-sm font-semibold text-tinta/70">{describirRango(rango.desde, rango.hasta, hoyEnBogota())}</p>

      {error && (
        <p role="alert" className="rounded-xl bg-fucsia/8 px-3 py-2 text-sm font-medium text-fucsia-osc">
          {error}
        </p>
      )}
      {cortes === null && <p className="text-tinta/60">Cargando…</p>}
      {cortes?.length === 0 && !error && <p className="text-tinta/60">No hay cortes en este rango.</p>}
      <ul className="space-y-2">
        {cortes?.map((corte) => {
          const abierta = corte.estado === "abierta";
          return (
            <li key={corte.id} className="rounded-2xl border border-tinta/10 bg-white p-4 text-sm">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="font-bold">
                    Corte #{corte.id} · {formatearFechaHora(corte.abierta_en)}
                    {abierta && <span className="ml-2 rounded-full bg-sol/30 px-2 py-0.5 text-xs font-bold">Abierta</span>}
                  </p>
                  <p className="text-tinta/60">
                    Abrió {corte.abierta_por}
                    {corte.cerrada_por ? ` · Cerró ${corte.cerrada_por}` : ""}
                  </p>
                </div>
                {!abierta && (
                  <div className="text-right tabular-nums">
                    <p className="text-tinta/60">
                      Esperado {formatearMoneda(corte.efectivo_esperado)} · Contado {formatearMoneda(corte.efectivo_contado)}
                    </p>
                    <p className={`font-bold ${Number(corte.diferencia) < 0 ? "text-fucsia-osc" : ""}`}>{describirDiferencia(corte.diferencia)}</p>
                  </div>
                )}
              </div>
              <button
                type="button"
                onClick={() => verFicha(corte.id)}
                aria-label={`Ver el corte ${corte.id}`}
                className="mt-2 text-sm font-semibold text-fucsia-osc"
              >
                {ficha?.id === corte.id ? "Ocultar" : "Ver detalle"}
              </button>
              {ficha?.id === corte.id && (
                <div className="mt-3">
                  <FichaCorte corte={ficha} alCerrarFicha={() => setFicha(null)} />
                </div>
              )}
            </li>
          );
        })}
      </ul>
      {hayMas && (
        <button type="button" onClick={verMas} className="rounded-xl border border-tinta/20 px-4 py-2 text-sm font-semibold hover:bg-papel">
          Ver más
        </button>
      )}
    </section>
  );
}

/**
 * Apartado Caja (Adendo v3, Fase G2: HU-13, RF-069 a RF-074).
 *
 * Roles: el administrador y el vendedor abren la caja, registran ingresos y retiros y la cierran con el conteo;
 * el propietario (`soloLectura`) solo consulta y exporta. El vendedor ve el efectivo esperado y solo los cortes
 * que abrio o cerro. Requiere conexion: no se guarda nada en el navegador, y la cola de ventas sin conexion no
 * cambia. No deja cerrar si este equipo tiene ventas guardadas sin enviar.
 *
 * @param {{soloLectura?: boolean}} props
 * @returns {JSX.Element}
 */
export function Caja({ soloLectura = false }) {
  const { token, usuarioActual } = useAuth();
  const sinConexion = useSinConexion();
  const navegadorEnLinea = useEnLinea();
  const sinRed = !sinConexion.enLinea || !navegadorEnLinea;
  const rol = usuarioActual?.rol;
  const puedeExportar = rol === "administrador" || rol === "propietario";
  const ventasSinEnviar = sinConexion.pendientes + sinConexion.conflictos;

  const [caja, setCaja] = useState(null);
  const [accion, setAccion] = useState(null); // null | "ingreso" | "retiro" | "cierre"
  const [corteCerrado, setCorteCerrado] = useState(null);
  const [version, setVersion] = useState(0);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      setCaja(await obtenerCajaActual(token));
    } catch (falla) {
      setError(falla.message || "No se pudo cargar la caja.");
    } finally {
      setCargando(false);
    }
  }, [token]);

  useEffect(() => {
    cargar();
  }, [cargar, sinRed]);

  /**
   * Recarga la caja y el historial despues de abrirla, moverla o cerrarla.
   *
   * @returns {void}
   */
  function alCambiar() {
    setAccion(null);
    setVersion((numero) => numero + 1);
    cargar();
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-display text-2xl font-extrabold">Caja</h2>
          {caja && (
            <p className="text-sm font-semibold text-tinta/70">
              {caja.abierta
                ? `Abierta por ${caja.corte.abierta_por} desde ${formatearFechaHora(caja.corte.abierta_en)}`
                : "La caja está cerrada"}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={cargar}
          disabled={cargando || sinRed}
          className="rounded-xl border border-tinta/20 px-3.5 py-2 text-sm font-semibold hover:bg-papel disabled:opacity-50"
        >
          {cargando ? "Actualizando…" : "Actualizar"}
        </button>
      </div>

      {sinRed && (
        <p role="status" className="rounded-xl border border-sol/60 bg-sol/20 px-3 py-2 text-sm">
          La caja necesita conexión con el servidor. Podrás usarla de nuevo cuando vuelva la conexión; las ventas siguen funcionando.
        </p>
      )}
      {error && (
        <p role="alert" className="rounded-xl bg-fucsia/8 px-3 py-2 text-sm font-medium text-fucsia-osc">
          {error}
        </p>
      )}

      {corteCerrado && (
        <div className="space-y-2">
          <p role="status" className="rounded-xl bg-papel px-3 py-2 text-sm font-bold">
            Caja cerrada. {describirDiferencia(corteCerrado.diferencia)}.
          </p>
          <FichaCorte corte={corteCerrado} alCerrarFicha={() => setCorteCerrado(null)} />
        </div>
      )}

      {caja && !caja.abierta && !soloLectura && !sinRed && (
        <FormularioApertura
          alAbrir={() => {
            setCorteCerrado(null);
            alCambiar();
          }}
        />
      )}
      {caja && !caja.abierta && soloLectura && <p className="text-tinta/60">No hay una caja abierta en este momento.</p>}

      {caja?.abierta && (
        <>
          <div className="rounded-2xl border border-tinta/10 bg-white p-4">
            <p className="text-sm font-semibold text-tinta/60">Efectivo esperado en la caja</p>
            <p className="mt-1 font-display text-4xl font-extrabold tabular-nums">{formatearMoneda(caja.cifras.efectivo_esperado)}</p>
            <p className="mt-1 text-xs text-tinta/50">Se calcula en vivo con las ventas, los gastos y los movimientos desde la apertura.</p>
          </div>

          <DesgloseDeCifras cifras={caja.cifras} />

          <Tarjeta titulo="Ingresos y retiros de esta caja">
            <ListaMovimientos movimientos={caja.movimientos} />
          </Tarjeta>

          {!soloLectura && accion === null && (
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setAccion("ingreso")}
                disabled={sinRed}
                className="rounded-xl border border-tinta/20 px-4 py-2 text-sm font-semibold hover:bg-papel disabled:opacity-50"
              >
                Registrar ingreso
              </button>
              <button
                type="button"
                onClick={() => setAccion("retiro")}
                disabled={sinRed}
                className="rounded-xl border border-tinta/20 px-4 py-2 text-sm font-semibold hover:bg-papel disabled:opacity-50"
              >
                Registrar retiro
              </button>
              <button
                type="button"
                onClick={() => setAccion("cierre")}
                disabled={sinRed}
                className="rounded-xl bg-fucsia px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
              >
                Cerrar caja
              </button>
            </div>
          )}
          {!soloLectura && (accion === "ingreso" || accion === "retiro") && (
            <FormularioMovimiento tipo={accion} alGuardar={alCambiar} alCancelar={() => setAccion(null)} />
          )}
          {!soloLectura && accion === "cierre" && (
            <FormularioCierre
              esperado={caja.cifras.efectivo_esperado}
              ventasSinEnviar={ventasSinEnviar}
              alCerrar={(corte) => {
                setCorteCerrado(corte);
                alCambiar();
              }}
              alCancelar={() => setAccion(null)}
            />
          )}
        </>
      )}

      <HistorialDeCortes puedeExportar={puedeExportar} version={version} sinRed={sinRed} />
    </section>
  );
}
