import { useCart } from "../context/cart-context";
import { formatearMoneda } from "../utils/formato";
import { LogoImagen } from "./marca";

/**
 * Botón circular de cantidad (+ / −).
 *
 * @param {{etiqueta: string, alPulsar: () => void, children: React.ReactNode}} props
 * @returns {JSX.Element}
 */
function BotonCantidad({ etiqueta, alPulsar, children }) {
  return (
    <button
      type="button"
      onClick={alPulsar}
      aria-label={etiqueta}
      className="grid h-8 w-8 place-items-center rounded-full border border-tinta/15 bg-white text-lg font-bold leading-none transition hover:border-tinta hover:bg-papel active:scale-90"
    >
      {children}
    </button>
  );
}

/**
 * Carrito de compras: agregar, quitar y modificar cantidades antes de pagar (tarjeta #21).
 *
 * @returns {JSX.Element}
 */
export function Carrito() {
  const { items, quitarProducto, actualizarCantidad } = useCart();

  if (items.length === 0) {
    return (
      <div className="carrito carrito-vacio flex flex-col items-center px-4 py-8 text-center">
        <LogoImagen className="h-28 w-auto" />
        <p className="mt-3 font-display text-lg font-bold">Aún no hay productos</p>
        <p className="mt-1 max-w-56 text-sm text-tinta/60">Escanea un código o busca por nombre para empezar la venta.</p>
      </div>
    );
  }

  return (
    <div className="carrito divide-y divide-tinta/8">
      {items.map((item) => (
        <div key={item.productoId} className="animate-pop py-3 first:pt-0">
          <div className="flex items-start justify-between gap-3">
            <p className="font-semibold leading-snug">{item.nombre}</p>
            <button
              type="button"
              onClick={() => quitarProducto(item.productoId)}
              aria-label={`Quitar ${item.nombre}`}
              className="-mr-1 grid h-7 w-7 shrink-0 place-items-center rounded-full text-tinta/45 transition hover:bg-fucsia/10 hover:text-fucsia"
            >
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
                <path d="M6 6l12 12M18 6L6 18" />
              </svg>
            </button>
          </div>
          <div className="mt-2 flex items-center justify-between">
            <div className="control-cantidad flex items-center gap-2.5">
              <BotonCantidad
                etiqueta={`Disminuir cantidad de ${item.nombre}`}
                alPulsar={() => actualizarCantidad(item.productoId, item.cantidad - 1)}
              >
                −
              </BotonCantidad>
              <span className="w-6 text-center font-display text-lg font-extrabold tabular-nums">{item.cantidad}</span>
              <BotonCantidad
                etiqueta={`Aumentar cantidad de ${item.nombre}`}
                alPulsar={() => actualizarCantidad(item.productoId, item.cantidad + 1)}
              >
                +
              </BotonCantidad>
              <span className="ml-1 text-sm text-tinta/55">× {formatearMoneda(item.precioUnitario)}</span>
            </div>
            <p className="font-display text-lg font-extrabold tabular-nums">
              {formatearMoneda(item.precioUnitario * item.cantidad)}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
