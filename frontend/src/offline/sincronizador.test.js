import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api/api-client", () => ({ crearVenta: vi.fn() }));

import { reiniciarAlmacenParaPruebas } from "./almacen";
import { ESTADO_CONFLICTO, ESTADO_PENDIENTE, armarVentaPendiente, encolarVenta, listarVentas } from "./cola-ventas";
import { sincronizarPendientes } from "./sincronizador";

beforeEach(async () => {
  await reiniciarAlmacenParaPruebas();
});

/** Encola una venta de prueba. */
async function encolar(uuid, { usuarioId = "7", hora = "15:00:00" } = {}) {
  await encolarVenta(
    armarVentaPendiente({
      uuid,
      numeroLocal: `SC-${uuid}`,
      usuarioId,
      creadaEn: new Date(`2026-10-14T${hora}Z`),
      items: [{ productoId: 1, nombre: "Piñata", precioUnitario: 26000, cantidad: 1 }],
      totales: { subtotal: 2600000, descuento: 0, ajuste: 0, total: 2600000 },
      validacionPagos: {
        payload: [{ metodo_pago: "efectivo", plataforma: null, monto: "26000", monto_recibido: "26000" }],
        vueltasCentavos: [0],
      },
      ventaSinCobro: false,
      descuentoPayload: { origen: "ninguno" },
      configuracion: null,
    })
  );
}

/** Error como el que lanza `solicitarApi` ante una respuesta con codigo >= 400. */
function errorApi(status, mensaje) {
  return Object.assign(new Error(mensaje), { name: "ApiError", status });
}

describe("sincronizarPendientes", () => {
  it("envia las ventas de la mas antigua a la mas reciente y las quita de la cola", async () => {
    await encolar("b", { hora: "16:00:00" });
    await encolar("a", { hora: "15:00:00" });
    const enviar = vi.fn().mockResolvedValue({ id: 1 });

    const resultado = await sincronizarPendientes({ token: "t", usuarioId: "7", enviar });

    expect(resultado).toEqual({ enviadas: 2, conflictos: 0, detenida: null });
    expect(enviar.mock.calls.map(([payload]) => payload.uuid_cliente)).toEqual(["a", "b"]);
    expect(enviar.mock.calls[0][1]).toBe("t");
    expect(await listarVentas()).toEqual([]);
  });

  it("envia el payload tal cual se guardo: uuid, hora real y precios", async () => {
    await encolar("a");
    const enviar = vi.fn().mockResolvedValue({ id: 1 });

    await sincronizarPendientes({ token: "t", usuarioId: "7", enviar });

    expect(enviar.mock.calls[0][0]).toMatchObject({
      uuid_cliente: "a",
      sin_conexion: { fecha: "2026-10-14T15:00:00.000Z" },
      detalles: [{ producto_id: 1, cantidad: 1, precio_unitario: "26000" }],
    });
  });

  it("sin conexion se detiene, conserva todo lo que falta y no marca conflictos", async () => {
    await encolar("a", { hora: "15:00:00" });
    await encolar("b", { hora: "16:00:00" });
    await encolar("c", { hora: "17:00:00" });
    const enviar = vi
      .fn()
      .mockResolvedValueOnce({ id: 1 })
      .mockRejectedValueOnce(new TypeError("Failed to fetch"));

    const resultado = await sincronizarPendientes({ token: "t", usuarioId: "7", enviar });

    expect(resultado).toEqual({ enviadas: 1, conflictos: 0, detenida: "conexion" });
    expect(enviar).toHaveBeenCalledTimes(2); // no insiste con la tercera
    const restantes = await listarVentas();
    expect(restantes.map((v) => [v.uuid, v.estado])).toEqual([
      ["b", ESTADO_PENDIENTE],
      ["c", ESTADO_PENDIENTE],
    ]);
  });

  it("el tunel caido (502) se trata como falta de conexion, no como rechazo", async () => {
    await encolar("a");
    const enviar = vi.fn().mockRejectedValue(errorApi(502, "Bad gateway"));

    const resultado = await sincronizarPendientes({ token: "t", usuarioId: "7", enviar });

    expect(resultado.detenida).toBe("conexion");
    expect((await listarVentas())[0].estado).toBe(ESTADO_PENDIENTE);
  });

  it("con la sesion vencida (401) se detiene y conserva la cola", async () => {
    await encolar("a");
    const enviar = vi.fn().mockRejectedValue(errorApi(401, "Token invalido"));

    const resultado = await sincronizarPendientes({ token: "t", usuarioId: "7", enviar });

    expect(resultado).toEqual({ enviadas: 0, conflictos: 0, detenida: "sesion" });
    expect((await listarVentas())[0].estado).toBe(ESTADO_PENDIENTE);
  });

  it("si el servidor rechaza una venta (sin stock) queda como conflicto con el motivo y sigue con las demas", async () => {
    await encolar("a", { hora: "15:00:00" });
    await encolar("b", { hora: "16:00:00" });
    const enviar = vi
      .fn()
      .mockRejectedValueOnce(errorApi(409, "Stock insuficiente para el producto 1."))
      .mockResolvedValueOnce({ id: 2 });

    const resultado = await sincronizarPendientes({ token: "t", usuarioId: "7", enviar });

    expect(resultado).toEqual({ enviadas: 1, conflictos: 1, detenida: null });
    const [conflicto] = await listarVentas();
    expect(conflicto).toMatchObject({ uuid: "a", estado: ESTADO_CONFLICTO, mensaje: "Stock insuficiente para el producto 1." });
  });

  it("no reintenta solas las ventas en conflicto", async () => {
    await encolar("a");
    await sincronizarPendientes({ token: "t", usuarioId: "7", enviar: vi.fn().mockRejectedValue(errorApi(422, "Pagos mal")) });
    const enviar = vi.fn().mockResolvedValue({ id: 1 });

    const resultado = await sincronizarPendientes({ token: "t", usuarioId: "7", enviar });

    expect(enviar).not.toHaveBeenCalled();
    expect(resultado.enviadas).toBe(0);
  });

  it("un vendedor envia solo sus ventas; las de otro esperan", async () => {
    await encolar("mia", { usuarioId: "7" });
    await encolar("ajena", { usuarioId: "8" });
    const enviar = vi.fn().mockResolvedValue({ id: 1 });

    await sincronizarPendientes({ token: "t", usuarioId: "7", enviar });

    expect(enviar.mock.calls.map(([p]) => p.uuid_cliente)).toEqual(["mia"]);
    expect((await listarVentas()).map((v) => v.uuid)).toEqual(["ajena"]);
  });

  it("un administrador envia las de todos", async () => {
    await encolar("mia", { usuarioId: "1" });
    await encolar("ajena", { usuarioId: "8" });
    const enviar = vi.fn().mockResolvedValue({ id: 1 });

    const resultado = await sincronizarPendientes({ token: "t", usuarioId: "1", esAdministrador: true, enviar });

    expect(resultado.enviadas).toBe(2);
    expect(await listarVentas()).toEqual([]);
  });

  it("sin ventas pendientes no hace nada", async () => {
    const enviar = vi.fn();
    expect(await sincronizarPendientes({ token: "t", usuarioId: "7", enviar })).toEqual({
      enviadas: 0,
      conflictos: 0,
      detenida: null,
    });
    expect(enviar).not.toHaveBeenCalled();
  });
});
