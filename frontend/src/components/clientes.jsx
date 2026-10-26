import { useCallback, useEffect, useState } from "react";
import { buscarClientes } from "../api/api-client";
import { useAuth } from "../context/auth-context";
import { formatearFechaHora, formatearMoneda } from "../utils/formato";
import { FichaCliente, InsigniasCliente } from "./ficha-cliente";
import { FormularioCliente } from "./formulario-cliente";

const SIN_FILTROS = { totalMin: "", totalMax: "", desde: "", hasta: "" };

/**
 * Un campo del panel de filtros por compras.
 *
 * @param {{etiqueta: string, tipo?: string, valor: string, alCambiar: (valor: string) => void}} props
 * @returns {JSX.Element}
 */
function CampoFiltro({ etiqueta, tipo = "text", valor, alCambiar }) {
  return (
    <label className="text-sm">
      <span className="mb-1 block font-medium text-tinta/70">{etiqueta}</span>
      <input
        type={tipo}
        inputMode={tipo === "text" ? "numeric" : undefined}
        value={valor}
        onChange={(evento) => alCambiar(tipo === "text" ? evento.target.value.replace(/\D/g, "") : evento.target.value)}
        className="w-full rounded-lg border border-tinta/20 bg-white px-3 py-2"
      />
    </label>
  );
}

/**
 * Clientes de la tienda (HU-07): busqueda, filtros por compras, alta y ficha con historial.
 *
 * Lo ven vendedores y administradores. El filtro por fechas cuenta solo las compras de ese rango; el de
 * total comprado se aplica sobre ese resumen. Los datos personales solo se muestran a quien atiende.
 *
 * @returns {JSX.Element}
 */
export function Clientes() {
  const { token } = useAuth();
  const [q, setQ] = useState("");
  const [filtros, setFiltros] = useState(SIN_FILTROS);
  const [mostrarFiltros, setMostrarFiltros] = useState(false);
  const [soloPromociones, setSoloPromociones] = useState(false);
  const [clientes, setClientes] = useState(null);
  const [error, setError] = useState(null);
  const [registrando, setRegistrando] = useState(false);
  const [fichaId, setFichaId] = useState(null);

  const cargar = useCallback(async () => {
    setError(null);
    try {
      setClientes(
        await buscarClientes(
          { q: q.trim(), ...filtros, ...(soloPromociones && { aceptaPublicidad: true }), limite: 100 },
          token
        )
      );
    } catch (falla) {
      setError(falla.message || "No se pudo cargar los clientes.");
      setClientes([]);
    }
  }, [q, filtros, soloPromociones, token]);

  useEffect(() => {
    const espera = setTimeout(cargar, 250);
    return () => clearTimeout(espera);
  }, [cargar]);

  if (fichaId !== null) {
    return <FichaCliente clienteId={fichaId} alVolver={() => setFichaId(null)} alCambiar={cargar} />;
  }

  const hayFiltros = Object.values(filtros).some(Boolean) || soloPromociones;

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-xl font-extrabold">Clientes</h2>
        <div className="flex flex-wrap gap-2">
          <input
            type="search"
            value={q}
            onChange={(evento) => setQ(evento.target.value)}
            placeholder="Buscar nombre, documento o teléfono…"
            aria-label="Buscar cliente"
            className="rounded-lg border border-tinta/20 bg-white px-3 py-2 text-sm"
          />
          <button
            type="button"
            aria-expanded={mostrarFiltros}
            onClick={() => setMostrarFiltros((valor) => !valor)}
            className="rounded-xl border border-tinta/20 px-3 py-2 text-sm font-semibold hover:bg-papel"
          >
            Filtrar por compras{hayFiltros ? " •" : ""}
          </button>
          <button
            type="button"
            onClick={() => setRegistrando(true)}
            className="rounded-xl bg-fucsia px-4 py-2 text-sm font-bold text-white"
          >
            Nuevo cliente
          </button>
        </div>
      </div>

      {mostrarFiltros && (
        <div className="grid gap-2.5 rounded-2xl border border-tinta/10 bg-white p-4 sm:grid-cols-4" aria-label="Filtros por compras">
          <CampoFiltro
            etiqueta="Total mínimo ($)"
            valor={filtros.totalMin}
            alCambiar={(valor) => setFiltros((actual) => ({ ...actual, totalMin: valor }))}
          />
          <CampoFiltro
            etiqueta="Total máximo ($)"
            valor={filtros.totalMax}
            alCambiar={(valor) => setFiltros((actual) => ({ ...actual, totalMax: valor }))}
          />
          <CampoFiltro
            etiqueta="Compras desde"
            tipo="date"
            valor={filtros.desde}
            alCambiar={(valor) => setFiltros((actual) => ({ ...actual, desde: valor }))}
          />
          <CampoFiltro
            etiqueta="Compras hasta"
            tipo="date"
            valor={filtros.hasta}
            alCambiar={(valor) => setFiltros((actual) => ({ ...actual, hasta: valor }))}
          />
          <label className="sm:col-span-4 flex items-center gap-2 text-sm font-medium">
            <input
              type="checkbox"
              checked={soloPromociones}
              onChange={(evento) => setSoloPromociones(evento.target.checked)}
            />
            Solo clientes que aceptaron recibir promociones
          </label>
          <div className="sm:col-span-4 flex items-center justify-between gap-3">
            <p className="text-xs text-tinta/55">
              Con fechas, solo cuentan las compras de ese rango y se omiten los clientes que no compraron en él.
            </p>
            <button
              type="button"
              onClick={() => {
                setFiltros(SIN_FILTROS);
                setSoloPromociones(false);
              }}
              className="rounded-lg border border-tinta/20 px-3 py-1.5 text-sm font-semibold hover:bg-papel"
            >
              Limpiar filtros
            </button>
          </div>
        </div>
      )}

      {registrando && (
        <FormularioCliente
          alGuardar={(creado) => {
            setRegistrando(false);
            setFichaId(creado.id);
            cargar();
          }}
          alCancelar={() => setRegistrando(false)}
        />
      )}

      {error && (
        <p role="alert" className="text-sm font-medium text-fucsia-osc">
          {error}
        </p>
      )}
      {clientes === null && <p className="text-tinta/60">Cargando…</p>}
      {clientes?.length === 0 && !error && <p className="text-tinta/60">No hay clientes que coincidan.</p>}

      <ul className="space-y-2">
        {clientes?.map((cliente) => (
          <li
            key={cliente.id}
            className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-tinta/10 bg-white p-4"
          >
            <div className="min-w-0 text-sm">
              <p className="flex flex-wrap items-center gap-2 font-bold">
                {cliente.nombre}
                <InsigniasCliente cliente={cliente} />
                {cliente.acepta_publicidad && (
                  <span className="rounded-full bg-turquesa/15 px-2 py-0.5 text-xs font-bold text-turquesa">
                    Acepta promociones
                  </span>
                )}
              </p>
              <p className="text-tinta/70">
                {[cliente.documento, cliente.telefono, cliente.email].filter(Boolean).join(" · ") || "Sin datos de contacto"}
              </p>
              <p className="text-xs text-tinta/55">
                {cliente.numero_ventas} {cliente.numero_ventas === 1 ? "venta" : "ventas"} ·{" "}
                {formatearMoneda(cliente.total_comprado)}
                {cliente.ultima_compra && ` · última ${formatearFechaHora(cliente.ultima_compra)}`}
              </p>
            </div>
            <button
              type="button"
              onClick={() => setFichaId(cliente.id)}
              className="rounded-lg border border-tinta/20 px-3 py-1.5 text-sm font-semibold hover:bg-papel"
            >
              Ver ficha
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
