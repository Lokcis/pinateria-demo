import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Dashboard, INTERVALO_ACTUALIZACION_MS } from "./dashboard";
import { AuthProvider } from "../context/auth-context";
import * as apiClient from "../api/api-client";

vi.mock("../api/api-client", async () => {
  const modulo = await vi.importActual("../api/api-client");
  return {
    ...modulo,
    obtenerResumenDashboard: vi.fn(),
    obtenerAlertasStock: vi.fn(),
    obtenerNotificaciones: vi.fn(),
    obtenerListaCompras: vi.fn(),
  };
});

const RESUMEN = {
  desde: "2026-10-27",
  hasta: "2026-10-27",
  ventas_por_dia: [{ fecha: "2026-10-27", total: "75000.00", cantidad: 2 }],
  total_vendido: "75000.00",
  cantidad_ventas: 2,
  ticket_promedio: "37500.00",
  total_por_metodo: { efectivo: "50000.00", tarjeta: "25000.00" },
  top_productos: [{ producto_id: 1, nombre: "Piñata Mickey Mouse", unidades: 3, total: "75000.00" }],
  compras: { recibidas: 1, pendientes: 2, total_recibido: "30000.00" },
  alertas_stock_bajo: 1,
  generado_en: "2026-10-27T20:30:00Z",
};

const ALERTAS = [{ id: 2, nombre: "Globo metalizado", categoria: "Globos", stock_actual: 0, stock_minimo: 5 }];

/** HU-03: ventas totales del dia y alertas de stock bajo, con actualizacion automatica. */
function renderizar() {
  return render(
    <AuthProvider>
      <Dashboard />
    </AuthProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  apiClient.obtenerResumenDashboard.mockResolvedValue(RESUMEN);
  apiClient.obtenerAlertasStock.mockResolvedValue(ALERTAS);
  apiClient.obtenerNotificaciones.mockResolvedValue({ no_leidas: 0, notificaciones: [] });
  apiClient.obtenerListaCompras.mockResolvedValue({ productos: [], generado_en: "2026-10-27T20:30:00Z" });
});

afterEach(() => {
  vi.useRealTimers();
});

describe("Dashboard", () => {
  it("muestra ventas del dia, metodos de pago, compras, top y alertas", async () => {
    renderizar();

    expect(await screen.findByText(/75\.000/, { selector: "p" })).toBeInTheDocument();
    expect(screen.getByText("Efectivo")).toBeInTheDocument();
    expect(screen.getByText("Piñata Mickey Mouse")).toBeInTheDocument();
    expect(screen.getByText("3 unidades")).toBeInTheDocument();
    expect(screen.getByText("Alertas de stock bajo ahora (1)")).toBeInTheDocument();
    expect(screen.getByText("0 / mín. 5")).toBeInTheDocument();
  });

  it("se actualiza solo cada intervalo, sin recargar la pagina", async () => {
    vi.useFakeTimers();
    renderizar();
    await act(async () => {});
    expect(apiClient.obtenerResumenDashboard).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(INTERVALO_ACTUALIZACION_MS);
    });

    expect(apiClient.obtenerResumenDashboard).toHaveBeenCalledTimes(2);
  });

  it("si no hay ventas ni alertas lo dice claramente", async () => {
    apiClient.obtenerResumenDashboard.mockResolvedValue({
      ...RESUMEN,
      total_vendido: "0",
      cantidad_ventas: 0,
      ticket_promedio: "0",
      total_por_metodo: {},
      top_productos: [],
    });
    apiClient.obtenerAlertasStock.mockResolvedValue([]);
    renderizar();

    expect(await screen.findByText("Todo el inventario está por encima del mínimo.")).toBeInTheDocument();
    expect(screen.getAllByText("Sin ventas aún")).toHaveLength(2);
  });

  it("muestra el error con opcion de reintentar si la primera carga falla", async () => {
    apiClient.obtenerResumenDashboard.mockRejectedValue(new Error("Sin conexion"));
    renderizar();

    expect(await screen.findByRole("alert")).toHaveTextContent("Sin conexion");
    expect(screen.getByRole("button", { name: "Reintentar" })).toBeInTheDocument();
  });
});

/** HU-10 (Adendo v2, mejora B1): el Dashboard muestra el contador de no leidas y abre la bandeja. */
describe("Dashboard: bandeja de stock bajo", () => {
  it("muestra el contador de no leídas y al tocarlo abre la bandeja y la lista de compras", async () => {
    const usuario = userEvent.setup();
    const notificacion = {
      id: 1,
      tipo: "stock_bajo",
      mensaje: "Stock bajo: Globo metalizado tiene 0 unidades (minimo configurado: 5).",
      leida: false,
      creada_en: "2026-10-27T20:00:00Z",
      producto_id: 2,
      producto_nombre: "Globo metalizado",
    };
    apiClient.obtenerNotificaciones.mockResolvedValue({ no_leidas: 3, notificaciones: [notificacion] });
    renderizar();

    const boton = await screen.findByRole("button", { name: "Notificaciones y lista de compras: 3 sin leer" });
    expect(boton).toHaveTextContent("3");
    expect(apiClient.obtenerNotificaciones).toHaveBeenCalledWith(null, { soloNoLeidas: true, limite: 1 });
    expect(screen.queryByText("Lista de compras", { exact: false })).not.toBeInTheDocument();

    await usuario.click(boton);

    expect(boton).toHaveAttribute("aria-expanded", "true");
    expect(await screen.findByText(notificacion.mensaje)).toBeInTheDocument();
    expect(await screen.findByText(/No hay productos en stock bajo/)).toBeInTheDocument();
  });
});

describe("Dashboard: si falla el contador de notificaciones", () => {
  it("el tablero carga igual", async () => {
    apiClient.obtenerNotificaciones.mockRejectedValue(new Error("Sin conexion"));
    renderizar();

    expect(await screen.findByText("Resumen")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});

describe("Dashboard: rangos de fechas", () => {
  const HOY = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Bogota" }).format(new Date());

  it("pide hoy por defecto", async () => {
    renderizar();
    await screen.findByText("Resumen");
    expect(apiClient.obtenerResumenDashboard).toHaveBeenLastCalledWith({ desde: HOY, hasta: HOY }, null);
  });

  it("al elegir 'Semana' pide los ultimos 7 dias y dibuja la serie por dia", async () => {
    const usuario = userEvent.setup();
    renderizar();
    await screen.findByText("Resumen");
    apiClient.obtenerResumenDashboard.mockResolvedValue({
      ...RESUMEN,
      desde: "2026-10-21",
      hasta: "2026-10-27",
      ventas_por_dia: Array.from({ length: 7 }, (_, i) => ({ fecha: `2026-10-${21 + i}`, total: "1000", cantidad: 1 })),
    });

    await usuario.click(screen.getByRole("tab", { name: "Semana" }));

    await waitFor(() => expect(screen.getByRole("group", { name: "Ventas por período" })).toBeInTheDocument());
    expect(screen.getByText(/cada barra es un día/)).toBeInTheDocument();
    expect(screen.getByText(/Toca una barra/)).toBeInTheDocument();

    await usuario.click(screen.getByRole("button", { name: /mié 21 oct/ }));
    expect(screen.getByRole("status")).toHaveTextContent(/mié 21 oct.*1 venta/);
    const [rango] = apiClient.obtenerResumenDashboard.mock.calls.at(-1);
    expect(rango.hasta).toBe(HOY);
    expect(rango.desde < rango.hasta).toBe(true);
  });

  it("en 'Ayer' no se refresca solo", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    renderizar();
    await act(async () => {});
    await act(async () => {
      screen.getByRole("tab", { name: "Ayer" }).click();
    });
    const llamadas = apiClient.obtenerResumenDashboard.mock.calls.length;

    await act(async () => {
      await vi.advanceTimersByTimeAsync(INTERVALO_ACTUALIZACION_MS * 2);
    });

    expect(apiClient.obtenerResumenDashboard).toHaveBeenCalledTimes(llamadas);
  });

  it("el rango personalizado se aplica con el calendario y valida los errores", async () => {
    const usuario = userEvent.setup();
    renderizar();
    await screen.findByText("Resumen");

    await usuario.click(screen.getByRole("tab", { name: "Personalizado" }));
    fireEvent.change(screen.getByLabelText("Desde"), { target: { value: "2026-01-10" } });
    fireEvent.change(screen.getByLabelText("Hasta"), { target: { value: "2026-01-01" } });
    await usuario.click(screen.getByRole("button", { name: "Aplicar" }));
    expect(screen.getByRole("alert")).toHaveTextContent("no puede ser posterior");

    fireEvent.change(screen.getByLabelText("Hasta"), { target: { value: "2026-01-20" } });
    await usuario.click(screen.getByRole("button", { name: "Aplicar" }));

    await waitFor(() =>
      expect(apiClient.obtenerResumenDashboard).toHaveBeenLastCalledWith(
        { desde: "2026-01-10", hasta: "2026-01-20" },
        null
      )
    );
  });
});
