import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { elegirOpcion } from "../utils/test-desplegable";
import { Compras } from "./compras";
import { AuthProvider } from "../context/auth-context";
import * as apiClient from "../api/api-client";

vi.mock("../api/api-client", async () => {
  const modulo = await vi.importActual("../api/api-client");
  return {
    ...modulo,
    obtenerCompras: vi.fn(),
    obtenerProveedores: vi.fn(),
    obtenerCatalogo: vi.fn(),
    crearCompra: vi.fn(),
    recibirCompra: vi.fn(),
    cancelarCompra: vi.fn(),
  };
});

const COMPRA_PENDIENTE = {
  id: 7,
  proveedor_id: 1,
  proveedor_nombre: "Papeles del Valle SAS",
  usuario_id: 1,
  fecha: "2026-09-25T20:40:00Z",
  estado: "pendiente",
  total: "5000.00",
  detalles: [
    { id: 1, producto_id: 3, producto_nombre: "Papel china rojo", cantidad: 5, costo_unitario: "1000.00", subtotal: "5000.00" },
  ],
};

function renderizar() {
  localStorage.setItem("mm_pos_token", `c.${btoa(JSON.stringify({ sub: "1", rol: "administrador" }))}.f`);
  return render(
    <AuthProvider>
      <Compras />
    </AuthProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  apiClient.obtenerProveedores.mockResolvedValue([{ id: 1, nombre_empresa: "Papeles del Valle SAS" }]);
  apiClient.obtenerCatalogo.mockResolvedValue({ total: 1, productos: [{ id: 3, nombre: "Papel china rojo" }] });
});

describe("Compras", () => {
  it("lista las compras con sus líneas y estado", async () => {
    apiClient.obtenerCompras.mockResolvedValue([COMPRA_PENDIENTE]);
    renderizar();

    expect(await screen.findByText(/#7 · Papeles del Valle SAS/)).toBeInTheDocument();
    expect(screen.getByText(/5 × Papel china rojo/)).toBeInTheDocument();
    expect(screen.getByText("Pendiente", { selector: "span" })).toBeInTheDocument();
  });

  it("al recibir una compra pide la forma de pago y recarga", async () => {
    apiClient.obtenerCompras.mockResolvedValue([COMPRA_PENDIENTE]);
    apiClient.recibirCompra.mockResolvedValue({ ...COMPRA_PENDIENTE, estado: "recibida" });
    renderizar();

    await userEvent.click(await screen.findByRole("button", { name: "Marcar recibida" }));
    expect(apiClient.recibirCompra).not.toHaveBeenCalled(); // primero pregunta como se pago
    expect(screen.getByText("¿Cómo se pagó esta compra?")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Confirmar recepción" }));

    await waitFor(() =>
      expect(apiClient.recibirCompra).toHaveBeenCalledWith(7, { metodo_pago: "efectivo", plataforma: null }, expect.any(String))
    );
    await waitFor(() => expect(apiClient.obtenerCompras).toHaveBeenCalledTimes(2));
  });

  it("en una transferencia exige y manda la plataforma", async () => {
    apiClient.obtenerCompras.mockResolvedValue([COMPRA_PENDIENTE]);
    apiClient.recibirCompra.mockResolvedValue({ ...COMPRA_PENDIENTE, estado: "recibida" });
    renderizar();

    await userEvent.click(await screen.findByRole("button", { name: "Marcar recibida" }));
    await elegirOpcion(screen.getByRole("combobox", { name: "Forma de pago de la compra" }), "transferencia");
    await userEvent.click(screen.getByRole("button", { name: "Confirmar recepción" }));
    expect(apiClient.recibirCompra).not.toHaveBeenCalled(); // falta la plataforma
    await elegirOpcion(screen.getByRole("combobox", { name: "Plataforma de la transferencia" }), "daviplata");
    await userEvent.click(screen.getByRole("button", { name: "Confirmar recepción" }));

    await waitFor(() =>
      expect(apiClient.recibirCompra).toHaveBeenCalledWith(7, { metodo_pago: "transferencia", plataforma: "daviplata" }, expect.any(String))
    );
  });

  it("se puede volver sin recibir la compra", async () => {
    apiClient.obtenerCompras.mockResolvedValue([COMPRA_PENDIENTE]);
    renderizar();

    await userEvent.click(await screen.findByRole("button", { name: "Marcar recibida" }));
    await userEvent.click(screen.getByRole("button", { name: "Volver" }));

    expect(screen.getByRole("button", { name: "Marcar recibida" })).toBeInTheDocument();
    expect(apiClient.recibirCompra).not.toHaveBeenCalled();
  });

  it("muestra como se pagó una compra recibida, o que no tiene forma de pago si es anterior", async () => {
    apiClient.obtenerCompras.mockResolvedValue([
      { ...COMPRA_PENDIENTE, id: 8, estado: "recibida", metodo_pago: "transferencia", plataforma: "nequi", recibida_en: "2026-10-19T15:00:00Z" },
      { ...COMPRA_PENDIENTE, id: 9, estado: "recibida", metodo_pago: null, plataforma: null, recibida_en: null },
    ]);
    renderizar();

    await screen.findByText(/#8/);
    expect(screen.getByText(/Pagada: Transferencia \(Nequi\)/)).toBeInTheDocument();
    expect(screen.getByText("Sin forma de pago registrada")).toBeInTheDocument();
  });

  it("no ofrece acciones sobre compras ya recibidas", async () => {
    apiClient.obtenerCompras.mockResolvedValue([{ ...COMPRA_PENDIENTE, estado: "recibida" }]);
    renderizar();

    await screen.findByText(/#7/);
    expect(screen.queryByRole("button", { name: "Marcar recibida" })).not.toBeInTheDocument();
  });

  it("registra una nueva orden con sus líneas", async () => {
    apiClient.obtenerCompras.mockResolvedValue([]);
    apiClient.crearCompra.mockResolvedValue(COMPRA_PENDIENTE);
    renderizar();
    await screen.findByText("No hay compras registradas.");

    await userEvent.click(screen.getByRole("button", { name: "Nueva compra" }));
    await waitFor(() => expect(apiClient.obtenerCatalogo).toHaveBeenCalled());
    const formulario = screen.getByRole("button", { name: "Registrar orden" }).closest("form");
    await elegirOpcion(within(formulario).getAllByRole("combobox")[0], "1");
    await elegirOpcion(screen.getByLabelText("Producto de la línea 1"), "3");
    await userEvent.type(screen.getByLabelText("Cantidad de la línea 1"), "5");
    await userEvent.type(screen.getByLabelText("Costo unitario de la línea 1"), "1000");
    await userEvent.click(screen.getByRole("button", { name: "Registrar orden" }));

    await waitFor(() =>
      expect(apiClient.crearCompra).toHaveBeenCalledWith(
        { proveedor_id: 1, detalles: [{ producto_id: 3, cantidad: 5, costo_unitario: 1000 }] },
        expect.any(String)
      )
    );
  });

  it("muestra el total redondeado a $50 y avisa del redondeo", async () => {
    apiClient.obtenerCompras.mockResolvedValue([]);
    renderizar();
    await screen.findByText("No hay compras registradas.");
    await userEvent.click(screen.getByRole("button", { name: "Nueva compra" }));
    await waitFor(() => expect(apiClient.obtenerCatalogo).toHaveBeenCalled());
    await userEvent.type(screen.getByLabelText("Cantidad de la línea 1"), "3");
    await userEvent.type(screen.getByLabelText("Costo unitario de la línea 1"), "1234");

    expect(screen.getByText(/Total:/)).toHaveTextContent(/3\.700/);
    expect(screen.getByText(/Redondeado a \$50/)).toHaveTextContent(/3\.702/);
  });
});
