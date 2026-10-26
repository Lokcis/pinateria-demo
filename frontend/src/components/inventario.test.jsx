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
    actualizarStockMinimo: vi.fn(),
    registrarAjusteInventario: vi.fn(),
    obtenerAjustesInventario: vi.fn(),
    obtenerCategorias: vi.fn(),
    crearProducto: vi.fn(),
  };
});

const PRODUCTO_NORMAL = {
  id: 1,
  nombre: "Piñata Mickey Mouse",
  descripcion: null,
  categoria_id: 1,
  categoria_nombre: "Piñatas",
  codigo_barras: null,
  tipo: "unidad",
  precio_venta: "25000.00",
  stock_actual: 12,
  stock_minimo: 5,
  activo: true,
};

const PRODUCTO_STOCK_BAJO = {
  ...PRODUCTO_NORMAL,
  id: 2,
  nombre: "Globo metalizado estrella",
  stock_actual: 2,
};

/** Crea un payload de JWT falso (sin verificar firma, solo para el frontend). */
function tokenFalso(rol) {
  const payload = btoa(JSON.stringify({ sub: "1", rol }));
  return `cabecera.${payload}.firma`;
}

function renderizar(rol = "vendedor") {
  localStorage.setItem("mm_pos_token", tokenFalso(rol));
  return render(
    <AuthProvider>
      <Inventario />
    </AuthProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
});

describe("Inventario", () => {
  it("muestra el catalogo con categoria y stock", async () => {
    apiClient.obtenerCatalogo.mockResolvedValue({ total: 1, productos: [PRODUCTO_NORMAL] });
    renderizar();

    expect(await screen.findByText("Piñata Mickey Mouse")).toBeInTheDocument();
    expect(screen.getByText("Piñatas")).toBeInTheDocument();
    expect(screen.queryByText("Stock bajo")).not.toBeInTheDocument();
  });

  it("marca stock bajo cuando stock_actual <= stock_minimo", async () => {
    apiClient.obtenerCatalogo.mockResolvedValue({ total: 1, productos: [PRODUCTO_STOCK_BAJO] });
    renderizar();

    expect(await screen.findByText("Stock bajo")).toBeInTheDocument();
  });

  it("sin resultados muestra un mensaje vacio", async () => {
    apiClient.obtenerCatalogo.mockResolvedValue({ total: 0, productos: [] });
    renderizar();

    expect(await screen.findByText(/no se encontraron productos/i)).toBeInTheDocument();
  });

  it("un error de carga muestra opcion de reintentar", async () => {
    apiClient.obtenerCatalogo.mockRejectedValue(new Error("Sin conexion"));
    renderizar();

    expect(await screen.findByRole("alert")).toHaveTextContent("Sin conexion");
  });

  it("el vendedor no ve el formulario de stock minimo, pero si el de ajustes", async () => {
    apiClient.obtenerCatalogo.mockResolvedValue({ total: 1, productos: [PRODUCTO_NORMAL] });
    apiClient.obtenerAjustesInventario.mockResolvedValue([]);
    renderizar("vendedor");

    await userEvent.click(await screen.findByRole("button", { name: /piñata mickey mouse/i }));

    expect(screen.queryByText("Stock mínimo")).not.toBeInTheDocument();
    expect(screen.getByText(/registrar ajuste manual/i)).toBeInTheDocument();
  });

  it("el administrador puede editar el stock minimo", async () => {
    apiClient.obtenerCatalogo.mockResolvedValue({ total: 1, productos: [PRODUCTO_NORMAL] });
    apiClient.obtenerAjustesInventario.mockResolvedValue([]);
    apiClient.actualizarStockMinimo.mockResolvedValue({ ...PRODUCTO_NORMAL, stock_minimo: 8 });
    renderizar("administrador");

    await userEvent.click(await screen.findByRole("button", { name: /piñata mickey mouse/i }));
    const campo = screen.getByLabelText(/stock mínimo/i);
    await userEvent.clear(campo);
    await userEvent.type(campo, "8");
    await userEvent.click(screen.getByRole("button", { name: /guardar/i }));

    await waitFor(() => expect(apiClient.actualizarStockMinimo).toHaveBeenCalledWith(1, 8, expect.any(String)));
    expect(await screen.findByText("Guardado.")).toBeInTheDocument();
  });

  it("registra un ajuste de entrada con cantidad positiva", async () => {
    apiClient.obtenerCatalogo.mockResolvedValue({ total: 1, productos: [PRODUCTO_NORMAL] });
    apiClient.obtenerAjustesInventario.mockResolvedValue([]);
    apiClient.registrarAjusteInventario.mockResolvedValue({
      id: 1,
      producto_id: 1,
      usuario_id: 1,
      tipo: "entrada",
      cantidad: 5,
      motivo: "Conteo",
      fecha: "2026-09-27T10:00:00Z",
    });
    renderizar("vendedor");

    await userEvent.click(await screen.findByRole("button", { name: /piñata mickey mouse/i }));
    const formulario = screen.getByText(/registrar ajuste manual/i).closest("form");
    await userEvent.type(within(formulario).getByPlaceholderText("0"), "5");
    await userEvent.type(within(formulario).getByPlaceholderText(/conteo físico/i), "Llego mercancia");
    await userEvent.click(within(formulario).getByRole("button", { name: /registrar ajuste/i }));

    await waitFor(() =>
      expect(apiClient.registrarAjusteInventario).toHaveBeenCalledWith(
        1,
        { tipo: "entrada", cantidad: 5, motivo: "Llego mercancia" },
        expect.any(String)
      )
    );
  });

  it("registra un ajuste de merma con cantidad negativa automaticamente", async () => {
    apiClient.obtenerCatalogo.mockResolvedValue({ total: 1, productos: [PRODUCTO_NORMAL] });
    apiClient.obtenerAjustesInventario.mockResolvedValue([]);
    apiClient.registrarAjusteInventario.mockResolvedValue({
      id: 2,
      producto_id: 1,
      usuario_id: 1,
      tipo: "merma",
      cantidad: -3,
      motivo: "Dañado",
      fecha: "2026-09-27T10:00:00Z",
    });
    renderizar("vendedor");

    await userEvent.click(await screen.findByRole("button", { name: /piñata mickey mouse/i }));
    const formulario = screen.getByText(/registrar ajuste manual/i).closest("form");
    await elegirOpcion(within(formulario).getByLabelText(/tipo/i), "merma");
    await userEvent.type(within(formulario).getByPlaceholderText("0"), "3");
    await userEvent.type(within(formulario).getByPlaceholderText(/conteo físico/i), "Dañado");
    await userEvent.click(within(formulario).getByRole("button", { name: /registrar ajuste/i }));

    await waitFor(() =>
      expect(apiClient.registrarAjusteInventario).toHaveBeenCalledWith(
        1,
        { tipo: "merma", cantidad: -3, motivo: "Dañado" },
        expect.any(String)
      )
    );
  });

  it("muestra el error del backend si el ajuste falla (ej. stock insuficiente)", async () => {
    apiClient.obtenerCatalogo.mockResolvedValue({ total: 1, productos: [PRODUCTO_NORMAL] });
    apiClient.obtenerAjustesInventario.mockResolvedValue([]);
    apiClient.registrarAjusteInventario.mockRejectedValue(new Error("Stock insuficiente para el producto id=1"));
    renderizar("vendedor");

    await userEvent.click(await screen.findByRole("button", { name: /piñata mickey mouse/i }));
    const formulario = screen.getByText(/registrar ajuste manual/i).closest("form");
    await elegirOpcion(within(formulario).getByLabelText(/tipo/i), "merma");
    await userEvent.type(within(formulario).getByPlaceholderText("0"), "999");
    await userEvent.type(within(formulario).getByPlaceholderText(/conteo físico/i), "x");
    await userEvent.click(within(formulario).getByRole("button", { name: /registrar ajuste/i }));

    expect(await screen.findByText(/stock insuficiente/i)).toBeInTheDocument();
  });

  it("el vendedor no ve el boton de nuevo producto", async () => {
    apiClient.obtenerCatalogo.mockResolvedValue({ total: 1, productos: [PRODUCTO_NORMAL] });
    renderizar("vendedor");

    await screen.findByText("Piñata Mickey Mouse");
    expect(screen.queryByRole("button", { name: /nuevo producto/i })).not.toBeInTheDocument();
  });

  it("HU-02: el administrador crea un producto sin codigo de barras y el catalogo se recarga", async () => {
    apiClient.obtenerCatalogo
      .mockResolvedValueOnce({ total: 1, productos: [PRODUCTO_NORMAL] })
      .mockResolvedValueOnce({ total: 2, productos: [PRODUCTO_NORMAL, { ...PRODUCTO_NORMAL, id: 9, nombre: "Ancheta nueva" }] });
    apiClient.obtenerCategorias.mockResolvedValue([{ id: 1, nombre: "Piñatas", descripcion: null }]);
    apiClient.crearProducto.mockResolvedValue({ ...PRODUCTO_NORMAL, id: 9, nombre: "Ancheta nueva", codigo_barras: null });
    renderizar("administrador");

    await screen.findByText("Piñata Mickey Mouse");
    await userEvent.click(screen.getByRole("button", { name: /nuevo producto/i }));

    const formulario = (await screen.findByText("Nuevo producto")).closest("form");
    await userEvent.type(within(formulario).getByLabelText(/nombre/i), "Ancheta nueva");
    await elegirOpcion(await within(formulario).findByLabelText(/categoría/i), "1");
    await userEvent.type(within(formulario).getByLabelText(/precio de venta/i), "45000");
    await userEvent.type(within(formulario).getByLabelText(/stock inicial/i), "3");
    await userEvent.click(within(formulario).getByRole("button", { name: /crear producto/i }));

    await waitFor(() =>
      expect(apiClient.crearProducto).toHaveBeenCalledWith(
        {
          nombre: "Ancheta nueva",
          categoria_id: 1,
          codigo_barras: null,
          precio_venta: 45000,
          stock_inicial: 3,
        },
        expect.any(String)
      )
    );
    expect(await screen.findByText("Ancheta nueva")).toBeInTheDocument();
  });

  it("HU-02: muestra el error si el codigo de barras ya esta en uso", async () => {
    apiClient.obtenerCatalogo.mockResolvedValue({ total: 1, productos: [PRODUCTO_NORMAL] });
    apiClient.obtenerCategorias.mockResolvedValue([{ id: 1, nombre: "Piñatas", descripcion: null }]);
    apiClient.crearProducto.mockRejectedValue(new Error("Ya existe un producto activo con el codigo de barras '123'."));
    renderizar("administrador");

    await screen.findByText("Piñata Mickey Mouse");
    await userEvent.click(screen.getByRole("button", { name: /nuevo producto/i }));
    const formulario = (await screen.findByText("Nuevo producto")).closest("form");
    await userEvent.type(within(formulario).getByLabelText(/nombre/i), "Otro");
    await elegirOpcion(await within(formulario).findByLabelText(/categoría/i), "1");
    await userEvent.type(within(formulario).getByLabelText(/precio de venta/i), "1000");
    await userEvent.type(within(formulario).getByLabelText(/stock inicial/i), "1");
    await userEvent.click(within(formulario).getByRole("button", { name: /crear producto/i }));

    expect(await screen.findByText(/ya existe un producto/i)).toBeInTheDocument();
  });

  it("muestra el historial de ajustes al expandir", async () => {
    apiClient.obtenerCatalogo.mockResolvedValue({ total: 1, productos: [PRODUCTO_NORMAL] });
    apiClient.obtenerAjustesInventario.mockResolvedValue([
      { id: 9, producto_id: 1, usuario_id: 1, tipo: "entrada", cantidad: 5, motivo: "Conteo", fecha: "2026-09-27T10:00:00Z" },
    ]);
    renderizar("vendedor");

    await userEvent.click(await screen.findByRole("button", { name: /piñata mickey mouse/i }));

    expect(await screen.findByText(/conteo/i)).toBeInTheDocument();
  });
});
