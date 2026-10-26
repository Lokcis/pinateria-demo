import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ConfirmacionPago } from "./confirmacion-pago";
import { AuthProvider } from "../context/auth-context";
import { CartProvider, useCart } from "../context/cart-context";
import { SinConexionContext, VALOR_SIN_CONEXION_INACTIVO } from "../context/sin-conexion-context";
import * as apiClient from "../api/api-client";

vi.mock("../api/api-client", async () => {
  const modulo = await vi.importActual("../api/api-client");
  return {
    ...modulo,
    crearVenta: vi.fn(),
    imprimirTicket: vi.fn(),
    obtenerConfiguracionDescuentos: vi.fn(),
    obtenerVendedores: vi.fn(),
    buscarClientes: vi.fn(),
  };
});

const CONFIG = {
  general: { tipo: "porcentaje", valor: "10.00", activo: true },
  topes: { tope_porcentaje: null, tope_monto: null, descripcion: "sin límite" },
};
const PRODUCTO = { id: 1, nombre: "Piñata Mickey", precio_venta: "26000.00", stock_actual: 5, categoria_nombre: "Piñatas" };

function CarritoCon({ productos }) {
  const { agregarProducto } = useCart();
  useEffect(() => {
    productos.forEach((producto) => agregarProducto(producto));
  }, [productos, agregarProducto]);
  return null;
}

/** Monta la pantalla de pago con un modo sin conexion simulado (`sc` pisa los valores por defecto). */
function renderizar(sc = {}) {
  localStorage.setItem("mm_pos_token", `x.${btoa(JSON.stringify({ sub: "1", rol: "vendedor" }))}.y`);
  const valor = {
    ...VALOR_SIN_CONEXION_INACTIVO,
    activo: true,
    disponible: true,
    enLinea: true,
    registrarVenta: vi.fn().mockResolvedValue(undefined),
    siguienteNumero: vi.fn().mockResolvedValue("SC-0007"),
    reportarFalloDeConexion: vi.fn(),
    guardarEnCache: vi.fn().mockResolvedValue(undefined),
    leerDeCache: vi.fn().mockResolvedValue(null),
    ...sc,
  };
  const resultado = render(
    <AuthProvider>
      <SinConexionContext.Provider value={valor}>
        <CartProvider>
          <CarritoCon productos={[PRODUCTO]} />
          <ConfirmacionPago />
        </CartProvider>
      </SinConexionContext.Provider>
    </AuthProvider>
  );
  return { ...resultado, valor };
}

async function confirmar(usuario) {
  const boton = await screen.findByRole("button", { name: "Confirmar venta" });
  await waitFor(() => expect(boton).toBeEnabled());
  await usuario.click(boton);
}

beforeEach(() => {
  vi.resetAllMocks();
  localStorage.clear();
  apiClient.obtenerConfiguracionDescuentos.mockResolvedValue(CONFIG);
  apiClient.obtenerVendedores.mockResolvedValue([]);
  apiClient.imprimirTicket.mockResolvedValue({ status: "ok" });
  apiClient.crearVenta.mockResolvedValue({
    id: 21, fecha: "2026-10-14T15:00:00Z", subtotal: "26000.00", descuento_monto: "0.00", ajuste_redondeo: "0.00",
    total: "26000.00", pagos: [{ metodo_pago: "efectivo", monto: "26000.00", monto_recibido: "26000.00", vueltas: "0.00" }],
    detalles: [{ producto_id: 1, cantidad: 1, precio_unitario: "26000.00", subtotal: "26000.00" }],
  });
});

describe("Confirmar una venta sin conexion (Fase 9)", () => {
  it("con la red caida no llama al servidor: guarda la venta en el equipo e imprime el ticket con su numero local", async () => {
    const usuario = userEvent.setup();
    apiClient.obtenerConfiguracionDescuentos.mockRejectedValue(new TypeError("Failed to fetch"));
    const { valor } = renderizar({ enLinea: false, leerDeCache: vi.fn().mockResolvedValue(CONFIG) });

    await confirmar(usuario);

    await waitFor(() => expect(valor.registrarVenta).toHaveBeenCalledTimes(1));
    expect(apiClient.crearVenta).not.toHaveBeenCalled();
    const entrada = valor.registrarVenta.mock.calls[0][0];
    expect(entrada).toMatchObject({ numeroLocal: "SC-0007", usuarioId: "1", estado: "pendiente" });
    expect(entrada.payload).toMatchObject({
      detalles: [{ producto_id: 1, cantidad: 1, precio_unitario: "26000" }],
      pagos: [{ metodo_pago: "efectivo", monto: "26000", monto_recibido: "26000" }],
      descuento: { origen: "ninguno" },
    });
    expect(entrada.payload.uuid_cliente).toMatch(/^[0-9a-f-]{36}$/);
    expect(entrada.payload.sin_conexion.fecha).toMatch(/^\d{4}-\d{2}-\d{2}T/);

    expect(await screen.findByText("Venta SC-0007 guardada sin conexión. Se enviará sola cuando vuelva la red.")).toBeInTheDocument();
    expect(apiClient.imprimirTicket).toHaveBeenCalledWith(expect.objectContaining({ venta_id: null, referencia: "SC-0007", total: "26000.00" }));
    // La pantalla queda lista para la venta siguiente.
    await waitFor(() => expect(screen.getByRole("button", { name: "Confirmar venta" })).toBeDisabled());
  });

  it("usa el descuento general guardado en el equipo y lo envia con el tipo y el valor que vio el cliente", async () => {
    const usuario = userEvent.setup();
    apiClient.obtenerConfiguracionDescuentos.mockRejectedValue(new TypeError("Failed to fetch"));
    const { valor } = renderizar({ enLinea: false, leerDeCache: vi.fn().mockResolvedValue(CONFIG) });

    await usuario.click(await screen.findByRole("button", { name: /descuento general/i }));
    await confirmar(usuario);

    await waitFor(() => expect(valor.registrarVenta).toHaveBeenCalled());
    const { payload, resumen } = valor.registrarVenta.mock.calls[0][0];
    expect(payload.descuento).toEqual({ origen: "general", tipo: "porcentaje", valor: "10.00" });
    expect(resumen.descuento_monto).toBe("2600.00");
  });

  it("sin conexion no se ofrece buscar clientes y lo explica", async () => {
    renderizar({ enLinea: false, leerDeCache: vi.fn().mockResolvedValue(CONFIG) });

    expect(await screen.findByText(/la venta no lleva cliente/i)).toBeInTheDocument();
    expect(screen.queryByLabelText("Buscar cliente")).not.toBeInTheDocument();
  });

  it("con conexion pero sin respuesta del servidor (red caida al confirmar) guarda la venta con el MISMO uuid que envio", async () => {
    const usuario = userEvent.setup();
    apiClient.crearVenta.mockRejectedValue(new TypeError("Failed to fetch"));
    const { valor } = renderizar();

    await confirmar(usuario);

    await waitFor(() => expect(valor.registrarVenta).toHaveBeenCalledTimes(1));
    const enviado = apiClient.crearVenta.mock.calls[0][0];
    const guardado = valor.registrarVenta.mock.calls[0][0];
    expect(guardado.payload.uuid_cliente).toBe(enviado.uuid_cliente);
    expect(valor.reportarFalloDeConexion).toHaveBeenCalled();
    expect(await screen.findByText(/Venta SC-0007 guardada sin conexión/)).toBeInTheDocument();
    // Pidio al servidor con un tiempo maximo, para no dejar al vendedor esperando.
    expect(apiClient.crearVenta.mock.calls[0][2]).toEqual({ tiempoMaximoMs: 12000 });
  });

  it("el tunel caido (502) tambien guarda la venta", async () => {
    const usuario = userEvent.setup();
    apiClient.crearVenta.mockRejectedValue(new apiClient.ApiError("Bad gateway", 502));
    const { valor } = renderizar();

    await confirmar(usuario);

    await waitFor(() => expect(valor.registrarVenta).toHaveBeenCalledTimes(1));
  });

  it("si el servidor RECHAZA la venta (sin stock) no la guarda: muestra el motivo", async () => {
    const usuario = userEvent.setup();
    apiClient.crearVenta.mockRejectedValue(new apiClient.ApiError("Stock insuficiente para Piñata Mickey.", 409));
    const { valor } = renderizar();

    await confirmar(usuario);

    expect(await screen.findByText("Stock insuficiente para Piñata Mickey.")).toBeInTheDocument();
    expect(valor.registrarVenta).not.toHaveBeenCalled();
  });

  it("si el navegador no puede guardar datos, avisa en vez de perder la venta", async () => {
    const usuario = userEvent.setup();
    apiClient.obtenerConfiguracionDescuentos.mockRejectedValue(new TypeError("Failed to fetch"));
    const { valor } = renderizar({ enLinea: false, disponible: false, leerDeCache: vi.fn().mockResolvedValue(CONFIG) });

    await confirmar(usuario);

    expect(await screen.findByText(/este navegador no puede guardar la venta/i)).toBeInTheDocument();
    expect(valor.registrarVenta).not.toHaveBeenCalled();
  });

  it("si falla la impresion de una venta sin conexion, avisa con su numero local y deja reintentar", async () => {
    const usuario = userEvent.setup();
    apiClient.obtenerConfiguracionDescuentos.mockRejectedValue(new TypeError("Failed to fetch"));
    apiClient.imprimirTicket.mockRejectedValueOnce(new Error("Impresora apagada")).mockResolvedValueOnce({ status: "ok" });
    renderizar({ enLinea: false, leerDeCache: vi.fn().mockResolvedValue(CONFIG) });

    await confirmar(usuario);

    expect(await screen.findByText(/La venta SC-0007 se guardó sin conexión, pero no se pudo imprimir el ticket: Impresora apagada/)).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Reintentar impresión" }));
    await waitFor(() => expect(apiClient.imprimirTicket).toHaveBeenCalledTimes(2));
    expect(apiClient.imprimirTicket.mock.calls[1][0]).toMatchObject({ referencia: "SC-0007" });
  });

  it("sin conexion usa la lista de vendedores guardada", async () => {
    apiClient.obtenerVendedores.mockRejectedValue(new TypeError("Failed to fetch"));
    apiClient.obtenerConfiguracionDescuentos.mockRejectedValue(new TypeError("Failed to fetch"));
    renderizar({
      enLinea: false,
      leerDeCache: vi.fn(async (clave) => (clave === "vendedores" ? [{ id: 1, nombre: "Ana" }, { id: 2, nombre: "Luis" }] : CONFIG)),
    });

    expect(await screen.findByText(/Ana/)).toBeInTheDocument();
  });
});

describe("Aviso de venta guardada (Fase 9)", () => {
  it("desaparece cuando vuelve la conexion, porque ya no es cierto que 'se enviara sola'", async () => {
    const usuario = userEvent.setup();
    apiClient.obtenerConfiguracionDescuentos.mockRejectedValue(new TypeError("Failed to fetch"));
    const sc = {
      enLinea: false,
      registrarVenta: vi.fn().mockResolvedValue(undefined),
      siguienteNumero: vi.fn().mockResolvedValue("SC-0007"),
      reportarFalloDeConexion: vi.fn(),
      guardarEnCache: vi.fn().mockResolvedValue(undefined),
      leerDeCache: vi.fn().mockResolvedValue(CONFIG),
    };
    const base = { ...VALOR_SIN_CONEXION_INACTIVO, activo: true, disponible: true };
    localStorage.setItem("mm_pos_token", `x.${btoa(JSON.stringify({ sub: "1", rol: "vendedor" }))}.y`);
    const arbol = (enLinea) => (
      <AuthProvider>
        <SinConexionContext.Provider value={{ ...base, ...sc, enLinea }}>
          <CartProvider>
            <CarritoCon productos={[PRODUCTO]} />
            <ConfirmacionPago />
          </CartProvider>
        </SinConexionContext.Provider>
      </AuthProvider>
    );
    const { rerender } = render(arbol(false));

    await confirmar(usuario);
    expect(await screen.findByText(/Venta SC-0007 guardada sin conexión/)).toBeInTheDocument();

    rerender(arbol(true));

    await waitFor(() => expect(screen.queryByText(/Venta SC-0007 guardada sin conexión/)).not.toBeInTheDocument());
  });
});
