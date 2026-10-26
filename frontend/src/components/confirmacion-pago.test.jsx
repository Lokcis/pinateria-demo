import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ConfirmacionPago } from "./confirmacion-pago";
import { AuthProvider } from "../context/auth-context";
import { CartProvider, useCart } from "../context/cart-context";
import { ApiError } from "../api/api-client";
import * as apiClient from "../api/api-client";
import { elegirOpcion } from "../utils/test-desplegable";
import { POLITICA_PRUEBA } from "../utils/politica-prueba";

vi.mock("../api/api-client", async () => {
  const modulo = await vi.importActual("../api/api-client");
  return {
    ...modulo,
    crearVenta: vi.fn(),
    imprimirTicket: vi.fn(),
    obtenerConfiguracionDescuentos: vi.fn(),
    obtenerVendedores: vi.fn(),
    buscarClientes: vi.fn(),
    crearCliente: vi.fn(),
    obtenerPoliticaDatos: vi.fn(),
  };
});

const SIN_DESCUENTOS = {
  general: null,
  topes: { tope_porcentaje: null, tope_monto: null, descripcion: "sin límite" },
};
const CON_GENERAL_Y_TOPES = {
  general: { tipo: "porcentaje", valor: "10.00", activo: true },
  topes: { tope_porcentaje: "10.00", tope_monto: "5000.00", descripcion: "hasta 10 % del subtotal y hasta $5.000" },
};

const PRODUCTO = { id: 1, nombre: "Piñata Mickey", precio_venta: "26000.00", stock_actual: 5, categoria_nombre: "Piñatas" };

/** Agrega productos al carrito al montarse (como hace la busqueda en el POS). */
function CarritoCon({ productos }) {
  const { agregarProducto } = useCart();
  useEffect(() => {
    productos.forEach((producto) => agregarProducto(producto));
  }, [productos, agregarProducto]);
  return null;
}

/**
 * Renderiza la confirmacion con un carrito y un rol.
 *
 * @param {{productos?: Array<object>, rol?: string}} opciones
 */
function renderizar({ productos = [PRODUCTO], rol = "vendedor" } = {}) {
  localStorage.setItem("mm_pos_token", `x.${btoa(JSON.stringify({ sub: "1", rol }))}.y`);
  return render(
    <AuthProvider>
      <CartProvider>
        <CarritoCon productos={productos} />
        <ConfirmacionPago />
      </CartProvider>
    </AuthProvider>
  );
}

/** Venta que devuelve el backend para un payload dado. */
function ventaDe(payload, total) {
  return {
    id: 21,
    fecha: "2026-10-08T20:00:00Z",
    subtotal: "26000.00",
    descuento_origen: payload.descuento.origen,
    descuento_tipo: null,
    descuento_valor: null,
    descuento_monto: "0.00",
    ajuste_redondeo: "0.00",
    total,
    detalles: [{ producto_id: 1, cantidad: 1, precio_unitario: "26000.00", subtotal: "26000.00", descuento_prorrateado: "0.00" }],
    pagos: payload.pagos.map((p) => ({ ...p, vueltas: "0.00" })),
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  apiClient.obtenerConfiguracionDescuentos.mockResolvedValue(SIN_DESCUENTOS);
  apiClient.obtenerVendedores.mockResolvedValue([]);
  apiClient.buscarClientes.mockResolvedValue([]);
  apiClient.obtenerPoliticaDatos.mockResolvedValue(POLITICA_PRUEBA);
  apiClient.imprimirTicket.mockResolvedValue({ status: "ok", modo: "mock" });
  apiClient.crearVenta.mockImplementation(async (payload) => ventaDe(payload, "26000.00"));
});

/** HU-05: pagos mixtos, plataforma, recibido y vueltas; no confirma si no cuadra. */
describe("ConfirmacionPago — pagos", () => {
  it("por defecto un pago en efectivo exacto por el total y se confirma de una vez", async () => {
    const usuario = userEvent.setup();
    renderizar();

    expect(await screen.findByRole("textbox", { name: "Monto del pago" })).toHaveValue("26000");
    await usuario.click(screen.getByRole("button", { name: "Confirmar venta" }));

    await waitFor(() => expect(apiClient.crearVenta).toHaveBeenCalledTimes(1));
    expect(apiClient.crearVenta.mock.calls[0][0]).toEqual({
      detalles: [{ producto_id: 1, cantidad: 1 }],
      pagos: [{ metodo_pago: "efectivo", plataforma: null, monto: "26000", monto_recibido: "26000" }],
      descuento: { origen: "ninguno" },
      // Fase 9: cada venta lleva su identificador, para que reenviarla nunca la duplique.
      uuid_cliente: expect.stringMatching(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/),
    });
    expect(await screen.findByText("Venta #21 registrada correctamente.")).toBeInTheDocument();
    const ticket = apiClient.imprimirTicket.mock.calls[0][0];
    expect(ticket.pagos[0]).toMatchObject({ metodo_pago: "efectivo", monto: "26000" });
  });

  it("muestra las vueltas del efectivo", async () => {
    const usuario = userEvent.setup();
    renderizar();

    await usuario.type(await screen.findByRole("textbox", { name: "Recibido en el pago" }), "50000");

    expect(screen.getByText(/Vueltas:/)).toHaveTextContent(/24\.000/);
  });

  it("efectivo y Nequi: muestra lo que falta, agrega el pago con el faltante y exige la plataforma", async () => {
    const usuario = userEvent.setup();
    renderizar();
    const monto = await screen.findByRole("textbox", { name: "Monto del pago" });

    await usuario.clear(monto);
    await usuario.type(monto, "20000");
    expect(screen.getByRole("status")).toHaveTextContent(/Falta \$\s?6\.000/);
    expect(screen.getByRole("button", { name: "Confirmar venta" })).toBeDisabled();

    await usuario.click(screen.getByRole("button", { name: "+ Agregar pago" }));
    expect(screen.getByRole("textbox", { name: "Monto del pago 2" })).toHaveValue("6000");
    expect(screen.getByText("Elige Nequi o Daviplata.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirmar venta" })).toBeDisabled();

    await usuario.click(within(screen.getByRole("radiogroup", { name: "Plataforma del pago 2" })).getByRole("radio", { name: "Nequi" }));
    expect(screen.getByRole("status")).toHaveTextContent("Pagos completos");
    await usuario.click(screen.getByRole("button", { name: "Confirmar venta" }));

    await waitFor(() => expect(apiClient.crearVenta).toHaveBeenCalledTimes(1));
    expect(apiClient.crearVenta.mock.calls[0][0].pagos).toEqual([
      { metodo_pago: "efectivo", plataforma: null, monto: "20000", monto_recibido: "20000" },
      { metodo_pago: "transferencia", plataforma: "nequi", monto: "6000", monto_recibido: null },
    ]);
  });

  it("si sobra no deja confirmar", async () => {
    const usuario = userEvent.setup();
    renderizar();
    const monto = await screen.findByRole("textbox", { name: "Monto del pago" });

    await usuario.clear(monto);
    await usuario.type(monto, "30000");

    expect(screen.getByRole("status")).toHaveTextContent(/Sobra \$\s?4\.000/);
    expect(screen.getByRole("button", { name: "Confirmar venta" })).toBeDisabled();
  });
});

/** HU-06: el general es opcional (lo aplica el vendedor), el manual respeta el limite del vendedor. */
describe("ConfirmacionPago — descuento", () => {
  it("con el general activo la venta arranca sin descuento", async () => {
    const usuario = userEvent.setup();
    apiClient.obtenerConfiguracionDescuentos.mockResolvedValue(CON_GENERAL_Y_TOPES);
    renderizar();

    expect(await screen.findByRole("button", { name: "Aplicar descuento general (10 %)" })).toBeInTheDocument();
    expect(screen.getByText("Sin descuento")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Monto del pago" })).toHaveValue("26000");
    await usuario.click(screen.getByRole("button", { name: "Confirmar venta" }));

    await waitFor(() => expect(apiClient.crearVenta).toHaveBeenCalledTimes(1));
    expect(apiClient.crearVenta.mock.calls[0][0].descuento).toEqual({ origen: "ninguno" });
  });

  it("el vendedor aplica el general a mano y lo puede quitar", async () => {
    const usuario = userEvent.setup();
    apiClient.obtenerConfiguracionDescuentos.mockResolvedValue(CON_GENERAL_Y_TOPES);
    renderizar();

    await usuario.click(await screen.findByRole("button", { name: "Aplicar descuento general (10 %)" }));
    expect(screen.getByText("Subtotal")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Monto del pago" })).toHaveValue("23400");

    await usuario.click(screen.getByRole("button", { name: "Quitar" }));
    expect(screen.getByRole("textbox", { name: "Monto del pago" })).toHaveValue("26000");

    await usuario.click(screen.getByRole("button", { name: "Aplicar descuento general (10 %)" }));
    await usuario.click(screen.getByRole("button", { name: "Confirmar venta" }));
    await waitFor(() => expect(apiClient.crearVenta).toHaveBeenCalledTimes(1));
    expect(apiClient.crearVenta.mock.calls[0][0].descuento).toEqual({ origen: "general" });
  });

  it("el vendedor ve su limite y no puede confirmar si lo supera", async () => {
    const usuario = userEvent.setup();
    apiClient.obtenerConfiguracionDescuentos.mockResolvedValue(CON_GENERAL_Y_TOPES);
    renderizar();

    await usuario.click(await screen.findByRole("button", { name: "Agregar descuento" }));
    expect(screen.getByText("Tu límite: hasta 10 % del subtotal y hasta $5.000.")).toBeInTheDocument();
    const valor = screen.getByRole("textbox", { name: "Porcentaje de descuento" });
    await usuario.clear(valor);
    await usuario.type(valor, "15");

    expect(screen.getByText("Supera tu límite: hasta 10 % del subtotal y hasta $5.000.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirmar venta" })).toBeDisabled();
  });

  it("el administrador no tiene limite", async () => {
    const usuario = userEvent.setup();
    apiClient.obtenerConfiguracionDescuentos.mockResolvedValue(CON_GENERAL_Y_TOPES);
    renderizar({ rol: "administrador" });

    await usuario.click(await screen.findByRole("button", { name: "Agregar descuento" }));
    expect(screen.queryByText(/Tu límite/)).not.toBeInTheDocument();
    const valor = screen.getByRole("textbox", { name: "Porcentaje de descuento" });
    await usuario.clear(valor);
    await usuario.type(valor, "50");

    expect(screen.getByRole("textbox", { name: "Monto del pago" })).toHaveValue("13000");
    expect(screen.getByRole("button", { name: "Confirmar venta" })).toBeEnabled();
  });

  it("con el 100 % la venta no lleva pagos", async () => {
    const usuario = userEvent.setup();
    renderizar({ rol: "administrador" });

    await usuario.click(await screen.findByRole("button", { name: "Agregar descuento" }));
    await usuario.type(screen.getByRole("textbox", { name: "Porcentaje de descuento" }), "100");

    expect(screen.getByText("El total es $0: la venta no lleva pagos.")).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Confirmar venta" }));
    await waitFor(() => expect(apiClient.crearVenta).toHaveBeenCalledTimes(1));
    expect(apiClient.crearVenta.mock.calls[0][0]).toMatchObject({
      pagos: [],
      descuento: { origen: "manual", tipo: "porcentaje", valor: "100" },
    });
  });

  it("si el general se apago durante la venta (409) recarga la configuracion y quita el descuento", async () => {
    const usuario = userEvent.setup();
    apiClient.obtenerConfiguracionDescuentos.mockResolvedValue(CON_GENERAL_Y_TOPES);
    apiClient.crearVenta.mockRejectedValue(
      new ApiError("El descuento general cambió mientras se hacía la venta. Revise el descuento y confirme de nuevo.", 409)
    );
    renderizar();
    await usuario.click(await screen.findByRole("button", { name: "Aplicar descuento general (10 %)" }));
    apiClient.obtenerConfiguracionDescuentos.mockResolvedValue(SIN_DESCUENTOS);

    await usuario.click(screen.getByRole("button", { name: "Confirmar venta" }));

    expect(await screen.findByText(/descuento general cambió/)).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: /Aplicar descuento general/ })).not.toBeInTheDocument()
    );
    expect(screen.getByRole("textbox", { name: "Monto del pago" })).toHaveValue("26000");
  });
});

const CLIENTE_CON_DESCUENTO = {
  id: 7,
  nombre: "María Pérez",
  documento: "1010202030",
  telefono: "3001234567",
  descuento_tipo: "porcentaje",
  descuento_valor: "10.00",
  utilizable: true,
};
const CLIENTE_SIN_DESCUENTO = { ...CLIENTE_CON_DESCUENTO, id: 8, nombre: "Carlos Ruiz", descuento_tipo: null, descuento_valor: null };

/** Busca un cliente por texto y lo elige de la lista de resultados. */
async function elegirCliente(usuario, texto, nombre) {
  await usuario.type(await screen.findByRole("searchbox", { name: "Buscar cliente" }), texto);
  await usuario.click(await screen.findByRole("button", { name: new RegExp(nombre) }));
}

/** HU-07 y HU-06: el cliente asociado a la venta y su descuento propio, que se sugiere. */
describe("ConfirmacionPago — cliente", () => {
  it("busca solo clientes utilizables y la venta se manda con su cliente_id", async () => {
    const usuario = userEvent.setup();
    apiClient.buscarClientes.mockResolvedValue([CLIENTE_SIN_DESCUENTO]);
    renderizar();

    await elegirCliente(usuario, "carl", "Carlos Ruiz");
    expect(apiClient.buscarClientes).toHaveBeenCalledWith(
      expect.objectContaining({ q: "carl", soloUtilizables: true }),
      expect.any(String)
    );
    expect(screen.getByText("Carlos Ruiz")).toBeInTheDocument();

    await usuario.click(screen.getByRole("button", { name: "Confirmar venta" }));
    await waitFor(() => expect(apiClient.crearVenta).toHaveBeenCalledTimes(1));
    expect(apiClient.crearVenta.mock.calls[0][0]).toMatchObject({ cliente_id: 8, descuento: { origen: "ninguno" } });
  });

  it("al elegir un cliente con descuento propio lo sugiere de una vez y lo manda como origen cliente", async () => {
    const usuario = userEvent.setup();
    apiClient.buscarClientes.mockResolvedValue([CLIENTE_CON_DESCUENTO]);
    renderizar();

    await elegirCliente(usuario, "mar", "María Pérez");

    expect(screen.getByText("Descuento del cliente:")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Monto del pago" })).toHaveValue("23400");
    await usuario.click(screen.getByRole("button", { name: "Confirmar venta" }));
    await waitFor(() => expect(apiClient.crearVenta).toHaveBeenCalledTimes(1));
    expect(apiClient.crearVenta.mock.calls[0][0]).toMatchObject({ cliente_id: 7, descuento: { origen: "cliente" } });
  });

  it("el descuento del cliente reemplaza al general: nunca se suman", async () => {
    const usuario = userEvent.setup();
    apiClient.obtenerConfiguracionDescuentos.mockResolvedValue(CON_GENERAL_Y_TOPES);
    apiClient.buscarClientes.mockResolvedValue([CLIENTE_CON_DESCUENTO]);
    renderizar();

    await usuario.click(await screen.findByRole("button", { name: "Aplicar descuento general (10 %)" }));
    await elegirCliente(usuario, "mar", "María Pérez");

    expect(screen.queryByText(/Descuento general:/)).not.toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Monto del pago" })).toHaveValue("23400");
  });

  it("el vendedor puede quitar el sugerido y volver a aplicarlo", async () => {
    const usuario = userEvent.setup();
    apiClient.buscarClientes.mockResolvedValue([CLIENTE_CON_DESCUENTO]);
    renderizar();
    await elegirCliente(usuario, "mar", "María Pérez");

    await usuario.click(screen.getByRole("button", { name: "Quitar" }));
    expect(screen.getByRole("textbox", { name: "Monto del pago" })).toHaveValue("26000");
    await usuario.click(screen.getByRole("button", { name: "Aplicar descuento del cliente (10 %)" }));
    expect(screen.getByRole("textbox", { name: "Monto del pago" })).toHaveValue("23400");
  });

  it("al quitar el cliente se va su descuento", async () => {
    const usuario = userEvent.setup();
    apiClient.buscarClientes.mockResolvedValue([CLIENTE_CON_DESCUENTO]);
    renderizar();
    await elegirCliente(usuario, "mar", "María Pérez");

    await usuario.click(screen.getByRole("button", { name: "Quitar cliente" }));

    expect(screen.getByRole("textbox", { name: "Monto del pago" })).toHaveValue("26000");
    expect(screen.getByRole("searchbox", { name: "Buscar cliente" })).toBeInTheDocument();
  });

  it("registra un cliente nuevo desde la venta: exige la autorizacion y lo deja asociado", async () => {
    const usuario = userEvent.setup();
    apiClient.crearCliente.mockResolvedValue({ ...CLIENTE_SIN_DESCUENTO, id: 9, nombre: "Lucía Mora" });
    renderizar();

    await usuario.click(await screen.findByRole("button", { name: "Nuevo cliente" }));
    await usuario.type(screen.getByLabelText("Nombre"), "Lucía Mora");
    expect(screen.getByRole("button", { name: "Guardar" })).toBeDisabled(); // sin autorizacion no se guarda

    await usuario.click(screen.getByRole("checkbox", { name: /autoriza el tratamiento/ }));
    await usuario.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() => expect(apiClient.crearCliente).toHaveBeenCalledTimes(1));
    expect(apiClient.crearCliente.mock.calls[0][0]).toMatchObject({
      nombre: "Lucía Mora",
      documento: null,
      autorizacion_aceptada: true,
      autorizacion_medio: "verbal",
      acepta_publicidad: false,
    });
    expect(await screen.findByText("Lucía Mora")).toBeInTheDocument();
  });

  it("muestra el error del servidor al registrar (documento repetido)", async () => {
    const usuario = userEvent.setup();
    apiClient.crearCliente.mockRejectedValue(new Error("Ya existe un cliente con ese documento."));
    renderizar();

    await usuario.click(await screen.findByRole("button", { name: "Nuevo cliente" }));
    await usuario.type(screen.getByLabelText("Nombre"), "Lucía Mora");
    await usuario.click(screen.getByRole("checkbox", { name: /autoriza el tratamiento/ }));
    await usuario.click(screen.getByRole("button", { name: "Guardar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Ya existe un cliente con ese documento.");
  });
});

/** HU-08: la venta queda a nombre de quien la realizo. */
describe("ConfirmacionPago — vendedor", () => {
  const VENDEDORES = [
    { id: 1, nombre: "Laura Gómez" },
    { id: 2, nombre: "Pedro Díaz" },
  ];

  it("lista a los vendedores con la sesion seleccionada y no manda vendedor_id si no se cambia", async () => {
    const usuario = userEvent.setup();
    apiClient.obtenerVendedores.mockResolvedValue(VENDEDORES);
    renderizar();

    expect(await screen.findByRole("combobox", { name: "Vendedor de la venta" })).toHaveTextContent("Laura Gómez");
    await usuario.click(screen.getByRole("button", { name: "Confirmar venta" }));
    await waitFor(() => expect(apiClient.crearVenta).toHaveBeenCalledTimes(1));
    expect(apiClient.crearVenta.mock.calls[0][0]).not.toHaveProperty("vendedor_id");
    expect(apiClient.imprimirTicket.mock.calls[0][0].vendedor).toBe("Laura Gómez");
  });

  it("la venta se registra a nombre del elegido y el ticket lo imprime", async () => {
    const usuario = userEvent.setup();
    apiClient.obtenerVendedores.mockResolvedValue(VENDEDORES);
    renderizar();

    await elegirOpcion(await screen.findByRole("combobox", { name: "Vendedor de la venta" }), "2");
    await usuario.click(screen.getByRole("button", { name: "Confirmar venta" }));

    await waitFor(() => expect(apiClient.crearVenta).toHaveBeenCalledTimes(1));
    expect(apiClient.crearVenta.mock.calls[0][0]).toMatchObject({ vendedor_id: 2 });
    expect(apiClient.imprimirTicket.mock.calls[0][0].vendedor).toBe("Pedro Díaz");
  });

  it("despues de cada venta vuelve a la sesion, para que nadie herede la venta de otro", async () => {
    const usuario = userEvent.setup();
    apiClient.obtenerVendedores.mockResolvedValue(VENDEDORES);
    renderizar();

    await elegirOpcion(await screen.findByRole("combobox", { name: "Vendedor de la venta" }), "2");
    await usuario.click(screen.getByRole("button", { name: "Confirmar venta" }));
    await screen.findByText("Venta #21 registrada correctamente.");

    expect(screen.getByRole("combobox", { name: "Vendedor de la venta" })).toHaveTextContent("Laura Gómez");
  });

  it("si la lista no carga, no se muestra el desplegable y la venta sigue a nombre de la sesion", async () => {
    const usuario = userEvent.setup();
    apiClient.obtenerVendedores.mockRejectedValue(new Error("sin red"));
    renderizar();

    await usuario.click(await screen.findByRole("button", { name: "Confirmar venta" }));
    await waitFor(() => expect(apiClient.crearVenta).toHaveBeenCalledTimes(1));
    expect(screen.queryByRole("combobox", { name: "Vendedor de la venta" })).not.toBeInTheDocument();
    expect(apiClient.crearVenta.mock.calls[0][0]).not.toHaveProperty("vendedor_id");
  });
});
