import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { elegirOpcion } from "../utils/test-desplegable";
import { Inventario } from "./inventario";
import { AuthProvider } from "../context/auth-context";
import * as apiClient from "../api/api-client";

vi.mock("../api/api-client", async () => {
  const modulo = await vi.importActual("../api/api-client");
  return {
    ...modulo,
    obtenerCatalogo: vi.fn(),
    obtenerCategorias: vi.fn(),
    obtenerAjustesInventario: vi.fn(),
    buscarProductos: vi.fn(),
    crearProducto: vi.fn(),
    editarProducto: vi.fn(),
    desactivarProducto: vi.fn(),
    obtenerProductosQueLoUsan: vi.fn(),
  };
});

const BASE = {
  descripcion: null,
  categoria_id: 1,
  categoria_nombre: "Fiesta",
  codigo_barras: null,
  precio_venta: "1000.00",
  stock_actual: 12,
  stock_minimo: 5,
  activo: true,
  componentes: [],
};
const GLOBO = { ...BASE, id: 1, nombre: "Globo rojo", tipo: "unidad" };
const ANCHETA = {
  ...BASE,
  id: 2,
  nombre: "Ancheta cumpleaños",
  tipo: "ancheta",
  precio_venta: "25000.00",
  componentes: [
    { producto_id: 1, nombre: "Globo rojo", cantidad: 3, activo: true },
    { producto_id: 3, nombre: "Dulce mixto", cantidad: 10, activo: false },
  ],
};

function renderizar() {
  localStorage.setItem("mm_pos_token", `c.${btoa(JSON.stringify({ sub: "1", rol: "administrador" }))}.f`);
  return render(
    <AuthProvider>
      <Inventario />
    </AuthProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  apiClient.obtenerCatalogo.mockResolvedValue({ total: 2, productos: [GLOBO, ANCHETA] });
  apiClient.obtenerCategorias.mockResolvedValue([{ id: 1, nombre: "Fiesta", descripcion: null }]);
  apiClient.obtenerAjustesInventario.mockResolvedValue([]);
  apiClient.obtenerProductosQueLoUsan.mockResolvedValue([]);
});

describe("Inventario — productos compuestos", () => {
  it("la tarjeta de una ancheta muestra de qué artículos está compuesta", async () => {
    renderizar();
    await userEvent.click(await screen.findByRole("button", { name: /Ancheta cumpleaños/ }));

    const composicion = screen.getByText("Compuesto por").parentElement;
    expect(within(composicion).getByText(/Globo rojo/)).toBeInTheDocument();
    expect(within(composicion).getByText("3 ×")).toBeInTheDocument();
    expect(within(composicion).getByText("10 ×")).toBeInTheDocument();
    expect(within(composicion).getByText("Inactivo")).toBeInTheDocument(); // el dulce está desactivado
  });

  it("un producto simple no muestra composición", async () => {
    renderizar();
    await userEvent.click(await screen.findByRole("button", { name: /Globo rojo/ }));
    expect(screen.queryByText("Compuesto por")).not.toBeInTheDocument();
  });

  it("al crear un producto compuesto se busca, se agrega el componente y se envía la receta", async () => {
    apiClient.buscarProductos.mockResolvedValue([{ id: 1, nombre: "Globo rojo" }]);
    apiClient.crearProducto.mockResolvedValue(ANCHETA);
    renderizar();
    await screen.findByText("Globo rojo");

    await userEvent.click(screen.getByRole("button", { name: "+ Nuevo producto" }));
    await userEvent.type(screen.getByLabelText("Nombre"), "Ancheta nueva");
    await elegirOpcion(screen.getByLabelText("Categoría"), "1");
    await userEvent.type(screen.getByLabelText("Precio de venta"), "25000");
    await userEvent.type(screen.getByLabelText("Stock inicial"), "0");

    await userEvent.click(screen.getByLabelText(/Producto compuesto/));
    await userEvent.type(screen.getByLabelText("Buscar componente"), "globo");
    await userEvent.click(screen.getByRole("button", { name: "Buscar artículo" }));
    await userEvent.click(await screen.findByRole("button", { name: "Globo rojo" }));
    const cantidad = screen.getByLabelText("Cantidad de Globo rojo");
    await userEvent.clear(cantidad);
    await userEvent.type(cantidad, "4");
    await userEvent.click(screen.getByRole("button", { name: "Crear producto" }));

    await waitFor(() => expect(apiClient.crearProducto).toHaveBeenCalled());
    expect(apiClient.crearProducto.mock.calls[0][0]).toMatchObject({
      nombre: "Ancheta nueva",
      tipo: "ancheta",
      componentes: [{ producto_id: 1, cantidad: 4 }],
    });
  });

  it("un producto simple se crea sin tipo ni componentes", async () => {
    apiClient.crearProducto.mockResolvedValue(GLOBO);
    renderizar();
    await screen.findByText("Globo rojo");

    await userEvent.click(screen.getByRole("button", { name: "+ Nuevo producto" }));
    await userEvent.type(screen.getByLabelText("Nombre"), "Globo azul");
    await elegirOpcion(screen.getByLabelText("Categoría"), "1");
    await userEvent.type(screen.getByLabelText("Precio de venta"), "500");
    await userEvent.type(screen.getByLabelText("Stock inicial"), "10");
    await userEvent.click(screen.getByRole("button", { name: "Crear producto" }));

    await waitFor(() => expect(apiClient.crearProducto).toHaveBeenCalled());
    const payload = apiClient.crearProducto.mock.calls[0][0];
    expect(payload).not.toHaveProperty("componentes");
    expect(payload).not.toHaveProperty("tipo");
  });

  it("al editar una ancheta se puede quitar un componente y se envía la receta completa", async () => {
    apiClient.editarProducto.mockResolvedValue(ANCHETA);
    renderizar();
    await userEvent.click(await screen.findByRole("button", { name: /Ancheta cumpleaños/ }));

    await userEvent.click(screen.getByRole("button", { name: "Editar datos" }));
    await userEvent.click(screen.getByRole("button", { name: "Quitar Dulce mixto" }));
    await userEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => expect(apiClient.editarProducto).toHaveBeenCalled());
    expect(apiClient.editarProducto.mock.calls[0][1]).toMatchObject({
      tipo: "ancheta",
      componentes: [{ producto_id: 1, cantidad: 3 }],
    });
  });

  it("al desmarcar 'compuesto' en una ancheta la vuelve unidad y vacía la receta", async () => {
    apiClient.editarProducto.mockResolvedValue(GLOBO);
    renderizar();
    await userEvent.click(await screen.findByRole("button", { name: /Ancheta cumpleaños/ }));

    await userEvent.click(screen.getByRole("button", { name: "Editar datos" }));
    await userEvent.click(screen.getByLabelText(/Producto compuesto/));
    await userEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => expect(apiClient.editarProducto).toHaveBeenCalled());
    expect(apiClient.editarProducto.mock.calls[0][1]).toMatchObject({ tipo: "unidad", componentes: [] });
  });

  it("avisa al desactivar un producto que es componente de una ancheta", async () => {
    apiClient.obtenerProductosQueLoUsan.mockResolvedValue([{ id: 2, nombre: "Ancheta cumpleaños", tipo: "ancheta", activo: true }]);
    apiClient.desactivarProducto.mockResolvedValue({ ...GLOBO, activo: false });
    renderizar();
    await userEvent.click(await screen.findByRole("button", { name: /Globo rojo/ }));

    await userEvent.click(screen.getByRole("button", { name: "Desactivar producto" }));

    const dialogo = await screen.findByRole("alertdialog");
    expect(apiClient.obtenerProductosQueLoUsan).toHaveBeenCalledWith(1, expect.any(String));
    expect(within(dialogo).getByRole("note")).toHaveTextContent("Ancheta cumpleaños");
    expect(within(dialogo).getByRole("note")).toHaveTextContent("se seguirá descontando");

    await userEvent.click(within(dialogo).getByRole("button", { name: "Desactivar" }));
    await waitFor(() => expect(apiClient.desactivarProducto).toHaveBeenCalled());
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });

  it("no desactiva si el administrador cancela el aviso", async () => {
    apiClient.obtenerProductosQueLoUsan.mockResolvedValue([{ id: 2, nombre: "Ancheta cumpleaños", tipo: "ancheta", activo: true }]);
    renderizar();
    await userEvent.click(await screen.findByRole("button", { name: /Globo rojo/ }));

    await userEvent.click(screen.getByRole("button", { name: "Desactivar producto" }));
    await userEvent.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Cancelar" }));

    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(apiClient.desactivarProducto).not.toHaveBeenCalled();
  });

  it("Escape cierra el cuadro sin desactivar", async () => {
    renderizar();
    await userEvent.click(await screen.findByRole("button", { name: /Globo rojo/ }));

    await userEvent.click(screen.getByRole("button", { name: "Desactivar producto" }));
    await screen.findByRole("alertdialog");
    await userEvent.keyboard("{Escape}");

    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(apiClient.desactivarProducto).not.toHaveBeenCalled();
  });

  it("si un producto no es componente de nada, el cuadro no lleva aviso", async () => {
    apiClient.desactivarProducto.mockResolvedValue({ ...GLOBO, activo: false });
    renderizar();
    await userEvent.click(await screen.findByRole("button", { name: /Globo rojo/ }));

    await userEvent.click(screen.getByRole("button", { name: "Desactivar producto" }));
    const dialogo = await screen.findByRole("alertdialog");

    expect(within(dialogo).queryByRole("note")).not.toBeInTheDocument();
    await userEvent.click(within(dialogo).getByRole("button", { name: "Desactivar" }));
    await waitFor(() => expect(apiClient.desactivarProducto).toHaveBeenCalled());
  });
});
