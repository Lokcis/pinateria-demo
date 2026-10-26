import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DashboardPage } from "./dashboard-page";
import { AuthProvider } from "../context/auth-context";
import * as apiClient from "../api/api-client";

vi.mock("../api/api-client", async () => {
  const modulo = await vi.importActual("../api/api-client");
  return {
    ...modulo,
    obtenerResumenDashboard: vi.fn(),
    obtenerAlertasStock: vi.fn(),
    obtenerNotificaciones: vi.fn(),
    obtenerCategoriasGasto: vi.fn(),
    obtenerGastos: vi.fn(),
    obtenerResumenGastos: vi.fn(),
    obtenerCajaActual: vi.fn(),
    obtenerCortes: vi.fn(),
  };
});

const RESUMEN_DASHBOARD = {
  desde: "2026-10-19",
  hasta: "2026-10-19",
  total_vendido: "0",
  cantidad_ventas: 0,
  ticket_promedio: "0",
  total_por_metodo: {},
  ventas_por_dia: [],
  top_productos: [],
  compras: { recibidas: 0, pendientes: 0, total_recibido: "0" },
  generado_en: "2026-10-19T15:00:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  localStorage.setItem("mm_pos_token", `c.${btoa(JSON.stringify({ sub: "3", rol: "propietario" }))}.f`);
  apiClient.obtenerResumenDashboard.mockResolvedValue(RESUMEN_DASHBOARD);
  apiClient.obtenerAlertasStock.mockResolvedValue([]);
  apiClient.obtenerNotificaciones.mockResolvedValue({ no_leidas: 0, notificaciones: [] });
  apiClient.obtenerCategoriasGasto.mockResolvedValue([{ id: 2, nombre: "Arriendo", activa: true, es_sistema: false }]);
  apiClient.obtenerGastos.mockResolvedValue([]);
  apiClient.obtenerResumenGastos.mockResolvedValue({
    desde: "2026-10-01",
    hasta: "2026-10-19",
    total: "0",
    total_compras: "0",
    total_operativo: "0",
    por_categoria: [],
    por_metodo_pago: [],
  });
  apiClient.obtenerCajaActual.mockResolvedValue({
    abierta: false,
    corte: null,
    cifras: null,
    movimientos: [],
    generado_en: "2026-10-20T15:00:00Z",
  });
  apiClient.obtenerCortes.mockResolvedValue([]);
});

describe("DashboardPage del propietario", () => {
  it("tiene las vistas Ventas, Ganancias, Gastos y Caja", async () => {
    render(
      <AuthProvider>
        <DashboardPage />
      </AuthProvider>
    );

    expect(await screen.findByRole("tab", { name: "Ventas" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Ganancias" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Gastos" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Caja" })).toBeInTheDocument();
  });

  it("Gastos es de solo lectura: se puede exportar pero no registrar", async () => {
    render(
      <AuthProvider>
        <DashboardPage />
      </AuthProvider>
    );

    await userEvent.click(await screen.findByRole("tab", { name: "Gastos" }));

    expect(await screen.findByText("No hay gastos en este rango.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Exportar" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Nuevo gasto" })).not.toBeInTheDocument();
    expect(apiClient.obtenerResumenGastos).toHaveBeenCalled();
  });

  it("Caja es de solo lectura: se consulta y se exporta, pero no se abre ni se cierra", async () => {
    render(
      <AuthProvider>
        <DashboardPage />
      </AuthProvider>
    );

    await userEvent.click(await screen.findByRole("tab", { name: "Caja" }));

    expect(await screen.findByText("No hay una caja abierta en este momento.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Exportar" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Abrir caja" })).not.toBeInTheDocument();
    expect(apiClient.obtenerCajaActual).toHaveBeenCalled();
  });
});
