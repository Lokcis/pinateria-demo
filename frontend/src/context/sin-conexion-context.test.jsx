import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api/api-client", async () => {
  const modulo = await vi.importActual("../api/api-client");
  return {
    ...modulo,
    crearVenta: vi.fn(),
    obtenerSalud: vi.fn(),
    obtenerCatalogo: vi.fn(),
    obtenerConfiguracionDescuentos: vi.fn(),
    obtenerVendedores: vi.fn(),
  };
});

import * as apiClient from "../api/api-client";
import { AuthProvider } from "./auth-context";
import { SinConexionProvider, useSinConexion } from "./sin-conexion-context";
import { reiniciarAlmacenParaPruebas } from "../offline/almacen";
import { leerDeCache, reiniciarCatalogoParaPruebas } from "../offline/catalogo-local";
import { armarVentaPendiente, encolarVenta, listarVentas } from "../offline/cola-ventas";

const CONFIG = { general: null, topes: { tope_porcentaje: null, tope_monto: null, descripcion: "sin límite" } };

/** Muestra lo que expone el contexto y deja guardar una venta de prueba. */
function Sonda() {
  const sc = useSinConexion();
  return (
    <div>
      <p>conexion: {sc.enLinea ? "si" : "no"}</p>
      <p>pendientes: {sc.pendientes}</p>
      <p>mis pendientes: {sc.misPendientes}</p>
      <p>conflictos: {sc.conflictos}</p>
      <p>catalogo: {sc.catalogo ? sc.catalogo.cantidad : "ninguno"}</p>
      <p>sesion vencida: {sc.sesionVencida ? "si" : "no"}</p>
      <p>envio: {sc.ultimoEnvio ? `${sc.ultimoEnvio.enviadas} enviadas` : "ninguno"}</p>
      <button type="button" onClick={() => sc.registrarVenta(ventaDePrueba("nueva", "1"))}>
        guardar
      </button>
    </div>
  );
}

function ventaDePrueba(uuid, usuarioId) {
  return armarVentaPendiente({
    uuid,
    numeroLocal: `SC-${uuid}`,
    usuarioId,
    creadaEn: new Date("2026-10-14T15:00:00Z"),
    items: [{ productoId: 1, nombre: "Piñata", precioUnitario: 26000, cantidad: 1 }],
    totales: { subtotal: 2600000, descuento: 0, ajuste: 0, total: 2600000 },
    validacionPagos: {
      payload: [{ metodo_pago: "efectivo", plataforma: null, monto: "26000", monto_recibido: "26000" }],
      vueltasCentavos: [0],
    },
    ventaSinCobro: false,
    descuentoPayload: { origen: "ninguno" },
    configuracion: null,
  });
}

function montar({ rol = "vendedor" } = {}) {
  localStorage.setItem("mm_pos_token", `x.${btoa(JSON.stringify({ sub: "1", rol }))}.y`);
  return render(
    <AuthProvider>
      <SinConexionProvider>
        <Sonda />
      </SinConexionProvider>
    </AuthProvider>
  );
}

beforeEach(async () => {
  vi.resetAllMocks();
  localStorage.clear();
  reiniciarCatalogoParaPruebas();
  await reiniciarAlmacenParaPruebas();
  Object.defineProperty(navigator, "onLine", { value: true, configurable: true });
  apiClient.obtenerSalud.mockResolvedValue({ status: "ok" });
  apiClient.obtenerCatalogo.mockResolvedValue({
    total: 1,
    productos: [{ id: 1, nombre: "Piñata", categoria_id: 1, categoria_nombre: "Piñatas", codigo_barras: null, tipo: "unidad", precio_venta: "26000.00", stock_actual: 5, stock_minimo: 1, activo: true }],
  });
  apiClient.obtenerConfiguracionDescuentos.mockResolvedValue(CONFIG);
  apiClient.obtenerVendedores.mockResolvedValue([{ id: 1, nombre: "Ana" }]);
  apiClient.crearVenta.mockResolvedValue({ id: 99 });
});

describe("SinConexionProvider", () => {
  it("al abrir con conexion descarga el catalogo y guarda los descuentos y los vendedores para usarlos sin red", async () => {
    montar();

    expect(await screen.findByText("catalogo: 1")).toBeInTheDocument();
    await waitFor(async () => expect(await leerDeCache("descuentos")).toEqual(CONFIG));
    expect(await leerDeCache("vendedores")).toEqual([{ id: 1, nombre: "Ana" }]);
  });

  it("al abrir con ventas guardadas y conexion, las envia solas", async () => {
    await encolarVenta(ventaDePrueba("a", "1"));
    await encolarVenta(ventaDePrueba("b", "1"));

    montar();

    await waitFor(() => expect(apiClient.crearVenta).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("pendientes: 0")).toBeInTheDocument();
    expect(await screen.findByText("envio: 2 enviadas")).toBeInTheDocument();
    expect(await listarVentas()).toEqual([]);
  });

  it("al perder la red avisa; la venta que se guarda espera; al volver la red se envia sola", async () => {
    const usuario = userEvent.setup();
    montar();
    await screen.findByText("catalogo: 1");

    act(() => window.dispatchEvent(new Event("offline")));
    expect(await screen.findByText("conexion: no")).toBeInTheDocument();

    await usuario.click(screen.getByRole("button", { name: "guardar" }));
    expect(await screen.findByText("pendientes: 1")).toBeInTheDocument();
    expect(apiClient.crearVenta).not.toHaveBeenCalled();

    act(() => window.dispatchEvent(new Event("online")));

    await waitFor(() => expect(apiClient.crearVenta).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("conexion: si")).toBeInTheDocument();
    expect(await screen.findByText("pendientes: 0")).toBeInTheDocument();
  });

  it("si el navegador dice que volvio la red pero el servidor no responde, sigue sin conexion", async () => {
    montar();
    await screen.findByText("catalogo: 1");
    act(() => window.dispatchEvent(new Event("offline")));
    await screen.findByText("conexion: no");
    apiClient.obtenerSalud.mockRejectedValue(new TypeError("Failed to fetch"));

    act(() => window.dispatchEvent(new Event("online")));

    await waitFor(() => expect(apiClient.obtenerSalud).toHaveBeenCalled());
    expect(screen.getByText("conexion: no")).toBeInTheDocument();
    expect(apiClient.crearVenta).not.toHaveBeenCalled();
  });

  it("si al enviar se cae la conexion, la venta se conserva y se pasa a sin conexion", async () => {
    await encolarVenta(ventaDePrueba("a", "1"));
    apiClient.crearVenta.mockRejectedValue(new TypeError("Failed to fetch"));

    montar();

    expect(await screen.findByText("conexion: no")).toBeInTheDocument();
    expect(await screen.findByText("pendientes: 1")).toBeInTheDocument();
    expect(screen.getByText("conflictos: 0")).toBeInTheDocument();
  });

  it("si la sesion vencio al enviar, lo indica y conserva la venta", async () => {
    await encolarVenta(ventaDePrueba("a", "1"));
    apiClient.crearVenta.mockRejectedValue(Object.assign(new Error("Token invalido"), { name: "ApiError", status: 401 }));

    montar();

    expect(await screen.findByText("sesion vencida: si")).toBeInTheDocument();
    expect(screen.getByText("pendientes: 1")).toBeInTheDocument();
  });

  it("una venta rechazada por el servidor pasa a conflicto y no se reenvia sola", async () => {
    await encolarVenta(ventaDePrueba("a", "1"));
    apiClient.crearVenta.mockRejectedValue(Object.assign(new Error("Stock insuficiente"), { name: "ApiError", status: 409 }));

    montar();

    expect(await screen.findByText("conflictos: 1")).toBeInTheDocument();
    expect(screen.getByText("pendientes: 0")).toBeInTheDocument();
    expect(apiClient.crearVenta).toHaveBeenCalledTimes(1);
  });

  it("un vendedor no envia las ventas guardadas por otra persona", async () => {
    await encolarVenta(ventaDePrueba("ajena", "8"));

    montar({ rol: "vendedor" });
    await screen.findByText("catalogo: 1");

    expect(screen.getByText("pendientes: 1")).toBeInTheDocument();
    expect(screen.getByText("mis pendientes: 0")).toBeInTheDocument();
    expect(apiClient.crearVenta).not.toHaveBeenCalled();
  });

  it("un administrador si envia las de todos", async () => {
    await encolarVenta(ventaDePrueba("ajena", "8"));

    montar({ rol: "administrador" });

    await waitFor(() => expect(apiClient.crearVenta).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("pendientes: 0")).toBeInTheDocument();
  });
});
