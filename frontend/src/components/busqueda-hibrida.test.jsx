import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { BusquedaHibrida } from "./busqueda-hibrida";
import { AuthProvider } from "../context/auth-context";
import { CartProvider, useCart } from "../context/cart-context";
import * as apiClient from "../api/api-client";

vi.mock("../api/api-client", async () => {
  const modulo = await vi.importActual("../api/api-client");
  return { ...modulo, buscarProductos: vi.fn() };
});

const PRODUCTO_DE_PRUEBA = {
  id: 1,
  nombre: "Piñata Mickey Mouse",
  descripcion: null,
  categoria_id: 1,
  codigo_barras: "7501234567890",
  tipo: "unidad",
  precio_venta: "25000.00",
  stock_actual: 10,
  stock_minimo: 5,
  activo: true,
};

/**
 * Consumidor minimo del carrito, solo para poder aserir su estado desde la prueba.
 *
 * @returns {JSX.Element}
 */
function ResumenCarritoParaPrueba() {
  const { items } = useCart();
  return <div data-testid="resumen-carrito">{items.length} items</div>;
}

/**
 * Renderiza `BusquedaHibrida` con los providers reales que necesita.
 *
 * @returns {ReturnType<typeof render>}
 */
function renderizarConProviders() {
  return render(
    <AuthProvider>
      <CartProvider>
        <BusquedaHibrida />
        <ResumenCarritoParaPrueba />
      </CartProvider>
    </AuthProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
});

describe("BusquedaHibrida", () => {
  it("HU-01: al escanear (rafaga rapida) agrega el producto de inmediato, sin clics adicionales", async () => {
    apiClient.buscarProductos.mockResolvedValue([PRODUCTO_DE_PRUEBA]);
    renderizarConProviders();

    const input = screen.getByLabelText(/escanear o buscar producto/i);
    const usuario = userEvent.setup({ delay: 5 }); // ráfaga: 5ms entre teclas, bajo el umbral de 50ms

    await usuario.type(input, "7501234567890");
    await usuario.keyboard("{Enter}");

    await waitFor(() => {
      expect(screen.getByTestId("resumen-carrito")).toHaveTextContent("1 items");
    });

    // Sin clics: no debe haber renderizado una lista de resultados para elegir.
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
    expect(input).toHaveValue("");
  });

  it("con tecleo manual (lento) muestra la lista de resultados en vez de agregar directo", async () => {
    apiClient.buscarProductos.mockResolvedValue([PRODUCTO_DE_PRUEBA]);
    renderizarConProviders();

    const input = screen.getByLabelText(/escanear o buscar producto/i);
    const usuario = userEvent.setup({ delay: 200 }); // tecleo humano normal

    await usuario.type(input, "mickey");
    await usuario.keyboard("{Enter}");

    await waitFor(() => {
      expect(screen.getByText(/Piñata Mickey Mouse/)).toBeInTheDocument();
    });

    // No se agrego automaticamente: el carrito sigue vacio hasta que el
    // vendedor haga clic sobre el resultado.
    expect(screen.getByTestId("resumen-carrito")).toHaveTextContent("0 items");
  });
});
