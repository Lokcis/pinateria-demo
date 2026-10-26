import { useCallback, useEffect, useState } from "react";
import { guardarDescuentoGeneral, guardarTopesDescuento, obtenerConfiguracionDescuentos } from "../api/api-client";
import { useAuth } from "../context/auth-context";
import { leerMonto, leerPorcentaje } from "../utils/calculo-venta";

const CLASE_INPUT = "w-full rounded-lg border border-tinta/20 bg-white px-3 py-2 text-right tabular-nums";

/**
 * Valida un valor de descuento o de tope antes de enviarlo.
 *
 * @param {number | null} valor
 * @param {"porcentaje" | "monto"} tipo
 * @returns {string | null} El error, o null si es valido.
 */
function validarValor(valor, tipo) {
  if (valor === null || !(valor > 0)) {
    return "Escribe un valor mayor que cero.";
  }
  if (tipo === "porcentaje" && valor > 100) {
    return "Un porcentaje no puede superar el 100 %.";
  }
  if (tipo === "monto" && !Number.isInteger(valor)) {
    return "Un valor en pesos va sin centavos.";
  }
  return null;
}

/**
 * Formulario del descuento general (RF-026).
 *
 * @param {{general: object | null, alGuardar: (configuracion: object) => void}} props
 * @returns {JSX.Element}
 */
function FormularioGeneral({ general, alGuardar }) {
  const { token } = useAuth();
  const [tipo, setTipo] = useState(general?.tipo ?? "porcentaje");
  const [valor, setValor] = useState(general ? String(Number(general.valor)) : "");
  const [activo, setActivo] = useState(general?.activo ?? false);
  const [estado, setEstado] = useState(null);

  /**
   * Valida y guarda el descuento general.
   *
   * @param {React.FormEvent} evento
   * @returns {Promise<void>}
   */
  async function enviar(evento) {
    evento.preventDefault();
    const numero = tipo === "porcentaje" ? leerPorcentaje(valor) : leerMonto(valor);
    const error = validarValor(numero, tipo);
    if (error) {
      setEstado({ tipo: "error", texto: error });
      return;
    }
    setEstado({ tipo: "info", texto: "Guardando…" });
    try {
      alGuardar(await guardarDescuentoGeneral({ tipo, valor: String(numero), activo }, token));
      setEstado({ tipo: "ok", texto: "Descuento general guardado." });
    } catch (falla) {
      setEstado({ tipo: "error", texto: falla.message || "No se pudo guardar el descuento general." });
    }
  }

  return (
    <form onSubmit={enviar} className="space-y-3 rounded-2xl border border-tinta/10 bg-white p-4 shadow-sm">
      <div>
        <h3 className="font-display text-lg font-extrabold">Descuento general</h3>
        <p className="text-sm text-tinta/60">
          No se aplica solo: en cada venta el vendedor puede aplicarlo a quien corresponda.
        </p>
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <div role="radiogroup" aria-label="Tipo del descuento general" className="inline-flex rounded-lg bg-papel-osc p-0.5">
          {[
            { valor: "porcentaje", etiqueta: "Porcentaje" },
            { valor: "monto", etiqueta: "Pesos" },
          ].map((opcion) => (
            <button
              key={opcion.valor}
              type="button"
              role="radio"
              aria-checked={tipo === opcion.valor}
              onClick={() => setTipo(opcion.valor)}
              className={`rounded-md px-3 py-1.5 text-sm font-bold ${tipo === opcion.valor ? "bg-white shadow-sm" : "text-tinta/60"}`}
            >
              {opcion.etiqueta}
            </button>
          ))}
        </div>
        <label className="w-36 text-sm">
          <span className="mb-1 block font-medium text-tinta/70">{tipo === "porcentaje" ? "Valor (%)" : "Valor ($)"}</span>
          <input value={valor} onChange={(e) => setValor(e.target.value)} inputMode="decimal" className={CLASE_INPUT} />
        </label>
        <label className="flex items-center gap-2 pb-2 text-sm font-medium">
          <input type="checkbox" checked={activo} onChange={(e) => setActivo(e.target.checked)} className="h-4 w-4" />
          Activo
        </label>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <button type="submit" className="rounded-xl bg-fucsia px-4 py-2 text-sm font-bold text-white">
          Guardar descuento general
        </button>
        {estado && (
          <span
            role={estado.tipo === "error" ? "alert" : "status"}
            className={`text-sm font-medium ${estado.tipo === "error" ? "text-fucsia-osc" : "text-tinta/70"}`}
          >
            {estado.texto}
          </span>
        )}
      </div>
    </form>
  );
}

/**
 * Formulario de los topes del descuento manual del vendedor (RF-042). Vacio = sin tope.
 *
 * @param {{topes: object, alGuardar: (configuracion: object) => void}} props
 * @returns {JSX.Element}
 */
function FormularioTopes({ topes, alGuardar }) {
  const { token } = useAuth();
  const [porcentaje, setPorcentaje] = useState(topes.tope_porcentaje ? String(Number(topes.tope_porcentaje)) : "");
  const [monto, setMonto] = useState(topes.tope_monto ? String(Number(topes.tope_monto)) : "");
  const [estado, setEstado] = useState(null);

  /**
   * Valida y guarda los topes; un campo vacio quita ese tope.
   *
   * @param {React.FormEvent} evento
   * @returns {Promise<void>}
   */
  async function enviar(evento) {
    evento.preventDefault();
    const valorPorcentaje = leerPorcentaje(porcentaje);
    const valorMonto = leerMonto(monto);
    const error =
      (valorPorcentaje !== null && validarValor(valorPorcentaje, "porcentaje")) ||
      (valorMonto !== null && validarValor(valorMonto, "monto"));
    if (error) {
      setEstado({ tipo: "error", texto: error });
      return;
    }
    setEstado({ tipo: "info", texto: "Guardando…" });
    try {
      const configuracion = await guardarTopesDescuento(
        {
          tope_porcentaje: valorPorcentaje === null ? null : String(valorPorcentaje),
          tope_monto: valorMonto === null ? null : String(valorMonto),
        },
        token
      );
      alGuardar(configuracion);
      setEstado({ tipo: "ok", texto: `Topes guardados: ${configuracion.topes.descripcion}.` });
    } catch (falla) {
      setEstado({ tipo: "error", texto: falla.message || "No se pudieron guardar los topes." });
    }
  }

  return (
    <form onSubmit={enviar} className="space-y-3 rounded-2xl border border-tinta/10 bg-white p-4 shadow-sm">
      <div>
        <h3 className="font-display text-lg font-extrabold">Topes del descuento manual</h3>
        <p className="text-sm text-tinta/60">
          Límite para el vendedor cuando cambia el descuento a mano. Se deben cumplir los dos. No aplican al
          administrador ni al descuento general. Deja un campo vacío para no poner ese tope.
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-sm">
          <span className="mb-1 block font-medium text-tinta/70">Porcentaje máximo del subtotal (%)</span>
          <input value={porcentaje} onChange={(e) => setPorcentaje(e.target.value)} inputMode="decimal" placeholder="Sin tope" className={CLASE_INPUT} />
        </label>
        <label className="text-sm">
          <span className="mb-1 block font-medium text-tinta/70">Monto máximo ($)</span>
          <input value={monto} onChange={(e) => setMonto(e.target.value)} inputMode="numeric" placeholder="Sin tope" className={CLASE_INPUT} />
        </label>
      </div>
      <p className="text-sm">
        Vigente: <strong>{topes.descripcion}</strong>
      </p>
      <div className="flex flex-wrap items-center gap-3">
        <button type="submit" className="rounded-xl bg-fucsia px-4 py-2 text-sm font-bold text-white">
          Guardar topes
        </button>
        {estado && (
          <span
            role={estado.tipo === "error" ? "alert" : "status"}
            className={`text-sm font-medium ${estado.tipo === "error" ? "text-fucsia-osc" : "text-tinta/70"}`}
          >
            {estado.texto}
          </span>
        )}
      </div>
    </form>
  );
}

/**
 * Configuracion de descuentos del administrador (Adendo v2, HU-06: RF-026, RF-042).
 *
 * @returns {JSX.Element}
 */
export function Descuentos() {
  const { token } = useAuth();
  const [configuracion, setConfiguracion] = useState(null);
  const [error, setError] = useState(null);

  const cargar = useCallback(async () => {
    try {
      setConfiguracion(await obtenerConfiguracionDescuentos(token));
      setError(null);
    } catch (falla) {
      setError(falla.message || "No se pudo cargar la configuración de descuentos.");
    }
  }, [token]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  return (
    <section className="space-y-4">
      <h2 className="font-display text-xl font-extrabold">Descuentos</h2>
      {error && (
        <p role="alert" className="rounded-xl bg-fucsia/8 px-3 py-2 text-sm font-medium text-fucsia-osc">
          {error}
        </p>
      )}
      {!configuracion ? (
        !error && <p className="text-tinta/60">Cargando…</p>
      ) : (
        <>
          <FormularioGeneral general={configuracion.general} alGuardar={setConfiguracion} />
          <FormularioTopes topes={configuracion.topes} alGuardar={setConfiguracion} />
        </>
      )}
    </section>
  );
}
