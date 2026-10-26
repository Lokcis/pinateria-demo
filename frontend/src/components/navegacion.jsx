import { useState } from "react";

/**
 * Iconos de la barra inferior (trazo simple, heredan el color del texto).
 *
 * @param {{d: string}} props `d` es el trazo del SVG.
 * @returns {JSX.Element}
 */
function Icono({ d }) {
  return (
    <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={d} />
    </svg>
  );
}

const ICONOS = {
  venta: "M6 6h15l-1.5 9h-12zM6 6 5 3H2M9 20.5a1 1 0 1 0 0-.01M18 20.5a1 1 0 1 0 0-.01",
  historial: "M12 7v5l3 2M21 12a9 9 0 1 1-3-6.7M21 4v4h-4",
  clientes: "M16 19v-1.5a3.5 3.5 0 0 0-3.5-3.5h-4A3.5 3.5 0 0 0 5 17.5V19M10.5 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6M19 19v-1.2a3 3 0 0 0-2-2.8M15.5 5.2a3 3 0 0 1 0 5.6",
  inventario: "M3 7.5 12 3l9 4.5v9L12 21l-9-4.5zM3 7.5l9 4.5 9-4.5M12 12v9",
  mas: "M5 12h.01M12 12h.01M19 12h.01",
};

/**
 * Agrupa las vistas por su grupo, conservando el orden en que aparecen.
 *
 * @param {Array<{id: string, etiqueta: string, grupo: string}>} vistas
 * @returns {Array<{nombre: string, vistas: Array<object>}>}
 */
function agrupar(vistas) {
  const grupos = [];
  for (const vista of vistas) {
    let grupo = grupos.find((g) => g.nombre === vista.grupo);
    if (!grupo) {
      grupo = { nombre: vista.grupo, vistas: [] };
      grupos.push(grupo);
    }
    grupo.vistas.push(vista);
  }
  return grupos;
}

/**
 * Menu lateral para pantallas anchas: las secciones agrupadas por tema, siempre a la vista.
 *
 * @param {{vistas: Array<object>, vista: string, alCambiar: (id: string) => void}} props
 * @returns {JSX.Element}
 */
function MenuLateral({ vistas, vista, alCambiar }) {
  return (
    <nav aria-label="Secciones del punto de venta" className="xl:sticky xl:top-4 xl:self-start">
      <div role="tablist" aria-orientation="vertical" aria-label="Secciones del punto de venta" className="flex flex-col gap-5">
        {agrupar(vistas).map((grupo) => (
          <div key={grupo.nombre} role="presentation">
            <p className="px-3 text-[11px] font-bold uppercase tracking-[0.14em] text-tinta/45">{grupo.nombre}</p>
            <div role="presentation" className="mt-1 flex flex-col gap-0.5">
              {grupo.vistas.map((opcion) => (
                <button
                  key={opcion.id}
                  type="button"
                  role="tab"
                  aria-selected={vista === opcion.id}
                  onClick={() => alCambiar(opcion.id)}
                  className={`rounded-xl px-3 py-2 text-left text-sm font-semibold transition ${
                    vista === opcion.id ? "bg-white shadow-sm" : "text-tinta/65 hover:bg-white/60 hover:text-tinta"
                  }`}
                >
                  {opcion.etiqueta}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </nav>
  );
}

/**
 * Barra inferior para celular: las secciones de uso diario y, si hay mas, un boton "Mas" que abre el resto.
 *
 * @param {{vistas: Array<object>, vista: string, alCambiar: (id: string) => void}} props
 * @returns {JSX.Element}
 */
function BarraInferior({ vistas, vista, alCambiar }) {
  const [masAbierto, setMasAbierto] = useState(false);
  const principales = vistas.filter((v) => v.principal);
  const secundarias = vistas.filter((v) => !v.principal);
  const enSecundaria = secundarias.some((v) => v.id === vista);

  /**
   * Cambia de seccion y cierra el menu "Mas".
   *
   * @param {string} id
   */
  function ir(id) {
    setMasAbierto(false);
    alCambiar(id);
  }

  return (
    <>
      {masAbierto && (
        <div className="fixed inset-0 z-40" onClick={(evento) => evento.target === evento.currentTarget && setMasAbierto(false)}>
          <div className="absolute inset-0 bg-tinta/40" aria-hidden="true" onClick={() => setMasAbierto(false)} />
          <div
            role="dialog"
            aria-label="Más secciones"
            className="absolute inset-x-0 bottom-0 max-h-[80vh] animate-subir overflow-y-auto rounded-t-3xl bg-papel p-5 pb-24 shadow-2xl"
          >
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-display text-lg font-extrabold">Más secciones</h2>
              <button type="button" onClick={() => setMasAbierto(false)} className="rounded-lg px-2 py-1 text-sm font-semibold text-tinta/60">
                Cerrar
              </button>
            </div>
            {agrupar(secundarias).map((grupo) => (
              <section key={grupo.nombre} className="mb-4">
                <p className="mb-1.5 text-[11px] font-bold uppercase tracking-[0.14em] text-tinta/45">{grupo.nombre}</p>
                <div className="grid grid-cols-2 gap-2">
                  {grupo.vistas.map((opcion) => (
                    <button
                      key={opcion.id}
                      type="button"
                      aria-current={vista === opcion.id ? "page" : undefined}
                      onClick={() => ir(opcion.id)}
                      className={`rounded-2xl border px-3 py-3 text-left text-sm font-semibold ${
                        vista === opcion.id ? "border-fucsia bg-white text-fucsia-osc" : "border-tinta/10 bg-white"
                      }`}
                    >
                      {opcion.etiqueta}
                    </button>
                  ))}
                </div>
              </section>
            ))}
          </div>
        </div>
      )}

      <nav
        aria-label="Secciones del punto de venta"
        className="fixed inset-x-0 bottom-0 z-50 border-t border-tinta/10 bg-white pb-[env(safe-area-inset-bottom)]"
      >
        <div role="tablist" aria-label="Secciones del punto de venta" className="mx-auto flex max-w-md">
          {principales.map((opcion) => (
            <button
              key={opcion.id}
              type="button"
              role="tab"
              aria-selected={vista === opcion.id && !masAbierto}
              aria-label={opcion.etiqueta}
              onClick={() => ir(opcion.id)}
              className={`flex flex-1 flex-col items-center gap-0.5 px-1 pb-2 pt-2.5 text-[11px] font-bold ${
                vista === opcion.id && !masAbierto ? "text-fucsia" : "text-tinta/55"
              }`}
            >
              <Icono d={ICONOS[opcion.icono] ?? ICONOS.venta} />
              {opcion.corta ?? opcion.etiqueta}
            </button>
          ))}
          {secundarias.length > 0 && (
            <button
              type="button"
              aria-expanded={masAbierto}
              aria-label="Más"
              onClick={() => setMasAbierto((abierto) => !abierto)}
              className={`flex flex-1 flex-col items-center gap-0.5 px-1 pb-2 pt-2.5 text-[11px] font-bold ${
                masAbierto || enSecundaria ? "text-fucsia" : "text-tinta/55"
              }`}
            >
              <Icono d={ICONOS.mas} />
              Más
            </button>
          )}
        </div>
      </nav>
    </>
  );
}

/**
 * Navegacion principal del punto de venta: menu lateral en pantallas anchas y barra inferior en celular.
 *
 * Es la misma lista de secciones en ambos casos; solo cambia como se presenta. Cada seccion indica su
 * `grupo`, si es `principal` (va directo en la barra del celular), su etiqueta `corta` y su `icono`.
 *
 * @param {{
 *   vistas: Array<{id: string, etiqueta: string, grupo: string, principal?: boolean, corta?: string, icono?: string}>,
 *   vista: string,
 *   alCambiar: (id: string) => void,
 *   ancha: boolean,
 * }} props
 * @returns {JSX.Element}
 */
export function Navegacion({ vistas, vista, alCambiar, ancha }) {
  return ancha ? (
    <MenuLateral vistas={vistas} vista={vista} alCambiar={alCambiar} />
  ) : (
    <BarraInferior vistas={vistas} vista={vista} alCambiar={alCambiar} />
  );
}
