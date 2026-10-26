import { useCallback, useEffect, useRef, useState } from "react";
import {
  anularGasto,
  crearGasto,
  editarGasto,
  exportarGastos,
  obtenerCategoriasGasto,
  obtenerGastos,
  obtenerResumenGastos,
} from "../api/api-client";
import { useAuth } from "../context/auth-context";
import { useSinConexion } from "../context/sin-conexion-context";
import { useEnLinea } from "../hooks/use-en-linea";
import { ETIQUETA_METODO_PAGO, ETIQUETA_PLATAFORMA, describirPago, esMultiploDe50, formatearFechaHora, formatearMoneda } from "../utils/formato";
import { descargarArchivo } from "../utils/descarga";
import { formatearDia, hoyEnBogota, rangoDePreset } from "../utils/rangos";
import { CategoriasGasto } from "./categorias-gasto";
import { Cifra, SelectorRango, Tarjeta } from "./dashboard";
import { Desplegable } from "./desplegable";

/** Filas que se piden por pagina de la lista. */
const TAMANO_PAGINA = 50;

const CLASE_CAMPO = "w-full rounded-lg border border-tinta/20 bg-white px-3 py-2";

/**
 * Formulario de alta y edicion de un gasto (Adendo v3, RF-059, RF-061).
 *
 * El vendedor no elige la fecha (siempre es la de hoy); el administrador puede poner una anterior. En efectivo el
 * monto debe ser multiplo de $50 y en una transferencia hay que elegir la plataforma.
 *
 * @param {{gasto?: object, categorias: Array<object>, esAdministrador: boolean,
 *   alGuardar: () => void, alCancelar: () => void}} props `gasto` presente indica edicion.
 * @returns {JSX.Element}
 */
function FormularioGasto({ gasto, categorias, esAdministrador, alGuardar, alCancelar }) {
  const { token } = useAuth();
  const hoy = hoyEnBogota();
  const [categoriaId, setCategoriaId] = useState(gasto ? String(gasto.categoria_id) : "");
  const [descripcion, setDescripcion] = useState(gasto?.descripcion ?? "");
  const [monto, setMonto] = useState(gasto ? String(Math.round(Number(gasto.monto))) : "");
  const [metodoPago, setMetodoPago] = useState(gasto?.metodo_pago ?? "efectivo");
  const [plataforma, setPlataforma] = useState(gasto?.plataforma ?? "");
  const [beneficiario, setBeneficiario] = useState(gasto?.beneficiario ?? "");
  const [fecha, setFecha] = useState(gasto?.fecha ?? hoy);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  // Al editar se conserva tambien una categoria que ya se desactivo (el gasto sigue en ella).
  const opciones = categorias.filter((categoria) => categoria.activa || categoria.id === gasto?.categoria_id);

  /**
   * Valida el formulario en el navegador (el servidor repite las mismas reglas).
   *
   * @returns {string | null} Mensaje de error, o null si todo esta bien.
   */
  function validar() {
    const pesos = Number(monto);
    if (!categoriaId) return "Elige la categoría del gasto.";
    if (!descripcion.trim()) return "Escribe qué se pagó.";
    if (!Number.isInteger(pesos) || pesos <= 0) return "El monto va en pesos enteros, mayor que cero.";
    if (metodoPago === "efectivo" && !esMultiploDe50(pesos)) return "En efectivo el monto debe ser múltiplo de $50.";
    if (metodoPago === "transferencia" && !plataforma) return "Elige la plataforma de la transferencia (Nequi o Daviplata).";
    return null;
  }

  /**
   * Guarda el gasto: crea uno nuevo o manda solo lo que cambio.
   *
   * @param {React.FormEvent} evento
   * @returns {Promise<void>}
   */
  async function enviar(evento) {
    evento.preventDefault();
    const mensaje = validar();
    if (mensaje) {
      setError(mensaje);
      return;
    }
    const datos = {
      categoria_id: Number(categoriaId),
      descripcion: descripcion.trim(),
      monto: Number(monto),
      metodo_pago: metodoPago,
      plataforma: metodoPago === "transferencia" ? plataforma : null,
      beneficiario: beneficiario.trim() || null,
    };
    setEnviando(true);
    setError(null);
    try {
      if (gasto) {
        const cambios = {};
        if (datos.categoria_id !== gasto.categoria_id) cambios.categoria_id = datos.categoria_id;
        if (datos.descripcion !== gasto.descripcion) cambios.descripcion = datos.descripcion;
        if (datos.monto !== Number(gasto.monto)) cambios.monto = datos.monto;
        if (datos.metodo_pago !== gasto.metodo_pago) cambios.metodo_pago = datos.metodo_pago;
        if (datos.plataforma !== gasto.plataforma) cambios.plataforma = datos.plataforma;
        if (datos.beneficiario !== gasto.beneficiario) cambios.beneficiario = datos.beneficiario;
        if (esAdministrador && fecha !== gasto.fecha) cambios.fecha = fecha;
        if (Object.keys(cambios).length === 0) {
          setError("No hay cambios que guardar.");
          setEnviando(false);
          return;
        }
        await editarGasto(gasto.id, cambios, token);
      } else {
        await crearGasto({ ...datos, ...(esAdministrador && { fecha }) }, token);
      }
      alGuardar();
    } catch (falla) {
      setError(falla.message || "No se pudo guardar el gasto.");
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={enviar} className="space-y-3 rounded-2xl border border-tinta/10 bg-white p-4 shadow-sm">
      <h3 className="font-display text-lg font-extrabold">{gasto ? "Editar gasto" : "Nuevo gasto"}</h3>
      <div className="grid gap-2.5 sm:grid-cols-2">
        <label className="text-sm">
          <span className="mb-1 block font-medium text-tinta/70">Categoría</span>
          <Desplegable value={categoriaId} onChange={(evento) => setCategoriaId(evento.target.value)} required className={CLASE_CAMPO}>
            <option value="">Selecciona…</option>
            {opciones.map((categoria) => (
              <option key={categoria.id} value={categoria.id}>
                {categoria.nombre}
              </option>
            ))}
          </Desplegable>
        </label>
        <label className="text-sm">
          <span className="mb-1 block font-medium text-tinta/70">Monto</span>
          <input
            type="number"
            inputMode="numeric"
            min="1"
            step="1"
            value={monto}
            onChange={(evento) => setMonto(evento.target.value)}
            required
            placeholder="$"
            className={CLASE_CAMPO}
          />
        </label>
        <label className="text-sm sm:col-span-2">
          <span className="mb-1 block font-medium text-tinta/70">Descripción</span>
          <input
            value={descripcion}
            onChange={(evento) => setDescripcion(evento.target.value)}
            required
            maxLength={255}
            placeholder="¿Qué se pagó?"
            className={CLASE_CAMPO}
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block font-medium text-tinta/70">Forma de pago</span>
          <Desplegable
            value={metodoPago}
            onChange={(evento) => {
              setMetodoPago(evento.target.value);
              if (evento.target.value !== "transferencia") setPlataforma("");
            }}
            className={CLASE_CAMPO}
            aria-label="Forma de pago"
          >
            {Object.entries(ETIQUETA_METODO_PAGO).map(([valor, etiqueta]) => (
              <option key={valor} value={valor}>
                {etiqueta}
              </option>
            ))}
          </Desplegable>
        </label>
        {metodoPago === "transferencia" && (
          <label className="text-sm">
            <span className="mb-1 block font-medium text-tinta/70">Plataforma</span>
            <Desplegable
              value={plataforma}
              onChange={(evento) => setPlataforma(evento.target.value)}
              required
              className={CLASE_CAMPO}
              aria-label="Plataforma de la transferencia"
            >
              <option value="">Selecciona…</option>
              {Object.entries(ETIQUETA_PLATAFORMA).map(([valor, etiqueta]) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </Desplegable>
          </label>
        )}
        <label className="text-sm">
          <span className="mb-1 block font-medium text-tinta/70">A quién se pagó (opcional)</span>
          <input
            value={beneficiario}
            onChange={(evento) => setBeneficiario(evento.target.value)}
            maxLength={120}
            placeholder="Solo el nombre"
            className={CLASE_CAMPO}
          />
        </label>
        {esAdministrador && (
          <label className="text-sm">
            <span className="mb-1 block font-medium text-tinta/70">Fecha</span>
            <input type="date" value={fecha} max={hoy} onChange={(evento) => setFecha(evento.target.value)} required className={CLASE_CAMPO} />
          </label>
        )}
      </div>
      {!esAdministrador && !gasto && <p className="text-xs text-tinta/60">Se registra con la fecha de hoy.</p>}
      {error && (
        <p role="alert" className="text-sm font-medium text-fucsia-osc">
          {error}
        </p>
      )}
      <div className="flex gap-2">
        <button type="submit" disabled={enviando} className="rounded-xl bg-fucsia px-4 py-2 text-sm font-bold text-white disabled:opacity-50">
          {enviando ? "Guardando…" : "Guardar gasto"}
        </button>
        <button type="button" onClick={alCancelar} className="rounded-xl border border-tinta/20 px-4 py-2 text-sm font-semibold hover:bg-papel">
          Cancelar
        </button>
      </div>
    </form>
  );
}

/**
 * Cuadro que pide el motivo para anular un gasto (RF-062). Sin motivo no se anula.
 *
 * @param {{gasto: object, alAnular: (motivo: string) => Promise<void>, alCancelar: () => void}} props
 * @returns {JSX.Element}
 */
function DialogoAnular({ gasto, alAnular, alCancelar }) {
  const [motivo, setMotivo] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);
  const campo = useRef(null);

  useEffect(() => {
    campo.current?.focus();
    const alPulsar = (evento) => {
      if (evento.key === "Escape") alCancelar();
    };
    document.addEventListener("keydown", alPulsar);
    return () => document.removeEventListener("keydown", alPulsar);
  }, [alCancelar]);

  /**
   * Envia la anulacion; el motivo debe tener al menos 3 letras.
   *
   * @param {React.FormEvent} evento
   * @returns {Promise<void>}
   */
  async function enviar(evento) {
    evento.preventDefault();
    if (motivo.trim().length < 3) {
      setError("Escribe el motivo de la anulación.");
      return;
    }
    setEnviando(true);
    setError(null);
    try {
      await alAnular(motivo.trim());
    } catch (falla) {
      setError(falla.message || "No se pudo anular el gasto.");
      setEnviando(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-tinta/50 p-4 backdrop-blur-[2px] sm:items-center"
      onClick={(evento) => evento.target === evento.currentTarget && alCancelar()}
    >
      <form
        onSubmit={enviar}
        role="dialog"
        aria-modal="true"
        aria-labelledby="anular-titulo"
        className="w-full max-w-md animate-pop rounded-3xl bg-white p-6 shadow-2xl shadow-tinta/30"
      >
        <h2 id="anular-titulo" className="font-display text-xl font-extrabold">
          ¿Anular este gasto?
        </h2>
        <p className="mt-2 text-sm text-tinta/70">
          {gasto.descripcion} · {formatearMoneda(gasto.monto)}. No se borra: queda tachado con tu nombre y deja de sumar en los totales.
        </p>
        <label className="mt-4 block text-sm">
          <span className="mb-1 block font-medium text-tinta/70">Motivo (obligatorio)</span>
          <textarea
            ref={campo}
            value={motivo}
            onChange={(evento) => setMotivo(evento.target.value)}
            maxLength={255}
            rows={2}
            className={CLASE_CAMPO}
          />
        </label>
        {error && (
          <p role="alert" className="mt-2 text-sm font-medium text-fucsia-osc">
            {error}
          </p>
        )}
        <div className="mt-5 flex flex-wrap justify-end gap-2.5">
          <button type="button" onClick={alCancelar} className="rounded-xl border border-tinta/20 px-4 py-2 text-sm font-semibold hover:bg-papel">
            Volver
          </button>
          <button
            type="submit"
            disabled={enviando}
            className="rounded-xl bg-fucsia px-4 py-2 text-sm font-bold text-white hover:bg-fucsia-osc disabled:opacity-50"
          >
            {enviando ? "Anulando…" : "Anular gasto"}
          </button>
        </div>
      </form>
    </div>
  );
}

/**
 * Una fila de la lista: un gasto o una compra recibida (solo lectura).
 *
 * @param {{gasto: object, alEditar: (gasto: object) => void, alAnular: (gasto: object) => void,
 *   alIrACompras?: () => void, soloLectura: boolean}} props
 * @returns {JSX.Element}
 */
function FilaGasto({ gasto, alEditar, alAnular, alIrACompras, soloLectura }) {
  const esCompra = gasto.origen === "compra";
  const tachado = gasto.anulado ? "line-through text-tinta/50" : "";
  const pago = gasto.metodo_pago ? describirPago(gasto) : "Sin forma de pago registrada";

  return (
    <li className={`rounded-2xl border border-tinta/10 bg-white p-4 text-sm ${gasto.anulado ? "bg-papel/60" : ""}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className={`font-bold ${tachado}`}>
            {gasto.descripcion}
            {esCompra && <span className="ml-2 rounded-full bg-cielo/20 px-2 py-0.5 text-xs font-bold text-tinta">Compra</span>}
          </p>
          <p className="text-tinta/60">
            {formatearDia(gasto.fecha)} · {gasto.categoria}
            {gasto.beneficiario && !esCompra ? ` · ${gasto.beneficiario}` : ""}
          </p>
          <p className="text-tinta/60">
            {pago} · Registró {gasto.registrado_por}
          </p>
        </div>
        <p className={`font-display text-lg font-extrabold tabular-nums ${tachado}`}>{formatearMoneda(gasto.monto)}</p>
      </div>

      {gasto.anulado && (
        <p className="mt-2 rounded-xl bg-fucsia/8 px-3 py-2 text-fucsia-osc">
          <strong>Anulado</strong> por {gasto.anulado_por} el {formatearFechaHora(gasto.anulado_en)} · Motivo: {gasto.motivo_anulacion}
        </p>
      )}
      {gasto.actualizado_por && !gasto.anulado && (
        <p className="mt-1 text-xs text-tinta/55">
          Editado por {gasto.actualizado_por} el {formatearFechaHora(gasto.actualizado_en)}
        </p>
      )}

      {!esCompra && !gasto.anulado && gasto.cubierto_por_corte && !gasto.editable && !soloLectura && (
        <p className="mt-2 text-xs text-tinta/60">
          Ya está en un corte de caja cerrado: para corregirlo pídele al administrador.
        </p>
      )}
      {esCompra && alIrACompras && (
        <button type="button" onClick={alIrACompras} className="mt-2 text-sm font-semibold text-fucsia-osc">
          Ver en Compras
        </button>
      )}
      {!soloLectura && gasto.editable && (
        <div className="mt-3 flex gap-2">
          <button
            type="button"
            onClick={() => alEditar(gasto)}
            aria-label={`Editar ${gasto.descripcion}`}
            className="rounded-lg border border-tinta/20 px-3 py-1.5 font-semibold hover:bg-papel"
          >
            Editar
          </button>
          <button
            type="button"
            onClick={() => alAnular(gasto)}
            aria-label={`Anular ${gasto.descripcion}`}
            className="rounded-lg border border-fucsia/40 px-3 py-1.5 font-semibold text-fucsia-osc hover:bg-fucsia/10"
          >
            Anular
          </button>
        </div>
      )}
    </li>
  );
}

/**
 * Totales vigentes del rango por categoria y por forma de pago (RF-065). Solo administrador y propietario.
 *
 * @param {{resumen: object}} props
 * @returns {JSX.Element}
 */
function TotalesDeGastos({ resumen }) {
  return (
    <>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <Cifra titulo="Total de gastos" valor={formatearMoneda(resumen.total)} detalle="Incluye las compras recibidas" />
        <Cifra titulo="Compras de mercancía" valor={formatearMoneda(resumen.total_compras)} />
        <Cifra titulo="Gastos operativos" valor={formatearMoneda(resumen.total_operativo)} detalle="Sin la mercancía" />
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <Tarjeta titulo="Por categoría">
          {resumen.por_categoria.length === 0 ? (
            <p className="text-sm text-tinta/50">Sin gastos en este rango</p>
          ) : (
            <ul className="space-y-1 text-sm">
              {resumen.por_categoria.map((fila) => (
                <li key={`${fila.categoria_id}-${fila.categoria}`} className="flex justify-between gap-3">
                  <span>
                    {fila.categoria} <span className="text-xs text-tinta/50">· {fila.cantidad}</span>
                  </span>
                  <span className="font-semibold tabular-nums">{formatearMoneda(fila.total)}</span>
                </li>
              ))}
            </ul>
          )}
        </Tarjeta>
        <Tarjeta titulo="Por forma de pago">
          {resumen.por_metodo_pago.length === 0 ? (
            <p className="text-sm text-tinta/50">Sin gastos en este rango</p>
          ) : (
            <ul className="space-y-1 text-sm">
              {resumen.por_metodo_pago.map((fila) => (
                <li key={fila.metodo_pago ?? "sin"} className="flex justify-between gap-3">
                  <span>{ETIQUETA_METODO_PAGO[fila.metodo_pago] || "Sin forma de pago"}</span>
                  <span className="font-semibold tabular-nums">{formatearMoneda(fila.total)}</span>
                </li>
              ))}
            </ul>
          )}
        </Tarjeta>
      </div>
    </>
  );
}

/**
 * Ventana de Gastos (Adendo v3, Fase G1: HU-12, RF-059 a RF-066).
 *
 * Roles: el administrador ve e ingresa todo (y las compras recibidas, totales, categorias y exportacion); el
 * vendedor solo registra y ve, edita y anula los suyos, sin totales ni compras; el propietario (`soloLectura`)
 * consulta y exporta. Requiere conexion: no se guarda nada en el navegador.
 *
 * @param {{soloLectura?: boolean, alIrACompras?: () => void}} props `alIrACompras` abre la vista Compras
 *   (solo el administrador la tiene).
 * @returns {JSX.Element}
 */
export function Gastos({ soloLectura = false, alIrACompras }) {
  const { token, usuarioActual } = useAuth();
  const sinConexion = useSinConexion();
  const navegadorEnLinea = useEnLinea();
  const sinRed = !sinConexion.enLinea || !navegadorEnLinea;
  const rol = usuarioActual?.rol;
  const esAdministrador = rol === "administrador";
  const veTotales = rol === "administrador" || rol === "propietario";

  const [preset, setPreset] = useState(rol === "vendedor" ? "hoy" : "mes");
  const [personalizado, setPersonalizado] = useState(() => ({ desde: hoyEnBogota(), hasta: hoyEnBogota() }));
  const [categoriaId, setCategoriaId] = useState("");
  const [metodoPago, setMetodoPago] = useState("");
  const [estado, setEstado] = useState("");
  const [incluirAnulados, setIncluirAnulados] = useState(false);
  const [categorias, setCategorias] = useState([]);
  const [gastos, setGastos] = useState(null);
  const [hayMas, setHayMas] = useState(false);
  const [resumen, setResumen] = useState(null);
  const [formulario, setFormulario] = useState(null); // null | "nuevo" | gasto a editar
  const [anulando, setAnulando] = useState(null);
  const [verCategorias, setVerCategorias] = useState(false);
  const [exportando, setExportando] = useState(false);
  const [error, setError] = useState(null);

  const cargarCategorias = useCallback(async () => {
    try {
      setCategorias(await obtenerCategoriasGasto(token));
    } catch {
      setCategorias([]);
    }
  }, [token]);

  useEffect(() => {
    cargarCategorias();
  }, [cargarCategorias]);

  const rango = preset === "personalizado" ? personalizado : rangoDePreset(preset, hoyEnBogota());
  const filtros = { ...rango, categoriaId, metodoPago };

  const cargar = useCallback(async () => {
    setError(null);
    const { desde, hasta } = preset === "personalizado" ? personalizado : rangoDePreset(preset, hoyEnBogota());
    const consulta = { desde, hasta, categoriaId, metodoPago };
    try {
      const [filas, totales] = await Promise.all([
        obtenerGastos({ ...consulta, estado, pagina: 1, tamanoPagina: TAMANO_PAGINA }, token),
        veTotales ? obtenerResumenGastos(consulta, token) : Promise.resolve(null),
      ]);
      setGastos(filas);
      setHayMas(filas.length === TAMANO_PAGINA);
      setResumen(totales);
    } catch (falla) {
      setError(falla.message || "No se pudieron cargar los gastos.");
      setGastos((actuales) => actuales ?? []);
    }
  }, [token, preset, personalizado, categoriaId, metodoPago, estado, veTotales]);

  useEffect(() => {
    cargar();
  }, [cargar, sinRed]);

  /**
   * Trae la siguiente pagina y la agrega al final de la lista.
   *
   * @returns {Promise<void>}
   */
  async function verMas() {
    setError(null);
    try {
      const pagina = Math.floor(gastos.length / TAMANO_PAGINA) + 1;
      const filas = await obtenerGastos({ ...filtros, estado, pagina, tamanoPagina: TAMANO_PAGINA }, token);
      setGastos((actuales) => [...actuales, ...filas]);
      setHayMas(filas.length === TAMANO_PAGINA);
    } catch (falla) {
      setError(falla.message || "No se pudieron cargar más gastos.");
    }
  }

  /**
   * Anula el gasto elegido con su motivo y recarga la lista.
   *
   * @param {string} motivo
   * @returns {Promise<void>}
   */
  async function anular(motivo) {
    await anularGasto(anulando.id, motivo, token);
    setAnulando(null);
    await cargar();
  }

  /**
   * Descarga el CSV del rango y los filtros actuales.
   *
   * @returns {Promise<void>}
   */
  async function exportar() {
    setExportando(true);
    setError(null);
    try {
      const { contenido, nombre } = await exportarGastos({ ...filtros, incluirAnulados }, token);
      descargarArchivo(contenido, nombre);
    } catch (falla) {
      setError(falla.message || "No se pudo exportar los gastos.");
    } finally {
      setExportando(false);
    }
  }

  const categoriasUsables = categorias.filter((categoria) => categoria.activa);

  return (
    <section className="space-y-4">
      {anulando && <DialogoAnular gasto={anulando} alAnular={anular} alCancelar={() => setAnulando(null)} />}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-2xl font-extrabold">Gastos</h2>
        <div className="flex flex-wrap gap-2">
          {esAdministrador && (
            <button
              type="button"
              onClick={() => setVerCategorias((visible) => !visible)}
              aria-expanded={verCategorias}
              className="rounded-xl border border-tinta/20 px-3.5 py-2 text-sm font-semibold hover:bg-papel"
            >
              Categorías
            </button>
          )}
          {veTotales && (
            <button
              type="button"
              onClick={exportar}
              disabled={exportando || sinRed}
              className="rounded-xl border border-tinta/20 px-3.5 py-2 text-sm font-semibold hover:bg-papel disabled:opacity-50"
            >
              {exportando ? "Exportando…" : "Exportar"}
            </button>
          )}
          {!soloLectura && (
            <button
              type="button"
              onClick={() => setFormulario("nuevo")}
              disabled={sinRed}
              className="rounded-xl bg-fucsia px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
            >
              Nuevo gasto
            </button>
          )}
        </div>
      </div>

      {sinRed && (
        <p role="status" className="rounded-xl border border-sol/60 bg-sol/20 px-3 py-2 text-sm">
          Los gastos necesitan conexión con el servidor. Podrás registrarlos de nuevo cuando vuelva la conexión; las ventas
          siguen funcionando.
        </p>
      )}

      {esAdministrador && verCategorias && (
        <CategoriasGasto categorias={categorias} alCambiar={cargarCategorias} alCerrar={() => setVerCategorias(false)} />
      )}

      {formulario && !soloLectura && (
        <FormularioGasto
          key={formulario === "nuevo" ? "nuevo" : formulario.id}
          gasto={formulario === "nuevo" ? undefined : formulario}
          categorias={formulario === "nuevo" ? categoriasUsables : categorias}
          esAdministrador={esAdministrador}
          alGuardar={() => {
            setFormulario(null);
            cargar();
          }}
          alCancelar={() => setFormulario(null)}
        />
      )}

      <SelectorRango
        preset={preset}
        personalizado={personalizado}
        alElegirPreset={setPreset}
        alAplicarPersonalizado={(nuevo) => {
          setPersonalizado(nuevo);
          setPreset("personalizado");
        }}
      />

      <div className="flex flex-wrap items-center gap-2">
        <Desplegable
          value={categoriaId}
          onChange={(evento) => setCategoriaId(evento.target.value)}
          aria-label="Filtrar por categoría"
          className="rounded-lg border border-tinta/20 bg-white px-3 py-2 text-sm"
        >
          <option value="">Todas las categorías</option>
          {(veTotales ? categorias : categoriasUsables).map((categoria) => (
            <option key={categoria.id} value={categoria.id}>
              {categoria.nombre}
            </option>
          ))}
        </Desplegable>
        <Desplegable
          value={metodoPago}
          onChange={(evento) => setMetodoPago(evento.target.value)}
          aria-label="Filtrar por forma de pago"
          className="rounded-lg border border-tinta/20 bg-white px-3 py-2 text-sm"
        >
          <option value="">Todas las formas de pago</option>
          {Object.entries(ETIQUETA_METODO_PAGO).map(([valor, etiqueta]) => (
            <option key={valor} value={valor}>
              {etiqueta}
            </option>
          ))}
        </Desplegable>
        <Desplegable
          value={estado}
          onChange={(evento) => setEstado(evento.target.value)}
          aria-label="Filtrar por estado"
          className="rounded-lg border border-tinta/20 bg-white px-3 py-2 text-sm"
        >
          <option value="">Vigentes y anulados</option>
          <option value="vigente">Solo vigentes</option>
          <option value="anulado">Solo anulados</option>
        </Desplegable>
        {veTotales && (
          <label className="flex items-center gap-1.5 text-sm text-tinta/70">
            <input type="checkbox" checked={incluirAnulados} onChange={(evento) => setIncluirAnulados(evento.target.checked)} />
            Incluir anulados al exportar
          </label>
        )}
      </div>

      {error && (
        <p role="alert" className="rounded-xl bg-fucsia/8 px-3 py-2 text-sm font-medium text-fucsia-osc">
          {error}
        </p>
      )}

      {resumen && <TotalesDeGastos resumen={resumen} />}

      {gastos === null && <p className="text-tinta/60">Cargando…</p>}
      {gastos?.length === 0 && !error && <p className="text-tinta/60">No hay gastos en este rango.</p>}
      <ul className="space-y-2">
        {gastos?.map((gasto) => (
          <FilaGasto
            key={`${gasto.origen}-${gasto.id}`}
            gasto={gasto}
            soloLectura={soloLectura}
            alEditar={(elegido) => setFormulario(elegido)}
            alAnular={setAnulando}
            alIrACompras={esAdministrador ? alIrACompras : undefined}
          />
        ))}
      </ul>
      {hayMas && (
        <button type="button" onClick={verMas} className="rounded-xl border border-tinta/20 px-4 py-2 text-sm font-semibold hover:bg-papel">
          Ver más
        </button>
      )}
    </section>
  );
}
