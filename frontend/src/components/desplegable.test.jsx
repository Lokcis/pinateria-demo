import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { Desplegable } from "./desplegable";

function Ejemplo({ alCambiar = () => {} }) {
  const [valor, setValor] = useState("");
  return (
    <form>
      <label>
        <span>Tipo</span>
        <Desplegable
          value={valor}
          onChange={(evento) => {
            setValor(evento.target.value);
            alCambiar(evento.target.value);
          }}
          required
        >
          <option value="" disabled>
            Elige…
          </option>
          <option value="paquete">Paquete</option>
          <option value="ancheta">Ancheta</option>
        </Desplegable>
      </label>
    </form>
  );
}

describe("Desplegable", () => {
  it("muestra el placeholder, abre el menú y elige una opción con el mouse", async () => {
    const alCambiar = vi.fn();
    render(<Ejemplo alCambiar={alCambiar} />);
    const combo = screen.getByRole("combobox");
    expect(combo).toHaveTextContent("Elige…");

    await userEvent.click(combo);
    expect(screen.getAllByRole("option")).toHaveLength(2); // la opción deshabilitada no se lista
    await userEvent.click(screen.getByRole("option", { name: "Ancheta" }));

    expect(alCambiar).toHaveBeenCalledWith("ancheta");
    expect(combo).toHaveTextContent("Ancheta");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("se maneja con el teclado y Escape lo cierra sin cambiar", async () => {
    const alCambiar = vi.fn();
    render(<Ejemplo alCambiar={alCambiar} />);
    screen.getByRole("combobox").focus();

    await userEvent.keyboard("{ArrowDown}{ArrowDown}{Enter}");
    expect(alCambiar).toHaveBeenCalledWith("ancheta");

    await userEvent.keyboard("{ArrowDown}");
    expect(screen.getByRole("listbox")).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("cierra el menú al hacer clic fuera", async () => {
    render(<Ejemplo />);
    await userEvent.click(screen.getByRole("combobox"));
    await userEvent.click(document.body);
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("required bloquea el envío mientras no haya selección", async () => {
    render(<Ejemplo />);
    const form = screen.getByRole("combobox").closest("form");
    expect(form.checkValidity()).toBe(false);
    await userEvent.click(screen.getByRole("combobox"));
    await userEvent.click(screen.getByRole("option", { name: "Paquete" }));
    expect(form.checkValidity()).toBe(true);
  });
});
