import { useEffect, useState } from "react";
import { crearCliente, editarCliente, obtenerPoliticaDatos } from "../api/api-client";
import { useAuth } from "../context/auth-context";
import { ETIQUETA_MEDIO_AUTORIZACION } from "../utils/formato";
import { Desplegable } from "./desplegable";
import { PoliticaDatos } from "./politica-datos";

const CAMPOS = [
  { id: "nombre", etiqueta: "Nombre", requerido: true },
  { id: "documento", etiqueta: "Documento" },
  { id: "telefono", etiqueta: "Teléfono", tipo: "tel", soloNumeros: true },
  { id: "email", etiqueta: "Correo", tipo: "email" },
];

/**
 * Formulario de alta/edicion de un cliente (HU-07: RF-029, RF-030).
 *
 * Al registrar muestra el aviso de privacidad y la politica vigentes, y exige marcar la autorizacion para
 * el tratamiento de los datos (Ley 1581 de 2012) y el medio por el que se dio; el servidor guarda ademas
 * la fecha, la version de la politica y el empleado. La autorizacion para recibir promociones es una casilla
 * APARTE, desmarcada por defecto. Al editar solo se cambian los datos de contacto y las promociones.
 *
 * @param {{cliente?: object, alGuardar: (cliente: object) => void, alCancelar: () => void,
 *   compacto?: boolean}} props `cliente` presente indica edicion; ausente, alta.
 * @returns {JSX.Element}
 */
export function FormularioCliente({ cliente, alGuardar, alCancelar, compacto = false }) {
  const { token } = useAuth();
  const [valores, setValores] = useState(() =>
    Object.fromEntries(CAMPOS.map(({ id }) => [id, cliente?.[id] ?? ""]))
  );
  const [autorizado, setAutorizado] = useState(false);
  const [promociones, setPromociones] = useState(Boolean(cliente?.acepta_publicidad));
  const [medio, setMedio] = useState("verbal");
  const [politica, setPolitica] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let activo = true;
    obtenerPoliticaDatos(token)
      .then((datos) => activo && setPolitica(datos))
      .catch(() => {}); // Solo informativo: el servidor registra la version por su cuenta.
    return () => {
      activo = false;
    };
  }, [token]);

  const puedeDarPromociones = !cliente || cliente.utilizable;

  /**
   * Envia el formulario; los campos opcionales vacios se mandan como null.
   *
   * @param {React.FormEvent} evento
   * @returns {Promise<void>}
   */
  async function enviar(evento) {
    evento.preventDefault();
    if (valores.telefono && valores.telefono.length < 7) {
      setError("El teléfono debe tener al menos 7 dígitos.");
      return;
    }
    setEnviando(true);
    setError(null);
    const datos = Object.fromEntries(Object.entries(valores).map(([campo, valor]) => [campo, valor.trim() || null]));
    try {
      let guardado;
      if (cliente) {
        const cambios = promociones !== Boolean(cliente.acepta_publicidad) ? { ...datos, acepta_publicidad: promociones } : datos;
        guardado = await editarCliente(cliente.id, cambios, token);
      } else {
        guardado = await crearCliente(
          { ...datos, autorizacion_aceptada: autorizado, autorizacion_medio: medio, acepta_publicidad: promociones },
          token
        );
      }
      alGuardar(guardado);
    } catch (falla) {
      setError(falla.message || "No se pudo guardar el cliente.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={enviar} className="space-y-3 rounded-2xl border border-tinta/10 bg-white p-4 shadow-sm">
      <h3 className={`font-display font-extrabold ${compacto ? "text-base" : "text-lg"}`}>
        {cliente ? "Editar cliente" : "Nuevo cliente"}
      </h3>
      <div className={`grid gap-2.5 ${compacto ? "" : "sm:grid-cols-2"}`}>
        {CAMPOS.map(({ id, etiqueta, requerido, tipo, soloNumeros }) => (
          <label key={id} className="text-sm">
            <span className="mb-1 block font-medium text-tinta/70">{etiqueta}</span>
            <input
              type={tipo || "text"}
              inputMode={soloNumeros ? "numeric" : undefined}
              maxLength={soloNumeros ? 15 : undefined}
              value={valores[id]}
              required={requerido}
              onChange={(evento) => {
                const valor = soloNumeros ? evento.target.value.replace(/\D/g, "") : evento.target.value;
                setValores((actual) => ({ ...actual, [id]: valor }));
              }}
              className="w-full rounded-lg border border-tinta/20 bg-white px-3 py-2"
            />
          </label>
        ))}
      </div>

      {!cliente && (
        <fieldset className="space-y-2 rounded-xl border border-tinta/12 bg-papel p-3">
          <legend className="px-1 text-xs font-bold uppercase tracking-wide text-tinta/55">Autorización de datos</legend>
          <PoliticaDatos politica={politica} />
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              checked={autorizado}
              onChange={(evento) => setAutorizado(evento.target.checked)}
              className="mt-1"
            />
            <span>{politica?.texto_autorizacion_empleado ?? "El cliente leyó o escuchó el aviso y autoriza el tratamiento de sus datos personales."}</span>
          </label>
          <label className="flex items-center gap-2 text-sm">
            <span className="font-medium text-tinta/70">La dio de forma</span>
            <Desplegable
              value={medio}
              onChange={(evento) => setMedio(evento.target.value)}
              aria-label="Medio de la autorización"
              className="rounded-lg border border-tinta/20 bg-white px-3 py-1.5"
            >
              {Object.entries(ETIQUETA_MEDIO_AUTORIZACION).map(([valor, etiqueta]) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </Desplegable>
          </label>
        </fieldset>
      )}

      <label className={`flex items-start gap-2 rounded-xl border border-tinta/12 p-3 text-sm ${puedeDarPromociones ? "" : "opacity-60"}`}>
        <input
          type="checkbox"
          checked={promociones}
          disabled={!puedeDarPromociones && !promociones}
          onChange={(evento) => setPromociones(evento.target.checked)}
          className="mt-1"
        />
        <span>
          {politica?.texto_promociones_empleado ?? "El cliente además autoriza que le envíen promociones y novedades de la tienda (opcional)."}
        </span>
      </label>

      {error && (
        <p role="alert" className="text-sm font-medium text-fucsia-osc">
          {error}
        </p>
      )}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={enviando || (!cliente && !autorizado)}
          className="rounded-xl bg-fucsia px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
        >
          {enviando ? "Guardando…" : "Guardar"}
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
