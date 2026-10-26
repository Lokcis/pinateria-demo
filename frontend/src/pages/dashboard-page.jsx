import { useState } from "react";
import { Caja } from "../components/caja";
import { Dashboard } from "../components/dashboard";
import { Gastos } from "../components/gastos";
import { PanelGanancias } from "../components/panel-ganancias";
import { Encabezado } from "../components/encabezado";
import { useAuth } from "../context/auth-context";
import { useEnLinea } from "../hooks/use-en-linea";

/**
 * Pantalla del propietario: supervision remota de solo lectura (HU-03, RF-013, RF-014).
 *
 * Tiene cuatro vistas: Ventas (el Dashboard), Ganancias (Adendo v2, Fase A3: HU-09, con los
 * costos solo de lectura y la ganancia neta del Adendo v3), Gastos (Fase G1: HU-12) y Caja (Fase G2: HU-13),
 * estas dos de solo lectura.
 *
 * @returns {JSX.Element}
 */
export function DashboardPage() {
  const { usuarioActual, cerrarSesion } = useAuth();
  const enLinea = useEnLinea();
  const [vista, setVista] = useState("ventas");

  return (
    <div className="dashboard-page min-h-screen">
      <Encabezado usuario={usuarioActual} alCerrarSesion={cerrarSesion} />
      {!enLinea && (
        <div role="alert" className="bg-fucsia px-4 py-2.5 text-center text-sm font-semibold text-white">
          Sin conexión a internet. Se muestran los últimos datos cargados.
        </div>
      )}
      <main className="mx-auto max-w-4xl px-4 py-6 sm:px-6">
        <div role="tablist" aria-label="Secciones del Dashboard" className="mb-4 inline-flex rounded-2xl bg-papel-osc p-1">
          {[
            { id: "ventas", etiqueta: "Ventas" },
            { id: "ganancias", etiqueta: "Ganancias" },
            { id: "gastos", etiqueta: "Gastos" },
            { id: "caja", etiqueta: "Caja" },
          ].map((opcion) => (
            <button
              key={opcion.id}
              type="button"
              role="tab"
              aria-selected={vista === opcion.id}
              onClick={() => setVista(opcion.id)}
              className={`rounded-xl px-4 py-2 text-sm font-bold transition ${
                vista === opcion.id ? "bg-white shadow-sm" : "text-tinta/60 hover:text-tinta"
              }`}
            >
              {opcion.etiqueta}
            </button>
          ))}
        </div>
        {vista === "ventas" && <Dashboard />}
        {vista === "ganancias" && <PanelGanancias puedeEditarCostos={false} />}
        {vista === "gastos" && <Gastos soloLectura />}
        {vista === "caja" && <Caja soloLectura />}
      </main>
    </div>
  );
}
