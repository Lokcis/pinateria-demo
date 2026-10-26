import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Descuentos } from "./descuentos";
import { AuthProvider } from "../context/auth-context";
import * as apiClient from "../api/api-client";

vi.mock("../api/api-client", async () => {
  const modulo = await vi.importActual("../api/api-client");
  return {
    ...modulo,
    obtenerConfiguracionDescuentos: vi.fn(),
    guardarDescuentoGeneral: vi.fn(),
    guardarTopesDescuento: vi.fn(),
  };
});

const SIN_CONFIGURAR = {
  general: null,
  topes: { tope_porcentaje: null, tope_monto: null, descripcion: "sin límite" },
};

function renderizar() {
  return render(
    <AuthProvider>
      <Descuentos />
    </AuthProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  apiClient.obtenerConfiguracionDescuentos.mockResolvedValue(SIN_CONFIGURAR);
});

/** HU-06: el administrador configura el descuento general y los topes del descuento manual. */
describe("Descuentos (administrador)", () => {
  it("guarda el descuento general en porcentaje y activo", async () => {
    const usuario = userEvent.setup();
    apiClient.guardarDescuentoGeneral.mockResolvedValue({
      ...SIN_CONFIGURAR,
      general: { tipo: "porcentaje", valor: "5.00", activo: true },
    });
    renderizar();

    await usuario.type(await screen.findByRole("textbox", { name: "Valor (%)" }), "5");
    await usuario.click(screen.getByRole("checkbox", { name: "Activo" }));
    await usuario.click(screen.getByRole("button", { name: "Guardar descuento general" }));

    await waitFor(() =>
      expect(apiClient.guardarDescuentoGeneral).toHaveBeenCalledWith({ tipo: "porcentaje", valor: "5", activo: true }, null)
    );
    expect(await screen.findByText("Descuento general guardado.")).toBeInTheDocument();
  });

  it("valida antes de enviar: porcentaje mayor a 100 y pesos con centavos", async () => {
    const usuario = userEvent.setup();
    renderizar();
    const valor = await screen.findByRole("textbox", { name: "Valor (%)" });

    await usuario.type(valor, "120");
    await usuario.click(screen.getByRole("button", { name: "Guardar descuento general" }));
    expect(screen.getByRole("alert")).toHaveTextContent("100 %");

    await usuario.click(screen.getByRole("radio", { name: "Pesos" }));
    const pesos = screen.getByRole("textbox", { name: "Valor ($)" });
    await usuario.clear(pesos);
    await usuario.type(pesos, "1000,5");
    await usuario.click(screen.getByRole("button", { name: "Guardar descuento general" }));
    expect(screen.getByRole("alert")).toHaveTextContent("sin centavos");
    expect(apiClient.guardarDescuentoGeneral).not.toHaveBeenCalled();
  });

  it("guarda los topes; un campo vacio queda sin tope", async () => {
    const usuario = userEvent.setup();
    apiClient.guardarTopesDescuento.mockResolvedValue({
      ...SIN_CONFIGURAR,
      topes: { tope_porcentaje: "10.00", tope_monto: null, descripcion: "hasta 10 % del subtotal" },
    });
    renderizar();

    expect(await screen.findByText("sin límite")).toBeInTheDocument();
    await usuario.type(screen.getByRole("textbox", { name: "Porcentaje máximo del subtotal (%)" }), "10");
    await usuario.click(screen.getByRole("button", { name: "Guardar topes" }));

    await waitFor(() =>
      expect(apiClient.guardarTopesDescuento).toHaveBeenCalledWith({ tope_porcentaje: "10", tope_monto: null }, null)
    );
    expect(await screen.findByText("Topes guardados: hasta 10 % del subtotal.")).toBeInTheDocument();
  });
});
