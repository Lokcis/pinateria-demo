import { describe, expect, it } from "vitest";

import { esErrorDeConexion, nuevoUuid } from "./conexion";

describe("esErrorDeConexion", () => {
  it("reconoce la falla de red de fetch (TypeError)", () => {
    expect(esErrorDeConexion(new TypeError("Failed to fetch"))).toBe(true);
  });

  it("reconoce el tiempo agotado", () => {
    expect(esErrorDeConexion(new DOMException("aborted", "AbortError"))).toBe(true);
    expect(esErrorDeConexion(new DOMException("timeout", "TimeoutError"))).toBe(true);
  });

  it.each([502, 503, 504, 521, 522, 530])("trata el estado %i (tunel o servidor caido) como falla de conexion", (status) => {
    expect(esErrorDeConexion({ name: "ApiError", status })).toBe(true);
  });

  it.each([400, 401, 403, 404, 409, 422, 500])("NO trata el estado %i como falla de conexion", (status) => {
    expect(esErrorDeConexion({ name: "ApiError", status })).toBe(false);
  });

  it("ignora lo que no es un error", () => {
    expect(esErrorDeConexion(null)).toBe(false);
    expect(esErrorDeConexion(undefined)).toBe(false);
  });
});

describe("nuevoUuid", () => {
  it("genera un UUID v4 distinto cada vez", () => {
    const a = nuevoUuid();
    const b = nuevoUuid();
    expect(a).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    expect(a).not.toBe(b);
  });
});
