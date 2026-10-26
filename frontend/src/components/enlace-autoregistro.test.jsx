import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { EnlaceAutoregistro } from "./enlace-autoregistro";
import { AuthProvider } from "../context/auth-context";
import * as apiClient from "../api/api-client";

vi.mock("../api/api-client", async () => {
  const modulo = await vi.importActual("../api/api-client");
  return {
    ...modulo,
    obtenerEnlaceAutoregistro: vi.fn(),
    generarEnlaceAutoregistro: vi.fn(),
    cambiarEstadoEnlaceAutoregistro: vi.fn(),
  };
});

const SIN_ENLACE = { existe: false, token: null, activo: false, actualizado_en: null, datos_completos: true, faltantes: [] };
const CON_ENLACE = { ...SIN_ENLACE, existe: true, token: "codigo-secreto-123", activo: true };

function renderizar() {
  localStorage.setItem("mm_pos_token", `c.${btoa(JSON.stringify({ sub: "1", rol: "administrador" }))}.f`);
  return render(
    <AuthProvider>
      <EnlaceAutoregistro />
    </AuthProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  apiClient.obtenerEnlaceAutoregistro.mockResolvedValue(CON_ENLACE);
});

/** HU-07: el administrador consulta, copia, desactiva y regenera el enlace (RF-048). */
describe("EnlaceAutoregistro", () => {
  it("muestra la dirección pública del enlace y su estado", async () => {
    renderizar();

    expect(await screen.findByLabelText("Dirección del enlace")).toHaveTextContent(`${window.location.origin}/registro/codigo-secreto-123`);
    expect(screen.getByText("Activo")).toBeInTheDocument();
  });

  it("copia la dirección al portapapeles", async () => {
    const usuario = userEvent.setup();
    renderizar();
    await screen.findByText("Activo"); // el enlace ya cargó

    await usuario.click(screen.getByRole("button", { name: "Copiar enlace" }));

    expect(await screen.findByRole("button", { name: "¡Copiado!" })).toBeInTheDocument();
    expect(await navigator.clipboard.readText()).toBe(`${window.location.origin}/registro/codigo-secreto-123`);
  });

  it("genera el primer enlace", async () => {
    const usuario = userEvent.setup();
    apiClient.obtenerEnlaceAutoregistro.mockResolvedValue(SIN_ENLACE);
    apiClient.generarEnlaceAutoregistro.mockResolvedValue(CON_ENLACE);
    renderizar();

    await usuario.click(await screen.findByRole("button", { name: "Generar enlace" }));

    expect(await screen.findByText("Activo")).toBeInTheDocument();
    expect(apiClient.generarEnlaceAutoregistro).toHaveBeenCalledTimes(1);
  });

  it("desactiva y vuelve a activar", async () => {
    const usuario = userEvent.setup();
    apiClient.cambiarEstadoEnlaceAutoregistro.mockResolvedValue({ ...CON_ENLACE, activo: false });
    renderizar();

    await usuario.click(await screen.findByRole("button", { name: "Desactivar" }));

    await waitFor(() => expect(apiClient.cambiarEstadoEnlaceAutoregistro).toHaveBeenCalledWith(false, expect.any(String)));
    expect(await screen.findByText("Desactivado")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Activar" })).toBeInTheDocument();
  });

  it("regenerar pide confirmar porque el enlace anterior deja de funcionar", async () => {
    const usuario = userEvent.setup();
    apiClient.generarEnlaceAutoregistro.mockResolvedValue({ ...CON_ENLACE, token: "codigo-nuevo-456" });
    renderizar();

    await usuario.click(await screen.findByRole("button", { name: "Generar enlace nuevo" }));
    const dialogo = await screen.findByRole("alertdialog");
    expect(dialogo).toHaveTextContent(/dejará de funcionar/);
    expect(apiClient.generarEnlaceAutoregistro).not.toHaveBeenCalled();

    await usuario.click(within(dialogo).getByRole("button", { name: "Generar nuevo" }));

    expect(await screen.findByLabelText("Dirección del enlace")).toHaveTextContent("codigo-nuevo-456");
  });

  it("cancelar la confirmación no cambia el enlace", async () => {
    const usuario = userEvent.setup();
    renderizar();

    await usuario.click(await screen.findByRole("button", { name: "Generar enlace nuevo" }));
    await usuario.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Cancelar" }));

    expect(apiClient.generarEnlaceAutoregistro).not.toHaveBeenCalled();
  });

  it("sin los datos del negocio avisa qué falta y no deja generarlo", async () => {
    apiClient.obtenerEnlaceAutoregistro.mockResolvedValue({
      ...SIN_ENLACE,
      datos_completos: false,
      faltantes: ["NEGOCIO_NIT", "NEGOCIO_CORREO_DATOS"],
    });
    renderizar();

    expect(await screen.findByRole("note")).toHaveTextContent(/NEGOCIO_NIT, NEGOCIO_CORREO_DATOS/);
    expect(screen.getByRole("button", { name: "Generar enlace" })).toBeDisabled();
  });

  it("muestra el error del servidor", async () => {
    const usuario = userEvent.setup();
    apiClient.cambiarEstadoEnlaceAutoregistro.mockRejectedValue(new Error("Faltan datos del negocio."));
    renderizar();

    await usuario.click(await screen.findByRole("button", { name: "Desactivar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Faltan datos del negocio.");
  });
});
