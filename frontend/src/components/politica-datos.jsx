/**
 * Una seccion de la politica: titulo, parrafos y vinetas.
 *
 * @param {{seccion: {titulo: string, parrafos: string[], items: string[]}}} props
 * @returns {JSX.Element}
 */
function SeccionPolitica({ seccion }) {
  return (
    <section className="mt-3">
      <h4 className="text-sm font-bold">{seccion.titulo}</h4>
      {seccion.parrafos.map((parrafo) => (
        <p key={parrafo} className="mt-1 text-sm text-tinta/80">
          {parrafo}
        </p>
      ))}
      {seccion.items.length > 0 && (
        <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-tinta/80">
          {seccion.items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

/**
 * Aviso de privacidad y Politica de Tratamiento de Datos vigentes (Ley 1581 de 2012; HU-07).
 *
 * Muestra el aviso corto y, desplegable, la politica completa. El texto lo arma el backend
 * (`GET /clientes/politica` o la ruta publica del autorregistro): asi lo que se lee es lo que queda
 * registrado como version aceptada.
 *
 * @param {{politica: object | null}} props Ver `PoliticaOut`.
 * @returns {JSX.Element | null}
 */
export function PoliticaDatos({ politica }) {
  if (!politica) return null;
  return (
    <div className="rounded-xl border border-tinta/12 bg-white p-3">
      <p className="text-xs font-bold uppercase tracking-wide text-tinta/55">Aviso de privacidad</p>
      <p className="mt-1 text-sm text-tinta/85">{politica.aviso}</p>
      <details className="mt-2">
        <summary className="cursor-pointer text-sm font-semibold text-fucsia-osc">
          Política de Tratamiento de Datos (versión {politica.version})
        </summary>
        <div className="mt-1 max-h-72 overflow-y-auto pr-1">
          {politica.secciones.map((seccion) => (
            <SeccionPolitica key={seccion.titulo} seccion={seccion} />
          ))}
        </div>
      </details>
      {!politica.datos_completos && (
        <p role="note" className="mt-2 rounded-lg bg-sol/25 px-2.5 py-1.5 text-xs font-medium">
          Faltan datos del negocio ({politica.faltantes.join(", ")}): complétalos en “Datos personales › Datos del
          negocio”. Mientras tanto la política queda como borrador y cada autorización se guarda con la versión “borrador”.
        </p>
      )}
    </div>
  );
}
