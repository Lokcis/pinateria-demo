import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { elegirOpcion } from "../utils/test-desplegable";
import { Inventario } from "./inventario";
import { AuthProvider } from "../context/auth-context";
import * as apiClient from "../api/api-client";

/** Pulsa el boton del cuadro de confirmacion propio (reemplaza a window.confirm). */
async function responderDialogo(nombre) {
  const dialogo = await screen.findByRole("alertdialog");
  await userEvent.click(within(dialogo).getByRole("button", { name: nombre }));
}

vi.mock("../api/api-client", async () => {
  const modulo = await vi.importActual("../api/api-client");
  return {
    ...modulo,
    obtenerCatalogo: vi.fn(),
    obtenerCategorias: vi.fn(),
    obtenerAjustesInventario: vi.fn(),
    editarProducto: vi.fn(),
    desactivarProducto: vi.fn(),
    reactivarProducto: vi.fn(),
  };
});

const PRODUCTO = {
  id: 1,
  nombre: "Piñata Mickey",
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

function renderizar(rol = "administrador") {
  localStorage.setItem("mm_pos_token", `c.${btoa(JSON.stringify({ sub: "1", rol }))}.f`);
  return render(
    <AuthProvider>
      <Inventario />
    </AuthProvider>
  );
}

async function abrirProducto() {
  await userEvent.click(await screen.findByRole("button", { name: /Piñata Mickey/ }));
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  apiClient.obtenerCatalogo.mockResolvedValue({ total: 1, productos: [PRODUCTO] });
  apiClient.obtenerCategorias.mockResolvedValue([{ id: 1, nombre: "Piñatas", descripcion: null }]);
  apiClient.obtenerAjustesInventario.mockResolvedValue([]);
});

describe("Inventario — RF-016 editar y desactivar productos", () => {
  it("el administrador edita los datos del producto", async () => {
    apiClient.editarProducto.mockResolvedValue({ ...PRODUCTO, precio_venta: "30000.00" });
    renderizar();
    await abrirProducto();

    await userEvent.click(screen.getByRole("button", { name: "Editar datos" }));
    const precio = screen.getByLabelText("Precio de venta");
    await userEvent.clear(precio);
    await userEvent.type(precio, "30000");
    await userEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => expect(apiClient.editarProducto).toHaveBeenCalled());
    expect(apiClient.editarProducto.mock.calls[0].slice(0, 2)).toEqual([
      1,
      { nombre: "Piñata Mickey", descripcion: null, categoria_id: 1, codigo_barras: null, precio_venta: 30000 },
    ]);
  });

  it("muestra el error si el código de barras ya está en uso", async () => {
    apiClient.editarProducto.mockRejectedValue(new Error("Ya existe un producto activo con el codigo de barras '123'."));
    renderizar();
    await abrirProducto();

    await userEvent.click(screen.getByRole("button", { name: "Editar datos" }));
    await userEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Ya existe un producto activo");
  });

  it("desactiva el producto tras confirmar y recarga el catálogo", async () => {
    apiClient.desactivarProducto.mockResolvedValue({ ...PRODUCTO, activo: false });
    renderizar();
    await abrirProducto();

    await userEvent.click(screen.getByRole("button", { name: "Desactivar producto" }));
    await responderDialogo("Desactivar");

    await waitFor(() => expect(apiClient.desactivarProducto).toHaveBeenCalledWith(1, expect.any(String)));
    await waitFor(() => expect(apiClient.obtenerCatalogo).toHaveBeenCalledTimes(2));
  });

  it("puede ver los inactivos y reactivar un producto", async () => {
    apiClient.reactivarProducto.mockResolvedValue({ ...PRODUCTO, activo: true });
    renderizar();
    await screen.findByText("Piñata Mickey");

    apiClient.obtenerCatalogo.mockResolvedValue({ total: 1, productos: [{ ...PRODUCTO, activo: false }] });
    await elegirOpcion(screen.getByLabelText("Estado de los productos"), "inactivos");
    await waitFor(() => expect(apiClient.obtenerCatalogo.mock.calls.at(-1)[0]).toMatchObject({ activo: false }));

    await abrirProducto();
    await userEvent.click(screen.getByRole("button", { name: "Reactivar producto" }));
    await responderDialogo("Reactivar");

    await waitFor(() => expect(apiClient.reactivarProducto).toHaveBeenCalledWith(1, expect.any(String)));
  });

  it("el vendedor no ve editar ni desactivar", async () => {
    renderizar("vendedor");
    await abrirProducto();

    expect(screen.queryByRole("button", { name: "Editar datos" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Desactivar producto" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Estado de los productos")).not.toBeInTheDocument();
  });
});
