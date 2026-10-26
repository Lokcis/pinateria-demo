import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Encabezado } from "./encabezado";
import { AuthProvider } from "../context/auth-context";

function renderizar(alCerrarSesion = () => {}, rol = "administrador") {
  localStorage.setItem("mm_pos_token", `c.${btoa(JSON.stringify({ sub: "1", rol }))}.f`);
  return render(
    <AuthProvider>
      <Encabezado usuario={{ sub: "1", rol }} alCerrarSesion={alCerrarSesion} />
    </AuthProvider>
  );
}

describe("Encabezado — menú de la cuenta", () => {
  it("empieza cerrado: solo muestra la marca y el botón de la cuenta con el rol", () => {
    renderizar();

    expect(screen.getByRole("button", { name: "Cuenta: Administrador" })).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cerrar sesión" })).not.toBeInTheDocument();
  });

  it("al abrirlo ofrece cambiar la contraseña y cerrar la sesión", async () => {
    const alCerrar = vi.fn();
    renderizar(alCerrar);

    await userEvent.click(screen.getByRole("button", { name: "Cuenta: Administrador" }));

    expect(screen.getByRole("menu", { name: "Cuenta" })).toHaveTextContent("Sesión: Administrador");
    expect(screen.getByRole("button", { name: "Cambiar contraseña" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("menuitem", { name: "Cerrar sesión" }));
    expect(alCerrar).toHaveBeenCalledTimes(1);
  });

  it("se cierra con Escape o al pulsar fuera", async () => {
    renderizar();
    const boton = screen.getByRole("button", { name: "Cuenta: Administrador" });

    await userEvent.click(boton);
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();

    await userEvent.click(boton);
    await userEvent.click(document.body);
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("el botón Cambiar contraseña abre su ventana sin cerrar el menú de golpe", async () => {
    renderizar();

    await userEvent.click(screen.getByRole("button", { name: "Cuenta: Administrador" }));
    await userEvent.click(screen.getByRole("button", { name: "Cambiar contraseña" }));

    expect(screen.getByRole("dialog", { name: "Cambiar contraseña" })).toBeInTheDocument();
  });

  it("muestra el rol que corresponde a cada usuario", () => {
    renderizar(() => {}, "propietario");

    expect(screen.getByRole("button", { name: "Cuenta: Propietario" })).toBeInTheDocument();
  });
});
