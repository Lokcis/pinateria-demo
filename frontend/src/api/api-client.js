/**
 * Cliente HTTP hacia el backend FastAPI y el agente de impresion local.
 *
 * Centraliza las URLs base y el manejo de errores para que los
 * componentes no construyan fetch() a mano en cada lugar.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const PRINTER_AGENT_URL = import.meta.env.VITE_PRINTER_AGENT_URL || "http://127.0.0.1:9100";

/**
 * Error de la API con el mensaje que el backend envio en `detail`.
 */
export class ApiError extends Error {
  /**
   * @param {string} mensaje - Mensaje de error legible para el usuario.
   * @param {number} status - Codigo HTTP de la respuesta.
   */
  constructor(mensaje, status) {
    super(mensaje);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Lo que ve la persona cuando no se puede hablar con el servidor (en lugar de "Failed to fetch"). */
const MENSAJE_SIN_SERVIDOR = "No hay conexión con el servidor. Revisa el internet e inténtalo de nuevo.";

/** Lo que ve la persona cuando el agente de impresion del PC del POS no responde. */
const MENSAJE_SIN_AGENTE =
  "No se pudo conectar con el agente de impresión. Revisa que esté abierto en el PC del POS y que la impresora esté encendida.";

/**
 * Hace un `fetch` y, si falla por falta de conexion, deja un mensaje en espanol en lugar del texto tecnico del
 * navegador ("Failed to fetch"). El error sigue siendo un `TypeError`: `esErrorDeConexion` (modo sin conexion)
 * se apoya en eso para decidir si una venta se guarda en la cola local.
 *
 * @param {string} url
 * @param {RequestInit} opciones
 * @param {string} mensajeSinRed - Mensaje para el caso de que no haya conexion.
 * @returns {Promise<Response>}
 */
async function pedir(url, opciones, mensajeSinRed) {
  try {
    return await fetch(url, opciones);
  } catch (error) {
    if (error instanceof TypeError) error.message = mensajeSinRed;
    throw error;
  }
}

/**
 * Ejecuta una request contra el backend y normaliza los errores.
 *
 * @param {string} ruta - Ruta relativa (ej. "/productos/buscar?q=abc").
 * @param {RequestInit} [opciones] - Opciones estandar de fetch.
 * @returns {Promise<unknown>} El cuerpo de la respuesta, parseado como JSON.
 * @throws {ApiError} Si la respuesta no es exitosa (status >= 400).
 */
async function solicitarApi(ruta, opciones = {}) {
  const respuesta = await pedir(`${API_BASE_URL}${ruta}`, opciones, MENSAJE_SIN_SERVIDOR);

  if (!respuesta.ok) {
    let mensaje = `Error ${respuesta.status} al llamar ${ruta}`;
    try {
      const cuerpoError = await respuesta.json();
      if (cuerpoError && cuerpoError.detail) {
        mensaje = cuerpoError.detail;
      }
    } catch {
      // El cuerpo no era JSON valido; se usa el mensaje generico.
    }
    throw new ApiError(mensaje, respuesta.status);
  }

  if (respuesta.status === 204) {
    return null;
  }
  return respuesta.json();
}

/**
 * Crea una senal que aborta una peticion pasado un tiempo (para no dejar al vendedor esperando con la red caida).
 *
 * @param {number} milisegundos
 * @returns {AbortSignal}
 */
function senalConTiempoMaximo(milisegundos) {
  if (typeof AbortSignal !== "undefined" && typeof AbortSignal.timeout === "function") {
    return AbortSignal.timeout(milisegundos);
  }
  const controlador = new AbortController();
  setTimeout(() => controlador.abort(), milisegundos);
  return controlador.signal;
}

/**
 * Comprueba que el servidor responde (modo sin conexion, Fase 9): `navigator.onLine` solo dice que hay una red,
 * no que el servidor se alcance.
 *
 * @param {number} [tiempoMaximoMs] - Tiempo maximo de espera.
 * @returns {Promise<{status: string}>}
 * @throws {Error} Si no responde a tiempo o la red falla.
 */
export async function obtenerSalud(tiempoMaximoMs = 5000) {
  return solicitarApi("/health", { cache: "no-store", signal: senalConTiempoMaximo(tiempoMaximoMs) });
}

/**
 * Construye el header Authorization a partir de un token JWT.
 *
 * @param {string} token - Access token JWT.
 * @returns {{Authorization: string}} El header listo para incluir en fetch.
 */
function encabezadoAutenticacion(token) {
  return { Authorization: `Bearer ${token}` };
}

/**
 * Autentica contra `POST /login` (formulario OAuth2 estandar).
 *
 * @param {string} username - Nombre de usuario.
 * @param {string} password - Contrasena en texto plano.
 * @returns {Promise<{access_token: string, token_type: string}>} El token emitido.
 * @throws {ApiError} Si las credenciales son invalidas (401).
 */
export async function iniciarSesion(username, password) {
  const formulario = new URLSearchParams();
  formulario.set("username", username);
  formulario.set("password", password);

  return solicitarApi("/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: formulario.toString(),
  });
}

/**
 * Busca productos por codigo de barras (match exacto) o nombre (fallback trigram).
 *
 * @param {string} query - Codigo de barras o texto a buscar.
 * @param {string} token - Access token JWT del usuario autenticado.
 * @returns {Promise<Array<object>>} Lista de productos encontrados (ver `ProductoOut`).
 */
export async function buscarProductos(query, token) {
  const parametros = new URLSearchParams({ q: query });
  return solicitarApi(`/productos/buscar?${parametros.toString()}`, {
    headers: encabezadoAutenticacion(token),
  });
}

/**
 * Crea una venta completa (encabezado + detalle + descuento de stock).
 *
 * @param {{detalles: Array<{producto_id: number, cantidad: number}>, pagos: Array<{metodo_pago: string,
 *   plataforma: string | null, monto: string, monto_recibido: string | null}>,
 *   descuento: {origen: string, tipo?: string, valor?: string}}} payload - Ver `VentaIn` (Adendo v2).
 *   Datos de la venta a crear.
 * @param {string} token - Access token JWT del usuario autenticado.
 * @param {{tiempoMaximoMs?: number}} [opciones] - Con `tiempoMaximoMs`, la peticion se aborta pasado ese tiempo
 *   (el POS guarda entonces la venta en la cola local; reenviarla es seguro porque lleva `uuid_cliente`).
 * @returns {Promise<object>} La venta creada (ver `VentaOut`). Si `payload.uuid_cliente` ya se habia registrado,
 *   el servidor responde 200 con la venta que ya tenia.
 * @throws {ApiError} 409 si no hay stock suficiente; 404/400 si algun
 *   producto no existe o no esta activo.
 */
export async function crearVenta(payload, token, { tiempoMaximoMs } = {}) {
  return solicitarApi("/ventas", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...encabezadoAutenticacion(token),
    },
    body: JSON.stringify(payload),
    ...(tiempoMaximoMs ? { signal: senalConTiempoMaximo(tiempoMaximoMs) } : {}),
  });
}

/**
 * Descuento general y topes del descuento manual vigentes (Adendo v2, RF-026, RF-042).
 *
 * @param {string} token - Access token JWT (vendedor o administrador).
 * @returns {Promise<{general: {tipo: string, valor: string, activo: boolean} | null,
 *   topes: {tope_porcentaje: string | null, tope_monto: string | null, descripcion: string}}>}
 */
export async function obtenerConfiguracionDescuentos(token) {
  return solicitarApi("/descuentos/configuracion", { headers: encabezadoAutenticacion(token) });
}

/**
 * Guarda el descuento general (solo administrador, RF-026).
 *
 * @param {{tipo: string, valor: string, activo: boolean}} datos
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} La configuracion actualizada.
 */
export async function guardarDescuentoGeneral(datos, token) {
  return solicitarApi("/descuentos/general", {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...encabezadoAutenticacion(token) },
    body: JSON.stringify(datos),
  });
}

/**
 * Guarda los topes del descuento manual (solo administrador, RF-042). `null` = sin tope.
 *
 * @param {{tope_porcentaje: string | null, tope_monto: string | null}} datos
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} La configuracion actualizada.
 */
export async function guardarTopesDescuento(datos, token) {
  return solicitarApi("/descuentos/topes", {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...encabezadoAutenticacion(token) },
    body: JSON.stringify(datos),
  });
}

/**
 * Tabla de costos de los productos (Adendo v2, Fase A3: RF-037). Administrador y propietario.
 *
 * @param {string} token - Access token JWT.
 * @param {{soloSinCosto?: boolean}} [filtros]
 * @returns {Promise<{productos: Array<object>, lineas_por_completar: number}>} Ver `TablaCostosOut`.
 */
export async function obtenerCostos(token, { soloSinCosto = false } = {}) {
  const consulta = soloSinCosto ? "?solo_sin_costo=true" : "";
  return solicitarApi(`/costos${consulta}`, { headers: encabezadoAutenticacion(token) });
}

/**
 * Guarda el costo de un producto (solo administrador, RF-037). `null` lo deja sin costo.
 *
 * @param {number} productoId
 * @param {string | null} costo
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} La fila actualizada (`CostoProductoOut`).
 */
export async function guardarCosto(productoId, costo, token) {
  return solicitarApi(`/productos/${productoId}/costo`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...encabezadoAutenticacion(token) },
    body: JSON.stringify({ costo_unitario: costo }),
  });
}

/**
 * Completa con el costo actual las lineas de ventas pasadas sin costo (solo administrador).
 *
 * @param {string} token - Access token JWT.
 * @returns {Promise<{lineas_completadas: number}>}
 */
export async function completarCostosVentas(token) {
  return solicitarApi("/costos/completar-ventas", { method: "POST", headers: encabezadoAutenticacion(token) });
}

/**
 * Margen bruto de un rango de dias (Adendo v2, Fase A3: RF-038, RF-039). Administrador y propietario.
 *
 * @param {{desde: string, hasta: string}} rango - Dias "AAAA-MM-DD" (zona de la tienda).
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} Ver `GananciasOut`.
 */
export async function obtenerGanancias(rango, token) {
  const parametros = new URLSearchParams({ desde: rango.desde, hasta: rango.hasta });
  return solicitarApi(`/ganancias?${parametros.toString()}`, { headers: encabezadoAutenticacion(token) });
}

/**
 * Obtiene las ventas de hoy con su resumen (RF-018).
 *
 * Un vendedor recibe solo sus ventas; un administrador, las de todos.
 *
 * @param {string} token - Access token JWT del usuario autenticado.
 * @returns {Promise<{fecha: string, cantidad_ventas: number, total_vendido: string,
 *   total_por_metodo: Record<string, string>, ventas: Array<object>}>} Ver `HistorialDiaOut`.
 */
export async function obtenerHistorialHoy(token) {
  return solicitarApi("/ventas/hoy", { headers: encabezadoAutenticacion(token) });
}

/**
 * Lista el catalogo de productos con filtro y paginacion (RF-006).
 *
 * @param {{q?: string, pagina?: number, tamanoPagina?: number}} filtro - Filtro y paginacion.
 * @param {string} token - Access token JWT del usuario autenticado.
 * @returns {Promise<{total: number, productos: Array<object>}>} Ver `CatalogoOut`.
 */
export async function obtenerCatalogo({ q, pagina = 1, tamanoPagina = 20, activo = true } = {}, token) {
  const parametros = new URLSearchParams({
    pagina: String(pagina),
    tamano_pagina: String(tamanoPagina),
    activo: String(activo),
  });
  if (q) {
    parametros.set("q", q);
  }
  return solicitarApi(`/productos?${parametros.toString()}`, {
    headers: encabezadoAutenticacion(token),
  });
}

/**
 * Edita los datos generales de un producto (RF-016). Requiere rol administrador.
 *
 * @param {number} productoId - Id del producto.
 * @param {{nombre?: string, descripcion?: string|null, categoria_id?: number,
 *   codigo_barras?: string|null, precio_venta?: number, tipo?: string,
 *   componentes?: Array<{producto_id: number, cantidad: number}>}} payload
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} El producto actualizado.
 * @throws {ApiError} 409 si el codigo de barras ya esta en uso.
 */
export async function editarProducto(productoId, payload, token) {
  return solicitarApi(`/productos/${productoId}`, opcionesJson("PATCH", token, payload));
}

/**
 * Desactiva un producto: deja de venderse pero conserva su historial (RF-016).
 *
 * @param {number} productoId - Id del producto.
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} El producto actualizado.
 */
export async function desactivarProducto(productoId, token) {
  return solicitarApi(`/productos/${productoId}/desactivar`, opcionesJson("PATCH", token));
}

/**
 * Lista los productos compuestos (paquetes/anchetas) que llevan un producto en su receta.
 * Sirve para avisar antes de desactivarlo. Requiere rol administrador.
 *
 * @param {number} productoId - Id del producto.
 * @param {string} token - Access token JWT.
 * @returns {Promise<Array<{id: number, nombre: string, tipo: string, activo: boolean}>>}
 */
export async function obtenerProductosQueLoUsan(productoId, token) {
  return solicitarApi(`/productos/${productoId}/usado-en`, { headers: encabezadoAutenticacion(token) });
}

/**
 * Reactiva un producto desactivado (RF-016).
 *
 * @param {number} productoId - Id del producto.
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} El producto actualizado.
 */
export async function reactivarProducto(productoId, token) {
  return solicitarApi(`/productos/${productoId}/reactivar`, opcionesJson("PATCH", token));
}

/**
 * Lista todas las categorias del catalogo (para poblar selectores en la UI).
 *
 * @param {string} token - Access token JWT del usuario autenticado.
 * @returns {Promise<Array<{id: number, nombre: string, descripcion: string|null}>>}
 */
export async function obtenerCategorias(token) {
  return solicitarApi("/categorias", { headers: encabezadoAutenticacion(token) });
}

/**
 * Da de alta una categoria (RF-017). Requiere rol administrador.
 *
 * @param {{nombre: string, descripcion?: string|null}} payload
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} La categoria creada.
 * @throws {ApiError} 409 si el nombre ya existe.
 */
export async function crearCategoria(payload, token) {
  return solicitarApi("/categorias", opcionesJson("POST", token, payload));
}

/**
 * Edita una categoria (RF-017).
 *
 * @param {number} categoriaId - Id de la categoria.
 * @param {{nombre?: string, descripcion?: string|null}} payload
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} La categoria actualizada.
 */
export async function editarCategoria(categoriaId, payload, token) {
  return solicitarApi(`/categorias/${categoriaId}`, opcionesJson("PATCH", token, payload));
}

/**
 * Elimina una categoria sin productos (RF-017).
 *
 * @param {number} categoriaId - Id de la categoria.
 * @param {string} token - Access token JWT.
 * @returns {Promise<null>}
 * @throws {ApiError} 409 si la categoria tiene productos.
 */
export async function eliminarCategoria(categoriaId, token) {
  return solicitarApi(`/categorias/${categoriaId}`, opcionesJson("DELETE", token));
}

/**
 * Lista todos los usuarios, activos e inactivos (RF-015). Requiere rol administrador.
 *
 * @param {string} token - Access token JWT.
 * @returns {Promise<Array<object>>} Ver `UsuarioOut`.
 */
export async function obtenerUsuarios(token) {
  return solicitarApi("/usuarios", { headers: encabezadoAutenticacion(token) });
}

/**
 * Crea un usuario con contrasena temporal (RF-015).
 *
 * @param {{nombre: string, username: string, password: string, rol: string}} payload
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} El usuario creado.
 * @throws {ApiError} 409 si el nombre de usuario ya existe.
 */
export async function crearUsuario(payload, token) {
  return solicitarApi("/usuarios", opcionesJson("POST", token, payload));
}

/**
 * Edita nombre, usuario, rol o estado activo de un usuario (RF-015).
 *
 * @param {number} usuarioId - Id del usuario.
 * @param {{nombre?: string, username?: string, rol?: string, activo?: boolean}} payload
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} El usuario actualizado.
 * @throws {ApiError} 403 si el administrador intenta desactivarse o quitarse el rol.
 */
export async function editarUsuario(usuarioId, payload, token) {
  return solicitarApi(`/usuarios/${usuarioId}`, opcionesJson("PATCH", token, payload));
}

/**
 * Fija una contrasena temporal nueva para un usuario (RF-015).
 *
 * @param {number} usuarioId - Id del usuario.
 * @param {string} password - Nueva contrasena temporal.
 * @param {string} token - Access token JWT.
 * @returns {Promise<null>}
 */
export async function restablecerPassword(usuarioId, password, token) {
  return solicitarApi(`/usuarios/${usuarioId}/password`, opcionesJson("POST", token, { password }));
}

/**
 * Cambia la contrasena del usuario autenticado (RF-015).
 *
 * @param {string} passwordActual - Contrasena vigente.
 * @param {string} passwordNueva - Contrasena nueva.
 * @param {string} token - Access token JWT.
 * @returns {Promise<null>}
 * @throws {ApiError} 400 si la contrasena actual no coincide.
 */
export async function cambiarMiPassword(passwordActual, passwordNueva, token) {
  return solicitarApi(
    "/cambiar-password",
    opcionesJson("POST", token, { password_actual: passwordActual, password_nueva: passwordNueva })
  );
}

/**
 * Da de alta un producto nuevo en el catalogo (HU-02, RF-016). Requiere rol administrador.
 *
 * @param {{nombre: string, descripcion?: string, categoria_id: number, codigo_barras?: string,
 *   tipo?: string, precio_venta: number, stock_inicial: number, stock_minimo?: number,
 *   componentes?: Array<{producto_id: number, cantidad: number}>}} payload
 * @param {string} token - Access token JWT del usuario autenticado.
 * @returns {Promise<object>} El producto creado (ver `ProductoOut`).
 * @throws {ApiError} 404 si la categoria no existe; 409 si el codigo de barras ya esta en uso.
 */
export async function crearProducto(payload, token) {
  return solicitarApi("/productos", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...encabezadoAutenticacion(token) },
    body: JSON.stringify(payload),
  });
}

/**
 * Actualiza el stock minimo de un producto (RF-007). Requiere rol administrador.
 *
 * @param {number} productoId - Id del producto.
 * @param {number} stockMinimo - Nuevo umbral de alerta.
 * @param {string} token - Access token JWT del usuario autenticado.
 * @returns {Promise<object>} El producto actualizado (ver `ProductoOut`).
 */
export async function actualizarStockMinimo(productoId, stockMinimo, token) {
  return solicitarApi(`/productos/${productoId}/stock-minimo`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...encabezadoAutenticacion(token) },
    body: JSON.stringify({ stock_minimo: stockMinimo }),
  });
}

/**
 * Registra un ajuste manual de inventario (RF-009).
 *
 * @param {number} productoId - Id del producto a ajustar.
 * @param {{tipo: string, cantidad: number, motivo: string}} payload - Datos del ajuste.
 * @param {string} token - Access token JWT del usuario autenticado.
 * @returns {Promise<object>} El ajuste registrado (ver `AjusteInventarioOut`).
 * @throws {ApiError} 400 si el signo de `cantidad` no corresponde al `tipo`; 409 si
 *   el ajuste dejaria el stock en negativo.
 */
export async function registrarAjusteInventario(productoId, payload, token) {
  return solicitarApi(`/productos/${productoId}/ajustes`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...encabezadoAutenticacion(token) },
    body: JSON.stringify(payload),
  });
}

/**
 * Obtiene el historial de ajustes manuales de un producto (RF-009).
 *
 * @param {number} productoId - Id del producto.
 * @param {string} token - Access token JWT del usuario autenticado.
 * @returns {Promise<Array<object>>} Los ajustes, del mas reciente al mas antiguo.
 */
export async function obtenerAjustesInventario(productoId, token) {
  return solicitarApi(`/productos/${productoId}/ajustes`, {
    headers: encabezadoAutenticacion(token),
  });
}

/**
 * Construye las opciones de fetch para una request JSON autenticada.
 *
 * @param {string} metodo - Verbo HTTP.
 * @param {string} token - Access token JWT.
 * @param {object} [cuerpo] - Cuerpo a serializar como JSON.
 * @returns {RequestInit}
 */
function opcionesJson(metodo, token, cuerpo) {
  return {
    method: metodo,
    headers: { "Content-Type": "application/json", ...encabezadoAutenticacion(token) },
    ...(cuerpo !== undefined && { body: JSON.stringify(cuerpo) }),
  };
}

/**
 * Lista el directorio de proveedores (RF-012). Requiere rol administrador (403 si no).
 *
 * @param {string|undefined} q - Filtro opcional por empresa o contacto.
 * @param {string} token - Access token JWT.
 * @returns {Promise<Array<object>>} Ver `ProveedorOut`.
 */
export async function obtenerProveedores(q, token) {
  const consulta = q ? `?${new URLSearchParams({ q }).toString()}` : "";
  return solicitarApi(`/proveedores${consulta}`, { headers: encabezadoAutenticacion(token) });
}

/**
 * Da de alta un proveedor (RF-012).
 *
 * @param {object} payload - Ver `ProveedorCrearIn`.
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} El proveedor creado.
 */
export async function crearProveedor(payload, token) {
  return solicitarApi("/proveedores", opcionesJson("POST", token, payload));
}

/**
 * Edita un proveedor; solo se envian los campos presentes (RF-012).
 *
 * @param {number} proveedorId - Id del proveedor.
 * @param {object} payload - Ver `ProveedorEditarIn`.
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} El proveedor actualizado.
 */
export async function editarProveedor(proveedorId, payload, token) {
  return solicitarApi(`/proveedores/${proveedorId}`, opcionesJson("PATCH", token, payload));
}

/**
 * Elimina un proveedor sin compras (RF-012).
 *
 * @param {number} proveedorId - Id del proveedor.
 * @param {string} token - Access token JWT.
 * @returns {Promise<null>}
 * @throws {ApiError} 409 si el proveedor tiene compras registradas.
 */
export async function eliminarProveedor(proveedorId, token) {
  return solicitarApi(`/proveedores/${proveedorId}`, opcionesJson("DELETE", token));
}

/**
 * Lista compras con filtros de historial por proveedor, producto y estado (RF-012).
 *
 * @param {{proveedorId?: number, productoId?: number, estado?: string}} filtro
 * @param {string} token - Access token JWT.
 * @returns {Promise<Array<object>>} Ver `CompraOut`, de la mas reciente a la mas antigua.
 */
export async function obtenerCompras({ proveedorId, productoId, estado } = {}, token) {
  const parametros = new URLSearchParams();
  if (proveedorId) parametros.set("proveedor_id", String(proveedorId));
  if (productoId) parametros.set("producto_id", String(productoId));
  if (estado) parametros.set("estado", estado);
  const consulta = parametros.toString();
  return solicitarApi(`/compras${consulta ? `?${consulta}` : ""}`, {
    headers: encabezadoAutenticacion(token),
  });
}

/**
 * Registra una orden de compra pendiente (RF-010).
 *
 * @param {{proveedor_id: number, detalles: Array<{producto_id: number, cantidad: number,
 *   costo_unitario: number}>}} payload
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} La compra creada (ver `CompraOut`).
 */
export async function crearCompra(payload, token) {
  return solicitarApi("/compras", opcionesJson("POST", token, payload));
}

/**
 * Marca una compra como recibida; el backend incrementa el stock (RF-011) y guarda como se pago (Adendo v3).
 *
 * @param {number} compraId - Id de la compra.
 * @param {{metodo_pago: string, plataforma?: string | null}} pago - Forma de pago; la plataforma (nequi o
 *   daviplata) es obligatoria solo en una transferencia.
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} La compra actualizada.
 * @throws {ApiError} 409 si la compra ya no esta pendiente; 422 si falta la plataforma de la transferencia.
 */
export async function recibirCompra(compraId, pago, token) {
  return solicitarApi(`/compras/${compraId}/recibir`, opcionesJson("PATCH", token, pago));
}

/**
 * Cancela una compra pendiente; no afecta el inventario.
 *
 * @param {number} compraId - Id de la compra.
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} La compra cancelada.
 * @throws {ApiError} 409 si la compra ya no esta pendiente.
 */
export async function cancelarCompra(compraId, token) {
  return solicitarApi(`/compras/${compraId}/cancelar`, opcionesJson("PATCH", token));
}


/**
 * Lista las categorias de gasto (Adendo v3, RF-060). El vendedor recibe solo las activas.
 *
 * @param {string} token - Access token JWT.
 * @returns {Promise<Array<{id: number, nombre: string, activa: boolean, es_sistema: boolean}>>}
 */
export async function obtenerCategoriasGasto(token) {
  return solicitarApi("/categorias-gasto", { headers: encabezadoAutenticacion(token) });
}

/**
 * Crea una categoria de gasto. Solo administrador.
 *
 * @param {{nombre: string}} payload
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} La categoria creada.
 * @throws {ApiError} 409 si ya existe una con ese nombre.
 */
export async function crearCategoriaGasto(payload, token) {
  return solicitarApi("/categorias-gasto", opcionesJson("POST", token, payload));
}

/**
 * Renombra, activa o desactiva una categoria de gasto. Solo administrador; la de sistema no se toca (409).
 *
 * @param {number} categoriaId
 * @param {{nombre?: string, activa?: boolean}} payload
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} La categoria actualizada.
 */
export async function editarCategoriaGasto(categoriaId, payload, token) {
  return solicitarApi(`/categorias-gasto/${categoriaId}`, opcionesJson("PATCH", token, payload));
}

/**
 * Arma el texto de consulta de los filtros de gastos (la lista, el resumen y la exportacion comparten filtros).
 *
 * @param {{desde?: string, hasta?: string, categoriaId?: number | string, metodoPago?: string, estado?: string,
 *   origen?: string, pagina?: number, tamanoPagina?: number}} filtros
 * @returns {URLSearchParams} Los parametros de la consulta (pueden estar vacios).
 */
function consultaDeGastos({ desde, hasta, categoriaId, metodoPago, estado, origen, pagina, tamanoPagina } = {}) {
  const parametros = new URLSearchParams();
  if (desde) parametros.set("desde", desde);
  if (hasta) parametros.set("hasta", hasta);
  if (categoriaId) parametros.set("categoria_id", String(categoriaId));
  if (metodoPago) parametros.set("metodo_pago", metodoPago);
  if (estado) parametros.set("estado", estado);
  if (origen) parametros.set("origen", origen);
  if (pagina) parametros.set("pagina", String(pagina));
  if (tamanoPagina) parametros.set("tamano_pagina", String(tamanoPagina));
  return parametros;
}

/**
 * Agrega a una ruta el texto de consulta, si lo hay.
 *
 * @param {string} ruta
 * @param {URLSearchParams} parametros
 * @returns {string}
 */
function conConsulta(ruta, parametros) {
  const texto = parametros.toString();
  return texto ? `${ruta}?${texto}` : ruta;
}

/**
 * Lista los gastos del rango (Adendo v3, RF-059). El administrador y el propietario reciben tambien las compras
 * recibidas; el vendedor, solo los gastos que registro el.
 *
 * @param {object} filtros - Ver `consultaDeGastos`.
 * @param {string} token - Access token JWT.
 * @returns {Promise<Array<object>>} Filas (ver `GastoOut`), de la mas reciente a la mas antigua.
 */
export async function obtenerGastos(filtros, token) {
  return solicitarApi(conConsulta("/gastos", consultaDeGastos(filtros)), { headers: encabezadoAutenticacion(token) });
}

/**
 * Totales vigentes del rango por categoria y forma de pago. Administrador y propietario (el vendedor recibe 403).
 *
 * @param {object} filtros - Ver `consultaDeGastos` (el estado y la paginacion no aplican).
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} Ver `ResumenGastosOut`.
 */
export async function obtenerResumenGastos(filtros, token) {
  const parametros = consultaDeGastos({ ...filtros, estado: undefined, pagina: undefined, tamanoPagina: undefined });
  return solicitarApi(conConsulta("/gastos/resumen", parametros), { headers: encabezadoAutenticacion(token) });
}

/**
 * Registra un gasto. Administrador y vendedor.
 *
 * @param {{categoria_id: number, descripcion: string, monto: number, metodo_pago: string, plataforma?: string | null,
 *   beneficiario?: string | null, fecha?: string}} payload
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} El gasto creado (ver `GastoOut`).
 */
export async function crearGasto(payload, token) {
  return solicitarApi("/gastos", opcionesJson("POST", token, payload));
}

/**
 * Edita un gasto vigente; solo viajan los campos que cambian.
 *
 * @param {number} gastoId
 * @param {object} cambios - Campos a cambiar (ver `GastoPatch`).
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} El gasto editado.
 */
export async function editarGasto(gastoId, cambios, token) {
  return solicitarApi(`/gastos/${gastoId}`, opcionesJson("PATCH", token, cambios));
}

/**
 * Anula un gasto vigente con su motivo (no se borra).
 *
 * @param {number} gastoId
 * @param {string} motivo - Por que se anula (obligatorio).
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} El gasto anulado.
 */
export async function anularGasto(gastoId, motivo, token) {
  return solicitarApi(`/gastos/${gastoId}/anular`, opcionesJson("POST", token, { motivo }));
}

/**
 * Descarga el CSV de los gastos y compras del rango y los filtros (RF-066). Administrador y propietario.
 *
 * @param {object} filtros - Ver `consultaDeGastos`; `incluirAnulados` agrega los anulados.
 * @param {string} token - Access token JWT.
 * @returns {Promise<{contenido: Blob, nombre: string}>} El archivo y el nombre con que guardarlo.
 * @throws {ApiError} Si el servidor rechaza la descarga.
 */
export async function exportarGastos({ incluirAnulados, ...filtros }, token) {
  const parametros = consultaDeGastos({ ...filtros, estado: undefined, pagina: undefined, tamanoPagina: undefined });
  if (incluirAnulados) parametros.set("incluir_anulados", "true");
  return descargarCsv(conConsulta("/gastos/exportar", parametros), "los gastos", "gastos.csv", token);
}

/**
 * Descarga un CSV autenticado del servidor.
 *
 * @param {string} ruta - Ruta (con su consulta) del endpoint de exportacion.
 * @param {string} queExporta - Lo que se exporta, para el mensaje de error ("los gastos").
 * @param {string} nombrePorDefecto - Nombre del archivo si el servidor no manda `Content-Disposition`.
 * @param {string} token - Access token JWT.
 * @returns {Promise<{contenido: Blob, nombre: string}>} El archivo y el nombre con que guardarlo.
 * @throws {ApiError} Si el servidor rechaza la descarga.
 */
async function descargarCsv(ruta, queExporta, nombrePorDefecto, token) {
  const respuesta = await pedir(`${API_BASE_URL}${ruta}`, { headers: encabezadoAutenticacion(token) }, MENSAJE_SIN_SERVIDOR);
  if (!respuesta.ok) {
    let mensaje = `Error ${respuesta.status} al exportar ${queExporta}`;
    try {
      const cuerpo = await respuesta.json();
      if (cuerpo?.detail) mensaje = cuerpo.detail;
    } catch {
      // El cuerpo no era JSON; se usa el mensaje generico.
    }
    throw new ApiError(mensaje, respuesta.status);
  }
  const nombre = /filename="([^"]+)"/.exec(respuesta.headers.get("Content-Disposition") || "")?.[1] || nombrePorDefecto;
  return { contenido: await respuesta.blob(), nombre };
}

/**
 * Consulta el estado de la caja y, si esta abierta, el efectivo esperado en vivo (Adendo v3, RF-070).
 *
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} Ver `CajaActualOut`.
 */
export async function obtenerCajaActual(token) {
  return solicitarApi("/caja/actual", { headers: encabezadoAutenticacion(token) });
}

/**
 * Abre la caja con la base indicada (multiplo de $50). Administrador y vendedor.
 *
 * @param {number} baseInicial - Efectivo con que arranca la caja.
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} La caja ya abierta (ver `CajaActualOut`).
 */
export async function abrirCaja(baseInicial, token) {
  return solicitarApi("/caja/abrir", opcionesJson("POST", token, { base_inicial: baseInicial }));
}

/**
 * Registra un ingreso o retiro manual en la caja abierta (RF-071).
 *
 * @param {{tipo: "ingreso" | "retiro", monto: number, motivo: string}} movimiento
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} La caja con el efectivo esperado ya actualizado.
 */
export async function registrarMovimientoCaja(movimiento, token) {
  return solicitarApi("/caja/movimientos", opcionesJson("POST", token, movimiento));
}

/**
 * Cierra la caja con el efectivo contado y guarda la foto del corte (RF-072).
 *
 * @param {{efectivoContado: number, observaciones?: string}} datos
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} La ficha del corte cerrado (ver `CorteCajaDetalleOut`).
 */
export async function cerrarCaja({ efectivoContado, observaciones }, token) {
  const cuerpo = { efectivo_contado: efectivoContado };
  if (observaciones) cuerpo.observaciones = observaciones;
  return solicitarApi("/caja/cerrar", opcionesJson("POST", token, cuerpo));
}

/**
 * Arma el texto de consulta del historial de cortes.
 *
 * @param {{desde?: string, hasta?: string, pagina?: number, tamanoPagina?: number}} filtros
 * @returns {URLSearchParams}
 */
function consultaDeCortes({ desde, hasta, pagina, tamanoPagina } = {}) {
  const parametros = new URLSearchParams();
  if (desde) parametros.set("desde", desde);
  if (hasta) parametros.set("hasta", hasta);
  if (pagina) parametros.set("pagina", String(pagina));
  if (tamanoPagina) parametros.set("tamano_pagina", String(tamanoPagina));
  return parametros;
}

/**
 * Lista los cortes de caja, del mas reciente al mas antiguo (RF-073). Un vendedor recibe solo los que abrio o cerro.
 *
 * @param {object} filtros - Ver `consultaDeCortes`.
 * @param {string} token - Access token JWT.
 * @returns {Promise<Array<object>>} Filas (ver `CorteCajaOut`).
 */
export async function obtenerCortes(filtros, token) {
  return solicitarApi(conConsulta("/caja/cortes", consultaDeCortes(filtros)), { headers: encabezadoAutenticacion(token) });
}

/**
 * Obtiene la ficha de un corte: su foto, sus movimientos y las ventas sin conexion enviadas despues del cierre.
 *
 * @param {number} corteId
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} Ver `CorteCajaDetalleOut`.
 */
export async function obtenerCorte(corteId, token) {
  return solicitarApi(`/caja/cortes/${corteId}`, { headers: encabezadoAutenticacion(token) });
}

/**
 * Descarga el CSV de los cortes cerrados del rango (RF-073). Administrador y propietario.
 *
 * @param {{desde?: string, hasta?: string}} filtros
 * @param {string} token - Access token JWT.
 * @returns {Promise<{contenido: Blob, nombre: string}>} El archivo y el nombre con que guardarlo.
 * @throws {ApiError} Si el servidor rechaza la descarga.
 */
export async function exportarCortes({ desde, hasta } = {}, token) {
  const parametros = consultaDeCortes({ desde, hasta });
  return descargarCsv(conConsulta("/caja/cortes/exportar", parametros), "los cortes de caja", "cortes_de_caja.csv", token);
}

/**
 * Obtiene el resumen del Dashboard para un rango de dias (HU-03). Requiere rol propietario o administrador.
 *
 * @param {{desde: string, hasta: string}} rango - Dias inclusivos "AAAA-MM-DD" (hora de Bogota).
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} Ver `ResumenDashboardOut`.
 * @throws {ApiError} 422 si el rango esta invertido, es futuro o supera 366 dias.
 */
export async function obtenerResumenDashboard({ desde, hasta }, token) {
  const parametros = new URLSearchParams({ desde, hasta });
  return solicitarApi(`/dashboard/resumen?${parametros.toString()}`, {
    headers: encabezadoAutenticacion(token),
  });
}

/**
 * Lista los productos con stock bajo, del mas critico al menos (RF-013).
 *
 * @param {string} token - Access token JWT.
 * @returns {Promise<Array<{id: number, nombre: string, categoria: string, stock_actual: number,
 *   stock_minimo: number}>>} Ver `AlertaStockOut`.
 */
export async function obtenerAlertasStock(token) {
  return solicitarApi("/dashboard/alertas-stock", { headers: encabezadoAutenticacion(token) });
}

/**
 * Bandeja de notificaciones de stock bajo (Adendo v2, mejora B1: RF-043).
 *
 * @param {string} token - Access token JWT.
 * @param {{soloNoLeidas?: boolean, limite?: number}} [filtros] - Filtros opcionales.
 * @returns {Promise<{no_leidas: number, notificaciones: Array<{id: number, tipo: string, mensaje: string,
 *   leida: boolean, creada_en: string, producto_id: number | null, producto_nombre: string | null}>}>}
 *   Ver `BandejaOut`.
 */
export async function obtenerNotificaciones(token, { soloNoLeidas = false, limite } = {}) {
  const parametros = new URLSearchParams();
  if (soloNoLeidas) {
    parametros.set("solo_no_leidas", "true");
  }
  if (limite) {
    parametros.set("limite", String(limite));
  }
  const consulta = parametros.toString();
  return solicitarApi(`/notificaciones${consulta ? `?${consulta}` : ""}`, {
    headers: encabezadoAutenticacion(token),
  });
}

/**
 * Marca una notificacion como leida (Adendo v2, mejora B1: RF-043).
 *
 * @param {number} notificacionId - Id de la notificacion.
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} La notificacion actualizada.
 * @throws {ApiError} 404 si no existe.
 */
export async function marcarNotificacionLeida(notificacionId, token) {
  return solicitarApi(`/notificaciones/${notificacionId}/leida`, {
    method: "PATCH",
    headers: encabezadoAutenticacion(token),
  });
}

/**
 * Marca como leidas todas las notificaciones pendientes (Adendo v2, mejora B1: RF-043).
 *
 * @param {string} token - Access token JWT.
 * @returns {Promise<{marcadas: number}>} Cuantas se marcaron.
 */
export async function marcarTodasLeidas(token) {
  return solicitarApi("/notificaciones/leer-todas", {
    method: "PATCH",
    headers: encabezadoAutenticacion(token),
  });
}

/**
 * Lista de compras: productos en stock bajo con la cantidad que falta (Adendo v2, mejora B1: RF-044).
 *
 * @param {string} token - Access token JWT.
 * @returns {Promise<{productos: Array<{producto_id: number, nombre: string, categoria: string,
 *   stock_actual: number, stock_minimo: number, faltante: number}>, generado_en: string}>}
 *   Ver `ListaComprasOut`.
 */
export async function obtenerListaCompras(token) {
  return solicitarApi("/dashboard/lista-compras", { headers: encabezadoAutenticacion(token) });
}

/**
 * Envia el ticket ya confirmado al agente de impresion local (best-effort).
 *
 * El agente corre en `localhost` del equipo POS, nunca en el servidor
 * remoto de Bogota (ver printer-agent/README.md). Un fallo aqui NO debe
 * revertir la venta, que ya quedo registrada en el backend: el llamador
 * decide como avisarle al vendedor si la impresion fallo.
 *
 * @param {object} ticket - Datos del ticket (ver `printer-agent/app/schemas.py`).
 * @returns {Promise<{status: string, modo: string}>} Confirmacion del agente.
 * @throws {ApiError} Si el agente no responde o la impresora fallo (503).
 */
export async function imprimirTicket(ticket) {
  const respuesta = await pedir(
    `${PRINTER_AGENT_URL}/imprimir`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(ticket),
    },
    MENSAJE_SIN_AGENTE
  );

  if (!respuesta.ok) {
    let mensaje = "No se pudo imprimir el ticket.";
    try {
      const cuerpoError = await respuesta.json();
      if (cuerpoError && cuerpoError.detail) {
        mensaje = cuerpoError.detail;
      }
    } catch {
      // El cuerpo no era JSON valido; se usa el mensaje generico.
    }
    throw new ApiError(mensaje, respuesta.status);
  }

  return respuesta.json();
}

/**
 * Quienes pueden figurar como vendedor de una venta: vendedores y administradores activos (HU-08, RF-036).
 *
 * @param {string} token - Access token JWT (vendedor o administrador).
 * @returns {Promise<Array<{id: number, nombre: string}>>}
 */
export async function obtenerVendedores(token) {
  return solicitarApi("/ventas/vendedores", { headers: encabezadoAutenticacion(token) });
}

/**
 * Politica de tratamiento de datos vigente: aviso de privacidad, textos de las casillas y politica completa.
 * Su `version` es la que queda como evidencia en cada autorizacion.
 *
 * @param {string} token - Access token JWT (vendedor o administrador).
 * @returns {Promise<object>} Ver `PoliticaOut`.
 */
export async function obtenerPoliticaDatos(token) {
  return solicitarApi("/clientes/politica", { headers: encabezadoAutenticacion(token) });
}

/**
 * Busca y lista clientes con su resumen de compras (HU-07, RF-030, RF-032, RF-033).
 *
 * @param {{q?: string, activo?: boolean, soloUtilizables?: boolean, aceptaPublicidad?: boolean, totalMin?: string,
 *   totalMax?: string, desde?: string, hasta?: string, limite?: number}} [filtros] - Fechas "AAAA-MM-DD" (hora de la tienda).
 * @param {string} token - Access token JWT (vendedor o administrador).
 * @returns {Promise<Array<object>>} Ver `ClienteListadoOut`.
 */
export async function buscarClientes(filtros = {}, token) {
  const parametros = new URLSearchParams();
  const equivalencias = { q: "q", totalMin: "total_min", totalMax: "total_max", desde: "desde", hasta: "hasta", limite: "limite" };
  for (const [campo, nombre] of Object.entries(equivalencias)) {
    if (filtros[campo] !== undefined && filtros[campo] !== null && filtros[campo] !== "") {
      parametros.set(nombre, String(filtros[campo]));
    }
  }
  if (filtros.activo !== undefined) parametros.set("activo", String(filtros.activo));
  if (filtros.soloUtilizables) parametros.set("solo_utilizables", "true");
  if (filtros.aceptaPublicidad !== undefined) parametros.set("acepta_publicidad", String(filtros.aceptaPublicidad));
  const consulta = parametros.toString();
  return solicitarApi(`/clientes${consulta ? `?${consulta}` : ""}`, { headers: encabezadoAutenticacion(token) });
}

/**
 * Ficha de un cliente: datos, total comprado e historial de ventas (RF-032).
 *
 * @param {number} clienteId
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} Ver `ClienteFichaOut`.
 */
export async function obtenerFichaCliente(clienteId, token) {
  return solicitarApi(`/clientes/${clienteId}`, { headers: encabezadoAutenticacion(token) });
}

/**
 * Registra un cliente con la evidencia de su autorizacion de datos (RF-029).
 *
 * @param {{nombre: string, documento: string | null, telefono: string | null, email: string | null,
 *   autorizacion_aceptada: boolean, autorizacion_medio: string}} payload
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} El cliente creado (`ClienteOut`).
 * @throws {ApiError} 409 si el documento ya existe.
 */
export async function crearCliente(payload, token) {
  return solicitarApi("/clientes", opcionesJson("POST", token, payload));
}

/**
 * Edita los datos de un cliente o lo da de baja/alta (RF-030).
 *
 * @param {number} clienteId
 * @param {{nombre?: string, documento?: string | null, telefono?: string | null, email?: string | null,
 *   activo?: boolean}} payload
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} El cliente actualizado.
 */
export async function editarCliente(clienteId, payload, token) {
  return solicitarApi(`/clientes/${clienteId}`, opcionesJson("PATCH", token, payload));
}

/**
 * Asigna o quita el descuento propio de un cliente (solo administrador, RF-025).
 *
 * @param {number} clienteId
 * @param {{tipo: string | null, valor: string | null}} descuento - Ambos en null lo quitan.
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} El cliente actualizado.
 */
export async function guardarDescuentoCliente(clienteId, descuento, token) {
  return solicitarApi(`/clientes/${clienteId}/descuento`, opcionesJson("PUT", token, descuento));
}

/**
 * Lista las solicitudes de los titulares de datos (solo administrador, RF-035).
 *
 * @param {{pendientes?: boolean, estado?: string, clienteId?: number}} [filtros]
 * @param {string} token - Access token JWT.
 * @returns {Promise<Array<object>>} Ver `SolicitudOut`, las mas urgentes primero.
 */
export async function obtenerSolicitudes(filtros = {}, token) {
  const parametros = new URLSearchParams();
  if (filtros.pendientes) parametros.set("pendientes", "true");
  if (filtros.estado) parametros.set("estado", filtros.estado);
  if (filtros.clienteId) parametros.set("cliente_id", String(filtros.clienteId));
  const consulta = parametros.toString();
  return solicitarApi(`/solicitudes-titular${consulta ? `?${consulta}` : ""}`, {
    headers: encabezadoAutenticacion(token),
  });
}

/**
 * Registra una solicitud de un titular; el backend calcula la fecha limite legal (RF-035).
 *
 * @param {{cliente_id: number, tipo: string, descripcion: string | null}} payload
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} La solicitud creada (`SolicitudOut`).
 */
export async function crearSolicitud(payload, token) {
  return solicitarApi("/solicitudes-titular", opcionesJson("POST", token, payload));
}

/**
 * Pone una solicitud en tramite, la resuelve o la rechaza. Resolver una supresion anonimiza al cliente.
 *
 * @param {number} solicitudId
 * @param {{estado: string, respuesta?: string | null}} payload
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} La solicitud actualizada.
 */
export async function actualizarSolicitud(solicitudId, payload, token) {
  return solicitarApi(`/solicitudes-titular/${solicitudId}`, opcionesJson("PATCH", token, payload));
}

/**
 * Estado del enlace de autorregistro (solo administrador, RF-048).
 *
 * @param {string} token - Access token JWT.
 * @returns {Promise<{existe: boolean, token: string | null, activo: boolean, datos_completos: boolean,
 *   faltantes: string[]}>}
 */
export async function obtenerEnlaceAutoregistro(token) {
  return solicitarApi("/autoregistro/enlace", { headers: encabezadoAutenticacion(token) });
}

/**
 * Genera el enlace de autorregistro o lo regenera con un codigo nuevo (el anterior deja de funcionar).
 *
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} El enlace nuevo.
 * @throws {ApiError} 409 si faltan datos del negocio.
 */
export async function generarEnlaceAutoregistro(token) {
  return solicitarApi("/autoregistro/enlace", opcionesJson("POST", token));
}

/**
 * Activa o desactiva el enlace de autorregistro sin cambiar su codigo.
 *
 * @param {boolean} activo
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} El enlace actualizado.
 */
export async function cambiarEstadoEnlaceAutoregistro(activo, token) {
  return solicitarApi("/autoregistro/enlace", opcionesJson("PATCH", token, { activo }));
}

/**
 * Aviso y politica para el formulario publico de autorregistro (sin sesion).
 *
 * @param {string} codigo - Codigo del enlace (parte final de la direccion).
 * @returns {Promise<object>} Ver `PoliticaOut`.
 * @throws {ApiError} 404 si el enlace no esta disponible (desactivado, regenerado o inexistente).
 */
export async function obtenerAutoregistroPublico(codigo) {
  return solicitarApi(`/publico/autoregistro/${encodeURIComponent(codigo)}`);
}

/**
 * Envia el formulario publico de autorregistro (sin sesion). La respuesta es neutra: igual si el cliente ya existia.
 *
 * @param {string} codigo - Codigo del enlace.
 * @param {{nombre: string, documento: string | null, telefono: string | null, email: string | null,
 *   acepta_politica: boolean, acepta_publicidad: boolean, sitio_web: string}} datos
 * @returns {Promise<{mensaje: string}>}
 * @throws {ApiError} 404 si el enlace no esta disponible; 429 si se hicieron demasiados envios.
 */
export async function enviarAutoregistro(codigo, datos) {
  return solicitarApi(`/publico/autoregistro/${encodeURIComponent(codigo)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(datos),
  });
}

/**
 * Datos del negocio para la politica de tratamiento de datos y lo que falta por completar (solo administrador).
 *
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} Ver `NegocioOut`.
 */
export async function obtenerDatosNegocio(token) {
  return solicitarApi("/negocio", { headers: encabezadoAutenticacion(token) });
}

/**
 * Guarda los datos del negocio (reemplaza los anteriores; solo administrador).
 *
 * @param {{nombre: string, documento: string, direccion: string, telefono: string, correo_datos: string,
 *   responsable_datos: string, politica_version: string, politica_fecha: string}} datos
 * @param {string} token - Access token JWT.
 * @returns {Promise<object>} Los datos guardados y su estado (`NegocioOut`).
 */
export async function guardarDatosNegocio(datos, token) {
  return solicitarApi("/negocio", opcionesJson("PUT", token, datos));
}

