import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Categorias } from "./categorias";
import { CambiarPassword } from "./cambiar-password";
import { AuthProvider } from "../context/auth-context";
import * as apiClient from "../api/api-client";

/** Pulsa el boton del cuadro de confirmacion propio (reemplaza a window.confirm). */
async function responderDialogo(nombre) {
  const dialogo = await screen.findByRole("alertdialog");
  await userEvent.click(within(dialogo).getByRole("button", { name: nombre }));
}

vi.mock("../api/api-client", async () => {
  const modulo = await vi.importActual("../api/api-client");
  return {
    ...modulo,
    obtenerCategorias: vi.fn(),
    crearCategoria: vi.fn(),
    editarCategoria: vi.fn(),
    eliminarCategoria: vi.fn(),
    cambiarMiPassword: vi.fn(),
  };
});

const GLOBOS = { id: 1, nombre: "Globos", descripcion: "De látex" };

function renderizar(componente) {
  localStorage.setItem("mm_pos_token", `c.${btoa(JSON.stringify({ sub: "1", rol: "administrador" }))}.f`);
  return render(<AuthProvider>{componente}</AuthProvider>);
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
});

describe("Categorias (RF-017)", () => {
  it("lista las categorías", async () => {
    apiClient.obtenerCategorias.mockResolvedValue([GLOBOS]);
    renderizar(<Categorias />);

    expect(await screen.findByText("Globos")).toBeInTheDocument();
    expect(screen.getByText("De látex")).toBeInTheDocument();
  });

  it("da de alta una categoría y recarga", async () => {
    apiClient.obtenerCategorias.mockResolvedValue([]);
    apiClient.crearCategoria.mockResolvedValue(GLOBOS);
    renderizar(<Categorias />);
    await screen.findByText("No hay categorías registradas.");

    await userEvent.click(screen.getByRole("button", { name: "Nueva categoría" }));
    await userEvent.type(screen.getByLabelText("Nombre"), "Globos");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() => expect(apiClient.crearCategoria).toHaveBeenCalled());
    expect(apiClient.crearCategoria.mock.calls[0][0]).toEqual({ nombre: "Globos", descripcion: null });
    await waitFor(() => expect(apiClient.obtenerCategorias).toHaveBeenCalledTimes(2));
  });

  it("edita una categoría", async () => {
    apiClient.obtenerCategorias.mockResolvedValue([GLOBOS]);
    apiClient.editarCategoria.mockResolvedValue({ ...GLOBOS, nombre: "Globos metálicos" });
    renderizar(<Categorias />);

    await userEvent.click(await screen.findByRole("button", { name: "Editar Globos" }));
    const campo = screen.getByLabelText("Nombre");
    await userEvent.clear(campo);
    await userEvent.type(campo, "Globos metálicos");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() => expect(apiClient.editarCategoria).toHaveBeenCalled());
    expect(apiClient.editarCategoria.mock.calls[0].slice(0, 2)).toEqual([1, { nombre: "Globos metálicos", descripcion: "De látex" }]);
  });

  it("muestra el error al eliminar una categoría con productos", async () => {
    apiClient.obtenerCategorias.mockResolvedValue([GLOBOS]);
    apiClient.eliminarCategoria.mockRejectedValue(new Error("No se puede eliminar una categoria que tiene productos."));
    renderizar(<Categorias />);

    await userEvent.click(await screen.findByRole("button", { name: "Eliminar Globos" }));
    await responderDialogo("Eliminar");

    expect(await screen.findByRole("alert")).toHaveTextContent("tiene productos");
  });
});

describe("CambiarPassword (RF-015)", () => {
  it("cambia la contraseña propia", async () => {
    apiClient.cambiarMiPassword.mockResolvedValue(null);
    renderizar(<CambiarPassword />);

    await userEvent.click(screen.getByRole("button", { name: "Cambiar contraseña" }));
    await userEvent.type(screen.getByLabelText("Contraseña actual"), "vieja-clave-1");
    await userEvent.type(screen.getByLabelText(/Contraseña nueva/), "nueva-clave-2");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() =>
      expect(apiClient.cambiarMiPassword).toHaveBeenCalledWith("vieja-clave-1", "nueva-clave-2", expect.any(String))
    );
    expect(await screen.findByRole("status")).toHaveTextContent("actualizada");
  });

  it("muestra el error si la contraseña actual es incorrecta", async () => {
    apiClient.cambiarMiPassword.mockRejectedValue(new Error("La contrasena actual es incorrecta."));
    renderizar(<CambiarPassword />);

    await userEvent.click(screen.getByRole("button", { name: "Cambiar contraseña" }));
    await userEvent.type(screen.getByLabelText("Contraseña actual"), "mala");
    await userEvent.type(screen.getByLabelText(/Contraseña nueva/), "nueva-clave-2");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("incorrecta");
  });
});
