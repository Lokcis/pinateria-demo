import { afterEach, describe, expect, it, vi } from "vitest";

import { imprimirTicket, obtenerSalud } from "./api-client";
import { esErrorDeConexion } from "../utils/conexion";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("mensajes cuando no hay conexion", () => {
  it("el servidor caido dice que no hay conexion en lugar de 'Failed to fetch', y sigue contando como falla de conexion", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    const error = await obtenerSalud().catch((falla) => falla);

    expect(error.message).toMatch(/No hay conexión con el servidor/);
    expect(error.message).not.toMatch(/Failed to fetch/);
    expect(esErrorDeConexion(error)).toBe(true);
  });

  it("el agente de impresion caido explica que hay que revisar el agente y la impresora", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    const error = await imprimirTicket({}).catch((falla) => falla);

    expect(error.message).toMatch(/agente de impresión/);
    expect(error.message).not.toMatch(/Failed to fetch/);
  });
});
