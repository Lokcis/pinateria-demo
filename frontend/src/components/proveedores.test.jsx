import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Proveedores } from "./proveedores";
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
    obtenerProveedores: vi.fn(),
    crearProveedor: vi.fn(),
    editarProveedor: vi.fn(),
    eliminarProveedor: vi.fn(),
  };
});

const PROVEEDOR = {
  id: 1,
  nombre_empresa: "Papeles del Valle SAS",
  nombre_contacto: "Marta Ruiz",
  telefono: "3001112233",
  email: null,
  direccion: null,
  notas: null,
};

function renderizar() {
  localStorage.setItem("mm_pos_token", `c.${btoa(JSON.stringify({ sub: "1", rol: "administrador" }))}.f`);
  return render(
    <AuthProvider>
      <Proveedores />
    </AuthProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
});

describe("Proveedores", () => {
  it("lista el directorio", async () => {
    apiClient.obtenerProveedores.mockResolvedValue([PROVEEDOR]);
    renderizar();

    expect(await screen.findByText("Papeles del Valle SAS")).toBeInTheDocument();
    expect(screen.getByText(/Marta Ruiz/)).toBeInTheDocument();
  });

  it("da de alta un proveedor y recarga la lista", async () => {
    apiClient.obtenerProveedores.mockResolvedValue([]);
    apiClient.crearProveedor.mockResolvedValue({ ...PROVEEDOR, id: 2 });
    renderizar();
    await screen.findByText("No hay proveedores registrados.");

    await userEvent.click(screen.getByRole("button", { name: "Nuevo proveedor" }));
    await userEvent.type(screen.getByLabelText("Empresa"), "Confites SA");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() => expect(apiClient.crearProveedor).toHaveBeenCalled());
    expect(apiClient.crearProveedor.mock.calls[0][0]).toMatchObject({ nombre_empresa: "Confites SA", telefono: null });
    await waitFor(() => expect(apiClient.obtenerProveedores).toHaveBeenCalledTimes(2));
  });

  it("muestra el error del backend al eliminar un proveedor con compras", async () => {
    apiClient.obtenerProveedores.mockResolvedValue([PROVEEDOR]);
    apiClient.eliminarProveedor.mockRejectedValue(new Error("No se puede eliminar un proveedor con compras registradas."));
    renderizar();

    await userEvent.click(await screen.findByRole("button", { name: "Eliminar" }));
    await responderDialogo("Eliminar");

    expect(await screen.findByRole("alert")).toHaveTextContent("compras registradas");
  });

  it("el campo teléfono solo acepta números", async () => {
    apiClient.obtenerProveedores.mockResolvedValue([]);
    renderizar();
    await screen.findByText("No hay proveedores registrados.");

    await userEvent.click(screen.getByRole("button", { name: "Nuevo proveedor" }));
    await userEvent.type(screen.getByLabelText("Teléfono"), "300-abc 111");

    expect(screen.getByLabelText("Teléfono")).toHaveValue("300111");
    expect(screen.getByLabelText("Correo")).toHaveAttribute("type", "email");
  });
});
