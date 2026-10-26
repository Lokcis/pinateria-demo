import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Caja } from "./caja";
import { AuthProvider } from "../context/auth-context";
import { SinConexionContext, VALOR_SIN_CONEXION_INACTIVO } from "../context/sin-conexion-context";
import * as apiClient from "../api/api-client";

vi.mock("../api/api-client", async () => {
  const modulo = await vi.importActual("../api/api-client");
  return {
    ...modulo,
    obtenerCajaActual: vi.fn(),
    abrirCaja: vi.fn(),
    registrarMovimientoCaja: vi.fn(),
    cerrarCaja: vi.fn(),
    obtenerCortes: vi.fn(),
    obtenerCorte: vi.fn(),
    exportarCortes: vi.fn(),
  };
});

const CIFRAS = {
  base_inicial: "100000.00",
  ventas_efectivo: "30000.00",
  ingresos: "20000.00",
  gastos_efectivo: "5000.00",
  compras_efectivo: "12000.00",
  retiros: "30000.00",
  efectivo_esperado: "103000.00",
  ventas_tarjeta: "15000.00",
  ventas_transferencia: "10000.00",
};

const CERRADA = {
  abierta: false,
  corte: null,
  cifras: null,
  movimientos: [],
  generado_en: "2026-10-20T15:00:00Z",
};

const ABIERTA = {
  abierta: true,
  corte: {
    id: 9,
    estado: "abierta",
    abierta_en: "2026-10-20T13:00:00Z",
    abierta_por: "Ana Pérez",
    cerrada_en: null,
    cerrada_por: null,
    base_inicial: "100000.00",
    efectivo_esperado: null,
    efectivo_contado: null,
    diferencia: null,
  },
  cifras: CIFRAS,
  movimientos: [
    { id: 1, tipo: "ingreso", monto: "20000.00", motivo: "Cambio para la caja", usuario: "Ana Pérez", creado_en: "2026-10-20T13:30:00Z" },
    { id: 2, tipo: "retiro", monto: "30000.00", motivo: "Consignación al banco", usuario: "Ana Pérez", creado_en: "2026-10-20T14:00:00Z" },
  ],
  generado_en: "2026-10-20T15:00:00Z",
};

const CORTE_CERRADO = {
  id: 8,
  estado: "cerrada",
  abierta_en: "2026-10-19T13:00:00Z",
  abierta_por: "Ana Pérez",
  cerrada_en: "2026-10-19T23:00:00Z",
  cerrada_por: "Luis Gómez",
  base_inicial: "100000.00",
  efectivo_esperado: "103000.00",
  efectivo_contado: "102000.00",
  diferencia: "-1000.00",
};

const FICHA = {
  ...CORTE_CERRADO,
  cifras: CIFRAS,
  observaciones: "Faltaron mil",
  movimientos: ABIERTA.movimientos,
  ventas_sin_conexion_tardias: { cantidad: 2, total: "40000.00" },
};

function renderizar(rol, propiedades = {}, sinConexion = {}) {
  localStorage.setItem("mm_pos_token", `c.${btoa(JSON.stringify({ sub: "7", rol }))}.f`);
  return render(
    <SinConexionContext.Provider value={{ ...VALOR_SIN_CONEXION_INACTIVO, ...sinConexion }}>
      <AuthProvider>
        <Caja {...propiedades} />
      </AuthProvider>
    </SinConexionContext.Provider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  apiClient.obtenerCajaActual.mockResolvedValue(CERRADA);
  apiClient.obtenerCortes.mockResolvedValue([CORTE_CERRADO]);
  apiClient.obtenerCorte.mockResolvedValue(FICHA);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Caja — abrir", () => {
  it("con la caja cerrada pide la base y la abre", async () => {
    apiClient.abrirCaja.mockImplementation(async () => {
      apiClient.obtenerCajaActual.mockResolvedValue(ABIERTA);
      return ABIERTA;
    });
    renderizar("vendedor");

    expect(await screen.findByText("La caja está cerrada")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Base en efectivo"), "100000");
    await userEvent.click(screen.getByRole("button", { name: "Abrir caja" }));

    await waitFor(() => expect(apiClient.abrirCaja).toHaveBeenCalledWith(100000, expect.any(String)));
    expect(await screen.findByText(/Abierta por Ana Pérez/)).toBeInTheDocument();
  });

  it("la base debe ser múltiplo de $50 y no llega al servidor si no lo es", async () => {
    renderizar("vendedor");
    await screen.findByText("La caja está cerrada");

    await userEvent.type(screen.getByLabelText("Base en efectivo"), "100025");
    await userEvent.click(screen.getByRole("button", { name: "Abrir caja" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("múltiplo de $50");
    expect(apiClient.abrirCaja).not.toHaveBeenCalled();
  });

  it("muestra el error del servidor si otra persona ya abrió la caja", async () => {
    apiClient.abrirCaja.mockRejectedValue(new Error("Ya hay una caja abierta: ciérrala antes de abrir otra."));
    renderizar("administrador");
    await screen.findByText("La caja está cerrada");

    await userEvent.type(screen.getByLabelText("Base en efectivo"), "50000");
    await userEvent.click(screen.getByRole("button", { name: "Abrir caja" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Ya hay una caja abierta");
  });
});

describe("Caja — abierta", () => {
  beforeEach(() => {
    apiClient.obtenerCajaActual.mockResolvedValue(ABIERTA);
  });

  it("muestra el efectivo esperado con su desglose y lo cobrado por tarjeta y transferencia", async () => {
    renderizar("vendedor");

    expect(await screen.findByText(/Abierta por Ana Pérez/)).toBeInTheDocument();
    expect(screen.getByText("Efectivo esperado en la caja").closest("div")).toHaveTextContent(/103\.000/);
    const calculo = screen.getByText("Cómo se calcula").closest("div");
    expect(within(calculo).getByText("Ventas en efectivo").closest("li")).toHaveTextContent(/30\.000/);
    expect(within(calculo).getByText("Retiros").closest("li")).toHaveTextContent(/30\.000/);
    const aparte = screen.getByText("Para comparar con el datáfono y el banco").closest("div");
    expect(aparte).toHaveTextContent(/15\.000/);
    expect(aparte).toHaveTextContent(/10\.000/);
    expect(screen.getByText(/Consignación al banco/)).toBeInTheDocument();
  });

  it("registra un retiro con su motivo", async () => {
    apiClient.registrarMovimientoCaja.mockResolvedValue(ABIERTA);
    renderizar("vendedor");
    await screen.findByText(/Abierta por Ana Pérez/);

    await userEvent.click(screen.getByRole("button", { name: "Registrar retiro" }));
    await userEvent.type(screen.getByLabelText("Monto"), "50000");
    await userEvent.type(screen.getByLabelText("Motivo"), "Consignación al banco");
    await userEvent.click(screen.getByRole("button", { name: "Registrar retiro" }));

    await waitFor(() =>
      expect(apiClient.registrarMovimientoCaja).toHaveBeenCalledWith(
        { tipo: "retiro", monto: 50000, motivo: "Consignación al banco" },
        expect.any(String)
      )
    );
  });

  it("el movimiento exige múltiplo de $50 y un motivo", async () => {
    renderizar("administrador");
    await screen.findByText(/Abierta por Ana Pérez/);

    await userEvent.click(screen.getByRole("button", { name: "Registrar ingreso" }));
    await userEvent.type(screen.getByLabelText("Monto"), "20025");
    await userEvent.type(screen.getByLabelText("Motivo"), "Cambio");
    await userEvent.click(screen.getByRole("button", { name: "Registrar ingreso" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("múltiplo de $50");

    expect(apiClient.registrarMovimientoCaja).not.toHaveBeenCalled();
  });

  it("cierra la caja: compara lo contado con lo esperado y muestra la ficha del corte", async () => {
    apiClient.cerrarCaja.mockImplementation(async () => {
      apiClient.obtenerCajaActual.mockResolvedValue(CERRADA);
      return FICHA;
    });
    renderizar("vendedor");
    await screen.findByText(/Abierta por Ana Pérez/);

    await userEvent.click(screen.getByRole("button", { name: "Cerrar caja" }));
    await userEvent.type(screen.getByLabelText("Efectivo contado"), "102000");
    expect(screen.getByRole("status")).toHaveTextContent("Faltan $ 1.000");
    await userEvent.type(screen.getByLabelText("Observaciones (opcional)"), "Faltaron mil");
    await userEvent.click(screen.getByRole("button", { name: "Cerrar caja" }));

    await waitFor(() =>
      expect(apiClient.cerrarCaja).toHaveBeenCalledWith(
        { efectivoContado: 102000, observaciones: "Faltaron mil" },
        expect.any(String)
      )
    );
    expect(await screen.findByText(/Caja cerrada\. Faltan/)).toBeInTheDocument();
    expect(screen.getByLabelText("Corte 8")).toBeInTheDocument();
    expect(await screen.findByText("La caja está cerrada")).toBeInTheDocument();
  });

  it("no deja cerrar si este equipo tiene ventas guardadas sin enviar", async () => {
    renderizar("vendedor", {}, { pendientes: 2, conflictos: 1 });
    await screen.findByText(/Abierta por Ana Pérez/);

    await userEvent.click(screen.getByRole("button", { name: "Cerrar caja" }));

    expect(screen.getByRole("alert")).toHaveTextContent("3 ventas guardadas sin enviar");
    expect(screen.getByRole("button", { name: "Cerrar caja" })).toBeDisabled();
    expect(apiClient.cerrarCaja).not.toHaveBeenCalled();
  });

  it("el contado debe ser múltiplo de $50", async () => {
    renderizar("vendedor");
    await screen.findByText(/Abierta por Ana Pérez/);

    await userEvent.click(screen.getByRole("button", { name: "Cerrar caja" }));
    await userEvent.type(screen.getByLabelText("Efectivo contado"), "102025");
    await userEvent.click(screen.getByRole("button", { name: "Cerrar caja" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("múltiplo de $50");
    expect(apiClient.cerrarCaja).not.toHaveBeenCalled();
  });
});

describe("Caja — propietario (solo lectura)", () => {
  it("ve la caja abierta y el historial, sin botones para operarla, y puede exportar", async () => {
    apiClient.obtenerCajaActual.mockResolvedValue(ABIERTA);
    renderizar("propietario", { soloLectura: true });

    expect(await screen.findByText(/Abierta por Ana Pérez/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cerrar caja" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Registrar retiro" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Registrar ingreso" })).not.toBeInTheDocument();
    expect(await screen.findByText(/Corte #8/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Exportar" })).toBeInTheDocument();
  });

  it("con la caja cerrada no ofrece abrirla", async () => {
    renderizar("propietario", { soloLectura: true });

    expect(await screen.findByText("No hay una caja abierta en este momento.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Abrir caja" })).not.toBeInTheDocument();
  });
});

describe("Caja — historial de cortes", () => {
  it("el vendedor ve su historial pero no puede exportar", async () => {
    renderizar("vendedor");

    expect(await screen.findByText(/Corte #8/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Exportar" })).not.toBeInTheDocument();
    expect(apiClient.obtenerCortes).toHaveBeenCalledWith(
      expect.objectContaining({ pagina: 1, tamanoPagina: 30 }),
      expect.any(String)
    );
  });

  it("abre la ficha de un corte con la foto, los movimientos y el aviso de ventas sin conexión enviadas después", async () => {
    renderizar("administrador");
    await screen.findByText(/Corte #8/);

    await userEvent.click(screen.getByRole("button", { name: "Ver el corte 8" }));

    const ficha = await screen.findByLabelText("Corte 8");
    expect(ficha).toHaveTextContent("Luis Gómez");
    expect(ficha).toHaveTextContent("Faltaron mil");
    expect(within(ficha).getByRole("note")).toHaveTextContent(/2.*40\.000/);
    expect(within(ficha).getByText(/Consignación al banco/)).toBeInTheDocument();
  });

  it("exporta los cortes del rango a CSV", async () => {
    const revocar = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL: vi.fn(() => "blob:cortes"), revokeObjectURL: revocar });
    const clic = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    apiClient.exportarCortes.mockResolvedValue({ contenido: new Blob(["x"]), nombre: "cortes_de_caja.csv" });
    renderizar("administrador");
    await screen.findByText(/Corte #8/);

    await userEvent.click(screen.getByRole("button", { name: "Exportar" }));

    await waitFor(() => expect(apiClient.exportarCortes).toHaveBeenCalledTimes(1));
    expect(apiClient.exportarCortes.mock.calls[0][0].desde).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    await waitFor(() => expect(clic).toHaveBeenCalled());
    expect(revocar).toHaveBeenCalledWith("blob:cortes");
    vi.unstubAllGlobals();
  });

  it("sin cortes dice que no hay", async () => {
    apiClient.obtenerCortes.mockResolvedValue([]);
    renderizar("administrador");

    expect(await screen.findByText("No hay cortes en este rango.")).toBeInTheDocument();
  });
});

describe("Caja — sin conexión", () => {
  it("avisa que necesita conexión y no deja operar la caja", async () => {
    apiClient.obtenerCajaActual.mockResolvedValue(ABIERTA);
    renderizar("vendedor", {}, { enLinea: false });

    expect(await screen.findByText(/La caja necesita conexión con el servidor/)).toBeInTheDocument();
    await screen.findByText(/Abierta por Ana Pérez/);
    expect(screen.getByRole("button", { name: "Cerrar caja" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Registrar retiro" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Actualizar" })).toBeDisabled();
  });

  it("muestra el error si el servidor no responde", async () => {
    apiClient.obtenerCajaActual.mockRejectedValue(new Error("Failed to fetch"));
    renderizar("vendedor");

    expect(await screen.findByRole("alert")).toHaveTextContent("Failed to fetch");
  });
});
