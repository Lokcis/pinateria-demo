import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DatosNegocio } from "./datos-negocio";
import { AuthProvider } from "../context/auth-context";
import * as apiClient from "../api/api-client";

vi.mock("../api/api-client", async () => {
  const modulo = await vi.importActual("../api/api-client");
  return { ...modulo, obtenerDatosNegocio: vi.fn(), guardarDatosNegocio: vi.fn() };
});

const VACIO = {
  nombre: "",
  documento: "",
  direccion: "",
  telefono: "",
  correo_datos: "",
  responsable_datos: "",
  politica_version: "1.0",
  politica_fecha: "",
  version_vigente: "borrador",
  datos_completos: false,
  faltantes: ["Nombre del negocio", "NIT o cédula", "Correo para solicitudes de datos"],
  actualizado_en: null,
};
const COMPLETO = {
  ...VACIO,
  nombre: "Piñatería Demo",
  documento: "900.123.456-7",
  direccion: "Calle 123 # 45-67, Bogotá",
  telefono: "3000000000",
  correo_datos: "datos@ejemplo.com",
  politica_fecha: "12-10-2026",
  version_vigente: "1.0",
  datos_completos: true,
  faltantes: [],
};

function renderizar(propiedades = {}) {
  localStorage.setItem("mm_pos_token", `c.${btoa(JSON.stringify({ sub: "1", rol: "administrador" }))}.f`);
  return render(
    <AuthProvider>
      <DatosNegocio {...propiedades} />
    </AuthProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  apiClient.obtenerDatosNegocio.mockResolvedValue(VACIO);
});

describe("DatosNegocio (HU-07): datos del responsable, editables desde la aplicación", () => {
  it("al inicio avisa qué falta y que la política queda como borrador", async () => {
    renderizar();

    expect(await screen.findByRole("note")).toHaveTextContent(/Falta: Nombre del negocio, NIT o cédula, Correo para solicitudes de datos/);
    expect(screen.getByRole("note")).toHaveTextContent(/borrador/);
  });

  it("explica que cualquier correo sirve, no solo uno del dominio", async () => {
    renderizar();

    expect(await screen.findByText(/Cualquier correo sirve/)).toBeInTheDocument();
  });

  it("guarda los datos escritos y avisa la versión que quedará en las autorizaciones", async () => {
    const usuario = userEvent.setup();
    const alGuardar = vi.fn();
    apiClient.guardarDatosNegocio.mockResolvedValue(COMPLETO);
    renderizar({ alGuardar });

    await usuario.type(await screen.findByLabelText(/Nombre o razón social/), "Piñatería Demo");
    await usuario.type(screen.getByLabelText(/NIT o cédula/), "900.123.456-7");
    await usuario.type(screen.getByLabelText(/Dirección y ciudad/), "Calle 123 # 45-67, Bogotá");
    await usuario.type(screen.getByLabelText(/Teléfono de la tienda/), "3000000000");
    await usuario.type(screen.getByLabelText(/Correo para consultas/), "datos@ejemplo.com");
    await usuario.type(screen.getByLabelText(/Fecha desde la que rige/), "12-10-2026");
    await usuario.click(screen.getByRole("button", { name: "Guardar datos" }));

    await waitFor(() => expect(apiClient.guardarDatosNegocio).toHaveBeenCalledTimes(1));
    expect(apiClient.guardarDatosNegocio.mock.calls[0][0]).toMatchObject({
      nombre: "Piñatería Demo",
      documento: "900.123.456-7",
      correo_datos: "datos@ejemplo.com",
      politica_fecha: "12-10-2026",
      politica_version: "1.0",
    });
    expect(await screen.findByRole("status")).toHaveTextContent(/versión 1\.0/);
    expect(screen.queryByRole("note")).not.toBeInTheDocument(); // ya no falta nada
    expect(alGuardar).toHaveBeenCalledTimes(1);
  });

  it("si queda algo sin completar lo dice y no promete versión oficial", async () => {
    const usuario = userEvent.setup();
    apiClient.guardarDatosNegocio.mockResolvedValue({ ...VACIO, nombre: "Mi tienda", faltantes: ["NIT o cédula"] });
    renderizar();

    await usuario.type(await screen.findByLabelText(/Nombre o razón social/), "Mi tienda");
    await usuario.click(screen.getByRole("button", { name: "Guardar datos" }));

    expect(await screen.findByRole("status")).toHaveTextContent(/aún falta completar/);
  });

  it("carga los datos ya guardados en el formulario", async () => {
    apiClient.obtenerDatosNegocio.mockResolvedValue(COMPLETO);
    renderizar();

    expect(await screen.findByLabelText(/Correo para consultas/)).toHaveValue("datos@ejemplo.com");
    expect(screen.queryByRole("note")).not.toBeInTheDocument();
  });

  it("muestra el error del servidor al guardar (correo mal escrito)", async () => {
    const usuario = userEvent.setup();
    apiClient.guardarDatosNegocio.mockRejectedValue(new Error("El correo no tiene un formato valido."));
    renderizar();

    await usuario.click(await screen.findByRole("button", { name: "Guardar datos" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("El correo no tiene un formato valido.");
  });
});
