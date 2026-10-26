/**
 * Catalogo de productos guardado en el equipo para vender y buscar sin conexion (Fase 9).
 *
 * Se descarga completo (solo productos activos) cada vez que hay conexion y se reemplaza de una vez: si la
 * descarga se interrumpe, queda la copia anterior. Guarda lo que el POS necesita; nunca costos.
 */

import { obtenerCatalogo } from "../api/api-client";
import { guardar, obtener, obtenerTodos, reemplazarTodos } from "./almacen";

const TAMANO_PAGINA = 100;
const LIMITE_RESULTADOS = 20;

/** Copia en memoria del catalogo, para no leer IndexedDB en cada busqueda. */
let copiaEnMemoria = null;

/**
 * Pasa un texto a minusculas y sin tildes, para buscar sin importar como se escribio.
 *
 * @param {string} texto
 * @returns {string}
 */
export function normalizar(texto) {
  return String(texto ?? "")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .trim();
}

/**
 * Deja de un producto solo lo que el POS usa sin conexion.
 *
 * @param {object} producto - `ProductoOut` del backend.
 * @returns {object}
 */
function compactar(producto) {
  return {
    id: producto.id,
    nombre: producto.nombre,
    categoria_id: producto.categoria_id,
    categoria_nombre: producto.categoria_nombre,
    codigo_barras: producto.codigo_barras,
    tipo: producto.tipo,
    precio_venta: producto.precio_venta,
    stock_actual: producto.stock_actual,
    stock_minimo: producto.stock_minimo,
    activo: producto.activo,
    texto_busqueda: normalizar(`${producto.nombre} ${producto.categoria_nombre ?? ""}`),
    nombre_normalizado: normalizar(producto.nombre),
  };
}

/**
 * Descarga todos los productos activos y reemplaza la copia local.
 *
 * @param {string} token - Access token JWT.
 * @returns {Promise<{cantidad: number, guardadoEn: string}>}
 * @throws {Error} Si falla la red o el almacenamiento; la copia anterior se conserva.
 */
export async function descargarCatalogo(token) {
  const productos = [];
  let pagina = 1;
  let total = Infinity;
  while (productos.length < total) {
    const respuesta = await obtenerCatalogo({ pagina, tamanoPagina: TAMANO_PAGINA, activo: true }, token);
    if (!respuesta || !Array.isArray(respuesta.productos)) {
      throw new Error("El servidor devolvió un catálogo con un formato inesperado.");
    }
    total = respuesta.total;
    if (respuesta.productos.length === 0) break;
    productos.push(...respuesta.productos.map(compactar));
    pagina += 1;
  }
  const guardadoEn = new Date().toISOString();
  await reemplazarTodos("catalogo", productos);
  await guardar("meta", { clave: "catalogo", valor: { guardadoEn, cantidad: productos.length } });
  copiaEnMemoria = productos;
  return { cantidad: productos.length, guardadoEn };
}

/**
 * Dice cuantos productos hay guardados y desde cuando.
 *
 * @returns {Promise<{cantidad: number, guardadoEn: string} | null>} `null` si nunca se descargo.
 */
export async function infoCatalogoLocal() {
  const registro = await obtener("meta", "catalogo");
  return registro?.valor ?? null;
}

/**
 * Lee el catalogo guardado (usa la copia en memoria si ya se leyo).
 *
 * @returns {Promise<Array<object>>}
 */
async function leerCatalogo() {
  if (copiaEnMemoria === null) {
    copiaEnMemoria = await obtenerTodos("catalogo");
  }
  return copiaEnMemoria;
}

/**
 * Busca en el catalogo guardado igual que el POS: un codigo de barras exacto da ese producto; si no, texto
 * parcial sin importar tildes ni mayusculas, en el nombre o la categoria (todas las palabras deben aparecer).
 *
 * @param {string} consulta - Codigo de barras o texto.
 * @returns {Promise<Array<object>>} Hasta 20 productos activos, los que empiezan por lo escrito primero.
 */
export async function buscarEnCatalogoLocal(consulta) {
  const texto = String(consulta ?? "").trim();
  if (!texto) return [];
  const catalogo = (await leerCatalogo()).filter((producto) => producto.activo !== false);

  const exacto = catalogo.find((producto) => producto.codigo_barras && producto.codigo_barras === texto);
  if (exacto) return [exacto];

  const palabras = normalizar(texto).split(/\s+/).filter(Boolean);
  const primera = palabras[0] ?? "";
  return catalogo
    .filter((producto) => palabras.every((palabra) => producto.texto_busqueda.includes(palabra)))
    .sort((a, b) => {
      const empiezaA = a.nombre_normalizado.startsWith(primera) ? 0 : 1;
      const empiezaB = b.nombre_normalizado.startsWith(primera) ? 0 : 1;
      return empiezaA - empiezaB || a.nombre.localeCompare(b.nombre, "es");
    })
    .slice(0, LIMITE_RESULTADOS);
}

/**
 * Guarda un dato suelto (configuracion de descuentos, lista de vendedores) para usarlo sin conexion.
 *
 * @param {string} clave
 * @param {unknown} valor
 * @returns {Promise<void>}
 */
export async function guardarEnCache(clave, valor) {
  await guardar("meta", { clave, valor, guardadoEn: new Date().toISOString() });
}

/**
 * Lee un dato suelto guardado antes.
 *
 * @param {string} clave
 * @returns {Promise<unknown | null>} El valor guardado, o `null` si no hay.
 */
export async function leerDeCache(clave) {
  const registro = await obtener("meta", clave);
  return registro?.valor ?? null;
}

/**
 * Olvida la copia en memoria. Solo para las pruebas.
 */
export function reiniciarCatalogoParaPruebas() {
  copiaEnMemoria = null;
}
