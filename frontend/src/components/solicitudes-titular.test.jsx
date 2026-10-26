import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SolicitudesTitular } from "./solicitudes-titular";
import { AuthProvider } from "../context/auth-context";
import * as apiClient from "../api/api-client";

vi.mock("../api/api-client", async () => {
  const modulo = await vi.importActual("../api/api-client");
  return { ...modulo, obtenerSolicitudes: vi.fn(), actualizarSolicitud: vi.fn(), obtenerEnlaceAutoregistro: vi.fn(), obtenerDatosNegocio: vi.fn() };
});

const SOLICITUD = {
  id: 10,
  cliente_id: 1,
  cliente_nombre: "María Pérez",
  tipo: "supresion",
  descripcion: "Quiere que borremos sus datos",
  estado: "recibida",
  recibida_en: "2026-10-12T15:00:00Z",
  fecha_limite: "2026-11-02",
  vencida: false,
  resuelta_en: null,
  atendida_por: null,
  respuesta: null,
};

function renderizar() {
  localStorage.setItem("mm_pos_token", `c.${btoa(JSON.stringify({ sub: "1", rol: "administrador" }))}.f`);
  return render(
    <AuthProvider>
      <SolicitudesTitular />
    </AuthProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  apiClient.obtenerSolicitudes.mockResolvedValue([SOLICITUD]);
  apiClient.obtenerDatosNegocio.mockResolvedValue({
    nombre: "", documento: "", direccion: "", telefono: "", correo_datos: "", responsable_datos: "",
    politica_version: "1.0", politica_fecha: "", version_vigente: "borrador", datos_completos: true, faltantes: [],
    actualizado_en: null,
  });
  apiClient.obtenerEnlaceAutoregistro.mockResolvedValue({
    existe: false, token: null, activo: false, actualizado_en: null, datos_completos: true, faltantes: [],
  });
  apiClient.actualizarSolicitud.mockResolvedValue({ ...SOLICITUD, estado: "en_tramite" });
});

describe("SolicitudesTitular (HU-07, RF-035)", () => {
  it("lista las pendientes con su fecha límite y pide solo las pendientes por defecto", async () => {
    renderizar();

    expect(await screen.findByText(/Supresión · María Pérez/)).toBeInTheDocument();
    expect(screen.getByText(/responder antes del .*nov.*2026/)).toBeInTheDocument();
    expect(screen.getByText("Recibida")).toBeInTheDocument();
    expect(apiClient.obtenerSolicitudes).toHaveBeenCalledWith({ pendientes: true }, expect.any(String));
  });

  it("marca las vencidas", async () => {
    apiClient.obtenerSolicitudes.mockResolvedValue([{ ...SOLICITUD, vencida: true }]);
    renderizar();

    expect(await screen.findByText("Vencida")).toBeInTheDocument();
  });

  it("al quitar el filtro trae todas", async () => {
    const usuario = userEvent.setup();
    renderizar();
    await screen.findByText(/Supresión/);

    await usuario.click(screen.getByRole("checkbox", { name: "Solo pendientes" }));

    await waitFor(() => expect(apiClient.obtenerSolicitudes).toHaveBeenLastCalledWith({ pendientes: false }, expect.any(String)));
  });

  it("pone la solicitud en trámite", async () => {
    const usuario = userEvent.setup();
    renderizar();

    await usuario.click(await screen.findByRole("button", { name: "Poner en trámite" }));

    await waitFor(() =>
      expect(apiClient.actualizarSolicitud).toHaveBeenCalledWith(10, { estado: "en_tramite", respuesta: null }, expect.any(String))
    );
  });

  it("resolver exige la respuesta y, en una supresión, pide confirmar el borrado de los datos", async () => {
    const usuario = userEvent.setup();
    renderizar();

    await usuario.click(await screen.findByRole("button", { name: "Resolver" }));
    const confirmar = screen.getByRole("button", { name: "Confirmar resolución" });
    expect(confirmar).toBeDisabled();

    await usuario.type(screen.getByLabelText(/Respuesta dada al titular/), "Se suprimieron sus datos.");
    await usuario.click(confirmar);

    const dialogo = await screen.findByRole("alertdialog");
    expect(dialogo).toHaveTextContent(/Se borrarán los datos personales/);
    expect(apiClient.actualizarSolicitud).not.toHaveBeenCalled(); // todavia no: falta aceptar

    await usuario.click(within(dialogo).getByRole("button", { name: "Resolver" }));
    await waitFor(() =>
      expect(apiClient.actualizarSolicitud).toHaveBeenCalledWith(
        10,
        { estado: "resuelta", respuesta: "Se suprimieron sus datos." },
        expect.any(String)
      )
    );
  });

  it("cancelar el cuadro de confirmación no resuelve nada", async () => {
    const usuario = userEvent.setup();
    renderizar();

    await usuario.click(await screen.findByRole("button", { name: "Resolver" }));
    await usuario.type(screen.getByLabelText(/Respuesta dada al titular/), "Listo");
    await usuario.click(screen.getByRole("button", { name: "Confirmar resolución" }));
    await usuario.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Cancelar" }));

    expect(apiClient.actualizarSolicitud).not.toHaveBeenCalled();
  });

  it("rechazar pide el motivo y no pide confirmación", async () => {
    const usuario = userEvent.setup();
    renderizar();

    await usuario.click(await screen.findByRole("button", { name: "Rechazar" }));
    await usuario.type(screen.getByLabelText(/motivo del rechazo/), "Tiene una obligación contable.");
    await usuario.click(screen.getByRole("button", { name: "Confirmar rechazo" }));

    await waitFor(() =>
      expect(apiClient.actualizarSolicitud).toHaveBeenCalledWith(
        10,
        { estado: "rechazada", respuesta: "Tiene una obligación contable." },
        expect.any(String)
      )
    );
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });

  it("una consulta se resuelve sin confirmación", async () => {
    const usuario = userEvent.setup();
    apiClient.obtenerSolicitudes.mockResolvedValue([{ ...SOLICITUD, tipo: "consulta" }]);
    renderizar();

    await usuario.click(await screen.findByRole("button", { name: "Resolver" }));
    await usuario.type(screen.getByLabelText(/Respuesta dada al titular/), "Se le envió la información.");
    await usuario.click(screen.getByRole("button", { name: "Confirmar resolución" }));

    await waitFor(() => expect(apiClient.actualizarSolicitud).toHaveBeenCalledTimes(1));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });

  it("las cerradas no tienen acciones y muestran quién respondió", async () => {
    apiClient.obtenerSolicitudes.mockResolvedValue([
      { ...SOLICITUD, estado: "resuelta", atendida_por: "Admin Uno", resuelta_en: "2026-10-13T15:00:00Z", respuesta: "Hecho" },
    ]);
    renderizar();

    expect(await screen.findByText(/Atendió Admin Uno/)).toHaveTextContent("Hecho");
    expect(screen.queryByRole("button", { name: "Resolver" })).not.toBeInTheDocument();
  });

  it("muestra el error del servidor", async () => {
    const usuario = userEvent.setup();
    apiClient.actualizarSolicitud.mockRejectedValue(new Error("La solicitud ya fue cerrada y no se puede modificar."));
    renderizar();

    await usuario.click(await screen.findByRole("button", { name: "Poner en trámite" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("ya fue cerrada");
  });
});
