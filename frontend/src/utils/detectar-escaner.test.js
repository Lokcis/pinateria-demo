import { describe, expect, it } from "vitest";
import { esPatronDeEscaner, UMBRAL_RAFAGA_MS } from "./detectar-escaner";

describe("esPatronDeEscaner", () => {
  it("HU-01: detecta un escaneo cuando el promedio entre teclas es muy rapido", () => {
    const deltasDeEscaner = [5, 4, 6, 5, 4, 5, 5, 4, 6, 5, 5, 4];
    expect(esPatronDeEscaner(deltasDeEscaner)).toBe(true);
  });

  it("HU-01: NO detecta un escaneo con tecleo manual normal (decenas/cientos de ms)", () => {
    const deltasDeTecleoHumano = [180, 220, 150, 300, 210];
    expect(esPatronDeEscaner(deltasDeTecleoHumano)).toBe(false);
  });

  it("no evalua el patron con muy pocos caracteres (informacion insuficiente)", () => {
    // Solo 1 delta (2 caracteres) es menos que LONGITUD_MINIMA_PARA_RAFAGA - 1.
    expect(esPatronDeEscaner([5])).toBe(false);
  });

  it("respeta el umbral exacto: justo en el limite no cuenta como rafaga", () => {
    const promedioExactoEnElUmbral = [UMBRAL_RAFAGA_MS, UMBRAL_RAFAGA_MS, UMBRAL_RAFAGA_MS];
    expect(esPatronDeEscaner(promedioExactoEnElUmbral)).toBe(false);
  });

  it("acepta un umbral y longitud minima configurables", () => {
    expect(esPatronDeEscaner([80, 90], 100, 3)).toBe(true);
    expect(esPatronDeEscaner([80, 90], 50, 3)).toBe(false);
  });
});
