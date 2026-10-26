import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HistorialDia } from "./historial-dia";
import { AuthProvider } from "../context/auth-context";
import * as apiClient from "../api/api-client";

vi.mock("../api/api-client", async () => {
  const modulo = await vi.importActual("../api/api-client");
  return { ...modulo, obtenerHistorialHoy: vi.fn(), imprimirTicket: vi.fn() };
});

const HISTORIAL = {
  fecha: "2026-09-25",
  cantidad_ventas: 2,
  total_vendido: "75000.00",
  total_por_metodo: { efectivo: "50000.00", tarjeta: "25000.00" },
  ventas: [
    {
      id: 8,
      fecha: "2026-09-25T20:40:00Z",
      subtotal: "25000.00",
      descuento_origen: "ninguno",
      descuento_tipo: null,
      descuento_valor: null,
      descuento_monto: "0.00",
      ajuste_redondeo: "0.00",
      total: "25000.00",
      pagos: [{ metodo_pago: "tarjeta", plataforma: null, monto: "25000.00", monto_recibido: null, vueltas: "0.00" }],
      vendedor: "Ana",
      detalles: [
        { producto_id: 1, nombre_producto: "Piñata Mickey Mouse", cantidad: 1, precio_unitario: "25000.00", subtotal: "25000.00" },
      ],
    },
    {
      id: 7,
      fecha: "2026-09-25T20:30:00Z",
      subtotal: "55000.00",
      descuento_origen: "general",
      descuento_tipo: "monto",
      descuento_valor: "5000.00",
      descuento_monto: "5000.00",
      ajuste_redondeo: "0.00",
      total: "50000.00",
      pagos: [
        { metodo_pago: "efectivo", plataforma: null, monto: "30000.00", monto_recibido: "50000.00", vueltas: "20000.00" },
        { metodo_pago: "transferencia", plataforma: "nequi", monto: "20000.00", monto_recibido: null, vueltas: "0.00" },
      ],
      vendedor: "Ana",
      detalles: [
        { producto_id: 1, nombre_producto: "Piñata Mickey Mouse", cantidad: 2, precio_unitario: "27500.00", subtotal: "55000.00" },
      ],
    },
  ],
};

function renderizar() {
  return render(
    <AuthProvider>
      <HistorialDia />
    </AuthProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
});

describe("HistorialDia", () => {
  it("muestra el resumen del dia y las ventas", async () => {
    apiClient.obtenerHistorialHoy.mockResolvedValue(HISTORIAL);
    renderizar();

    expect(await screen.findByText("Venta #8")).toBeInTheDocument();
    expect(screen.getByText("Venta #7")).toBeInTheDocument();
    expect(screen.getByText("transacciones")).toBeInTheDocument();
    expect(screen.getAllByText(/75\.000/).length).toBeGreaterThan(0);
    // Adendo v2 (HU-05): cada pago se ve con su metodo y plataforma.
    expect(screen.getByText("Transferencia (Nequi)")).toBeInTheDocument();
    expect(screen.getAllByText("Efectivo").length).toBeGreaterThan(0);
  });

  it("el detalle muestra descuento, pagos mixtos y vueltas", async () => {
    apiClient.obtenerHistorialHoy.mockResolvedValue(HISTORIAL);
    renderizar();

    await userEvent.click(await screen.findByRole("button", { name: /venta #7/i }));

    expect(screen.getByText("Descuento general")).toBeInTheDocument();
    expect(screen.getByText(/−\$\s?5\.000/)).toBeInTheDocument();
    expect(screen.getByText(/Recibido \$\s?50\.000 · vueltas \$\s?20\.000/)).toBeInTheDocument();
  });

  it("avisa quien registro la venta cuando es otra persona distinta del vendedor", async () => {
    apiClient.obtenerHistorialHoy.mockResolvedValue({
      ...HISTORIAL,
      ventas: [{ ...HISTORIAL.ventas[0], vendedor: "Admin", registrada_por: "Ana" }, HISTORIAL.ventas[1]],
    });
    renderizar();

    await userEvent.click(await screen.findByRole("button", { name: /venta #8/i }));
    expect(screen.getByText(/Atendió: Admin · Registrada por: Ana/)).toBeInTheDocument();

    // Una venta sin ese dato (la registro el mismo vendedor) no muestra la leyenda.
    await userEvent.click(screen.getByRole("button", { name: /venta #7/i }));
    expect(screen.getAllByText(/Atendió:/)).toHaveLength(2);
    expect(screen.getAllByText(/Registrada por/)).toHaveLength(1);
  });

  it("la fila de cada venta puede saltar de linea para que en el celular el total no se salga de la tarjeta", async () => {
    apiClient.obtenerHistorialHoy.mockResolvedValue(HISTORIAL);
    renderizar();

    const fila = await screen.findByRole("button", { name: /Venta #7/ });

    expect(fila.className).toMatch(/flex-wrap/);
  });

  it("sin ventas muestra un mensaje vacio", async () => {
    apiClient.obtenerHistorialHoy.mockResolvedValue({
      ...HISTORIAL,
      cantidad_ventas: 0,
      total_vendido: "0.00",
      total_por_metodo: {},
      ventas: [],
    });
    renderizar();

    expect(await screen.findByText(/todavía no hay ventas registradas hoy/i)).toBeInTheDocument();
  });

  it("muestra un error con opcion de reintentar si falla la carga", async () => {
    apiClient.obtenerHistorialHoy.mockRejectedValue(new Error("Sin conexion"));
    renderizar();

    expect(await screen.findByRole("alert")).toHaveTextContent("Sin conexion");
    expect(screen.getByRole("button", { name: /reintentar/i })).toBeInTheDocument();
  });

  it("reimprime el ticket de una venta con los nombres de producto del historial", async () => {
    apiClient.obtenerHistorialHoy.mockResolvedValue(HISTORIAL);
    apiClient.imprimirTicket.mockResolvedValue({ status: "ok", modo: "mock" });
    renderizar();

    await userEvent.click(await screen.findByRole("button", { name: /venta #7/i }));
    await userEvent.click(screen.getByRole("button", { name: /reimprimir ticket/i }));

    await waitFor(() => expect(apiClient.imprimirTicket).toHaveBeenCalledTimes(1));
    const ticket = apiClient.imprimirTicket.mock.calls[0][0];
    expect(ticket.venta_id).toBe(7);
    expect(ticket.lineas[0].nombre_producto).toBe("Piñata Mickey Mouse");
    expect(ticket).toMatchObject({ subtotal: "55000.00", descuento_tipo: "monto", descuento_monto: "5000.00" });
    expect(ticket.pagos).toHaveLength(2);
    expect(ticket.pagos[0]).toMatchObject({ metodo_pago: "efectivo", monto_recibido: "50000.00", vueltas: "20000.00" });
    expect(ticket).not.toHaveProperty("metodo_pago");
    expect(await screen.findByText(/ticket enviado/i)).toBeInTheDocument();
  });
});

describe("HistorialDia — ventas hechas sin conexion (Fase 9)", () => {
  it("marca con 'Sin conexión' las ventas que se enviaron despues, y solo esas", async () => {
    apiClient.obtenerHistorialHoy.mockResolvedValue({
      ...HISTORIAL,
      ventas: [{ ...HISTORIAL.ventas[0], sin_conexion: true }, { ...HISTORIAL.ventas[1], sin_conexion: false }],
    });
    renderizar();

    await screen.findByText("Venta #8");

    expect(screen.getAllByText("Sin conexión")).toHaveLength(1);
    expect(screen.getByText("Sin conexión").closest("button")).toHaveTextContent("Venta #8");
  });
});
