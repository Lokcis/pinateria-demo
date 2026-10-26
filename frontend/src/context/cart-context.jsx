import { createContext, useCallback, useContext, useMemo, useState } from "react";

const CartContext = createContext(null);

/**
 * Provee el estado del carrito de compras (tarjeta Trello #21).
 *
 * @param {{children: React.ReactNode}} props
 * @returns {JSX.Element}
 */
export function CartProvider({ children }) {
  const [items, setItems] = useState([]);

  const agregarProducto = useCallback((producto) => {
    setItems((itemsActuales) => {
      const yaExiste = itemsActuales.find((item) => item.productoId === producto.id);
      if (yaExiste) {
        return itemsActuales.map((item) =>
          item.productoId === producto.id ? { ...item, cantidad: item.cantidad + 1 } : item
        );
      }
      return [
        ...itemsActuales,
        {
          productoId: producto.id,
          nombre: producto.nombre,
          precioUnitario: Number(producto.precio_venta),
          cantidad: 1,
        },
      ];
    });
  }, []);

  const quitarProducto = useCallback((productoId) => {
    setItems((itemsActuales) => itemsActuales.filter((item) => item.productoId !== productoId));
  }, []);

  const actualizarCantidad = useCallback(
    (productoId, cantidad) => {
      if (cantidad <= 0) {
        quitarProducto(productoId);
        return;
      }
      setItems((itemsActuales) =>
        itemsActuales.map((item) => (item.productoId === productoId ? { ...item, cantidad } : item))
      );
    },
    [quitarProducto]
  );

  const vaciarCarrito = useCallback(() => setItems([]), []);

  const total = useMemo(
    () => items.reduce((acumulado, item) => acumulado + item.precioUnitario * item.cantidad, 0),
    [items]
  );

  const valor = useMemo(
    () => ({ items, agregarProducto, quitarProducto, actualizarCantidad, vaciarCarrito, total }),
    [items, agregarProducto, quitarProducto, actualizarCantidad, vaciarCarrito, total]
  );

  return <CartContext.Provider value={valor}>{children}</CartContext.Provider>;
}

/**
 * Hook de acceso al contexto del carrito.
 *
 * @returns {{
 *   items: Array<{productoId: number, nombre: string, precioUnitario: number, cantidad: number}>,
 *   agregarProducto: (producto: object) => void,
 *   quitarProducto: (productoId: number) => void,
 *   actualizarCantidad: (productoId: number, cantidad: number) => void,
 *   vaciarCarrito: () => void,
 *   total: number,
 * }}
 * @throws {Error} Si se usa fuera de un `CartProvider`.
 */
export function useCart() {
  const contexto = useContext(CartContext);
  if (contexto === null) {
    throw new Error("useCart debe usarse dentro de un CartProvider.");
  }
  return contexto;
}
