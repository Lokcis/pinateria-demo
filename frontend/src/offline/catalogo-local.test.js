import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api/api-client", () => ({ obtenerCatalogo: vi.fn() }));

import { obtenerCatalogo } from "../api/api-client";
import { reiniciarAlmacenParaPruebas } from "./almacen";
import {
  buscarEnCatalogoLocal,
  descargarCatalogo,
  guardarEnCache,
  infoCatalogoLocal,
  leerDeCache,
  normalizar,
  reiniciarCatalogoParaPruebas,
} from "./catalogo-local";

/** Un producto como lo devuelve GET /productos. */
function producto(id, nombre, extra = {}) {
  return {
    id,
    nombre,
    descripcion: null,
    categoria_id: 1,
    categoria_nombre: "Piñatas",
    codigo_barras: null,
    tipo: "unidad",
    precio_venta: "10000.00",
    stock_actual: 5,
    stock_minimo: 2,
    activo: true,
    componentes: [],
    ...extra,
  };
}

beforeEach(async () => {
  vi.resetAllMocks();
  reiniciarCatalogoParaPruebas();
  await reiniciarAlmacenParaPruebas();
});

describe("descargarCatalogo", () => {
  it("recorre todas las paginas y guarda cuantos productos hay y cuando", async () => {
    obtenerCatalogo
      .mockResolvedValueOnce({ total: 3, productos: [producto(1, "Globo"), producto(2, "Piñata")] })
      .mockResolvedValueOnce({ total: 3, productos: [producto(3, "Vela")] });

    const info = await descargarCatalogo("token");

    expect(info.cantidad).toBe(3);
    expect(obtenerCatalogo).toHaveBeenNthCalledWith(1, { pagina: 1, tamanoPagina: 100, activo: true }, "token");
    expect(obtenerCatalogo).toHaveBeenNthCalledWith(2, { pagina: 2, tamanoPagina: 100, activo: true }, "token");
    expect(await infoCatalogoLocal()).toMatchObject({ cantidad: 3 });
  });

  it("no guarda costos ni la receta", async () => {
    obtenerCatalogo.mockResolvedValueOnce({ total: 1, productos: [producto(1, "Globo", { costo_unitario: "3000" })] });
    await descargarCatalogo("token");

    const [encontrado] = await buscarEnCatalogoLocal("globo");

    expect(encontrado).not.toHaveProperty("costo_unitario");
    expect(encontrado).not.toHaveProperty("componentes");
  });

  it("si la descarga falla a medias, conserva la copia anterior", async () => {
    obtenerCatalogo.mockResolvedValueOnce({ total: 1, productos: [producto(1, "Globo")] });
    await descargarCatalogo("token");

    obtenerCatalogo
      .mockResolvedValueOnce({ total: 150, productos: Array.from({ length: 100 }, (_, i) => producto(100 + i, `Otro ${i}`)) })
      .mockRejectedValueOnce(new TypeError("Failed to fetch"));
    await expect(descargarCatalogo("token")).rejects.toThrow();

    reiniciarCatalogoParaPruebas(); // fuerza a leer de IndexedDB
    expect((await buscarEnCatalogoLocal("globo")).map((p) => p.id)).toEqual([1]);
    expect(await infoCatalogoLocal()).toMatchObject({ cantidad: 1 });
  });

  it("un catalogo nuevo reemplaza al anterior (un producto desactivado deja de estar)", async () => {
    obtenerCatalogo.mockResolvedValueOnce({ total: 2, productos: [producto(1, "Globo"), producto(2, "Vela")] });
    await descargarCatalogo("token");
    obtenerCatalogo.mockResolvedValueOnce({ total: 1, productos: [producto(1, "Globo")] });
    await descargarCatalogo("token");

    expect(await buscarEnCatalogoLocal("vela")).toEqual([]);
  });
});

describe("buscarEnCatalogoLocal", () => {
  beforeEach(async () => {
    obtenerCatalogo.mockResolvedValueOnce({
      total: 5,
      productos: [
        producto(1, "Piñata Mickey Mouse", { codigo_barras: "7701234567890" }),
        producto(2, "Globo metalizado estrella", { categoria_id: 2, categoria_nombre: "Globos" }),
        producto(3, "Globo latex rojo", { categoria_id: 2, categoria_nombre: "Globos" }),
        producto(4, "Bolsa de dulces", { categoria_nombre: "Dulces" }),
        producto(5, "Vela número 5", { activo: false }),
      ],
    });
    await descargarCatalogo("token");
  });

  it("un codigo de barras exacto da ese unico producto", async () => {
    expect((await buscarEnCatalogoLocal("7701234567890")).map((p) => p.id)).toEqual([1]);
  });

  it("busca texto parcial sin importar mayusculas ni tildes", async () => {
    expect((await buscarEnCatalogoLocal("PINATA")).map((p) => p.id)).toEqual([1]);
    expect((await buscarEnCatalogoLocal("piñ")).map((p) => p.id)).toEqual([1]);
  });

  it("tambien busca por categoria", async () => {
    expect((await buscarEnCatalogoLocal("dulces")).map((p) => p.id)).toEqual([4]);
    expect((await buscarEnCatalogoLocal("globos")).map((p) => p.id).sort()).toEqual([2, 3]);
  });

  it("todas las palabras escritas deben aparecer", async () => {
    expect((await buscarEnCatalogoLocal("globo rojo")).map((p) => p.id)).toEqual([3]);
  });

  it("los que empiezan por lo escrito salen primero", async () => {
    expect((await buscarEnCatalogoLocal("globo")).map((p) => p.id)).toEqual([3, 2]); // orden alfabetico entre los que empiezan igual
    expect((await buscarEnCatalogoLocal("estrella")).map((p) => p.id)).toEqual([2]);
  });

  it("no ofrece productos desactivados ni devuelve nada con texto vacio", async () => {
    expect(await buscarEnCatalogoLocal("vela")).toEqual([]);
    expect(await buscarEnCatalogoLocal("   ")).toEqual([]);
  });

  it("devuelve a lo sumo 20 resultados", async () => {
    obtenerCatalogo.mockResolvedValueOnce({
      total: 30,
      productos: Array.from({ length: 30 }, (_, i) => producto(100 + i, `Confite ${i}`)),
    });
    await descargarCatalogo("token");

    expect(await buscarEnCatalogoLocal("confite")).toHaveLength(20);
  });
});

describe("copia de datos sueltos", () => {
  it("guarda y lee la configuracion de descuentos", async () => {
    const config = { general: { tipo: "porcentaje", valor: "10.00", activo: true }, topes: {} };
    await guardarEnCache("descuentos", config);
    expect(await leerDeCache("descuentos")).toEqual(config);
  });

  it("devuelve null si no hay nada guardado", async () => {
    expect(await leerDeCache("vendedores")).toBeNull();
  });
});

describe("normalizar", () => {
  it("quita tildes y mayusculas", () => {
    expect(normalizar("  PIÑATA Ñandú  ")).toBe("pinata nandu");
  });
});
