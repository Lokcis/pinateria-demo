import { describe, expect, it } from "vitest";

import { describirRango, hoyEnBogota, rangoDePreset, restarMeses, validarRango } from "./rangos";

describe("rangos", () => {
  it("calcula los rangos rapidos terminando hoy", () => {
    const hoy = "2026-10-27";
    expect(rangoDePreset("hoy", hoy)).toEqual({ desde: hoy, hasta: hoy });
    expect(rangoDePreset("ayer", hoy)).toEqual({ desde: "2026-10-26", hasta: "2026-10-26" });
    expect(rangoDePreset("semana", hoy)).toEqual({ desde: "2026-10-21", hasta: hoy });
    expect(rangoDePreset("mes", hoy)).toEqual({ desde: "2026-09-28", hasta: hoy });
    expect(rangoDePreset("3meses", hoy)).toEqual({ desde: "2026-07-28", hasta: hoy });
    expect(rangoDePreset("6meses", hoy)).toEqual({ desde: "2026-04-28", hasta: hoy });
    expect(rangoDePreset("anio", hoy)).toEqual({ desde: "2025-10-28", hasta: hoy });
  });

  it("cruza meses y años y respeta el ultimo dia del mes", () => {
    expect(rangoDePreset("ayer", "2026-01-01").desde).toBe("2025-12-31");
    expect(restarMeses("2026-03-31", 1)).toBe("2026-02-28");
    expect(restarMeses("2026-01-15", 2)).toBe("2025-11-15");
  });

  it("el año bisiesto no supera el maximo del backend (366 dias)", () => {
    const { desde, hasta } = rangoDePreset("anio", "2028-03-01");
    expect(validarRango(desde, hasta, "2028-03-01")).toBeNull();
  });

  it("el dia de hoy se toma en hora de Bogota, no UTC", () => {
    // 2026-10-28 02:00 UTC = 2026-10-27 21:00 en Bogota
    expect(hoyEnBogota(new Date("2026-10-28T02:00:00Z"))).toBe("2026-10-27");
  });

  it("describe el rango", () => {
    expect(describirRango("2026-10-27", "2026-10-27", "2026-10-27")).toBe("Hoy");
    expect(describirRango("2026-10-26", "2026-10-26", "2026-10-27")).toBe("Ayer");
    expect(describirRango("2026-10-01", "2026-10-27", "2026-10-27")).toContain("–");
  });

  it("valida los rangos personalizados", () => {
    const hoy = "2026-10-27";
    expect(validarRango("", "2026-10-01", hoy)).toMatch(/Elige/);
    expect(validarRango("2026-10-10", "2026-10-01", hoy)).toMatch(/posterior/);
    expect(validarRango("2026-10-01", "2026-10-28", hoy)).toMatch(/futuras/);
    expect(validarRango("2024-01-01", "2026-10-27", hoy)).toMatch(/superar/);
    expect(validarRango("2026-10-01", "2026-10-27", hoy)).toBeNull();
  });
});
