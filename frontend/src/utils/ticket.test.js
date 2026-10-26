import { describe, expect, it } from "vitest";
import { construirTicket, construirTicketLocal } from "./ticket";

const VENTA = {
  id: 9,
  fecha: "2026-10-12T20:00:00Z",
  subtotal: "20000.00",
  descuento_tipo: null,
  descuento_valor: null,
  descuento_monto: "0.00",
  ajuste_redondeo: "0.00",
  total: "20000.00",
  pagos: [{ metodo_pago: "efectivo", plataforma: null, monto: "20000.00", monto_recibido: "20000.00", vueltas: "0.00" }],
  detalles: [{ producto_id: 1, cantidad: 1, precio_unitario: "20000.00", subtotal: "20000.00" }],
};

describe("construirTicket — vendedor (HU-08)", () => {
  it("incluye quien realizó la venta para que el ticket lo imprima", () => {
    expect(construirTicket(VENTA, () => "Piñata", "Laura Gómez").vendedor).toBe("Laura Gómez");
  });

  it("sin vendedor manda null y el resto del ticket no cambia", () => {
    const ticket = construirTicket(VENTA, () => "Piñata");
    expect(ticket.vendedor).toBeNull();
    expect(ticket.lineas[0].nombre_producto).toBe("Piñata");
  });

  it("no envía datos del cliente al agente de impresión", () => {
    const ticket = construirTicket({ ...VENTA, cliente: "María Pérez", cliente_id: 7 }, () => "Piñata", "Laura");
    expect(JSON.stringify(ticket)).not.toContain("María");
    expect(ticket).not.toHaveProperty("cliente");
  });
});

describe("construirTicketLocal (venta hecha sin conexion)", () => {
  const entrada = {
    numeroLocal: "SC-0003",
    creadaEn: "2026-10-14T15:00:00.000Z",
    resumen: {
      subtotal: "30600.00",
      descuento_tipo: "porcentaje",
      descuento_valor: "10",
      descuento_monto: "3060.00",
      ajuste_redondeo: "10.00",
      total: "27550.00",
      vendedor: "Ana",
      lineas: [{ producto_id: 4, nombre: "Piñata", cantidad: 1, precio_unitario: "30600.00", subtotal: "30600.00" }],
      pagos: [{ metodo_pago: "efectivo", plataforma: null, monto: "27550", monto_recibido: "30000", vueltas: "2450.00" }],
    },
  };

  it("lleva la referencia local y no el numero de venta", () => {
    const ticket = construirTicketLocal(entrada);
    expect(ticket).toMatchObject({ venta_id: null, referencia: "SC-0003", fecha: "2026-10-14T15:00:00.000Z", vendedor: "Ana" });
  });

  it("trae los totales, el descuento, los pagos y las lineas que espera el agente", () => {
    const ticket = construirTicketLocal(entrada);
    expect(ticket).toMatchObject({
      subtotal: "30600.00",
      descuento_tipo: "porcentaje",
      descuento_monto: "3060.00",
      ajuste_redondeo: "10.00",
      total: "27550.00",
    });
    expect(ticket.pagos[0]).toMatchObject({ metodo_pago: "efectivo", monto_recibido: "30000", vueltas: "2450.00" });
    expect(ticket.lineas).toEqual([{ nombre_producto: "Piñata", cantidad: 1, precio_unitario: "30600.00", subtotal: "30600.00" }]);
  });
});
