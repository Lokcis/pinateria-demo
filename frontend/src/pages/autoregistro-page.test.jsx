import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../app";
import { AutoregistroPage } from "./autoregistro-page";
import { ApiError } from "../api/api-client";
import * as apiClient from "../api/api-client";
import { POLITICA_PRUEBA } from "../utils/politica-prueba";

vi.mock("../api/api-client", async () => {
  const modulo = await vi.importActual("../api/api-client");
  return { ...modulo, obtenerAutoregistroPublico: vi.fn(), enviarAutoregistro: vi.fn() };
});

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  apiClient.obtenerAutoregistroPublico.mockResolvedValue(POLITICA_PRUEBA);
  apiClient.enviarAutoregistro.mockResolvedValue({ mensaje: "Recibimos tu registro. ¡Gracias!" });
});

/** HU-07: formulario público de autorregistro (RF-046 a RF-049). */
describe("AutoregistroPage", () => {
  it("abre sin sesión y muestra el aviso de privacidad y la política vigentes", async () => {
    render(<AutoregistroPage token="abc123" />);

    expect(await screen.findByText(/Tienda de Prueba \(NIT 900\) usará tus datos/)).toBeInTheDocument();
    expect(screen.getByText(/Política de Tratamiento de Datos \(versión 1\.0\)/)).toBeInTheDocument();
    expect(apiClient.obtenerAutoregistroPublico).toHaveBeenCalledWith("abc123");
  });

  it("no deja enviar sin marcar la aceptación; la casilla de promociones es aparte y viene desmarcada", async () => {
    const usuario = userEvent.setup();
    render(<AutoregistroPage token="abc123" />);

    const registrar = await screen.findByRole("button", { name: "Registrarme" });
    expect(registrar).toBeDisabled();
    const promociones = screen.getByRole("checkbox", { name: /promociones y novedades/ });
    expect(promociones).not.toBeChecked();

    await usuario.type(screen.getByLabelText(/^Nombre/), "Lucía Mora");
    await usuario.click(promociones); // solo promociones: sigue bloqueado
    expect(registrar).toBeDisabled();
    await usuario.click(screen.getByRole("checkbox", { name: /autorizo el tratamiento/ }));
    expect(registrar).toBeEnabled();
  });

  it("envía los datos con la aceptación y muestra el mensaje neutro", async () => {
    const usuario = userEvent.setup();
    render(<AutoregistroPage token="abc123" />);

    await usuario.type(await screen.findByLabelText(/^Nombre/), "Lucía Mora");
    await usuario.type(screen.getByLabelText(/^Teléfono/), "311-222 3344");
    await usuario.click(screen.getByRole("checkbox", { name: /autorizo el tratamiento/ }));
    await usuario.click(screen.getByRole("checkbox", { name: /promociones y novedades/ }));
    await usuario.click(screen.getByRole("button", { name: "Registrarme" }));

    await waitFor(() => expect(apiClient.enviarAutoregistro).toHaveBeenCalledTimes(1));
    expect(apiClient.enviarAutoregistro).toHaveBeenCalledWith("abc123", {
      nombre: "Lucía Mora",
      documento: null,
      telefono: "3112223344", // solo dígitos
      email: null,
      acepta_politica: true,
      acepta_publicidad: true,
      sitio_web: "",
    });
    expect(await screen.findByRole("status")).toHaveTextContent("Recibimos tu registro. ¡Gracias!");
    expect(screen.queryByRole("button", { name: "Registrarme" })).not.toBeInTheDocument();
  });

  it("incluye un campo trampa invisible para las personas y fuera del teclado", async () => {
    render(<AutoregistroPage token="abc123" />);

    const trampa = (await screen.findByLabelText("Sitio web", { selector: "input" }));
    expect(trampa).toHaveAttribute("tabindex", "-1");
    expect(trampa.closest("[aria-hidden='true']")).not.toBeNull();
  });

  it("rechaza un teléfono corto sin llamar al servidor", async () => {
    const usuario = userEvent.setup();
    render(<AutoregistroPage token="abc123" />);

    await usuario.type(await screen.findByLabelText(/^Nombre/), "Lucía");
    await usuario.type(screen.getByLabelText(/^Teléfono/), "12345");
    await usuario.click(screen.getByRole("checkbox", { name: /autorizo el tratamiento/ }));
    await usuario.click(screen.getByRole("button", { name: "Registrarme" }));

    expect(screen.getByRole("alert")).toHaveTextContent("al menos 7 dígitos");
    expect(apiClient.enviarAutoregistro).not.toHaveBeenCalled();
  });

  it("un enlace desactivado o regenerado muestra un mensaje claro y no ofrece el formulario", async () => {
    apiClient.obtenerAutoregistroPublico.mockRejectedValue(
      new ApiError("Este enlace no está disponible. Pide uno nuevo en la tienda.", 404)
    );
    render(<AutoregistroPage token="viejo" />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Este enlace no está disponible");
    expect(screen.queryByRole("button", { name: "Registrarme" })).not.toBeInTheDocument();
  });

  it("muestra el error si hay demasiados envíos (429)", async () => {
    const usuario = userEvent.setup();
    apiClient.enviarAutoregistro.mockRejectedValue(new ApiError("Demasiados intentos. Inténtalo de nuevo más tarde.", 429));
    render(<AutoregistroPage token="abc123" />);

    await usuario.type(await screen.findByLabelText(/^Nombre/), "Lucía");
    await usuario.click(screen.getByRole("checkbox", { name: /autorizo el tratamiento/ }));
    await usuario.click(screen.getByRole("button", { name: "Registrarme" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Demasiados intentos");
  });
});

describe("App — ruta pública /registro/<código>", () => {
  it("la dirección /registro/<código> abre el formulario público sin pedir inicio de sesión", async () => {
    window.history.pushState({}, "", "/registro/mi-codigo");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Regístrate como cliente" })).toBeInTheDocument();
    expect(apiClient.obtenerAutoregistroPublico).toHaveBeenCalledWith("mi-codigo");
    expect(screen.queryByRole("button", { name: "Ingresar" })).not.toBeInTheDocument();
    window.history.pushState({}, "", "/");
  });

  it("cualquier otra dirección sigue pidiendo iniciar sesión", () => {
    window.history.pushState({}, "", "/");
    render(<App />);

    expect(screen.getByRole("button", { name: "Ingresar" })).toBeInTheDocument();
  });
});
