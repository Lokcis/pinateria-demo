import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AvisoValidacion } from "./aviso-validacion";

function Formulario({ alEnviar = () => {} }) {
  return (
    <>
      <form
        onSubmit={(evento) => {
          evento.preventDefault();
          alEnviar();
        }}
      >
        <label>
          Cantidad
          <input type="number" min="1" defaultValue="-5" />
        </label>
        <label>
          Nombre
          <input required />
        </label>
        <button type="submit">Guardar</button>
      </form>
      <AvisoValidacion />
    </>
  );
}

describe("AvisoValidacion", () => {
  it("muestra el mensaje del navegador con el estilo de la aplicación y enfoca el primer campo con error", async () => {
    const alEnviar = vi.fn();
    render(<Formulario alEnviar={alEnviar} />);

    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));

    const aviso = await screen.findByRole("alert");
    expect(aviso.textContent).toContain(screen.getByLabelText("Cantidad").validationMessage);
    expect(aviso.textContent.length).toBeGreaterThan(2);
    expect(screen.getByLabelText("Cantidad")).toHaveFocus();
    expect(alEnviar).not.toHaveBeenCalled();
  });

  it("solo muestra un aviso aunque haya varios campos incorrectos", async () => {
    render(<Formulario />);

    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));

    expect(await screen.findAllByRole("alert")).toHaveLength(1);
  });

  it("se quita al corregir el campo", async () => {
    render(<Formulario />);
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await screen.findByRole("alert");

    await userEvent.clear(screen.getByLabelText("Cantidad"));
    await userEvent.type(screen.getByLabelText("Cantidad"), "3");

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("se quita con Escape", async () => {
    render(<Formulario />);
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    await screen.findByRole("alert");

    await userEvent.keyboard("{Escape}");

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("con el formulario correcto no muestra nada y deja enviar", async () => {
    const alEnviar = vi.fn();
    render(<Formulario alEnviar={alEnviar} />);
    await userEvent.clear(screen.getByLabelText("Cantidad"));
    await userEvent.type(screen.getByLabelText("Cantidad"), "2");
    await userEvent.type(screen.getByLabelText("Nombre"), "Ana");

    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));

    expect(alEnviar).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
