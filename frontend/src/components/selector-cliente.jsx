import { useEffect, useState } from "react";
import { buscarClientes } from "../api/api-client";
import { useAuth } from "../context/auth-context";
import { formatearMoneda } from "../utils/formato";
import { FormularioCliente } from "./formulario-cliente";

/**
 * Describe el descuento propio de un cliente (ej. "10 %" o "$2.000"), o null si no tiene.
 *
 * @param {object} cliente
 * @returns {string | null}
 */
function describirDescuentoCliente(cliente) {
  if (!cliente.descuento_tipo) return null;
  return cliente.descuento_tipo === "porcentaje"
    ? `${Number(cliente.descuento_valor).toLocaleString("es-CO")} %`
    : formatearMoneda(cliente.descuento_valor);
}

/**
 * Asociar un cliente a la venta (HU-07: RF-031): busca por nombre, documento o telefono, o registra uno nuevo.
 *
 * Solo ofrece clientes que se pueden usar (activos y con la autorizacion vigente); el servidor lo vuelve a validar.
 *
 * @param {{cliente: object | null, alCambiar: (cliente: object | null) => void, deshabilitado?: boolean}} props
 * @returns {JSX.Element}
 */
export function SelectorCliente({ cliente, alCambiar, deshabilitado = false }) {
  const { token } = useAuth();
  const [texto, setTexto] = useState("");
  const [resultados, setResultados] = useState([]);
  const [buscando, setBuscando] = useState(false);
  const [error, setError] = useState(null);
  const [registrando, setRegistrando] = useState(false);

  const consulta = texto.trim();

  useEffect(() => {
    if (consulta.length < 2) {
      setResultados([]);
      return undefined;
    }
    let vigente = true;
    const espera = setTimeout(async () => {
      setBuscando(true);
      try {
        const encontrados = await buscarClientes({ q: consulta, soloUtilizables: true, limite: 8 }, token);
        if (vigente) {
          setResultados(encontrados);
          setError(null);
        }
      } catch (falla) {
        if (vigente) setError(falla.message || "No se pudo buscar clientes.");
      } finally {
        if (vigente) setBuscando(false);
      }
    }, 250);
    return () => {
      vigente = false;
      clearTimeout(espera);
    };
  }, [consulta, token]);

  /**
   * Elige un cliente y limpia la busqueda.
   *
   * @param {object} elegido
   */
  function elegir(elegido) {
    setTexto("");
    setResultados([]);
    setRegistrando(false);
    alCambiar(elegido);
  }

  if (cliente) {
    const descuento = describirDescuentoCliente(cliente);
    return (
      <section aria-label="Cliente" className="rounded-xl border border-tinta/12 bg-white p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm">
            <span className="font-semibold text-tinta/65">Cliente: </span>
            <strong>{cliente.nombre}</strong>
            {descuento && (
              <span className="ml-2 rounded-full bg-turquesa/15 px-2 py-0.5 text-xs font-bold text-turquesa">
                Descuento {descuento}
              </span>
            )}
          </p>
          <button
            type="button"
            disabled={deshabilitado}
            onClick={() => alCambiar(null)}
            className="rounded-lg border border-tinta/20 px-2.5 py-1 text-xs font-semibold transition hover:border-tinta"
          >
            Quitar cliente
          </button>
        </div>
      </section>
    );
  }

  return (
    <section aria-label="Cliente" className="rounded-xl border border-tinta/12 bg-white p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-semibold text-tinta/65">Cliente</p>
        {!registrando && (
          <button
            type="button"
            disabled={deshabilitado}
            onClick={() => setRegistrando(true)}
            className="rounded-lg border border-tinta/20 px-2.5 py-1 text-xs font-semibold transition hover:border-tinta"
          >
            Nuevo cliente
          </button>
        )}
      </div>

      {registrando ? (
        <div className="mt-2">
          <FormularioCliente compacto alGuardar={elegir} alCancelar={() => setRegistrando(false)} />
        </div>
      ) : (
        <>
          <input
            type="search"
            value={texto}
            disabled={deshabilitado}
            onChange={(evento) => setTexto(evento.target.value)}
            placeholder="Buscar por nombre, documento o teléfono (opcional)"
            aria-label="Buscar cliente"
            className="mt-2 w-full rounded-lg border border-tinta/20 bg-white px-3 py-2 text-sm"
          />
          {error && (
            <p role="alert" className="mt-1 text-xs font-medium text-fucsia-osc">
              {error}
            </p>
          )}
          {consulta.length >= 2 && !buscando && !error && resultados.length === 0 && (
            <p className="mt-1 text-xs text-tinta/55">Sin resultados. Puede registrarlo con “Nuevo cliente”.</p>
          )}
          {resultados.length > 0 && (
            <ul aria-label="Clientes encontrados" className="mt-1 divide-y divide-tinta/8 rounded-lg border border-tinta/12">
              {resultados.map((resultado) => {
                const descuento = describirDescuentoCliente(resultado);
                return (
                  <li key={resultado.id}>
                    <button
                      type="button"
                      onClick={() => elegir(resultado)}
                      className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm hover:bg-papel"
                    >
                      <span>
                        <span className="font-semibold">{resultado.nombre}</span>
                        <span className="ml-2 text-xs text-tinta/55">
                          {[resultado.documento, resultado.telefono].filter(Boolean).join(" · ")}
                        </span>
                      </span>
                      {descuento && <span className="text-xs font-bold text-turquesa">{descuento}</span>}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </>
      )}
    </section>
  );
}
