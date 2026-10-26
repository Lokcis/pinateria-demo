import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Usuarios } from "./usuarios";
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
    obtenerUsuarios: vi.fn(),
    crearUsuario: vi.fn(),
    editarUsuario: vi.fn(),
    restablecerPassword: vi.fn(),
  };
});

const YO = { id: 1, nombre: "Dueña Admin", username: "admin", rol: "administrador", activo: true };
const ANA = { id: 2, nombre: "Ana Pérez", username: "ana", rol: "vendedor", activo: true };

function renderizar() {
  localStorage.setItem("mm_pos_token", `c.${btoa(JSON.stringify({ sub: "1", rol: "administrador" }))}.f`);
  return render(
    <AuthProvider>
      <Usuarios />
    </AuthProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
});

describe("Usuarios (RF-015)", () => {
  it("lista los usuarios y no permite desactivarse a sí mismo", async () => {
    apiClient.obtenerUsuarios.mockResolvedValue([YO, ANA]);
    renderizar();

    expect(await screen.findByText("Ana Pérez")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Desactivar Ana Pérez" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Desactivar Dueña Admin" })).not.toBeInTheDocument();
  });

  it("crea un usuario con contraseña temporal y recarga la lista", async () => {
    apiClient.obtenerUsuarios.mockResolvedValue([YO]);
    apiClient.crearUsuario.mockResolvedValue({ ...ANA });
    renderizar();
    await screen.findByText("Dueña Admin");

    await userEvent.click(screen.getByRole("button", { name: "Nuevo usuario" }));
    await userEvent.type(screen.getByLabelText("Nombre"), "Ana Pérez");
    await userEvent.type(screen.getByLabelText("Usuario"), "ana");
    await userEvent.type(screen.getByLabelText("Contraseña temporal"), "temporal-123");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() => expect(apiClient.crearUsuario).toHaveBeenCalled());
    expect(apiClient.crearUsuario.mock.calls[0][0]).toMatchObject({
      nombre: "Ana Pérez",
      username: "ana",
      password: "temporal-123",
      rol: "vendedor",
    });
    await waitFor(() => expect(apiClient.obtenerUsuarios).toHaveBeenCalledTimes(2));
  });

  it("desactiva a un usuario tras confirmar", async () => {
    apiClient.obtenerUsuarios.mockResolvedValue([YO, ANA]);
    apiClient.editarUsuario.mockResolvedValue({ ...ANA, activo: false });
    renderizar();

    await userEvent.click(await screen.findByRole("button", { name: "Desactivar Ana Pérez" }));
    await responderDialogo("Desactivar");

    await waitFor(() => expect(apiClient.editarUsuario).toHaveBeenCalledWith(2, { activo: false }, expect.any(String)));
  });

  it("restablece la contraseña temporal", async () => {
    apiClient.obtenerUsuarios.mockResolvedValue([YO, ANA]);
    apiClient.restablecerPassword.mockResolvedValue(null);
    vi.spyOn(window, "prompt").mockReturnValue("temporal-nueva-1");
    renderizar();

    await userEvent.click(await screen.findByRole("button", { name: "Restablecer contraseña de Ana Pérez" }));

    await waitFor(() => expect(apiClient.restablecerPassword).toHaveBeenCalledWith(2, "temporal-nueva-1", expect.any(String)));
    expect(await screen.findByRole("status")).toHaveTextContent("restablecida");
  });

  it("muestra el error del backend (usuario duplicado)", async () => {
    apiClient.obtenerUsuarios.mockResolvedValue([YO]);
    apiClient.crearUsuario.mockRejectedValue(new Error("Ya existe un usuario con ese nombre de usuario."));
    renderizar();
    await screen.findByText("Dueña Admin");

    await userEvent.click(screen.getByRole("button", { name: "Nuevo usuario" }));
    await userEvent.type(screen.getByLabelText("Nombre"), "Otra");
    await userEvent.type(screen.getByLabelText("Usuario"), "admin");
    await userEvent.type(screen.getByLabelText("Contraseña temporal"), "temporal-123");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Ya existe");
  });

  it("al editarse a sí mismo el selector de rol queda bloqueado", async () => {
    apiClient.obtenerUsuarios.mockResolvedValue([YO, ANA]);
    renderizar();

    await userEvent.click(await screen.findByRole("button", { name: "Editar Dueña Admin" }));

    expect(screen.getByLabelText("Rol")).toBeDisabled();
  });
});
