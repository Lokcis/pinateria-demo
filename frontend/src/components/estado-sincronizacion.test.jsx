import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { EstadoSincronizacion } from "./estado-sincronizacion";
import { AuthProvider } from "../context/auth-context";
import { SinConexionContext, VALOR_SIN_CONEXION_INACTIVO } from "../context/sin-conexion-context";
import * as apiClient from "../api/api-client";

vi.mock("../api/api-client", async () => {
  const modulo = await vi.importActual("../api/api-client");
  return { ...modulo, imprimirTicket: vi.fn() };
});

/** Una venta de la cola, como la deja `armarVentaPendiente`. */
function venta(uuid, extra = {}) {
  return {
    uuid,
    numeroLocal: `SC-000${uuid}`,
    usuarioId: "1",
    creadaEn: "2026-10-14T15:00:00.000Z",
    estado: "pendiente",
    mensaje: null,
    intentos: 0,
    payload: {},
    resumen: {
      subtotal: "26000.00", descuento_tipo: null, descuento_valor: null, descuento_monto: "0.00", ajuste_redondeo: "0.00",
      total: "26000.00", vendedor: "Ana",
      lineas: [{ producto_id: 1, nombre: "Piñata Mickey", cantidad: 2, precio_unitario: "13000.00", subtotal: "26000.00" }],
      pagos: [{ metodo_pago: "efectivo", plataforma: null, monto: "26000", monto_recibido: "26000", vueltas: "0.00" }],
    },
    ...extra,
  };
}

function renderizar(sc = {}) {
  localStorage.setItem("mm_pos_token", `x.${btoa(JSON.stringify({ sub: "1", rol: "vendedor" }))}.y`);
  const valor = {
    ...VALOR_SIN_CONEXION_INACTIVO,
    activo: true,
    disponible: true,
    enLinea: true,
    ventas: [],
    sincronizar: vi.fn(),
    reintentarVenta: vi.fn(),
    descartarVenta: vi.fn(),
    descartarAviso: vi.fn(),
    ...sc,
  };
  render(
    <AuthProvider>
      <SinConexionContext.Provider value={valor}>
        <EstadoSincronizacion />
      </SinConexionContext.Provider>
    </AuthProvider>
  );
  return valor;
}

beforeEach(() => {
  vi.resetAllMocks();
  localStorage.clear();
});

describe("EstadoSincronizacion", () => {
  it("no muestra nada cuando hay conexion y no hay ventas guardadas", () => {
    renderizar();
    expect(screen.queryByRole("region")).not.toBeInTheDocument();
  });

  it("sin conexion avisa que se puede seguir vendiendo, que no cierre sesion y desde cuando es el catalogo", () => {
    renderizar({ enLinea: false, catalogo: { cantidad: 152, guardadoEn: new Date().toISOString() } });

    const alerta = screen.getByText("Sin conexión con el servidor.").closest("div");
    expect(within(alerta).getByText(/Puedes seguir vendiendo/)).toBeInTheDocument();
    expect(within(alerta).getByText(/152 productos/)).toBeInTheDocument();
    expect(within(alerta).getByText(/No cierres sesión/)).toBeInTheDocument();
  });

  it("sin conexion y sin catalogo guardado pide conectarse una vez", () => {
    renderizar({ enLinea: false, catalogo: null });
    expect(screen.getByText(/Todavía no hay catálogo guardado/)).toBeInTheDocument();
  });

  it("con ventas por enviar muestra cuantas hay y permite enviarlas ahora", async () => {
    const usuario = userEvent.setup();
    const sc = renderizar({ ventas: [venta("1"), venta("2")], pendientes: 2, misPendientes: 2 });

    expect(screen.getByText("2 ventas guardadas sin conexión por enviar.")).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Enviar ahora" }));
    expect(sc.sincronizar).toHaveBeenCalled();
  });

  it("mientras envia lo dice y oculta el boton", () => {
    renderizar({ ventas: [venta("1")], pendientes: 1, misPendientes: 1, sincronizando: true });
    expect(screen.getByText("Enviando ventas guardadas…")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Enviar ahora" })).not.toBeInTheDocument();
  });

  it("con la sesion vencida pide iniciar sesion de nuevo y aclara que nada se pierde", () => {
    renderizar({ ventas: [venta("1")], pendientes: 1, misPendientes: 1, sesionVencida: true });
    expect(screen.getByText("Tu sesión venció.")).toBeInTheDocument();
    expect(screen.getByText(/no se pierden/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Iniciar sesión de nuevo" })).toBeInTheDocument();
  });

  it("avisa de las ventas guardadas por otra persona", () => {
    renderizar({ ventas: [venta("1", { usuarioId: "8" })], pendientes: 1, misPendientes: 0, pendientesDeOtros: 1 });
    expect(screen.getByText(/1 venta guardada por otra persona/)).toBeInTheDocument();
  });

  it("al terminar de enviar avisa cuantas se enviaron y se puede cerrar el aviso", async () => {
    const usuario = userEvent.setup();
    const sc = renderizar({ ultimoEnvio: { enviadas: 3, conflictos: 0 } });

    expect(screen.getByText("Se enviaron 3 ventas guardadas sin conexión.")).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Entendido" }));
    expect(sc.descartarAviso).toHaveBeenCalled();
  });

  it("el aviso de lo enviado concuerda en singular y no aparece si la conexion vuelve a caer", () => {
    const { unmount } = render(
      <AuthProvider>
        <SinConexionContext.Provider
          value={{ ...VALOR_SIN_CONEXION_INACTIVO, activo: true, disponible: true, enLinea: true, ultimoEnvio: { enviadas: 1, conflictos: 1 } }}
        >
          <EstadoSincronizacion />
        </SinConexionContext.Provider>
      </AuthProvider>
    );
    expect(screen.getByText("Se envió 1 venta guardada sin conexión. 1 necesita revisión.")).toBeInTheDocument();
    unmount();

    renderizar({ enLinea: false, ultimoEnvio: { enviadas: 1, conflictos: 0 } });
    expect(screen.queryByText(/Se envió 1 venta guardada/)).not.toBeInTheDocument();
  });

  it("lista las ventas guardadas con su numero, total y productos", async () => {
    const usuario = userEvent.setup();
    renderizar({ ventas: [venta("1")], pendientes: 1, misPendientes: 1 });

    await usuario.click(screen.getByRole("button", { name: "Ver ventas guardadas (1)" }));

    const lista = screen.getByRole("list", { name: "Ventas guardadas sin conexión" });
    expect(within(lista).getByText("SC-0001")).toBeInTheDocument();
    expect(within(lista).getByText("Por enviar")).toBeInTheDocument();
    expect(within(lista).getByText("2 × Piñata Mickey")).toBeInTheDocument();
    expect(within(lista).getByText(/26.000/)).toBeInTheDocument();
  });

  it("una venta en conflicto muestra el motivo y se puede reintentar", async () => {
    const usuario = userEvent.setup();
    const sc = renderizar({
      ventas: [venta("1", { estado: "conflicto", mensaje: "Stock insuficiente para Piñata Mickey." })],
      conflictos: 1,
    });

    expect(screen.getByText(/1 venta no se pudo registrar/)).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Ver ventas guardadas (1)" }));
    expect(screen.getByText(/Stock insuficiente para Piñata Mickey\./)).toBeInTheDocument();

    await usuario.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(sc.reintentarVenta).toHaveBeenCalledWith("1");
  });

  it("descartar una venta en conflicto pide confirmacion y no la borra si se cancela", async () => {
    const usuario = userEvent.setup();
    const sc = renderizar({ ventas: [venta("1", { estado: "conflicto", mensaje: "Sin stock." })], conflictos: 1 });
    await usuario.click(screen.getByRole("button", { name: "Ver ventas guardadas (1)" }));

    await usuario.click(screen.getByRole("button", { name: "Descartar" }));
    expect(await screen.findByText("¿Descartar la venta SC-0001?")).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(sc.descartarVenta).not.toHaveBeenCalled();

    await usuario.click(screen.getByRole("button", { name: "Descartar" }));
    await usuario.click(await screen.findByRole("button", { name: "Descartar venta" }));
    expect(sc.descartarVenta).toHaveBeenCalledWith("1");
  });

  it("una venta por enviar no se puede descartar, solo reimprimir", async () => {
    const usuario = userEvent.setup();
    renderizar({ ventas: [venta("1")], pendientes: 1, misPendientes: 1 });
    await usuario.click(screen.getByRole("button", { name: "Ver ventas guardadas (1)" }));

    expect(screen.queryByRole("button", { name: "Descartar" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reimprimir ticket" })).toBeInTheDocument();
  });

  it("reimprimir envia al agente el ticket con la referencia local", async () => {
    const usuario = userEvent.setup();
    apiClient.imprimirTicket.mockResolvedValue({ status: "ok" });
    renderizar({ ventas: [venta("1")], pendientes: 1, misPendientes: 1 });
    await usuario.click(screen.getByRole("button", { name: "Ver ventas guardadas (1)" }));

    await usuario.click(screen.getByRole("button", { name: "Reimprimir ticket" }));

    expect(apiClient.imprimirTicket).toHaveBeenCalledWith(expect.objectContaining({ venta_id: null, referencia: "SC-0001", total: "26000.00" }));
    expect(await screen.findByText("Ticket enviado a la impresora.")).toBeInTheDocument();
  });

  it("avisa si el navegador no puede guardar datos", () => {
    renderizar({ disponible: false });
    expect(screen.getByText(/no permite guardar datos en el equipo/i)).toBeInTheDocument();
  });
});
