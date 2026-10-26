import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LogoImagen, Logotipo } from "./marca";

describe("Logotipo / LogoImagen (identidad visual)", () => {
  it("el logotipo muestra el logo oficial y el nombre escrito (el logo es decorativo para los lectores de pantalla)", () => {
    const { container } = render(<Logotipo />);

    expect(screen.getByText("Piñatería Demo")).toBeInTheDocument();
    expect(screen.getByText("Piñatería")).toBeInTheDocument();
    const imagen = container.querySelector("img");
    expect(imagen).toHaveAttribute("src", "/logo-demo.png");
    expect(imagen).toHaveAttribute("alt", "");
    expect(imagen).toHaveAttribute("aria-hidden", "true");
  });

  it("el tamaño grande agranda el logo", () => {
    const { container } = render(<Logotipo grande />);

    expect(container.querySelector("img")).toHaveClass("h-16");
  });

  it("el logo es un PNG transparente y lleva sus proporciones para evitar saltos al cargar", () => {
    const { container } = render(<LogoImagen />);

    const imagen = container.querySelector("img");
    expect(imagen).toHaveAttribute("src", "/logo-demo.png");
    expect(imagen).toHaveAttribute("width", "1024");
    expect(imagen).toHaveAttribute("height", "719");
  });
});
