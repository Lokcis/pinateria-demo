import { Desplegable } from "./desplegable";

/**
 * Desplegable de quien realiza la venta (HU-08: RF-036).
 *
 * En el PC del punto de venta puede haber una sola sesion abierta mientras atienden distintas personas;
 * la venta queda a nombre de la persona elegida. Por defecto es el usuario de la sesion. No se muestra
 * si la lista no cargo: la venta se registra entonces a nombre de la sesion.
 *
 * @param {{
 *   vendedores: Array<{id: number, nombre: string}>,
 *   valor: string,
 *   alCambiar: (id: string) => void,
 *   deshabilitado?: boolean,
 * }} props `valor` es el id elegido, como texto.
 * @returns {JSX.Element | null}
 */
export function SelectorVendedor({ vendedores, valor, alCambiar, deshabilitado = false }) {
  if (vendedores.length === 0) return null;
  return (
    <section aria-label="Vendedor" className="flex items-center justify-between gap-2 rounded-xl border border-tinta/12 bg-white p-3">
      <p className="text-sm font-semibold text-tinta/65">Vendedor</p>
      <Desplegable
        value={valor}
        onChange={(evento) => alCambiar(evento.target.value)}
        disabled={deshabilitado}
        aria-label="Vendedor de la venta"
        className="min-w-44 rounded-lg border border-tinta/20 bg-white px-3 py-1.5 text-sm"
      >
        {vendedores.map((vendedor) => (
          <option key={vendedor.id} value={String(vendedor.id)}>
            {vendedor.nombre}
          </option>
        ))}
      </Desplegable>
    </section>
  );
}
