import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { elegirOpcion } from "../utils/test-desplegable";
import { Gastos } from "./gastos";
import { AuthProvider } from "../context/auth-context";
import * as apiClient from "../api/api-client";

vi.mock("../api/api-client", async () => {
  const modulo = await vi.importActual("../api/api-client");
  return {
    ...modulo,
    obtenerCategoriasGasto: vi.fn(),
    crearCategoriaGasto: vi.fn(),
    editarCategoriaGasto: vi.fn(),
    obtenerGastos: vi.fn(),
    obtenerResumenGastos: vi.fn(),
    crearGasto: vi.fn(),
    editarGasto: vi.fn(),
    anularGasto: vi.fn(),
    exportarGastos: vi.fn(),
  };
});

const CATEGORIAS = [
  { id: 1, nombre: "Compra de mercancía", activa: true, es_sistema: true },
  { id: 2, nombre: "Arriendo", activa: true, es_sistema: false },
  { id: 3, nombre: "Servicios públicos", activa: true, es_sistema: false },
  { id: 4, nombre: "Vieja", activa: false, es_sistema: false },
];

const base = {
  origen: "gasto",
  fecha: "2026-10-19",
  categoria_id: 2,
  categoria: "Arriendo",
  beneficiario: null,
  metodo_pago: "efectivo",
  plataforma: null,
  registrado_por_id: 7,
  registrado_por: "Ana Pérez",
  creado_en: "2026-10-19T15:00:00Z",
  actualizado_en: null,
  actualizado_por: null,
  anulado: false,
  anulado_en: null,
  anulado_por: null,
  motivo_anulacion: null,
  cubierto_por_corte: false,
  editable: true,
};

const GASTO = { ...base, id: 11, descripcion: "Pago del local", monto: "150000.00", beneficiario: "Inmobiliaria" };
const ANULADO = {
  ...base,
  id: 12,
  descripcion: "Pago repetido",
  monto: "20000.00",
  anulado: true,
  editable: false,
  anulado_en: "2026-10-19T16:00:00Z",
  anulado_por: "Ana Pérez",
  motivo_anulacion: "Lo anoté dos veces",
};
const COMPRA = {
  ...base,
  origen: "compra",
  id: 5,
  descripcion: "Compra #5 — Papeles del Valle SAS",
  categoria_id: 1,
  categoria: "Compra de mercancía",
  monto: "10000.00",
  metodo_pago: "tarjeta",
  editable: false,
};

const RESUMEN = {
  desde: "2026-10-01",
  hasta: "2026-10-19",
  total: "180000.00",
  total_compras: "10000.00",
  total_operativo: "170000.00",
  por_categoria: [
    { categoria_id: 2, categoria: "Arriendo", cantidad: 1, total: "150000.00" },
    { categoria_id: 1, categoria: "Compra de mercancía", cantidad: 1, total: "10000.00" },
  ],
  por_metodo_pago: [
    { metodo_pago: "efectivo", total: "170000.00" },
    { metodo_pago: "tarjeta", total: "10000.00" },
  ],
};

function renderizar(rol, propiedades = {}) {
  localStorage.setItem("mm_pos_token", `c.${btoa(JSON.stringify({ sub: "7", rol }))}.f`);
  return render(
    <AuthProvider>
      <Gastos {...propiedades} />
    </AuthProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  apiClient.obtenerCategoriasGasto.mockResolvedValue(CATEGORIAS);
  apiClient.obtenerGastos.mockResolvedValue([GASTO, ANULADO, COMPRA]);
  apiClient.obtenerResumenGastos.mockResolvedValue(RESUMEN);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Gastos — corte de caja cerrado (Adendo v3, Fase G2: RF-074)", () => {
  it("el vendedor ve un gasto ya cubierto por un corte sin botones de editar y con la explicación", async () => {
    apiClient.obtenerGastos.mockResolvedValue([{ ...GASTO, cubierto_por_corte: true, editable: false }]);
    renderizar("vendedor");

    expect(await screen.findByText("Pago del local")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Editar Pago del local/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Anular Pago del local/ })).not.toBeInTheDocument();
    expect(screen.getByText(/Ya está en un corte de caja cerrado/)).toBeInTheDocument();
  });

  it("el administrador sigue pudiendo editarlo y no ve esa explicación", async () => {
    apiClient.obtenerGastos.mockResolvedValue([{ ...GASTO, cubierto_por_corte: true, editable: true }]);
    renderizar("administrador");

    expect(await screen.findByRole("button", { name: /Editar Pago del local/ })).toBeInTheDocument();
    expect(screen.queryByText(/Ya está en un corte de caja cerrado/)).not.toBeInTheDocument();
  });
});

describe("Gastos — administrador", () => {
  it("lista los gastos y las compras, con totales por categoría y forma de pago", async () => {
    renderizar("administrador");

    expect(await screen.findByText("Pago del local")).toBeInTheDocument();
    expect(screen.getByText("Compra #5 — Papeles del Valle SAS")).toBeInTheDocument();
    expect(screen.getByText("Total de gastos").closest("div")).toHaveTextContent(/180\.000/);
    expect(screen.getByText("Gastos operativos").closest("div")).toHaveTextContent(/170\.000/);
    const porCategoria = screen.getByText("Por categoría").closest("section, div");
    expect(porCategoria).toHaveTextContent("Arriendo");
    expect(screen.getByText("Por forma de pago").closest("section, div")).toHaveTextContent("Tarjeta");
  });

  it("la compra es de solo lectura y enlaza a Compras", async () => {
    const alIrACompras = vi.fn();
    renderizar("administrador", { alIrACompras });

    await screen.findByText("Pago del local");
    expect(screen.queryByRole("button", { name: /Editar Compra #5/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Anular Compra #5/ })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Ver en Compras" }));
    expect(alIrACompras).toHaveBeenCalled();
  });

  it("un gasto anulado se ve tachado con quién, cuándo y por qué, y sin acciones", async () => {
    renderizar("administrador");

    const descripcion = await screen.findByText("Pago repetido");
    expect(descripcion.closest("p")).toHaveClass("line-through");
    const fila = descripcion.closest("li");
    expect(fila).toHaveTextContent(/Anulado por Ana Pérez/);
    expect(fila).toHaveTextContent("Motivo: Lo anoté dos veces");
    expect(within(fila).queryByRole("button")).not.toBeInTheDocument();
  });

  it("registra un gasto en efectivo con la fecha elegida", async () => {
    apiClient.crearGasto.mockResolvedValue(GASTO);
    renderizar("administrador");
    await screen.findByText("Pago del local");

    await userEvent.click(screen.getByRole("button", { name: "Nuevo gasto" }));
    const formulario = screen.getByRole("button", { name: "Guardar gasto" }).closest("form");
    await elegirOpcion(within(formulario).getAllByRole("combobox")[0], "2");
    await userEvent.type(within(formulario).getByPlaceholderText("$"), "150000");
    await userEvent.type(within(formulario).getByPlaceholderText("¿Qué se pagó?"), "Pago del local");
    await userEvent.click(screen.getByRole("button", { name: "Guardar gasto" }));

    await waitFor(() => expect(apiClient.crearGasto).toHaveBeenCalledTimes(1));
    const [payload] = apiClient.crearGasto.mock.calls[0];
    expect(payload).toMatchObject({
      categoria_id: 2,
      descripcion: "Pago del local",
      monto: 150000,
      metodo_pago: "efectivo",
      plataforma: null,
      beneficiario: null,
    });
    expect(payload.fecha).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("no ofrece las categorías desactivadas al registrar", async () => {
    renderizar("administrador");
    await screen.findByText("Pago del local");

    await userEvent.click(screen.getByRole("button", { name: "Nuevo gasto" }));
    const formulario = screen.getByRole("button", { name: "Guardar gasto" }).closest("form");
    await userEvent.click(within(formulario).getAllByRole("combobox")[0]);

    const opciones = screen.getAllByRole("option").map((o) => o.textContent);
    expect(opciones).toContain("Arriendo");
    expect(opciones).not.toContain("Vieja");
  });

  it("edita un gasto mandando solo lo que cambió", async () => {
    apiClient.editarGasto.mockResolvedValue({ ...GASTO, monto: "160000.00" });
    renderizar("administrador");
    await screen.findByText("Pago del local");

    await userEvent.click(screen.getByRole("button", { name: "Editar Pago del local" }));
    const monto = screen.getByPlaceholderText("$");
    await userEvent.clear(monto);
    await userEvent.type(monto, "160000");
    await userEvent.click(screen.getByRole("button", { name: "Guardar gasto" }));

    await waitFor(() => expect(apiClient.editarGasto).toHaveBeenCalledWith(11, { monto: 160000 }, expect.any(String)));
  });

  it("avisa si se guarda sin cambios", async () => {
    renderizar("administrador");
    await screen.findByText("Pago del local");

    await userEvent.click(screen.getByRole("button", { name: "Editar Pago del local" }));
    await userEvent.click(screen.getByRole("button", { name: "Guardar gasto" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("No hay cambios que guardar.");
    expect(apiClient.editarGasto).not.toHaveBeenCalled();
  });

  it("para anular pide el motivo y lo envía", async () => {
    apiClient.anularGasto.mockResolvedValue({ ...GASTO, anulado: true });
    renderizar("administrador");
    await screen.findByText("Pago del local");

    await userEvent.click(screen.getByRole("button", { name: "Anular Pago del local" }));
    const dialogo = screen.getByRole("dialog");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Anular gasto" }));
    expect(within(dialogo).getByRole("alert")).toHaveTextContent("Escribe el motivo");
    expect(apiClient.anularGasto).not.toHaveBeenCalled();

    await userEvent.type(within(dialogo).getByRole("textbox"), "Monto mal digitado");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Anular gasto" }));

    await waitFor(() => expect(apiClient.anularGasto).toHaveBeenCalledWith(11, "Monto mal digitado", expect.any(String)));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(apiClient.obtenerGastos).toHaveBeenCalledTimes(2); // recargó la lista
  });

  it("exporta con el rango y los filtros actuales y descarga el archivo", async () => {
    const crear = vi.fn(() => "blob:gastos");
    const revocar = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL: crear, revokeObjectURL: revocar });
    const clic = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    apiClient.exportarGastos.mockResolvedValue({ contenido: new Blob(["x"]), nombre: "gastos_2026-10-01_a_2026-10-19.csv" });
    renderizar("administrador");
    await screen.findByText("Pago del local");

    await userEvent.click(screen.getByRole("button", { name: "Exportar" }));

    await waitFor(() => expect(apiClient.exportarGastos).toHaveBeenCalledTimes(1));
    const [filtros] = apiClient.exportarGastos.mock.calls[0];
    expect(filtros).toMatchObject({ categoriaId: "", metodoPago: "", incluirAnulados: false });
    expect(filtros.desde).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    await waitFor(() => expect(clic).toHaveBeenCalled());
    expect(revocar).toHaveBeenCalledWith("blob:gastos");
    vi.unstubAllGlobals();
  });

  it("administra las categorías: crea una y desactiva otra; la de sistema no se toca", async () => {
    apiClient.crearCategoriaGasto.mockResolvedValue({ id: 9, nombre: "Papelería", activa: true, es_sistema: false });
    apiClient.editarCategoriaGasto.mockResolvedValue({ ...CATEGORIAS[1], activa: false });
    renderizar("administrador");
    await screen.findByText("Pago del local");

    await userEvent.click(screen.getByRole("button", { name: "Categorías" }));
    const panel = screen.getByRole("region", { name: "Categorías de gasto" });
    expect(within(panel).getByText("De sistema")).toBeInTheDocument();
    expect(within(panel).queryByRole("button", { name: /Desactivar Compra de mercancía/ })).not.toBeInTheDocument();

    await userEvent.type(within(panel).getByLabelText("Nombre de la nueva categoría"), "Papelería");
    await userEvent.click(within(panel).getByRole("button", { name: "Agregar" }));
    await waitFor(() => expect(apiClient.crearCategoriaGasto).toHaveBeenCalledWith({ nombre: "Papelería" }, expect.any(String)));

    await userEvent.click(within(panel).getByRole("button", { name: "Desactivar Arriendo" }));
    await waitFor(() => expect(apiClient.editarCategoriaGasto).toHaveBeenCalledWith(2, { activa: false }, expect.any(String)));
  });
});

describe("Gastos — validaciones del formulario", () => {
  async function abrirFormulario() {
    renderizar("administrador");
    await screen.findByText("Pago del local");
    await userEvent.click(screen.getByRole("button", { name: "Nuevo gasto" }));
    const formulario = screen.getByRole("button", { name: "Guardar gasto" }).closest("form");
    await elegirOpcion(within(formulario).getAllByRole("combobox")[0], "3");
    await userEvent.type(within(formulario).getByPlaceholderText("¿Qué se pagó?"), "Luz");
    return formulario;
  }

  it("en efectivo exige un múltiplo de $50 y no llama a la API", async () => {
    const formulario = await abrirFormulario();
    await userEvent.type(within(formulario).getByPlaceholderText("$"), "20025");
    await userEvent.click(screen.getByRole("button", { name: "Guardar gasto" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("múltiplo de $50");
    expect(apiClient.crearGasto).not.toHaveBeenCalled();
  });

  it("en transferencia exige la plataforma y la manda", async () => {
    apiClient.crearGasto.mockResolvedValue(GASTO);
    const formulario = await abrirFormulario();
    await userEvent.type(within(formulario).getByPlaceholderText("$"), "20025");
    await elegirOpcion(screen.getByRole("combobox", { name: "Forma de pago" }), "transferencia");
    await userEvent.click(screen.getByRole("button", { name: "Guardar gasto" }));
    expect(apiClient.crearGasto).not.toHaveBeenCalled(); // falta la plataforma (campo requerido)

    await elegirOpcion(screen.getByRole("combobox", { name: "Plataforma de la transferencia" }), "nequi");
    await userEvent.click(screen.getByRole("button", { name: "Guardar gasto" }));

    await waitFor(() => expect(apiClient.crearGasto).toHaveBeenCalledTimes(1));
    expect(apiClient.crearGasto.mock.calls[0][0]).toMatchObject({ monto: 20025, metodo_pago: "transferencia", plataforma: "nequi" });
  });

  it("muestra el error del servidor si rechaza el gasto", async () => {
    apiClient.crearGasto.mockRejectedValue(new Error("La categoria «Vieja» esta desactivada."));
    const formulario = await abrirFormulario();
    await userEvent.type(within(formulario).getByPlaceholderText("$"), "20050");
    await userEvent.click(screen.getByRole("button", { name: "Guardar gasto" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("esta desactivada");
  });
});

describe("Gastos — vendedor", () => {
  it("no ve totales, exportar ni categorías, y no pide el resumen", async () => {
    apiClient.obtenerGastos.mockResolvedValue([GASTO]);
    renderizar("vendedor");

    await screen.findByText("Pago del local");
    expect(apiClient.obtenerResumenGastos).not.toHaveBeenCalled();
    expect(screen.queryByText("Total de gastos")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Exportar" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Categorías" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Nuevo gasto" })).toBeInTheDocument();
  });

  it("registra sin elegir fecha (siempre es la de hoy) y solo ve las categorías activas", async () => {
    apiClient.obtenerCategoriasGasto.mockResolvedValue(CATEGORIAS.filter((c) => c.activa));
    apiClient.obtenerGastos.mockResolvedValue([]);
    apiClient.crearGasto.mockResolvedValue(GASTO);
    renderizar("vendedor");
    await screen.findByText("No hay gastos en este rango.");

    await userEvent.click(screen.getByRole("button", { name: "Nuevo gasto" }));
    const formulario = screen.getByRole("button", { name: "Guardar gasto" }).closest("form");
    expect(within(formulario).queryByLabelText("Fecha")).not.toBeInTheDocument();
    expect(within(formulario).getByText("Se registra con la fecha de hoy.")).toBeInTheDocument();
    await elegirOpcion(within(formulario).getAllByRole("combobox")[0], "2");
    await userEvent.type(within(formulario).getByPlaceholderText("$"), "5000");
    await userEvent.type(within(formulario).getByPlaceholderText("¿Qué se pagó?"), "Bolsas");
    await userEvent.click(screen.getByRole("button", { name: "Guardar gasto" }));

    await waitFor(() => expect(apiClient.crearGasto).toHaveBeenCalledTimes(1));
    expect(apiClient.crearGasto.mock.calls[0][0]).not.toHaveProperty("fecha");
  });

  it("pide los gastos de hoy por defecto", async () => {
    renderizar("vendedor");
    await screen.findByText("Pago del local");

    const [filtros] = apiClient.obtenerGastos.mock.calls[0];
    expect(filtros.desde).toBe(filtros.hasta);
  });
});

describe("Gastos — propietario (solo lectura)", () => {
  it("consulta y exporta, pero no registra, edita ni anula", async () => {
    renderizar("propietario", { soloLectura: true });

    await screen.findByText("Pago del local");
    expect(screen.getByText("Total de gastos")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Exportar" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Nuevo gasto" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Editar / })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Anular / })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Categorías" })).not.toBeInTheDocument();
  });
});

describe("Gastos — sin conexión", () => {
  it("avisa que necesita conexión y no deja registrar ni exportar", async () => {
    vi.spyOn(navigator, "onLine", "get").mockReturnValue(false);
    renderizar("administrador");

    await screen.findByText("Pago del local");
    expect(screen.getByRole("status")).toHaveTextContent("necesitan conexión");
    expect(screen.getByRole("button", { name: "Nuevo gasto" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Exportar" })).toBeDisabled();
  });

  it("muestra el error si el servidor no responde", async () => {
    apiClient.obtenerGastos.mockRejectedValue(new Error("Failed to fetch"));
    renderizar("administrador");

    expect(await screen.findByRole("alert")).toHaveTextContent("Failed to fetch");
  });
});
