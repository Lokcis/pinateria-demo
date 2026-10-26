import { useState } from "react";
import { CartProvider, useCart } from "../context/cart-context";
import { useAuth } from "../context/auth-context";
import { SinConexionProvider, useSinConexion } from "../context/sin-conexion-context";
import { usePantallaAncha } from "../hooks/use-pantalla-ancha";
import { BusquedaHibrida } from "../components/busqueda-hibrida";
import { Carrito } from "../components/carrito";
import { ConfirmacionPago } from "../components/confirmacion-pago";
import { HistorialDia } from "../components/historial-dia";
import { Caja } from "../components/caja";
import { Compras } from "../components/compras";
import { Gastos } from "../components/gastos";
import { useConfirmar } from "../components/dialogo-confirmacion";
import { EstadoSincronizacion } from "../components/estado-sincronizacion";
import { Inventario } from "../components/inventario";
import { Encabezado } from "../components/encabezado";
import { Navegacion } from "../components/navegacion";
import { Proveedores } from "../components/proveedores";
import { Categorias } from "../components/categorias";
import { Usuarios } from "../components/usuarios";
import { StockBajo } from "../components/stock-bajo";
import { Descuentos } from "../components/descuentos";
import { PanelGanancias } from "../components/panel-ganancias";
import { Clientes } from "../components/clientes";
import { SolicitudesTitular } from "../components/solicitudes-titular";
import { formatearMoneda } from "../utils/formato";

const ROLES_CON_ACCESO_AL_POS = new Set(["vendedor", "administrador"]);

/**
 * Secciones del punto de venta, agrupadas por tema. Las de Fases 3 y 5 y del Adendo v2 (B1: HU-10; A1: HU-06;
 * A2: HU-07; A3: HU-09) marcadas `soloAdministrador` solo las ve el administrador (HU-04, RF-021); el backend
 * ademas responde 403. "Gastos" y "Caja" (Adendo v3) las ven el administrador y el vendedor; el servidor limita al vendedor
 * a sus propios gastos y a los cortes que abrio o cerro. `principal` indica cuales van directo en la barra inferior del celular (el vendedor
 * tambien lleva Inventario; el resto queda en "Mas").
 */
const VISTAS = [
  { id: "venta", etiqueta: "Nueva venta", corta: "Vender", grupo: "Ventas", principal: true, icono: "venta" },
  { id: "historial", etiqueta: "Ventas de hoy", corta: "Hoy", grupo: "Ventas", principal: true, icono: "historial" },
  { id: "clientes", etiqueta: "Clientes", grupo: "Clientes", principal: true, icono: "clientes" },
  { id: "datos-personales", etiqueta: "Datos personales", grupo: "Clientes", soloAdministrador: true },
  { id: "inventario", etiqueta: "Inventario", grupo: "Inventario y compras", icono: "inventario" },
  { id: "stock-bajo", etiqueta: "Stock bajo", grupo: "Inventario y compras", soloAdministrador: true },
  { id: "compras", etiqueta: "Compras", grupo: "Inventario y compras", soloAdministrador: true },
  { id: "proveedores", etiqueta: "Proveedores", grupo: "Inventario y compras", soloAdministrador: true },
  { id: "categorias", etiqueta: "Categorías", grupo: "Inventario y compras", soloAdministrador: true },
  { id: "gastos", etiqueta: "Gastos", grupo: "Gastos y caja" },
  { id: "caja", etiqueta: "Caja", grupo: "Gastos y caja" },
  { id: "descuentos", etiqueta: "Descuentos", grupo: "Negocio", soloAdministrador: true },
  { id: "ganancias", etiqueta: "Ganancias", grupo: "Negocio", soloAdministrador: true },
  { id: "usuarios", etiqueta: "Usuarios", grupo: "Negocio", soloAdministrador: true },
];

/**
 * Secciones que ve un rol, con la marca `principal` ajustada: el vendedor lleva Inventario en la barra del celular.
 *
 * @param {boolean} esAdministrador
 * @returns {Array<object>}
 */
function vistasDelRol(esAdministrador) {
  return VISTAS.filter((vista) => esAdministrador || !vista.soloAdministrador).map((vista) =>
    vista.id === "inventario" && !esAdministrador ? { ...vista, principal: true } : vista
  );
}

/**
 * Panel con el resumen de la venta en curso. En pantallas anchas es una columna fija a la derecha; en celular
 * se abre a pantalla completa desde la barra de venta (y se cierra para seguir agregando productos).
 *
 * @param {{abierto: boolean, alCerrar: () => void}} props `abierto` solo importa en celular.
 * @returns {JSX.Element}
 */
function PanelVenta({ abierto, alCerrar }) {
  const { items } = useCart();
  const cantidad = items.reduce((suma, item) => suma + item.cantidad, 0);

  return (
    <aside
      aria-label="Venta actual"
      className={`${
        abierto ? "fixed inset-0 z-[60] block overflow-y-auto bg-papel p-4 pb-8" : "hidden"
      } xl:sticky xl:top-4 xl:z-auto xl:block xl:self-start xl:overflow-visible xl:bg-transparent xl:p-0`}
    >
      <button
        type="button"
        onClick={alCerrar}
        className="mb-3 rounded-xl px-1 py-1 text-sm font-bold text-fucsia-osc xl:hidden"
      >
        ← Seguir agregando
      </button>
      <div className="rounded-3xl border border-tinta/10 bg-white p-4 shadow-sm sm:p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-display text-xl font-extrabold">Venta actual</h2>
          {cantidad > 0 && (
            <span className="rounded-full bg-fucsia px-2.5 py-0.5 text-xs font-bold text-white">
              {cantidad} {cantidad === 1 ? "artículo" : "artículos"}
            </span>
          )}
        </div>
        <Carrito />
        <div className="mt-2">
          <ConfirmacionPago />
        </div>
      </div>
    </aside>
  );
}

/**
 * Barra fija del celular con el total de la venta en curso; al tocarla se abre el panel de la venta.
 * Solo aparece cuando hay productos en el carrito.
 *
 * @param {{alAbrir: () => void}} props
 * @returns {JSX.Element | null}
 */
export function BarraVenta({ alAbrir }) {
  const { items, total } = useCart();
  const cantidad = items.reduce((suma, item) => suma + item.cantidad, 0);
  if (cantidad === 0) return null;

  return (
    <button
      type="button"
      onClick={alAbrir}
      className="sombra-dura fixed inset-x-3 bottom-[calc(4.5rem+env(safe-area-inset-bottom))] z-30 flex items-center justify-between rounded-2xl border-2 border-tinta bg-fucsia px-4 py-3 text-left text-white xl:hidden"
    >
      <span className="text-sm font-bold">
        {cantidad} {cantidad === 1 ? "artículo" : "artículos"} · Ver venta
      </span>
      <span className="font-display text-lg font-extrabold tabular-nums">{formatearMoneda(total)}</span>
    </button>
  );
}

/**
 * Vista "Nueva venta": busqueda de productos y panel de la venta.
 *
 * @returns {JSX.Element}
 */
function VistaVenta() {
  const [panelAbierto, setPanelAbierto] = useState(false);

  return (
    <main className="pos-main grid gap-5 py-4 xl:grid-cols-[minmax(0,1fr)_24rem] xl:py-0">
      <BusquedaHibrida />
      <PanelVenta abierto={panelAbierto} alCerrar={() => setPanelAbierto(false)} />
      <BarraVenta alAbrir={() => setPanelAbierto(true)} />
    </main>
  );
}

/**
 * Pagina principal del punto de venta: menu de secciones, busqueda + carrito + confirmacion de pago.
 *
 * Los roles con acceso se montan dentro del `SinConexionProvider` (Fase 9): cola local de ventas, copia del
 * catalogo y envio automatico al volver la red. El propietario no usa el POS y no lo necesita.
 *
 * @returns {JSX.Element}
 */
export function PosPage() {
  const { usuarioActual, cerrarSesion } = useAuth();
  const rolActual = usuarioActual?.rol;

  if (!ROLES_CON_ACCESO_AL_POS.has(rolActual)) {
    return (
      <div className="pos-page pos-sin-acceso grid min-h-screen place-items-center px-4">
        <div className="max-w-md rounded-3xl border border-tinta/10 bg-white p-8 text-center shadow-sm">
          <h1 className="font-display text-2xl font-extrabold">Sin acceso al punto de venta</h1>
          <p className="mt-3 text-tinta/70">
            Tu rol ({rolActual || "desconocido"}) no tiene acceso al punto de venta. El rol{" "}
            <strong>propietario</strong> entra al Dashboard de solo lectura.
          </p>
          <button
            type="button"
            onClick={cerrarSesion}
            className="mt-6 rounded-xl border-2 border-tinta px-5 py-2.5 font-semibold transition hover:bg-papel"
          >
            Cerrar sesion
          </button>
        </div>
      </div>
    );
  }

  return (
    <SinConexionProvider>
      <PosConSesion />
    </SinConexionProvider>
  );
}

/**
 * El POS para un usuario con acceso: menu de secciones y la vista elegida.
 *
 * Envuelve todo en su propio `CartProvider` para que el carrito se
 * reinicie limpio cada vez que se monta la pagina (ej. al volver a
 * iniciar sesion).
 *
 * @returns {JSX.Element}
 */
function PosConSesion() {
  const { usuarioActual, cerrarSesion } = useAuth();
  const sinConexion = useSinConexion();
  const { confirmar, dialogo } = useConfirmar();
  const ancha = usePantallaAncha();
  const [vista, setVista] = useState("venta");
  const rolActual = usuarioActual?.rol;
  const esAdministrador = rolActual === "administrador";
  const vistas = vistasDelRol(esAdministrador);

  /**
   * Cierra la sesion, avisando antes si es mala idea: sin conexion no se puede volver a entrar, y las ventas
   * guardadas sin enviar se conservan pero solo se envian al iniciar sesion con conexion.
   *
   * @returns {Promise<void>}
   */
  async function salir() {
    const sinRed = !sinConexion.enLinea;
    const guardadas = sinConexion.pendientes + sinConexion.conflictos;
    if (sinRed || guardadas > 0) {
      const seguro = await confirmar({
        titulo: "¿Cerrar sesión?",
        mensaje: sinRed
          ? "No hay conexión con el servidor: para volver a entrar necesitas que vuelva internet y no podrás vender mientras tanto."
          : `Hay ${guardadas} ${guardadas === 1 ? "venta guardada" : "ventas guardadas"} sin conexión que no se han enviado.`,
        aviso:
          guardadas > 0
            ? "No se pierden: se quedan en este equipo y se envían cuando inicies sesión con conexión."
            : undefined,
        textoConfirmar: "Cerrar sesión",
        peligro: sinRed,
      });
      if (!seguro) return;
    }
    cerrarSesion();
  }

  return (
    <CartProvider>
      <div className="pos-page min-h-screen">
        <Encabezado usuario={usuarioActual} alCerrarSesion={salir} />
        {dialogo}

        <EstadoSincronizacion />

        <div className="mx-auto flex max-w-[90rem] items-start gap-6 px-4 sm:px-6 xl:py-6">
          {ancha && (
            <div className="w-52 shrink-0">
              <Navegacion vistas={vistas} vista={vista} alCambiar={setVista} ancha />
            </div>
          )}

          <div className={`min-w-0 flex-1 ${ancha ? "" : "pb-28"}`}>
            {vista === "venta" && <VistaVenta />}
            {vista === "historial" && (
              <main className="mx-auto max-w-4xl py-4 xl:py-0">
                <HistorialDia />
              </main>
            )}
            {vista === "clientes" && (
              <main className="mx-auto max-w-4xl py-4 xl:py-0">
                <Clientes />
              </main>
            )}
            {vista === "inventario" && (
              <main className="mx-auto max-w-4xl py-4 xl:py-0">
                <Inventario />
              </main>
            )}
            {vista === "gastos" && (
              <main className="mx-auto max-w-4xl py-4 xl:py-0">
                <Gastos alIrACompras={() => setVista("compras")} />
              </main>
            )}
            {vista === "caja" && (
              <main className="mx-auto max-w-4xl py-4 xl:py-0">
                <Caja />
              </main>
            )}
            {esAdministrador && vista === "stock-bajo" && (
              <main className="mx-auto max-w-4xl py-4 xl:py-0">
                <StockBajo />
              </main>
            )}
            {esAdministrador && vista === "compras" && (
              <main className="mx-auto max-w-4xl py-4 xl:py-0">
                <Compras />
              </main>
            )}
            {esAdministrador && vista === "proveedores" && (
              <main className="mx-auto max-w-4xl py-4 xl:py-0">
                <Proveedores />
              </main>
            )}
            {esAdministrador && vista === "categorias" && (
              <main className="mx-auto max-w-4xl py-4 xl:py-0">
                <Categorias />
              </main>
            )}
            {esAdministrador && vista === "descuentos" && (
              <main className="mx-auto max-w-4xl py-4 xl:py-0">
                <Descuentos />
              </main>
            )}
            {esAdministrador && vista === "datos-personales" && (
              <main className="mx-auto max-w-4xl py-4 xl:py-0">
                <SolicitudesTitular />
              </main>
            )}
            {esAdministrador && vista === "ganancias" && (
              <main className="mx-auto max-w-5xl py-4 xl:py-0">
                <PanelGanancias puedeEditarCostos />
              </main>
            )}
            {esAdministrador && vista === "usuarios" && (
              <main className="mx-auto max-w-4xl py-4 xl:py-0">
                <Usuarios />
              </main>
            )}
          </div>
        </div>

        {!ancha && <Navegacion vistas={vistas} vista={vista} alCambiar={setVista} ancha={false} />}
      </div>
    </CartProvider>
  );
}
