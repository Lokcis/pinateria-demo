import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { BarraVenta, PosPage } from "./pos-page";
import { AuthProvider } from "../context/auth-context";
import { CartProvider, useCart } from "../context/cart-context";
import * as apiClient from "../api/api-client";

vi.mock("../api/api-client", async () => {
  const modulo = await vi.importActual("../api/api-client");
  return {
    ...modulo,
    obtenerHistorialHoy: vi.fn(),
    obtenerCatalogo: vi.fn(),
    obtenerConfiguracionDescuentos: vi.fn(),
    obtenerVendedores: vi.fn(),
    obtenerSalud: vi.fn(),
    obtenerCategoriasGasto: vi.fn(),
    obtenerGastos: vi.fn(),
    obtenerResumenGastos: vi.fn(),
    obtenerCajaActual: vi.fn(),
    obtenerCortes: vi.fn(),
  };
});

/** Crea un payload de JWT falso (sin verificar firma, solo para el frontend). */
function tokenFalso(rol) {
  return `cabecera.${btoa(JSON.stringify({ sub: "1", rol }))}.firma`;
}

function renderizar(rol) {
  localStorage.setItem("mm_pos_token", tokenFalso(rol));
  return render(
    <AuthProvider>
      <PosPage />
    </AuthProvider>
  );
}

beforeEach(() => {
  localStorage.clear();
  // El POS pide estos datos al abrirse; con respuestas de prueba, la red "funciona".
  apiClient.obtenerConfiguracionDescuentos.mockResolvedValue({
    general: null,
    topes: { tope_porcentaje: null, tope_monto: null, descripcion: "sin límite" },
  });
  apiClient.obtenerVendedores.mockResolvedValue([]);
  apiClient.obtenerCatalogo.mockResolvedValue({ total: 0, productos: [] });
  apiClient.obtenerSalud.mockResolvedValue({ status: "ok" });
});

describe("PosPage — RBAC de proveedores y compras (HU-04)", () => {
  it("el vendedor no ve las pestañas de Proveedores ni Compras", () => {
    renderizar("vendedor");

    expect(screen.getByRole("tab", { name: "Inventario" })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Proveedores" })).not.toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Compras" })).not.toBeInTheDocument();
  });

  it("el administrador ve las pestañas de Proveedores y Compras", () => {
    renderizar("administrador");

    expect(screen.getByRole("tab", { name: "Proveedores" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Compras" })).toBeInTheDocument();
  });
});

describe("PosPage — RBAC de Usuarios y Categorías (Fase 5)", () => {
  it("el vendedor no ve las pestañas de Usuarios ni Categorías", () => {
    renderizar("vendedor");

    expect(screen.queryByRole("tab", { name: "Usuarios" })).not.toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Categorías" })).not.toBeInTheDocument();
  });

  it("el administrador ve las pestañas de Usuarios y Categorías", () => {
    renderizar("administrador");

    expect(screen.getByRole("tab", { name: "Usuarios" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Categorías" })).toBeInTheDocument();
  });
});

describe("PosPage — pestaña Stock bajo (Adendo v2, mejora B1: HU-10)", () => {
  it("el vendedor no ve la pestaña Stock bajo", () => {
    renderizar("vendedor");

    expect(screen.queryByRole("tab", { name: "Stock bajo" })).not.toBeInTheDocument();
  });

  it("el administrador ve la pestaña Stock bajo", () => {
    renderizar("administrador");

    expect(screen.getByRole("tab", { name: "Stock bajo" })).toBeInTheDocument();
  });
});

describe("PosPage — pestaña Descuentos (Adendo v2, Fase A1: HU-06)", () => {
  it("el vendedor no ve la pestaña Descuentos", () => {
    renderizar("vendedor");

    expect(screen.queryByRole("tab", { name: "Descuentos" })).not.toBeInTheDocument();
  });

  it("el administrador ve la pestaña Descuentos", () => {
    renderizar("administrador");

    expect(screen.getByRole("tab", { name: "Descuentos" })).toBeInTheDocument();
  });
});

describe("PosPage — pestaña Ganancias (Adendo v2, Fase A3: HU-09)", () => {
  it("el vendedor no ve la pestaña Ganancias", () => {
    renderizar("vendedor");

    expect(screen.queryByRole("tab", { name: "Ganancias" })).not.toBeInTheDocument();
  });

  it("el administrador ve la pestaña Ganancias", () => {
    renderizar("administrador");

    expect(screen.getByRole("tab", { name: "Ganancias" })).toBeInTheDocument();
  });
});

describe("PosPage — Gastos (Adendo v3, Fase G1: HU-12)", () => {
  it("el vendedor y el administrador ven Gastos, en el grupo Gastos y caja", () => {
    for (const rol of ["vendedor", "administrador"]) {
      const { unmount } = renderizar(rol);

      expect(screen.getByRole("tab", { name: "Gastos" })).toBeInTheDocument();
      expect(screen.getByText("Gastos y caja")).toBeInTheDocument();
      unmount();
    }
  });

  it("al elegir Gastos se abre la ventana de gastos", async () => {
    apiClient.obtenerCategoriasGasto.mockResolvedValue([]);
    apiClient.obtenerGastos.mockResolvedValue([]);
    apiClient.obtenerResumenGastos.mockResolvedValue({
      desde: "2026-10-01", hasta: "2026-10-19", total: "0", total_compras: "0", total_operativo: "0",
      por_categoria: [], por_metodo_pago: [],
    });
    renderizar("administrador");

    await userEvent.click(screen.getByRole("tab", { name: "Gastos" }));

    expect(await screen.findByRole("heading", { name: "Gastos" })).toBeInTheDocument();
    expect(await screen.findByText("No hay gastos en este rango.")).toBeInTheDocument();
  });
});

describe("PosPage — Caja (Adendo v3, Fase G2: HU-13)", () => {
  it("el vendedor y el administrador ven Caja junto a Gastos", () => {
    for (const rol of ["vendedor", "administrador"]) {
      const { unmount } = renderizar(rol);

      expect(screen.getByRole("tab", { name: "Caja" })).toBeInTheDocument();
      unmount();
    }
  });

  it("al elegir Caja se abre el apartado de la caja", async () => {
    apiClient.obtenerCajaActual.mockResolvedValue({ abierta: false, corte: null, cifras: null, movimientos: [], generado_en: "2026-10-20T15:00:00Z" });
    apiClient.obtenerCortes.mockResolvedValue([]);
    renderizar("vendedor");

    await userEvent.click(screen.getByRole("tab", { name: "Caja" }));

    expect(await screen.findByRole("heading", { name: "Caja" })).toBeInTheDocument();
    expect(await screen.findByText("La caja está cerrada")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Abrir caja" })).toBeInTheDocument();
  });
});

describe("PosPage — pestañas de clientes (Adendo v2, Fase A2: HU-07)", () => {
  it("el vendedor ve Clientes pero no Datos personales", () => {
    renderizar("vendedor");

    expect(screen.getByRole("tab", { name: "Clientes" })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Datos personales" })).not.toBeInTheDocument();
  });

  it("el administrador ve Clientes y Datos personales", () => {
    renderizar("administrador");

    expect(screen.getByRole("tab", { name: "Clientes" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Datos personales" })).toBeInTheDocument();
  });
});

/** Simula una pantalla angosta (celular): `matchMedia` dice que no hay 1280 px de ancho. */
function simularCelular() {
  window.matchMedia = (consulta) => ({
    matches: false,
    media: consulta,
    addEventListener: () => {},
    removeEventListener: () => {},
  });
}

describe("PosPage — celular (barra inferior)", () => {
  afterEach(() => {
    delete window.matchMedia;
  });

  it("el vendedor ve cuatro secciones directas (con Inventario) y Más solo con Gastos y Caja", async () => {
    simularCelular();
    renderizar("vendedor");

    expect(screen.getAllByRole("tab").map((t) => t.textContent)).toEqual(["Vender", "Hoy", "Clientes", "Inventario"]);
    await userEvent.click(screen.getByRole("button", { name: "Más" }));
    const hoja = screen.getByRole("dialog", { name: "Más secciones" });
    expect(within(hoja).getAllByRole("button").map((b) => b.textContent).filter((t) => t !== "Cerrar")).toEqual(["Gastos", "Caja"]);
  });

  it("el administrador ve tres secciones y Más, con el resto de las secciones agrupadas", async () => {
    simularCelular();
    renderizar("administrador");

    expect(screen.getAllByRole("tab").map((t) => t.textContent)).toEqual(["Vender", "Hoy", "Clientes"]);
    await userEvent.click(screen.getByRole("button", { name: "Más" }));
    const hoja = screen.getByRole("dialog", { name: "Más secciones" });
    for (const nombre of ["Datos personales", "Inventario", "Stock bajo", "Compras", "Proveedores", "Categorías", "Gastos", "Caja", "Descuentos", "Ganancias", "Usuarios"]) {
      expect(within(hoja).getByRole("button", { name: nombre })).toBeInTheDocument();
    }
  });

  it("el vendedor no tiene en Más las secciones del administrador", () => {
    simularCelular();
    renderizar("vendedor");

    expect(screen.queryByRole("button", { name: "Compras" })).not.toBeInTheDocument();
    expect(screen.queryByText("Usuarios")).not.toBeInTheDocument();
  });

  it("cambiar de sección desde la barra muestra esa pantalla", async () => {
    simularCelular();
    apiClient.obtenerHistorialHoy.mockResolvedValue({ fecha: "2026-10-13", cantidad_ventas: 0, total_vendido: "0", total_por_metodo: {}, ventas: [] });
    renderizar("vendedor");

    await userEvent.click(screen.getByRole("tab", { name: "Ventas de hoy" }));

    expect(screen.getByRole("tab", { name: "Ventas de hoy" })).toHaveAttribute("aria-selected", "true");
  });
});

/** Carga el carrito al montarse, como hace la busqueda al agregar un producto. */
function CarritoCon({ productos }) {
  const { agregarProducto } = useCart();
  useEffect(() => {
    productos.forEach((producto) => agregarProducto(producto));
  }, [productos, agregarProducto]);
  return null;
}

describe("BarraVenta (celular): total siempre a la vista", () => {
  it("no aparece con el carrito vacío", () => {
    render(
      <CartProvider>
        <BarraVenta alAbrir={() => {}} />
      </CartProvider>
    );

    expect(screen.queryByRole("button", { name: /Ver venta/ })).not.toBeInTheDocument();
  });

  it("con productos muestra la cantidad y el total, y abre el panel al tocarla", async () => {
    const alAbrir = vi.fn();
    const producto = { id: 1, nombre: "Piñata", precio_venta: "26000.00", stock_actual: 5, categoria_nombre: "Piñatas" };
    render(
      <CartProvider>
        <CarritoCon productos={[producto, producto]} />
        <BarraVenta alAbrir={alAbrir} />
      </CartProvider>
    );

    const barra = await screen.findByRole("button", { name: /Ver venta/ });
    expect(barra).toHaveTextContent("2 artículos");
    expect(barra).toHaveTextContent(/52\.000/);
    await userEvent.click(barra);
    expect(alAbrir).toHaveBeenCalledTimes(1);
  });
});


describe("PosPage — modo sin conexión (Fase 9)", () => {
  beforeEach(() => {
    Object.defineProperty(navigator, "onLine", { value: true, configurable: true });
  });

  it("al perder la red avisa que se puede seguir vendiendo y no bloquea la búsqueda", async () => {
    renderizar("vendedor");

    act(() => window.dispatchEvent(new Event("offline")));

    expect(await screen.findByText("Sin conexión con el servidor.")).toBeInTheDocument();
    expect(screen.getByText(/Puedes seguir vendiendo/)).toBeInTheDocument();
    expect(screen.getByLabelText(/escanear o buscar producto/i)).toBeEnabled();
  });

  it("cerrar sesión sin conexión pide confirmación y, si se cancela, se queda", async () => {
    const usuario = userEvent.setup();
    renderizar("vendedor");
    act(() => window.dispatchEvent(new Event("offline")));
    await screen.findByText("Sin conexión con el servidor.");

    await usuario.click(screen.getByRole("button", { name: /Cuenta/ }));
    await usuario.click(screen.getByRole("menuitem", { name: "Cerrar sesión" }));

    expect(await screen.findByText("¿Cerrar sesión?")).toBeInTheDocument();
    expect(screen.getByText(/para volver a entrar necesitas que vuelva internet/)).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(localStorage.getItem("mm_pos_token")).not.toBeNull();
  });

  it("con conexión y sin ventas guardadas cierra la sesión sin preguntar", async () => {
    const usuario = userEvent.setup();
    renderizar("vendedor");

    await usuario.click(screen.getByRole("button", { name: /Cuenta/ }));
    await usuario.click(screen.getByRole("menuitem", { name: "Cerrar sesión" }));

    await waitFor(() => expect(localStorage.getItem("mm_pos_token")).toBeNull());
  });
});
