import { beforeEach, describe, expect, it } from "vitest";

import { reiniciarAlmacenParaPruebas } from "./almacen";
import {
  ESTADO_CONFLICTO,
  ESTADO_PENDIENTE,
  armarVentaPendiente,
  eliminarVenta,
  encolarVenta,
  listarVentas,
  marcarConflicto,
  reabrirVenta,
  siguienteNumeroLocal,
} from "./cola-ventas";

beforeEach(async () => {
  await reiniciarAlmacenParaPruebas();
});

/** Una venta de $26.000: una piñata, pagada en efectivo con $30.000. */
function datosVenta(extra = {}) {
  return {
    uuid: "11111111-1111-4111-8111-111111111111",
    numeroLocal: "SC-0001",
    usuarioId: "7",
    creadaEn: new Date("2026-10-14T15:00:00Z"),
    items: [{ productoId: 1, nombre: "Piñata Mickey", precioUnitario: 26000, cantidad: 1 }],
    totales: { subtotal: 2600000, descuento: 0, ajuste: 0, total: 2600000 },
    validacionPagos: {
      payload: [{ metodo_pago: "efectivo", plataforma: null, monto: "26000", monto_recibido: "30000" }],
      vueltasCentavos: [400000],
    },
    ventaSinCobro: false,
    descuentoPayload: { origen: "ninguno" },
    configuracion: null,
    ...extra,
  };
}

describe("armarVentaPendiente", () => {
  it("arma el payload de POST /ventas con el uuid, la hora real y el precio que vio el cliente", () => {
    const entrada = armarVentaPendiente(datosVenta());

    expect(entrada.payload).toEqual({
      detalles: [{ producto_id: 1, cantidad: 1, precio_unitario: "26000" }],
      pagos: [{ metodo_pago: "efectivo", plataforma: null, monto: "26000", monto_recibido: "30000" }],
      descuento: { origen: "ninguno" },
      uuid_cliente: "11111111-1111-4111-8111-111111111111",
      sin_conexion: { fecha: "2026-10-14T15:00:00.000Z" },
    });
    expect(entrada).toMatchObject({ numeroLocal: "SC-0001", usuarioId: "7", estado: ESTADO_PENDIENTE, intentos: 0 });
  });

  it("guarda un resumen para mostrar la venta y reimprimir su ticket sin el servidor", () => {
    const { resumen } = armarVentaPendiente(datosVenta({ vendedorNombre: "Ana" }));

    expect(resumen).toMatchObject({ total: "26000.00", subtotal: "26000.00", descuento_monto: "0.00", vendedor: "Ana" });
    expect(resumen.lineas).toEqual([
      { producto_id: 1, nombre: "Piñata Mickey", cantidad: 1, precio_unitario: "26000.00", subtotal: "26000.00" },
    ]);
    expect(resumen.pagos).toEqual([
      { metodo_pago: "efectivo", plataforma: null, monto: "26000", monto_recibido: "30000", vueltas: "4000.00" },
    ]);
  });

  it("envia el descuento general con el tipo y el valor que vio el cliente", () => {
    const entrada = armarVentaPendiente(
      datosVenta({
        descuentoPayload: { origen: "general" },
        configuracion: { general: { tipo: "porcentaje", valor: "10.00", activo: true } },
        totales: { subtotal: 2600000, descuento: 260000, ajuste: 0, total: 2340000 },
      })
    );

    expect(entrada.payload.descuento).toEqual({ origen: "general", tipo: "porcentaje", valor: "10.00" });
    expect(entrada.resumen).toMatchObject({ descuento_tipo: "porcentaje", descuento_valor: "10.00", descuento_monto: "2600.00" });
  });

  it("deja el descuento manual como esta", () => {
    const manual = { origen: "manual", tipo: "monto", valor: "2000" };
    expect(armarVentaPendiente(datosVenta({ descuentoPayload: manual })).payload.descuento).toEqual(manual);
  });

  it("una venta en $0 no lleva pagos", () => {
    const entrada = armarVentaPendiente(datosVenta({ ventaSinCobro: true }));
    expect(entrada.payload.pagos).toEqual([]);
    expect(entrada.resumen.pagos).toEqual([]);
  });

  it("incluye vendedor_id solo si se eligio otro vendedor, y cliente_id solo si la red cayo con un cliente elegido", () => {
    expect(armarVentaPendiente(datosVenta()).payload).not.toHaveProperty("vendedor_id");
    expect(armarVentaPendiente(datosVenta()).payload).not.toHaveProperty("cliente_id");

    const payload = armarVentaPendiente(datosVenta({ vendedorId: 9, clienteId: 31 })).payload;
    expect(payload).toMatchObject({ vendedor_id: 9, cliente_id: 31 });
  });
});

describe("cola de ventas", () => {
  it("guarda las ventas y las lista de la mas antigua a la mas reciente", async () => {
    await encolarVenta(armarVentaPendiente(datosVenta({ uuid: "b", numeroLocal: "SC-0002", creadaEn: new Date("2026-10-14T16:00:00Z") })));
    await encolarVenta(armarVentaPendiente(datosVenta({ uuid: "a", numeroLocal: "SC-0001", creadaEn: new Date("2026-10-14T15:00:00Z") })));

    const ventas = await listarVentas();

    expect(ventas.map((v) => v.numeroLocal)).toEqual(["SC-0001", "SC-0002"]);
  });

  it("la misma venta guardada dos veces queda una sola (misma clave uuid)", async () => {
    const entrada = armarVentaPendiente(datosVenta());
    await encolarVenta(entrada);
    await encolarVenta(entrada);

    expect(await listarVentas()).toHaveLength(1);
  });

  it("un conflicto guarda el motivo y cuenta el intento; reabrirla la deja pendiente de nuevo", async () => {
    await encolarVenta(armarVentaPendiente(datosVenta()));

    await marcarConflicto("11111111-1111-4111-8111-111111111111", "Stock insuficiente.");
    let [venta] = await listarVentas();
    expect(venta).toMatchObject({ estado: ESTADO_CONFLICTO, mensaje: "Stock insuficiente.", intentos: 1 });

    await reabrirVenta("11111111-1111-4111-8111-111111111111");
    [venta] = await listarVentas();
    expect(venta).toMatchObject({ estado: ESTADO_PENDIENTE, mensaje: null, intentos: 1 });
  });

  it("eliminar quita la venta de la cola", async () => {
    await encolarVenta(armarVentaPendiente(datosVenta()));
    await eliminarVenta("11111111-1111-4111-8111-111111111111");
    expect(await listarVentas()).toEqual([]);
  });

  it("marcar o reabrir una venta que ya no existe no falla", async () => {
    await expect(marcarConflicto("no-existe", "x")).resolves.toBeUndefined();
    await expect(reabrirVenta("no-existe")).resolves.toBeUndefined();
  });

  it("numera las ventas sin conexion de a una: SC-0001, SC-0002...", async () => {
    expect(await siguienteNumeroLocal()).toBe("SC-0001");
    expect(await siguienteNumeroLocal()).toBe("SC-0002");
    expect(await siguienteNumeroLocal()).toBe("SC-0003");
  });

  it("dos ventas confirmadas a la vez no repiten numero", async () => {
    const numeros = await Promise.all([siguienteNumeroLocal(), siguienteNumeroLocal(), siguienteNumeroLocal()]);
    expect(new Set(numeros).size).toBe(3);
  });
});
