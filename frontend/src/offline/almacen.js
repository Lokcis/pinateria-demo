/**
 * Almacen local en IndexedDB para el modo sin conexion (Fase 9).
 *
 * Guarda tres cosas en el navegador del PC de la tienda:
 * - `ventas`: la cola de ventas hechas sin conexion que aun no llegan al servidor (clave: `uuid`).
 * - `catalogo`: copia de los productos activos para vender y buscar sin red (clave: `id`).
 * - `meta`: datos sueltos (configuracion de descuentos, vendedores, consecutivo local) con clave `clave`.
 *
 * NO se guardan datos personales de clientes: sin conexion no se asocia cliente a la venta.
 */

const NOMBRE_BASE = "mm_pos_sin_conexion";
const VERSION_BASE = 1;

let promesaBase = null;

/**
 * Indica si este navegador permite guardar datos locales (IndexedDB).
 *
 * @returns {boolean}
 */
export function almacenDisponible() {
  try {
    return typeof indexedDB !== "undefined" && indexedDB !== null;
  } catch {
    return false;
  }
}

/**
 * Abre (o reutiliza) la base local y crea sus almacenes la primera vez.
 *
 * @returns {Promise<IDBDatabase>}
 * @throws {Error} Si el navegador no permite IndexedDB (ej. ventana privada de algunos navegadores).
 */
function abrirBase() {
  if (promesaBase) return promesaBase;
  promesaBase = new Promise((resolver, rechazar) => {
    if (!almacenDisponible()) {
      rechazar(new Error("Este navegador no permite guardar datos para trabajar sin conexión."));
      return;
    }
    const peticion = indexedDB.open(NOMBRE_BASE, VERSION_BASE);
    peticion.onupgradeneeded = () => {
      const base = peticion.result;
      if (!base.objectStoreNames.contains("ventas")) base.createObjectStore("ventas", { keyPath: "uuid" });
      if (!base.objectStoreNames.contains("catalogo")) base.createObjectStore("catalogo", { keyPath: "id" });
      if (!base.objectStoreNames.contains("meta")) base.createObjectStore("meta", { keyPath: "clave" });
    };
    peticion.onsuccess = () => resolver(peticion.result);
    peticion.onerror = () => rechazar(peticion.error || new Error("No se pudo abrir el almacenamiento local."));
    peticion.onblocked = () => rechazar(new Error("El almacenamiento local está bloqueado por otra pestaña."));
  }).catch((error) => {
    promesaBase = null; // permite reintentar
    throw error;
  });
  return promesaBase;
}

/**
 * Ejecuta una transaccion y resuelve cuando termina de confirmarse.
 *
 * @template T
 * @param {string[]} almacenes - Nombres de los almacenes que toca.
 * @param {"readonly" | "readwrite"} modo
 * @param {(tx: IDBTransaction) => IDBRequest | undefined} operacion - Recibe la transaccion; puede devolver una
 *   peticion cuyo resultado se entrega.
 * @returns {Promise<T>}
 */
async function transaccion(almacenes, modo, operacion) {
  const base = await abrirBase();
  return new Promise((resolver, rechazar) => {
    const tx = base.transaction(almacenes, modo);
    let resultado;
    const peticion = operacion(tx);
    if (peticion) {
      peticion.onsuccess = () => {
        resultado = peticion.result;
      };
    }
    tx.oncomplete = () => resolver(resultado);
    tx.onerror = () => rechazar(tx.error || new Error("Falló una operación del almacenamiento local."));
    tx.onabort = () => rechazar(tx.error || new Error("Se canceló una operación del almacenamiento local."));
  });
}

/**
 * Lee todos los registros de un almacen.
 *
 * @param {"ventas" | "catalogo" | "meta"} almacen
 * @returns {Promise<Array<object>>}
 */
export function obtenerTodos(almacen) {
  return transaccion([almacen], "readonly", (tx) => tx.objectStore(almacen).getAll());
}

/**
 * Lee un registro por su clave.
 *
 * @param {"ventas" | "catalogo" | "meta"} almacen
 * @param {string | number} clave
 * @returns {Promise<object | undefined>}
 */
export function obtener(almacen, clave) {
  return transaccion([almacen], "readonly", (tx) => tx.objectStore(almacen).get(clave));
}

/**
 * Guarda (o reemplaza) un registro.
 *
 * @param {"ventas" | "catalogo" | "meta"} almacen
 * @param {object} registro
 * @returns {Promise<void>}
 */
export async function guardar(almacen, registro) {
  await transaccion([almacen], "readwrite", (tx) => tx.objectStore(almacen).put(registro));
}

/**
 * Reemplaza TODO el contenido de un almacen por los registros dados, en una sola transaccion
 * (si algo falla, queda lo anterior).
 *
 * @param {"ventas" | "catalogo" | "meta"} almacen
 * @param {Array<object>} registros
 * @returns {Promise<void>}
 */
export async function reemplazarTodos(almacen, registros) {
  await transaccion([almacen], "readwrite", (tx) => {
    const tienda = tx.objectStore(almacen);
    tienda.clear();
    registros.forEach((registro) => tienda.put(registro));
  });
}

/**
 * Borra un registro por su clave.
 *
 * @param {"ventas" | "catalogo" | "meta"} almacen
 * @param {string | number} clave
 * @returns {Promise<void>}
 */
export async function borrar(almacen, clave) {
  await transaccion([almacen], "readwrite", (tx) => tx.objectStore(almacen).delete(clave));
}

/**
 * Suma 1 a un contador guardado en `meta` y devuelve el nuevo valor, de forma atomica.
 *
 * @param {string} clave
 * @returns {Promise<number>} El valor despues de sumar (empieza en 1).
 */
export async function incrementarContador(clave) {
  const base = await abrirBase();
  return new Promise((resolver, rechazar) => {
    const tx = base.transaction(["meta"], "readwrite");
    const tienda = tx.objectStore("meta");
    let nuevo = 1;
    const lectura = tienda.get(clave);
    lectura.onsuccess = () => {
      nuevo = (lectura.result?.valor ?? 0) + 1;
      tienda.put({ clave, valor: nuevo });
    };
    tx.oncomplete = () => resolver(nuevo);
    tx.onerror = () => rechazar(tx.error);
    tx.onabort = () => rechazar(tx.error);
  });
}

/**
 * Cierra la conexion y olvida la base abierta. Solo para las pruebas, que borran la base entre casos.
 *
 * @returns {Promise<void>}
 */
export async function reiniciarAlmacenParaPruebas() {
  if (promesaBase) {
    try {
      (await promesaBase).close();
    } catch {
      // ya estaba cerrada o nunca abrio
    }
    promesaBase = null;
  }
  if (almacenDisponible()) {
    await new Promise((resolver) => {
      const peticion = indexedDB.deleteDatabase(NOMBRE_BASE);
      peticion.onsuccess = peticion.onerror = peticion.onblocked = () => resolver();
    });
  }
}
