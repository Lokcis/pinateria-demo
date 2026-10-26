import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Navegacion } from "./navegacion";

const VISTAS = [
  { id: "venta", etiqueta: "Nueva venta", corta: "Vender", grupo: "Ventas", principal: true, icono: "venta" },
  { id: "historial", etiqueta: "Ventas de hoy", corta: "Hoy", grupo: "Ventas", principal: true, icono: "historial" },
  { id: "clientes", etiqueta: "Clientes", grupo: "Clientes", principal: true, icono: "clientes" },
  { id: "inventario", etiqueta: "Inventario", grupo: "Inventario y compras", icono: "inventario" },
  { id: "compras", etiqueta: "Compras", grupo: "Inventario y compras" },
  { id: "usuarios", etiqueta: "Usuarios", grupo: "Negocio" },
];

describe("Navegacion — pantalla ancha (menú lateral)", () => {
  it("muestra todas las secciones como pestañas verticales, agrupadas por tema", () => {
    render(<Navegacion vistas={VISTAS} vista="venta" alCambiar={() => {}} ancha />);

    expect(screen.getByRole("tablist")).toHaveAttribute("aria-orientation", "vertical");
    expect(screen.getAllByRole("tab")).toHaveLength(VISTAS.length);
    for (const grupo of ["Ventas", "Inventario y compras", "Negocio"]) {
      expect(screen.getByText(grupo)).toBeInTheDocument();
    }
    expect(screen.getAllByText("Clientes")).toHaveLength(2); // el título del grupo y la pestaña
    expect(screen.getByRole("tab", { name: "Nueva venta" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Compras" })).toHaveAttribute("aria-selected", "false");
  });

  it("cambia de sección al pulsar una pestaña", async () => {
    const alCambiar = vi.fn();
    render(<Navegacion vistas={VISTAS} vista="venta" alCambiar={alCambiar} ancha />);

    await userEvent.click(screen.getByRole("tab", { name: "Usuarios" }));

    expect(alCambiar).toHaveBeenCalledWith("usuarios");
  });
});

describe("Navegacion — celular (barra inferior)", () => {
  it("lleva directo las secciones principales con su nombre corto y un botón Más", () => {
    render(<Navegacion vistas={VISTAS} vista="venta" alCambiar={() => {}} ancha={false} />);

    expect(screen.getAllByRole("tab").map((t) => t.textContent)).toEqual(["Vender", "Hoy", "Clientes"]);
    expect(screen.getByRole("tab", { name: "Nueva venta" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("button", { name: "Más" })).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("Más abre el resto de secciones agrupadas y al elegir una cambia y cierra", async () => {
    const alCambiar = vi.fn();
    render(<Navegacion vistas={VISTAS} vista="venta" alCambiar={alCambiar} ancha={false} />);

    await userEvent.click(screen.getByRole("button", { name: "Más" }));
    const hoja = screen.getByRole("dialog", { name: "Más secciones" });
    expect(within(hoja).getByText("Inventario y compras")).toBeInTheDocument();
    expect(within(hoja).getByText("Negocio")).toBeInTheDocument();
    expect(within(hoja).queryByRole("button", { name: "Nueva venta" })).not.toBeInTheDocument(); // las principales no se repiten

    await userEvent.click(within(hoja).getByRole("button", { name: "Compras" }));

    expect(alCambiar).toHaveBeenCalledWith("compras");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("Más se marca como activo cuando la sección actual está dentro de él", () => {
    render(<Navegacion vistas={VISTAS} vista="usuarios" alCambiar={() => {}} ancha={false} />);

    expect(screen.getAllByRole("tab").every((t) => t.getAttribute("aria-selected") === "false")).toBe(true);
    expect(screen.getByRole("button", { name: "Más" })).toHaveClass("text-fucsia");
  });

  it("se puede cerrar el menú Más sin elegir nada", async () => {
    render(<Navegacion vistas={VISTAS} vista="venta" alCambiar={() => {}} ancha={false} />);

    await userEvent.click(screen.getByRole("button", { name: "Más" }));
    await userEvent.click(screen.getByRole("button", { name: "Cerrar" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("sin secciones secundarias no muestra el botón Más", () => {
    render(<Navegacion vistas={VISTAS.filter((v) => v.principal)} vista="venta" alCambiar={() => {}} ancha={false} />);

    expect(screen.queryByRole("button", { name: "Más" })).not.toBeInTheDocument();
  });
});
