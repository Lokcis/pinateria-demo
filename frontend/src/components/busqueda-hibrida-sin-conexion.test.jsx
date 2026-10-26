import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { BusquedaHibrida } from "./busqueda-hibrida";
import { AuthProvider } from "../context/auth-context";
import { CartProvider, useCart } from "../context/cart-context";
import { SinConexionContext, VALOR_SIN_CONEXION_INACTIVO } from "../context/sin-conexion-context";
import * as apiClient from "../api/api-client";

vi.mock("../api/api-client", async () => {
  const modulo = await vi.importActual("../api/api-client");
  return { ...modulo, buscarProductos: vi.fn() };
});

const GLOBO = { id: 2, nombre: "Globo metalizado", categoria_id: 2, categoria_nombre: "Globos", precio_venta: "5000.00", stock_actual: 9, stock_minimo: 2 };

function EnCarrito() {
  const { items } = useCart();
  return <p>en el carrito: {items.map((i) => i.nombre).join(", ") || "nada"}</p>;
}

function renderizar(sc = {}) {
  localStorage.setItem("mm_pos_token", `x.${btoa(JSON.stringify({ sub: "1", rol: "vendedor" }))}.y`);
  const valor = {
    ...VALOR_SIN_CONEXION_INACTIVO,
    activo: true,
    disponible: true,
    catalogo: { cantidad: 30, guardadoEn: new Date().toISOString() },
    buscarLocal: vi.fn().mockResolvedValue([GLOBO]),
    reportarFalloDeConexion: vi.fn(),
    ...sc,
  };
  render(
    <AuthProvider>
      <SinConexionContext.Provider value={valor}>
        <CartProvider>
          <BusquedaHibrida />
          <EnCarrito />
        </CartProvider>
      </SinConexionContext.Provider>
    </AuthProvider>
  );
  return valor;
}

async function buscar(usuario, texto) {
  const campo = screen.getByRole("textbox");
  await usuario.type(campo, texto);
  await usuario.keyboard("{Enter}");
}

beforeEach(() => {
  vi.resetAllMocks();
  localStorage.clear();
});

describe("Busqueda de productos sin conexion (Fase 9)", () => {
  it("sin conexion busca en el catalogo guardado, sin llamar al servidor, y avisa que el stock puede estar desactualizado", async () => {
    const usuario = userEvent.setup({ delay: 80 });
    const sc = renderizar({ enLinea: false });

    await buscar(usuario, "glo");

    expect(await screen.findByText("Globo metalizado")).toBeInTheDocument();
    expect(sc.buscarLocal).toHaveBeenCalledWith("glo");
    expect(apiClient.buscarProductos).not.toHaveBeenCalled();
    expect(screen.getByText(/el stock mostrado puede estar desactualizado/i)).toBeInTheDocument();
    expect(screen.getByText("Sin conexión · catálogo guardado")).toBeInTheDocument();
  });

  it("un producto elegido de la lista guardada se agrega al carrito con su precio", async () => {
    const usuario = userEvent.setup({ delay: 80 });
    renderizar({ enLinea: false });

    await buscar(usuario, "glo");
    await usuario.click(await screen.findByRole("button", { name: /Globo metalizado/ }));

    expect(screen.getByText("en el carrito: Globo metalizado")).toBeInTheDocument();
  });

  it("si el servidor no responde, cae al catalogo guardado y deja marcada la falta de conexion", async () => {
    const usuario = userEvent.setup({ delay: 80 });
    apiClient.buscarProductos.mockRejectedValue(new TypeError("Failed to fetch"));
    const sc = renderizar({ enLinea: true });

    await buscar(usuario, "glo");

    expect(await screen.findByText("Globo metalizado")).toBeInTheDocument();
    expect(sc.reportarFalloDeConexion).toHaveBeenCalled();
  });

  it("un error del servidor que no es de conexion se muestra tal cual, sin buscar en lo guardado", async () => {
    const usuario = userEvent.setup({ delay: 80 });
    apiClient.buscarProductos.mockRejectedValue(new apiClient.ApiError("Error interno", 500));
    const sc = renderizar({ enLinea: true });

    await buscar(usuario, "glo");

    expect(await screen.findByText("Error interno")).toBeInTheDocument();
    expect(sc.buscarLocal).not.toHaveBeenCalled();
  });

  it("sin conexion y sin catalogo guardado explica que hace falta conectarse una vez", async () => {
    const usuario = userEvent.setup({ delay: 80 });
    renderizar({ enLinea: false, catalogo: null, buscarLocal: vi.fn().mockResolvedValue([]) });

    await buscar(usuario, "glo");

    expect(await screen.findByText(/sin catálogo guardado en este equipo/i)).toBeInTheDocument();
  });

  it("con conexion todo sigue igual: usa el servidor", async () => {
    const usuario = userEvent.setup({ delay: 80 });
    apiClient.buscarProductos.mockResolvedValue([GLOBO]);
    const sc = renderizar({ enLinea: true });

    await buscar(usuario, "glo");

    await waitFor(() => expect(apiClient.buscarProductos).toHaveBeenCalledWith("glo", expect.any(String)));
    expect(await screen.findByText("Globo metalizado")).toBeInTheDocument();
    expect(sc.buscarLocal).not.toHaveBeenCalled();
    expect(screen.queryByText(/desactualizado/i)).not.toBeInTheDocument();
  });
});
