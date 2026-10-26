import { describe, expect, it } from "vitest";

import {
  aCentavos,
  calcularDescuento,
  calcularTotales,
  leerMonto,
  leerPorcentaje,
  resolverDescuento,
  superaTopes,
  validarPagos,
} from "./calculo-venta";

const CONFIGURACION = {
  general: { tipo: "porcentaje", valor: "10.00", activo: true },
  topes: { tope_porcentaje: "10.00", tope_monto: "5000.00", descripcion: "hasta 10 % del subtotal y hasta $5.000" },
};

/** HU-06: descuento sobre el subtotal y despues redondeo a $50, igual que el backend. */
describe("calculo de la venta", () => {
  it("lee montos con punto de miles y porcentajes con coma o punto", () => {
    expect(leerMonto("20.000")).toBe(20000);
    expect(leerMonto("$ 5000")).toBe(5000);
    expect(leerMonto("")).toBeNull();
    expect(leerPorcentaje("7,5")).toBe(7.5);
    expect(leerPorcentaje("7.5")).toBe(7.5);
  });

  it("descuenta sobre el subtotal y redondea despues (3.060 con 10 % -> 2.750)", () => {
    const { centavos } = calcularDescuento(aCentavos(3060), "porcentaje", 10);
    expect(calcularTotales(aCentavos(3060), centavos)).toEqual({
      subtotal: 306000,
      descuento: 30600,
      ajuste: -400,
      total: 275000,
    });
  });

  it("redondea el porcentaje al centavo como el backend (7,5 % de 1.025 = 76,88)", () => {
    expect(calcularDescuento(aCentavos(1025), "porcentaje", 7.5).centavos).toBe(7688);
  });

  it("rechaza porcentajes mayores a 100, montos con centavos y montos mayores al subtotal", () => {
    expect(calcularDescuento(100000, "porcentaje", 120).error).toMatch(/100/);
    expect(calcularDescuento(100000, "monto", 10.5).error).toMatch(/centavos/);
    expect(calcularDescuento(100000, "monto", 2000).error).toMatch(/mayor que el subtotal/);
  });

  it("los topes se cumplen los dos", () => {
    expect(superaTopes(aCentavos(100000), aCentavos(5000), CONFIGURACION.topes)).toBe(false);
    expect(superaTopes(aCentavos(10000), aCentavos(1500), CONFIGURACION.topes)).toBe(true);
    expect(superaTopes(aCentavos(100000), aCentavos(6000), CONFIGURACION.topes)).toBe(true);
    expect(superaTopes(aCentavos(100), aCentavos(100), { tope_porcentaje: null, tope_monto: null })).toBe(false);
  });

  it("el general no se limita por los topes; el manual del vendedor si, el del administrador no", () => {
    const subtotal = aCentavos(20000);
    expect(resolverDescuento({ origen: "general" }, CONFIGURACION, subtotal, false)).toMatchObject({
      centavos: 200000,
      error: null,
      payload: { origen: "general" },
    });
    const manual = { origen: "manual", tipo: "porcentaje", valor: "15" };
    expect(resolverDescuento(manual, CONFIGURACION, subtotal, false).error).toBe(
      "Supera tu límite: hasta 10 % del subtotal y hasta $5.000."
    );
    expect(resolverDescuento(manual, CONFIGURACION, subtotal, true)).toMatchObject({
      centavos: 300000,
      error: null,
      payload: { origen: "manual", tipo: "porcentaje", valor: "15" },
    });
    expect(resolverDescuento({ origen: "manual", tipo: null }, CONFIGURACION, subtotal, false)).toMatchObject({
      centavos: 0,
      payload: { origen: "manual" },
    });
  });
});

/** HU-05: suma de pagos = total, plataforma en transferencia, recibido y vueltas en efectivo. */
describe("validacion de pagos", () => {
  const efectivo = (monto, recibido = "") => ({ metodo: "efectivo", plataforma: null, monto, recibido });

  it("pagos mixtos con vueltas y payload listo", () => {
    const resultado = validarPagos(
      [efectivo("20000", "50000"), { metodo: "transferencia", plataforma: "nequi", monto: "6000", recibido: "" }],
      aCentavos(26000)
    );
    expect(resultado.errores).toEqual(["", ""]);
    expect(resultado.faltaCentavos).toBe(0);
    expect(resultado.vueltasCentavos).toEqual([3000000, 0]);
    expect(resultado.payload).toEqual([
      { metodo_pago: "efectivo", plataforma: null, monto: "20000", monto_recibido: "50000" },
      { metodo_pago: "transferencia", plataforma: "nequi", monto: "6000", monto_recibido: null },
    ]);
  });

  it("efectivo sin recibido se toma como pago exacto", () => {
    const resultado = validarPagos([efectivo("5000")], aCentavos(5000));
    expect(resultado.errores).toEqual([""]);
    expect(resultado.payload[0].monto_recibido).toBe("5000");
  });

  it("muestra cuanto falta o sobra", () => {
    expect(validarPagos([efectivo("20000")], aCentavos(26000)).faltaCentavos).toBe(600000);
    expect(validarPagos([efectivo("30000")], aCentavos(26000)).sobraCentavos).toBe(400000);
  });

  it.each([
    [{ metodo: "transferencia", plataforma: null, monto: "5000", recibido: "" }, "Nequi o Daviplata"],
    [efectivo("4990"), "múltiplo de $50"],
    [efectivo("5000", "4000"), "no puede ser menor"],
    [efectivo("5000", "5020"), "múltiplo de $50"],
    [{ metodo: "tarjeta", plataforma: null, monto: "", recibido: "" }, "monto entero"],
  ])("pago invalido: %o -> %s", (pago, mensaje) => {
    expect(validarPagos([pago], aCentavos(5000)).errores[0]).toContain(mensaje);
  });
});

describe("resolverDescuento — descuento propio del cliente (Fase A2)", () => {
  const subtotal = aCentavos(26000);
  const porcentaje = { descuento_tipo: "porcentaje", descuento_valor: "10.00" };

  it("usa el descuento del cliente sin aplicar topes", () => {
    const topes = { topes: { tope_porcentaje: "1", tope_monto: "100", descripcion: "x" } };
    expect(resolverDescuento({ origen: "cliente" }, topes, subtotal, false, porcentaje)).toEqual({
      centavos: aCentavos(2600),
      error: null,
      payload: { origen: "cliente" },
    });
  });

  it("un descuento en pesos mayor que el subtotal se limita al subtotal", () => {
    const grande = { descuento_tipo: "monto", descuento_valor: "50000.00" };
    expect(resolverDescuento({ origen: "cliente" }, CONFIGURACION, subtotal, false, grande).centavos).toBe(subtotal);
  });

  it("sin cliente o sin descuento propio la venta queda sin descuento", () => {
    const esperado = { centavos: 0, error: null, payload: { origen: "ninguno" } };
    expect(resolverDescuento({ origen: "cliente" }, CONFIGURACION, subtotal, false, null)).toEqual(esperado);
    expect(
      resolverDescuento({ origen: "cliente" }, CONFIGURACION, subtotal, false, { descuento_tipo: null, descuento_valor: null })
    ).toEqual(esperado);
  });
});
