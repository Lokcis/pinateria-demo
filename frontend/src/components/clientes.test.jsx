import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Clientes } from "./clientes";
import { AuthProvider } from "../context/auth-context";
import * as apiClient from "../api/api-client";
import { POLITICA_PRUEBA } from "../utils/politica-prueba";

vi.mock("../api/api-client", async () => {
  const modulo = await vi.importActual("../api/api-client");
  return {
    ...modulo,
    buscarClientes: vi.fn(),
    crearCliente: vi.fn(),
    editarCliente: vi.fn(),
    obtenerFichaCliente: vi.fn(),
    guardarDescuentoCliente: vi.fn(),
    crearSolicitud: vi.fn(),
    obtenerPoliticaDatos: vi.fn(),
  };
});

const CLIENTE = {
  id: 1,
  nombre: "María Pérez",
  documento: "1010202030",
  telefono: "3001234567",
  email: "maria@example.com",
  descuento_tipo: null,
  descuento_valor: null,
  activo: true,
  utilizable: true,
  autorizacion_fecha: "2026-10-12T15:00:00Z",
  autorizacion_medio: "verbal",
  autorizacion_version: "borrador",
  origen_registro: "empleado",
  autorizacion_revocada_en: null,
  anonimizado_en: null,
  creado_en: "2026-10-12T15:00:00Z",
  numero_ventas: 2,
  total_comprado: "40000.00",
  ultima_compra: "2026-10-12T16:00:00Z",
};

const FICHA = {
  ...CLIENTE,
  autorizacion_recogida_por: "Laura Gómez",
  ventas: [
    {
      id: 31,
      fecha: "2026-10-12T16:00:00Z",
      total: "10000.00",
      vendedor: "Laura Gómez",
      pagos: [{ metodo_pago: "transferencia", plataforma: "nequi", monto: "10000.00", monto_recibido: null, vueltas: "0.00" }],
    },
  ],
};

function renderizar(rol = "vendedor") {
  localStorage.setItem("mm_pos_token", `c.${btoa(JSON.stringify({ sub: "1", rol }))}.f`);
  return render(
    <AuthProvider>
      <Clientes />
    </AuthProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  apiClient.buscarClientes.mockResolvedValue([CLIENTE]);
  apiClient.obtenerFichaCliente.mockResolvedValue(FICHA);
  apiClient.obtenerPoliticaDatos.mockResolvedValue(POLITICA_PRUEBA);
});

describe("Clientes — listado y búsqueda (HU-07)", () => {
  it("lista los clientes con su total comprado", async () => {
    renderizar();

    expect(await screen.findByText("María Pérez")).toBeInTheDocument();
    expect(screen.getByText(/1010202030 · 3001234567/)).toBeInTheDocument();
    expect(screen.getByText(/2 ventas/)).toHaveTextContent(/40\.000/);
  });

  it("busca por texto y manda los filtros por compras al servidor", async () => {
    const usuario = userEvent.setup();
    renderizar();
    await screen.findByText("María Pérez");

    await usuario.type(screen.getByRole("searchbox", { name: "Buscar cliente" }), "mar");
    await waitFor(() => expect(apiClient.buscarClientes).toHaveBeenLastCalledWith(expect.objectContaining({ q: "mar" }), expect.any(String)));

    await usuario.click(screen.getByRole("button", { name: /Filtrar por compras/ }));
    const filtros = screen.getByLabelText("Filtros por compras");
    await usuario.type(within(filtros).getByLabelText("Total mínimo ($)"), "50000");
    await usuario.type(within(filtros).getByLabelText("Compras desde"), "2026-10-01");

    await waitFor(() =>
      expect(apiClient.buscarClientes).toHaveBeenLastCalledWith(
        expect.objectContaining({ q: "mar", totalMin: "50000", desde: "2026-10-01" }),
        expect.any(String)
      )
    );
  });

  it("marca los clientes desactivados, con autorización revocada o anonimizados", async () => {
    apiClient.buscarClientes.mockResolvedValue([
      { ...CLIENTE, id: 2, nombre: "Ana", activo: false, utilizable: false },
      { ...CLIENTE, id: 3, nombre: "Beto", autorizacion_revocada_en: "2026-10-12T17:00:00Z", utilizable: false },
      { ...CLIENTE, id: 4, nombre: "Cliente anonimizado", activo: false, anonimizado_en: "2026-10-12T17:00:00Z" },
    ]);
    renderizar();

    expect(await screen.findByText("Desactivado")).toBeInTheDocument();
    expect(screen.getByText("Autorización revocada")).toBeInTheDocument();
    expect(screen.getByText("Anonimizado")).toBeInTheDocument();
  });

  it("muestra el error si el listado falla", async () => {
    apiClient.buscarClientes.mockRejectedValue(new Error("Sin conexión"));
    renderizar();

    expect(await screen.findByRole("alert")).toHaveTextContent("Sin conexión");
  });
});

describe("Clientes — registro (HU-07)", () => {
  it("no deja guardar sin la autorización y manda el medio elegido; abre la ficha del nuevo cliente", async () => {
    const usuario = userEvent.setup();
    apiClient.crearCliente.mockResolvedValue(CLIENTE);
    renderizar();
    await screen.findByText("María Pérez");

    await usuario.click(screen.getByRole("button", { name: "Nuevo cliente" }));
    expect(await screen.findByText(/Tienda de Prueba \(NIT 900\) usará tus datos/)).toBeInTheDocument();
    expect(screen.getByText(/Política de Tratamiento de Datos \(versión 1\.0\)/)).toBeInTheDocument();
    await usuario.type(screen.getByLabelText("Nombre"), "Lucía Mora");
    await usuario.type(screen.getByLabelText("Teléfono"), "30a0-111");
    expect(screen.getByLabelText("Teléfono")).toHaveValue("300111"); // solo dígitos
    expect(screen.getByRole("button", { name: "Guardar" })).toBeDisabled();

    await usuario.click(screen.getByRole("checkbox", { name: /autoriza el tratamiento/ }));
    await usuario.type(screen.getByLabelText("Teléfono"), "2222");
    await usuario.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() => expect(apiClient.crearCliente).toHaveBeenCalledTimes(1));
    expect(apiClient.crearCliente.mock.calls[0][0]).toEqual({
      nombre: "Lucía Mora",
      documento: null,
      telefono: "3001112222",
      email: null,
      autorizacion_aceptada: true,
      autorizacion_medio: "verbal",
      acepta_publicidad: false, // la casilla de promociones es aparte y viene desmarcada
    });
    expect(await screen.findByRole("heading", { name: "María Pérez" })).toBeInTheDocument(); // ficha del creado
  });

  it("rechaza un teléfono corto sin llamar al servidor", async () => {
    const usuario = userEvent.setup();
    renderizar();
    await screen.findByText("María Pérez");

    await usuario.click(screen.getByRole("button", { name: "Nuevo cliente" }));
    await usuario.type(screen.getByLabelText("Nombre"), "Lucía");
    await usuario.type(screen.getByLabelText("Teléfono"), "12345");
    await usuario.click(screen.getByRole("checkbox", { name: /autoriza el tratamiento/ }));
    await usuario.click(screen.getByRole("button", { name: "Guardar" }));

    expect(screen.getByRole("alert")).toHaveTextContent("al menos 7 dígitos");
    expect(apiClient.crearCliente).not.toHaveBeenCalled();
  });
});

describe("Clientes — ficha", () => {
  async function abrirFicha(usuario, rol) {
    renderizar(rol);
    await usuario.click(await screen.findByRole("button", { name: "Ver ficha" }));
    await screen.findByRole("heading", { name: "María Pérez" });
  }

  it("muestra la evidencia de la autorización, el total comprado y el historial con vendedor y pagos", async () => {
    const usuario = userEvent.setup();
    await abrirFicha(usuario, "vendedor");

    expect(screen.getByText(/Autorización de datos:.*medio verbal.*política versión borrador/)).toBeInTheDocument();
    expect(screen.getByText(/la recogió Laura Gómez/)).toBeInTheDocument();
    expect(screen.getByText("Total comprado").parentElement).toHaveTextContent(/40\.000/);
    const historial = screen.getByLabelText("Historial de ventas");
    expect(within(historial).getByText(/Venta #31/)).toBeInTheDocument();
    expect(within(historial).getByText(/Atendió: Laura Gómez · Transferencia \(Nequi\)/)).toBeInTheDocument();
  });

  it("el vendedor no ve el descuento propio ni las solicitudes del titular", async () => {
    const usuario = userEvent.setup();
    await abrirFicha(usuario, "vendedor");

    expect(screen.queryByLabelText("Descuento propio")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Solicitud del titular")).not.toBeInTheDocument();
  });

  it("el administrador asigna el descuento propio", async () => {
    const usuario = userEvent.setup();
    apiClient.guardarDescuentoCliente.mockResolvedValue({ ...CLIENTE, descuento_tipo: "porcentaje", descuento_valor: "10.00" });
    await abrirFicha(usuario, "administrador");

    await usuario.type(screen.getByLabelText("Valor del descuento del cliente"), "10");
    await usuario.click(screen.getByRole("button", { name: "Guardar descuento" }));

    await waitFor(() =>
      expect(apiClient.guardarDescuentoCliente).toHaveBeenCalledWith(1, { tipo: "porcentaje", valor: "10" }, expect.any(String))
    );
  });

  it("no guarda un descuento vacío o en cero", async () => {
    const usuario = userEvent.setup();
    await abrirFicha(usuario, "administrador");

    await usuario.click(screen.getByRole("button", { name: "Guardar descuento" }));

    expect(screen.getByRole("alert")).toHaveTextContent("mayor que cero");
    expect(apiClient.guardarDescuentoCliente).not.toHaveBeenCalled();
  });

  it("el administrador registra una solicitud del titular y ve la fecha límite", async () => {
    const usuario = userEvent.setup();
    apiClient.crearSolicitud.mockResolvedValue({ id: 5, fecha_limite: "2026-11-02" });
    await abrirFicha(usuario, "administrador");

    const formulario = screen.getByLabelText("Solicitud del titular");
    await usuario.type(within(formulario).getByLabelText("Detalle de la solicitud"), "Quiere borrar sus datos");
    await usuario.click(within(formulario).getByRole("button", { name: "Registrar solicitud" }));

    await waitFor(() =>
      expect(apiClient.crearSolicitud).toHaveBeenCalledWith(
        { cliente_id: 1, tipo: "consulta", descripcion: "Quiere borrar sus datos" },
        expect.any(String)
      )
    );
    expect(await screen.findByText(/Fecha límite de respuesta: 2026-11-02/)).toBeInTheDocument();
  });

  it("desactiva al cliente", async () => {
    const usuario = userEvent.setup();
    apiClient.editarCliente.mockResolvedValue({ ...CLIENTE, activo: false });
    await abrirFicha(usuario, "vendedor");

    await usuario.click(screen.getByRole("button", { name: "Desactivar" }));

    await waitFor(() => expect(apiClient.editarCliente).toHaveBeenCalledWith(1, { activo: false }, expect.any(String)));
  });

  it("un cliente anonimizado ya no se puede editar ni tiene descuento ni solicitudes", async () => {
    const usuario = userEvent.setup();
    apiClient.obtenerFichaCliente.mockResolvedValue({
      ...FICHA,
      nombre: "Cliente anonimizado",
      documento: null,
      telefono: null,
      email: null,
      activo: false,
      anonimizado_en: "2026-10-12T18:00:00Z",
    });
    renderizar("administrador");
    await usuario.click(await screen.findByRole("button", { name: "Ver ficha" }));
    await screen.findByRole("heading", { name: "Cliente anonimizado" });

    expect(screen.queryByRole("button", { name: "Editar" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Descuento propio")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Historial de ventas")).toHaveTextContent("Venta #31"); // las ventas se conservan
  });
});

describe("Clientes — promociones y aviso (autorización aparte)", () => {
  it("la casilla de promociones es distinta de la autorización, viene desmarcada y se manda si se marca", async () => {
    const usuario = userEvent.setup();
    apiClient.crearCliente.mockResolvedValue(CLIENTE);
    renderizar();
    await screen.findByText("María Pérez");

    await usuario.click(screen.getByRole("button", { name: "Nuevo cliente" }));
    const promociones = await screen.findByRole("checkbox", { name: /promociones y novedades/ });
    const autorizacion = screen.getByRole("checkbox", { name: /autoriza el tratamiento/ });
    expect(promociones).not.toBeChecked();
    expect(promociones).not.toBe(autorizacion);

    await usuario.type(screen.getByLabelText("Nombre"), "Lucía Mora");
    await usuario.click(promociones);
    // Marcar solo las promociones no basta: la autorización de datos sigue siendo obligatoria.
    expect(screen.getByRole("button", { name: "Guardar" })).toBeDisabled();
    await usuario.click(autorizacion);
    await usuario.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() => expect(apiClient.crearCliente).toHaveBeenCalledTimes(1));
    expect(apiClient.crearCliente.mock.calls[0][0]).toMatchObject({ autorizacion_aceptada: true, acepta_publicidad: true });
  });

  it("muestra la política completa desplegable con sus secciones", async () => {
    const usuario = userEvent.setup();
    renderizar();
    await screen.findByText("María Pérez");

    await usuario.click(screen.getByRole("button", { name: "Nuevo cliente" }));
    expect(await screen.findByText("7. Derechos del titular")).toBeInTheDocument();
    expect(screen.getByText("Suprimirlos.")).toBeInTheDocument();
  });

  it("avisa cuando faltan datos del negocio y la política queda como borrador", async () => {
    const usuario = userEvent.setup();
    apiClient.obtenerPoliticaDatos.mockResolvedValue({
      ...POLITICA_PRUEBA,
      version: "borrador",
      datos_completos: false,
      faltantes: ["Correo para solicitudes de datos"],
    });
    renderizar();
    await screen.findByText("María Pérez");

    await usuario.click(screen.getByRole("button", { name: "Nuevo cliente" }));

    expect(await screen.findByRole("note")).toHaveTextContent(/Correo para solicitudes de datos.*borrador/);
  });

  it("el filtro de promociones pide solo a quienes aceptaron", async () => {
    const usuario = userEvent.setup();
    renderizar();
    await screen.findByText("María Pérez");

    await usuario.click(screen.getByRole("button", { name: /Filtrar por compras/ }));
    await usuario.click(screen.getByRole("checkbox", { name: /aceptaron recibir promociones/ }));

    await waitFor(() =>
      expect(apiClient.buscarClientes).toHaveBeenLastCalledWith(
        expect.objectContaining({ aceptaPublicidad: true }),
        expect.any(String)
      )
    );
  });

  it("marca a quienes aceptan promociones y muestra su estado en la ficha", async () => {
    const usuario = userEvent.setup();
    apiClient.buscarClientes.mockResolvedValue([{ ...CLIENTE, acepta_publicidad: true, publicidad_fecha: "2026-10-12T15:00:00Z" }]);
    apiClient.obtenerFichaCliente.mockResolvedValue({ ...FICHA, acepta_publicidad: true, publicidad_fecha: "2026-10-12T15:00:00Z", origen_registro: "autoregistro" });
    renderizar();

    expect(await screen.findByText("Acepta promociones")).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Ver ficha" }));
    expect(await screen.findByText(/Promociones: autorizó el/)).toBeInTheDocument();
    expect(screen.getByText(/se registró solo por el enlace/)).toBeInTheDocument();
  });

  it("al editar, cambiar solo las promociones manda únicamente ese cambio adicional", async () => {
    const usuario = userEvent.setup();
    apiClient.editarCliente.mockResolvedValue({ ...CLIENTE, acepta_publicidad: true });
    renderizar();
    await usuario.click(await screen.findByRole("button", { name: "Ver ficha" }));
    await screen.findByRole("heading", { name: "María Pérez" });

    await usuario.click(screen.getByRole("button", { name: "Editar" }));
    await usuario.click(screen.getByRole("checkbox", { name: /promociones y novedades/ }));
    await usuario.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() => expect(apiClient.editarCliente).toHaveBeenCalledTimes(1));
    expect(apiClient.editarCliente.mock.calls[0][1]).toMatchObject({ acepta_publicidad: true });
  });
});

