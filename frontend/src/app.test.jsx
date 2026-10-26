import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./app";
import * as apiClient from "./api/api-client";

vi.mock("./api/api-client", async () => {
  const modulo = await vi.importActual("./api/api-client");
  return {
    ...modulo,
    obtenerResumenDashboard: vi.fn().mockResolvedValue({
      desde: "2026-10-27",
      hasta: "2026-10-27",
      ventas_por_dia: [],
      total_vendido: "0",
      cantidad_ventas: 0,
      ticket_promedio: "0",
      total_por_metodo: {},
      top_productos: [],
      compras: { recibidas: 0, pendientes: 0, total_recibido: "0" },
      alertas_stock_bajo: 0,
      generado_en: "2026-10-27T20:30:00Z",
    }),
    obtenerAlertasStock: vi.fn().mockResolvedValue([]),
    obtenerNotificaciones: vi.fn().mockResolvedValue({ no_leidas: 0, notificaciones: [] }),
    obtenerHistorialHoy: vi.fn().mockResolvedValue({
      fecha: "2026-10-27",
      cantidad_ventas: 0,
      total_vendido: "0",
      total_por_metodo: {},
      ventas: [],
    }),
  };
});

/** Arma un JWT sin firma valido solo para que el frontend lea el rol (la firma la valida el backend). */
function guardarSesion(rol) {
  const payload = btoa(JSON.stringify({ sub: "1", rol }));
  localStorage.setItem("mm_pos_token", `x.${payload}.y`);
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
});

describe("App: pantalla segun el rol", () => {
  it("el propietario entra directo al Dashboard, sin las pestañas del POS", async () => {
    guardarSesion("propietario");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Resumen" })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Nueva venta" })).not.toBeInTheDocument();
    expect(apiClient.obtenerResumenDashboard).toHaveBeenCalled();
  });

  it("el administrador sigue entrando al punto de venta", async () => {
    guardarSesion("administrador");
    render(<App />);

    expect(await screen.findByRole("tab", { name: "Nueva venta" })).toBeInTheDocument();
    expect(apiClient.obtenerResumenDashboard).not.toHaveBeenCalled();
  });

  it("sin sesion muestra el inicio de sesion", () => {
    render(<App />);
    expect(screen.queryByRole("heading", { name: "Resumen" })).not.toBeInTheDocument();
  });
});
