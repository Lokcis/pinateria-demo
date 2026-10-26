import { describe, expect, it } from "vitest";

import { agruparSerie, escalaEje, indicesConEtiqueta } from "./serie";

/** Serie diaria consecutiva desde `inicio` con `total` fijo por dia. */
function serieDesde(inicio, dias, total = "1000") {
  const base = Date.parse(`${inicio}T00:00:00Z`);
  return Array.from({ length: dias }, (_, i) => ({
    fecha: new Date(base + i * 86400000).toISOString().slice(0, 10),
    total,
    cantidad: 1,
  }));
}

describe("agruparSerie", () => {
  it("hasta 31 dias, una barra por dia con su dia de la semana", () => {
    const { granularidad, columnas } = agruparSerie(serieDesde("2026-10-21", 7));
    expect(granularidad).toBe("dia");
    expect(columnas).toHaveLength(7);
    expect(columnas[0].etiqueta).toBe("mié 21"); // 21 oct 2026 es miercoles
    expect(columnas[0].descripcion).toBe("mié 21 oct");
  });

  it("de 32 a 186 dias, una barra por semana (lunes a domingo) que conserva el total", () => {
    const serie = serieDesde("2026-07-28", 92); // ~3 meses
    const { granularidad, columnas } = agruparSerie(serie);
    expect(granularidad).toBe("semana");
    expect(columnas[0].descripcion).toBe("Semana del 28 jul al 2 ago"); // la semana empieza el lunes 27, pero el rango el martes 28
    expect(columnas[0].dias).toBe(6); // el rango empieza un martes: semana incompleta
    expect(columnas.reduce((suma, c) => suma + c.total, 0)).toBe(92 * 1000);
    expect(columnas.reduce((suma, c) => suma + c.cantidad, 0)).toBe(92);
  });

  it("mas de 186 dias, una barra por mes calendario", () => {
    const { granularidad, columnas } = agruparSerie(serieDesde("2025-10-28", 365));
    expect(granularidad).toBe("mes");
    expect(columnas).toHaveLength(13);
    expect(columnas[0].descripcion).toBe("oct 2025");
    expect(columnas[0].dias).toBe(4); // 28 a 31 de octubre
    expect(columnas.reduce((suma, c) => suma + c.total, 0)).toBe(365 * 1000);
  });
});

describe("escalaEje", () => {
  it("elige un tope redondo que contiene el maximo", () => {
    expect(escalaEje(75000)).toEqual({ tope: 80000, marcas: [0, 20000, 40000, 60000, 80000] });
    expect(escalaEje(1000).tope).toBe(1000);
    expect(escalaEje(1234567).tope).toBeGreaterThanOrEqual(1234567);
  });

  it("sin ventas devuelve una escala valida", () => {
    expect(escalaEje(0)).toEqual({ tope: 1, marcas: [0, 1] });
  });
});

describe("indicesConEtiqueta", () => {
  it("con pocas barras etiqueta todas; con muchas, como maximo el limite", () => {
    expect(indicesConEtiqueta(5).size).toBe(5);
    expect(indicesConEtiqueta(31).size).toBeLessThanOrEqual(6);
    expect(indicesConEtiqueta(31).has(0)).toBe(true);
  });
});
