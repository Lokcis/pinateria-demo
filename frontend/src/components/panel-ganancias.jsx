import { useState } from "react";
import { Costos } from "./costos";
import { Ganancias } from "./ganancias";

const VISTAS = [
  { id: "margen", etiqueta: "Margen" },
  { id: "costos", etiqueta: "Costos" },
];

/**
 * Ganancias y costos juntos (Adendo v2, Fase A3: HU-09).
 *
 * La usan la pestaña "Ganancias" del administrador (costos editables) y el Dashboard del
 * propietario (costos solo de lectura).
 *
 * @param {{puedeEditarCostos: boolean}} props
 * @returns {JSX.Element}
 */
export function PanelGanancias({ puedeEditarCostos }) {
  const [vista, setVista] = useState("margen");

  return (
    <div className="space-y-4">
      <div role="tablist" aria-label="Ganancias" className="inline-flex rounded-xl bg-papel-osc p-1">
        {VISTAS.map((opcion) => (
          <button
            key={opcion.id}
            type="button"
            role="tab"
            aria-selected={vista === opcion.id}
            onClick={() => setVista(opcion.id)}
            className={`rounded-lg px-3.5 py-1.5 text-sm font-bold transition ${
              vista === opcion.id ? "bg-white shadow-sm" : "text-tinta/60 hover:text-tinta"
            }`}
          >
            {opcion.etiqueta}
          </button>
        ))}
      </div>
      {vista === "margen" ? <Ganancias /> : <Costos editable={puedeEditarCostos} />}
    </div>
  );
}
