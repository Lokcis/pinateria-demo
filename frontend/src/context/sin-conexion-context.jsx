import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { obtenerConfiguracionDescuentos, obtenerSalud, obtenerVendedores } from "../api/api-client";
import { useAuth } from "./auth-context";
import { almacenDisponible } from "../offline/almacen";
import {
  buscarEnCatalogoLocal,
  descargarCatalogo,
  guardarEnCache,
  infoCatalogoLocal,
  leerDeCache,
} from "../offline/catalogo-local";
import {
  ESTADO_CONFLICTO,
  ESTADO_PENDIENTE,
  eliminarVenta,
  encolarVenta,
  listarVentas,
  reabrirVenta,
  siguienteNumeroLocal,
} from "../offline/cola-ventas";
import { sincronizarPendientes } from "../offline/sincronizador";
import { esErrorDeConexion } from "../utils/conexion";

/** Cada cuanto se comprueba el servidor mientras no hay conexion o quedan ventas por enviar. */
const INTERVALO_COMPROBACION_MS = 20000;
/** Cada cuanto se refresca la copia del catalogo mientras hay conexion. */
const INTERVALO_CATALOGO_MS = 10 * 60 * 1000;

export const SinConexionContext = createContext(null);

/** Valor cuando no hay proveedor (pruebas de componentes sueltos): el modo sin conexion queda apagado. */
export const VALOR_SIN_CONEXION_INACTIVO = {
  activo: false,
  disponible: false,
  enLinea: true,
  ventas: [],
  pendientes: 0,
  misPendientes: 0,
  conflictos: 0,
  pendientesDeOtros: 0,
  sincronizando: false,
  sesionVencida: false,
  ultimoEnvio: null,
  catalogo: null,
  sincronizar: async () => {},
  registrarVenta: async () => {},
  reintentarVenta: async () => {},
  descartarVenta: async () => {},
  reportarFalloDeConexion: () => {},
  siguienteNumero: async () => "SC-0001",
  buscarLocal: async () => [],
  guardarEnCache: async () => {},
  leerDeCache: async () => null,
  descartarAviso: () => {},
};

/**
 * Provee el modo sin conexion del POS (Fase 9): estado real de la conexion, cola local de ventas, copia del
 * catalogo y envio automatico al volver la red.
 *
 * `navigator.onLine` solo dice si hay red, no si el servidor responde (el tunel puede estar caido), asi que
 * mientras no hay conexion o quedan ventas por enviar se consulta `/health` cada pocos segundos.
 *
 * @param {{children: React.ReactNode}} props
 * @returns {JSX.Element}
 */
export function SinConexionProvider({ children }) {
  const { token, usuarioActual } = useAuth();
  const usuarioId = String(usuarioActual?.sub ?? "");
  const esAdministrador = usuarioActual?.rol === "administrador";

  const [enLinea, setEnLinea] = useState(() => (typeof navigator === "undefined" ? true : navigator.onLine));
  const [ventas, setVentas] = useState([]);
  const [sincronizando, setSincronizando] = useState(false);
  const [sesionVencida, setSesionVencida] = useState(false);
  const [ultimoEnvio, setUltimoEnvio] = useState(null);
  const [catalogo, setCatalogo] = useState(null);
  const [fallaAlmacen, setFallaAlmacen] = useState(false);
  const disponible = almacenDisponible() && !fallaAlmacen;

  // Valores vigentes para los temporizadores y manejadores, que no deben quedar con datos viejos.
  const vigente = useRef({});
  const enCurso = useRef(false);

  const misPendientes = ventas.filter(
    (v) => v.estado === ESTADO_PENDIENTE && (esAdministrador || v.usuarioId === usuarioId)
  ).length;
  const pendientes = ventas.filter((v) => v.estado === ESTADO_PENDIENTE).length;
  const conflictos = ventas.filter((v) => v.estado === ESTADO_CONFLICTO).length;
  vigente.current = { token, usuarioId, esAdministrador, enLinea, misPendientes };

  const refrescarVentas = useCallback(async () => {
    try {
      setVentas(await listarVentas());
    } catch {
      setFallaAlmacen(true);
    }
  }, []);

  const comprobarConexion = useCallback(async () => {
    try {
      await obtenerSalud();
      setEnLinea(true);
      return true;
    } catch {
      setEnLinea(false);
      return false;
    }
  }, []);

  const sincronizar = useCallback(async () => {
    const { token: tokenActual, usuarioId: id, esAdministrador: admin } = vigente.current;
    if (enCurso.current || !tokenActual) return;
    enCurso.current = true;
    setSincronizando(true);
    try {
      const resultado = await sincronizarPendientes({ token: tokenActual, usuarioId: id, esAdministrador: admin });
      if (resultado.enviadas > 0 || resultado.conflictos > 0) {
        setUltimoEnvio({ enviadas: resultado.enviadas, conflictos: resultado.conflictos });
      }
      setSesionVencida(resultado.detenida === "sesion");
      if (resultado.detenida === "conexion") setEnLinea(false);
    } catch {
      setFallaAlmacen(true);
    } finally {
      enCurso.current = false;
      setSincronizando(false);
      await refrescarVentas();
    }
  }, [refrescarVentas]);

  const actualizarCatalogo = useCallback(async () => {
    const { token: tokenActual } = vigente.current;
    if (!tokenActual) return;
    try {
      const info = await descargarCatalogo(tokenActual);
      setCatalogo(info);
      // Lo que tambien hace falta para vender sin conexion: el descuento general, los topes y los vendedores.
      const [configuracion, vendedores] = await Promise.all([
        obtenerConfiguracionDescuentos(tokenActual),
        obtenerVendedores(tokenActual).catch(() => null),
      ]);
      await guardarEnCache("descuentos", configuracion);
      if (vendedores) await guardarEnCache("vendedores", vendedores);
    } catch (error) {
      if (esErrorDeConexion(error)) setEnLinea(false);
      else if (error?.status === 401) setSesionVencida(true);
      // Cualquier otro fallo (almacenamiento): se conserva la copia anterior.
    }
  }, []);

  // Al abrir: leer la cola y ver cuanto catalogo hay guardado.
  useEffect(() => {
    refrescarVentas();
    infoCatalogoLocal()
      .then(setCatalogo)
      .catch(() => setFallaAlmacen(true));
  }, [refrescarVentas]);

  // Eventos del navegador: perder la red es inmediato; recuperarla se confirma con el servidor.
  useEffect(() => {
    const alDesconectar = () => setEnLinea(false);
    const alConectar = () => {
      comprobarConexion();
    };
    window.addEventListener("offline", alDesconectar);
    window.addEventListener("online", alConectar);
    return () => {
      window.removeEventListener("offline", alDesconectar);
      window.removeEventListener("online", alConectar);
    };
  }, [comprobarConexion]);

  // Con conexion: refrescar el catalogo (al abrir, al volver la red o al iniciar sesion).
  useEffect(() => {
    if (token && enLinea) actualizarCatalogo();
  }, [token, enLinea, actualizarCatalogo]);

  // Con conexion y ventas por enviar (al abrir, al volver la red, al iniciar sesion o al quedar una nueva): enviarlas.
  useEffect(() => {
    if (token && enLinea && misPendientes > 0) sincronizar();
  }, [token, enLinea, misPendientes, sincronizar]);

  // Mientras no haya conexion o queden ventas por enviar, preguntarle al servidor cada tanto.
  useEffect(() => {
    if (!token) return undefined;
    const reloj = setInterval(async () => {
      const { enLinea: conectado, misPendientes: pendientesMios } = vigente.current;
      if (conectado && pendientesMios === 0) return;
      const ok = await comprobarConexion();
      if (ok && pendientesMios > 0) sincronizar();
    }, INTERVALO_COMPROBACION_MS);
    return () => clearInterval(reloj);
  }, [token, comprobarConexion, sincronizar]);

  // Con conexion, mantener fresca la copia del catalogo.
  useEffect(() => {
    if (!token) return undefined;
    const reloj = setInterval(() => {
      if (vigente.current.enLinea) actualizarCatalogo();
    }, INTERVALO_CATALOGO_MS);
    return () => clearInterval(reloj);
  }, [token, actualizarCatalogo]);

  const registrarVenta = useCallback(
    async (entrada) => {
      await encolarVenta(entrada);
      await refrescarVentas();
    },
    [refrescarVentas]
  );

  const reintentarVenta = useCallback(
    async (uuid) => {
      await reabrirVenta(uuid);
      await refrescarVentas();
      await sincronizar();
    },
    [refrescarVentas, sincronizar]
  );

  const descartarVenta = useCallback(
    async (uuid) => {
      await eliminarVenta(uuid);
      await refrescarVentas();
    },
    [refrescarVentas]
  );

  const reportarFalloDeConexion = useCallback(() => setEnLinea(false), []);
  const descartarAviso = useCallback(() => setUltimoEnvio(null), []);

  const valor = useMemo(
    () => ({
      activo: true,
      disponible,
      enLinea,
      ventas,
      pendientes,
      misPendientes,
      conflictos,
      pendientesDeOtros: esAdministrador ? 0 : pendientes - misPendientes,
      sincronizando,
      sesionVencida,
      ultimoEnvio,
      catalogo,
      sincronizar,
      registrarVenta,
      reintentarVenta,
      descartarVenta,
      reportarFalloDeConexion,
      siguienteNumero: siguienteNumeroLocal,
      buscarLocal: buscarEnCatalogoLocal,
      guardarEnCache,
      leerDeCache,
      descartarAviso,
    }),
    [
      disponible,
      enLinea,
      ventas,
      pendientes,
      misPendientes,
      conflictos,
      esAdministrador,
      sincronizando,
      sesionVencida,
      ultimoEnvio,
      catalogo,
      sincronizar,
      registrarVenta,
      reintentarVenta,
      descartarVenta,
      reportarFalloDeConexion,
      descartarAviso,
    ]
  );

  return <SinConexionContext.Provider value={valor}>{children}</SinConexionContext.Provider>;
}

/**
 * Acceso al modo sin conexion. Fuera de un `SinConexionProvider` devuelve un valor inactivo (siempre en
 * linea, sin cola), para que los componentes se prueben sueltos sin montarlo todo.
 *
 * @returns {typeof VALOR_SIN_CONEXION_INACTIVO}
 */
export function useSinConexion() {
  return useContext(SinConexionContext) ?? VALOR_SIN_CONEXION_INACTIVO;
}
