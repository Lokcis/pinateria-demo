import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Carrito } from "./carrito";
import { CartProvider } from "../context/cart-context";

describe("Carrito vacío", () => {
  it("muestra el logo del negocio y el aviso de que aún no hay productos", () => {
    const { container } = render(
      <CartProvider>
        <Carrito />
      </CartProvider>,
    );

    expect(screen.getByText("Aún no hay productos")).toBeInTheDocument();
    const logo = container.querySelector(".carrito-vacio img");
    expect(logo).toHaveAttribute("src", "/logo-demo.png");
  });
});
