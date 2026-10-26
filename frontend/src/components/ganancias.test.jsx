import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Costos } from "./costos";
import { Ganancias } from "./ganancias";
import { AuthProvider } from "../context/auth-context";
import * as apiClient from "../api/api-client";

vi.mock("../api/api-client", async () => {
  const modulo = await vi.importActual("../api/api-client");
  return {
    ...modulo,
    obtenerGanancias: vi.fn(),
    obtenerCostos: vi.fn(),
    guardarCosto: vi.fn(),
    completarCostosVentas: vi.fn(),
  };
});

const margen = (ingreso, costo) => ({
  ingreso_neto: String(ingreso),
  costo_total: String(costo),
  margen: String(ingreso - costo),
  margen_porcentaje: ingreso ? String(Math.round(((ingreso - costo) * 1000) / ingreso) / 10) : null,
});

const GANANCIAS = {
  desde: "2026-10-06",
  hasta: "2026-10-08",
  resumen: margen(54000, 35000),
  por_dia: [
    { fecha: "2026-10-06", ...margen(0, 0) },
    { fecha: "2026-10-07", ...margen(10000, 12000) },
    { fecha: "2026-10-08", ...margen(44000, 23000) },
  ],
  por_producto: [
    { producto_id: 1, nombre: "Piñata Mickey", unidades: 2, ...margen(44000, 23000) },
    { producto_id: 2, nombre: "Globo", unidades: 4, ...margen(10000, 12000) },
  ],
  sin_costo: { lineas: 3, ingreso_neto: "36000.00" },
  neta: {
    margen_bruto: "19000.00",
    gastos_operativos: "5000.00",
    ganancia_neta: "14000.00",
    incompleta: true,
    ventas_cobradas: "90000.00",
    compras_recibidas: "10000.00",
    gastos_totales: "15000.00",
    resultado_de_caja: "75000.00",
  },
  generado_en: "2026-10-08T20:00:00Z",
};

const PRODUCTOS = [
  {
    producto_id: 5, nombre: "Ancheta Cumpleaños", categoria: "Anchetas", tipo: "ancheta", activo: true,
    precio_venta: "9000.00", costo_unitario: null, costo_sugerido: "1400.00", sugerido_incompleto: false,
  },
  {
    producto_id: 6, nombre: "Globo", categoria: "Globos", tipo: "unidad", activo: true,
    precio_venta: "1000.00", costo_unitario: "300.00", costo_sugerido: null, sugerido_incompleto: false,
  },
];

function renderizar(componente) {
  return render(<AuthProvider>{componente}</AuthProvider>);
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  apiClient.obtenerGanancias.mockResolvedValue(GANANCIAS);
  apiClient.obtenerCostos.mockResolvedValue({ productos: PRODUCTOS, lineas_por_completar: 4 });
});

/** Adendo v3, Fase G3 (RF-067): ganancia neta = margen bruto − gastos operativos; resultado de caja aparte. */
describe("Ganancias — ganancia neta y resultado de caja", () => {
  it("muestra la neta con sus gastos operativos y, aparte, el resultado de caja", async () => {
    renderizar(<Ganancias />);

    const seccion = await screen.findByRole("region", { name: "Ganancia neta" });
    expect(within(seccion).getByText("Ganancia neta", { selector: "p" }).closest("div")).toHaveTextContent(/14\.000/);
    expect(within(seccion).getByText("Gastos operativos").closest("div")).toHaveTextContent(/5\.000/);
    expect(within(seccion).getByText("Resultado de caja").closest("div")).toHaveTextContent(/75\.000/);
    expect(within(seccion).getByText("Cobrado en ventas").closest("div")).toHaveTextContent(/90\.000/);
    expect(within(seccion).getByText("Gastos totales").closest("div")).toHaveTextContent(/15\.000/);
    expect(within(seccion).getByText(/Incluye \$\s?10\.000 de compras recibidas/)).toBeInTheDocument();
    expect(within(seccion).getByText(/no es una ganancia contable/)).toBeInTheDocument();
  });

  it("avisa que la neta está incompleta cuando faltan costos", async () => {
    renderizar(<Ganancias />);

    const seccion = await screen.findByRole("region", { name: "Ganancia neta" });
    expect(within(seccion).getByRole("note")).toHaveTextContent("Ganancia neta incompleta");
  });

  it("sin ventas sin costo no muestra el aviso, y una neta negativa se ve como pérdida", async () => {
    apiClient.obtenerGanancias.mockResolvedValue({
      ...GANANCIAS,
      sin_costo: { lineas: 0, ingreso_neto: "0" },
      neta: { ...GANANCIAS.neta, incompleta: false, ganancia_neta: "-3000.00" },
    });
    renderizar(<Ganancias />);

    const seccion = await screen.findByRole("region", { name: "Ganancia neta" });
    expect(within(seccion).queryByRole("note")).not.toBeInTheDocument();
    expect(within(seccion).getByText("Pérdida en el período")).toBeInTheDocument();
  });
});

/** HU-09: "el dashboard muestre el margen por periodo y por producto con graficos"; sin costo aparte. */
describe("Ganancias", () => {
  it("muestra el margen, el porcentaje, el aviso de ventas sin costo y el margen por producto", async () => {
    renderizar(<Ganancias />);

    expect(await screen.findByText("Margen bruto")).toBeInTheDocument();
    expect(screen.getByText(/19\.000/)).toBeInTheDocument();
    expect(screen.getByText("35,2 %")).toBeInTheDocument();
    expect(screen.getByText(/3/, { selector: "strong" })).toBeInTheDocument();
    expect(screen.getByText(/sin\s+costo/)).toBeInTheDocument();
    const productos = screen.getAllByRole("listitem").map((item) => item.textContent);
    expect(productos[0]).toContain("Piñata Mickey");
    expect(productos[1]).toMatch(/Globo.*-\$\s?2\.000/);
  });

  it("pide el mes por defecto", async () => {
    renderizar(<Ganancias />);
    await screen.findByText("Margen bruto");
    const [rango] = apiClient.obtenerGanancias.mock.calls[0];
    expect(rango.desde < rango.hasta).toBe(true);
  });

  it("el grafico marca un dia con perdida", async () => {
    const usuario = userEvent.setup();
    renderizar(<Ganancias />);

    const grafico = await screen.findByRole("group", { name: "Margen por período" });
    const barras = within(grafico).getAllByRole("button");
    expect(barras).toHaveLength(3);
    await usuario.click(barras[1]);
    expect(screen.getByRole("status")).toHaveTextContent("(pérdida)");
  });
});

/** HU-09: "el administrador pueda registrar a mano el costo ... y ... un costo sugerido" para anchetas. */
describe("Costos", () => {
  it("el administrador guarda un costo escrito y el sugerido de una ancheta", async () => {
    const usuario = userEvent.setup();
    apiClient.guardarCosto.mockImplementation(async (id, costo) => ({ ...PRODUCTOS[0], costo_unitario: costo }));
    renderizar(<Costos editable />);

    const campo = await screen.findByRole("textbox", { name: "Costo de Globo" });
    expect(campo).toHaveValue("300");
    await usuario.clear(campo);
    await usuario.type(campo, "350,5");
    await usuario.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(apiClient.guardarCosto).toHaveBeenCalledWith(6, "350.5", null));

    await usuario.click(screen.getByRole("button", { name: "Usar el costo sugerido para Ancheta Cumpleaños" }));
    await waitFor(() => expect(apiClient.guardarCosto).toHaveBeenCalledWith(5, "1400", null));
  });

  it("rechaza un costo no valido sin llamar al backend", async () => {
    const usuario = userEvent.setup();
    renderizar(<Costos editable />);

    const campo = await screen.findByRole("textbox", { name: "Costo de Globo" });
    await usuario.clear(campo);
    await usuario.type(campo, "-5");
    await usuario.click(screen.getByRole("button", { name: "Guardar" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Costo no válido.");
    expect(apiClient.guardarCosto).not.toHaveBeenCalled();
  });

  it("completa los costos de ventas anteriores tras confirmar", async () => {
    const usuario = userEvent.setup();
    apiClient.completarCostosVentas.mockResolvedValue({ lineas_completadas: 4 });
    renderizar(<Costos editable />);

    await usuario.click(await screen.findByRole("button", { name: "Completar costos de ventas anteriores" }));
    await usuario.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Completar" }));

    await waitFor(() => expect(apiClient.completarCostosVentas).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("Se completaron 4 líneas.")).toBeInTheDocument();
  });

  it("el propietario solo ve los costos, sin editar ni completar", async () => {
    renderizar(<Costos editable={false} />);

    expect(await screen.findByText("Ancheta Cumpleaños")).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Completar/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Usar/ })).not.toBeInTheDocument();
  });

  it("filtra los productos sin costo", async () => {
    const usuario = userEvent.setup();
    renderizar(<Costos editable />);
    await screen.findByText("Globo");

    await usuario.click(screen.getByRole("checkbox", { name: "Solo sin costo" }));

    await waitFor(() => expect(apiClient.obtenerCostos).toHaveBeenLastCalledWith(null, { soloSinCosto: true }));
  });
});
