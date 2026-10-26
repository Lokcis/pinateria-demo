import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { BandejaNotificaciones } from "./bandeja-notificaciones";
import { ListaCompras } from "./lista-compras";
import { AuthProvider } from "../context/auth-context";
import * as apiClient from "../api/api-client";

vi.mock("../api/api-client", async () => {
  const modulo = await vi.importActual("../api/api-client");
  return {
    ...modulo,
    obtenerNotificaciones: vi.fn(),
    marcarNotificacionLeida: vi.fn(),
    marcarTodasLeidas: vi.fn(),
    obtenerListaCompras: vi.fn(),
  };
});

const BANDEJA = {
  no_leidas: 2,
  notificaciones: [
    {
      id: 3,
      tipo: "stock_bajo",
      mensaje: "Stock bajo: Globo metalizado tiene 0 unidades (minimo configurado: 5).",
      leida: false,
      creada_en: "2026-10-08T15:00:00Z",
      producto_id: 2,
      producto_nombre: "Globo metalizado",
    },
    {
      id: 2,
      tipo: "stock_bajo",
      mensaje: "Stock bajo: Velas tiene 1 unidades (minimo configurado: 5).",
      leida: false,
      creada_en: "2026-10-08T14:00:00Z",
      producto_id: 4,
      producto_nombre: "Velas",
    },
    {
      id: 1,
      tipo: "stock_bajo",
      mensaje: "Stock bajo: Confeti tiene 2 unidades (minimo configurado: 5).",
      leida: true,
      creada_en: "2026-10-07T14:00:00Z",
      producto_id: 5,
      producto_nombre: "Confeti",
    },
  ],
};

const LISTA = {
  productos: [
    { producto_id: 2, nombre: "Globo metalizado", categoria: "Globos", stock_actual: 0, stock_minimo: 5, faltante: 5 },
    { producto_id: 4, nombre: "Velas", categoria: "Velas", stock_actual: 5, stock_minimo: 5, faltante: 0 },
  ],
  generado_en: "2026-10-08T15:00:00Z",
};

/**
 * Renderiza un componente dentro del proveedor de autenticacion.
 *
 * @param {JSX.Element} componente
 */
function renderizar(componente) {
  return render(<AuthProvider>{componente}</AuthProvider>);
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  apiClient.obtenerNotificaciones.mockResolvedValue(BANDEJA);
  apiClient.obtenerListaCompras.mockResolvedValue(LISTA);
});

/** HU-10: "la bandeja muestre las notificaciones ... y el contador de no leidas"; marcar una o todas. */
describe("BandejaNotificaciones", () => {
  it("muestra el contador y las notificaciones en el orden recibido (la más reciente primero)", async () => {
    const alCambiarNoLeidas = vi.fn();
    renderizar(<BandejaNotificaciones alCambiarNoLeidas={alCambiarNoLeidas} />);

    expect(await screen.findByText("· 2 sin leer")).toBeInTheDocument();
    const mensajes = screen.getAllByRole("listitem").map((item) => item.textContent);
    expect(mensajes[0]).toContain("Globo metalizado");
    expect(mensajes[2]).toContain("Confeti");
    // La ya leida no tiene boton para marcar.
    expect(screen.getAllByRole("button", { name: /^Marcar como leída/ })).toHaveLength(2);
    expect(alCambiarNoLeidas).toHaveBeenCalledWith(2);
  });

  it("marcar una la envía al backend y recarga el contador", async () => {
    const usuario = userEvent.setup();
    const alCambiarNoLeidas = vi.fn();
    apiClient.marcarNotificacionLeida.mockResolvedValue({});
    renderizar(<BandejaNotificaciones alCambiarNoLeidas={alCambiarNoLeidas} />);
    await screen.findByText("· 2 sin leer");

    apiClient.obtenerNotificaciones.mockResolvedValue({
      no_leidas: 1,
      notificaciones: BANDEJA.notificaciones.map((n) => (n.id === 3 ? { ...n, leida: true } : n)),
    });
    await usuario.click(screen.getByRole("button", { name: /Marcar como leída: Stock bajo: Globo metalizado/ }));

    expect(apiClient.marcarNotificacionLeida).toHaveBeenCalledWith(3, null);
    expect(await screen.findByText("· 1 sin leer")).toBeInTheDocument();
    expect(alCambiarNoLeidas).toHaveBeenLastCalledWith(1);
  });

  it("marcar todas deja el contador en cero y desactiva el botón", async () => {
    const usuario = userEvent.setup();
    apiClient.marcarTodasLeidas.mockResolvedValue({ marcadas: 2 });
    renderizar(<BandejaNotificaciones />);
    await screen.findByText("· 2 sin leer");

    apiClient.obtenerNotificaciones.mockResolvedValue({
      no_leidas: 0,
      notificaciones: BANDEJA.notificaciones.map((n) => ({ ...n, leida: true })),
    });
    await usuario.click(screen.getByRole("button", { name: "Marcar todas como leídas" }));

    expect(apiClient.marcarTodasLeidas).toHaveBeenCalledTimes(1);
    expect(await screen.findByText("· 0 sin leer")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Marcar todas como leídas" })).toBeDisabled();
  });

  it("sin notificaciones lo dice claramente", async () => {
    apiClient.obtenerNotificaciones.mockResolvedValue({ no_leidas: 0, notificaciones: [] });
    renderizar(<BandejaNotificaciones />);

    expect(await screen.findByText("No hay notificaciones.")).toBeInTheDocument();
  });
});

/** HU-10: lista de compras con la cantidad faltante; WhatsApp con la lista escrita o copiarla como texto. */
describe("ListaCompras", () => {
  it("muestra cada producto con lo que hay, el mínimo y lo que falta", async () => {
    renderizar(<ListaCompras />);

    const filaGlobo = (await screen.findByText("Globo metalizado")).closest("tr");
    expect(within(filaGlobo).getAllByRole("cell").map((c) => c.textContent)).toEqual([
      "Globo metalizado · Globos",
      "0",
      "5",
      "5",
    ]);
    const filaVelas = screen.getByText("Velas", { selector: "td" }).closest("tr");
    expect(within(filaVelas).getAllByRole("cell")[3]).toHaveTextContent("en el mínimo");
  });

  it("el botón de WhatsApp abre wa.me con la lista escrita, en una pestaña nueva", async () => {
    renderizar(<ListaCompras />);

    const enlace = await screen.findByRole("link", { name: "Enviar por WhatsApp" });
    const href = enlace.getAttribute("href");
    expect(href.startsWith("https://wa.me/?text=")).toBe(true);
    const mensaje = decodeURIComponent(href.slice("https://wa.me/?text=".length));
    expect(mensaje).toContain("• Globo metalizado: faltan 5 (hay 0, mínimo 5)");
    expect(mensaje).toContain("• Velas: en el mínimo (hay 5, mínimo 5)");
    expect(enlace).toHaveAttribute("target", "_blank");
    expect(enlace).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("copiar texto pone el mensaje en el portapapeles", async () => {
    const usuario = userEvent.setup();
    const escribir = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue();
    renderizar(<ListaCompras />);

    await usuario.click(await screen.findByRole("button", { name: "Copiar texto" }));

    expect(escribir).toHaveBeenCalledWith(expect.stringContaining("Lista de compras – Piñatería Demo"));
    expect(screen.getByRole("status")).toHaveTextContent("Lista copiada");
  });

  it("si el navegador no deja copiar, muestra el texto para copiarlo a mano", async () => {
    const usuario = userEvent.setup();
    vi.spyOn(navigator.clipboard, "writeText").mockRejectedValue(new Error("sin permiso"));
    renderizar(<ListaCompras />);

    await usuario.click(await screen.findByRole("button", { name: "Copiar texto" }));

    expect(screen.getByRole("textbox", { name: "Texto de la lista de compras" }).value).toContain(
      "Globo metalizado"
    );
  });

  it("si la lista es muy larga no ofrece WhatsApp, solo copiar", async () => {
    apiClient.obtenerListaCompras.mockResolvedValue({
      productos: Array.from({ length: 80 }, (_, i) => ({
        producto_id: i + 1,
        nombre: `Producto con nombre largo ${i}`,
        categoria: "Varios",
        stock_actual: 1,
        stock_minimo: 10,
        faltante: 9,
      })),
      generado_en: "2026-10-08T15:00:00Z",
    });
    renderizar(<ListaCompras />);

    expect(await screen.findByText(/muy larga para abrirla en WhatsApp/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Enviar por WhatsApp" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copiar texto" })).toBeInTheDocument();
  });

  it("sin productos en stock bajo no muestra botones de exportar", async () => {
    apiClient.obtenerListaCompras.mockResolvedValue({ productos: [], generado_en: "2026-10-08T15:00:00Z" });
    renderizar(<ListaCompras />);

    expect(await screen.findByText(/No hay productos en stock bajo/)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("button", { name: "Copiar texto" })).not.toBeInTheDocument());
  });
});
