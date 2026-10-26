# Modo sin conexión (Fase 9)

**Versión 1.0 — 14-10-2026.** Qué hace el punto de venta cuando se cae internet en la tienda, cómo está construido y cómo se opera. Implementa los requerimientos RF-050 a RF-057 y la historia HU-11 (ver `01` y `02`).

## 1. Qué resuelve

El servidor está fuera de la tienda y esta llega a él por internet (Cloudflare Tunnel). Antes de la Fase 9, si se caía internet en la tienda —o el servidor o el túnel— **no se podía vender**: el POS dependía del servidor para buscar productos y registrar cada venta. La mitigación era un enlace de respaldo (router 4G).

Ahora el POS **sigue vendiendo sin conexión**: la venta se guarda en el equipo de la tienda, el ticket se imprime igual (el agente de impresión es local) y, cuando vuelve la conexión, la venta se envía sola al servidor. No hace falta que el vendedor haga nada especial.

El router 4G sigue siendo recomendable (evita tener que vender sin conexión), pero ya no es la única defensa.

## 2. Qué se puede y qué no se puede hacer sin conexión

| Acción | Sin conexión |
|---|---|
| Buscar productos (por nombre, categoría o código de barras / lector) | Sí, en una copia del catálogo guardada en el equipo |
| Armar la venta, calcular el total y redondear a $50 | Sí |
| Pagos mixtos, vueltas, Nequi y Daviplata | Sí |
| Descuento general y descuento manual (con los topes) | Sí, con la configuración guardada la última vez que hubo conexión |
| Elegir quién atendió (vendedor) | Sí, con la lista guardada |
| Imprimir el ticket | Sí (el agente es local); sale con un número local, por ejemplo `SC-0003` |
| Asociar un cliente a la venta o registrar clientes | **No.** Los datos de clientes no se guardan en el equipo (Habeas Data) |
| Historial del día, inventario, compras, proveedores, ganancias, Dashboard | **No** (necesitan el servidor) |
| Iniciar sesión | **No.** Por eso no se debe cerrar sesión mientras no hay conexión |

Las ventas hechas sin conexión no aparecen en el Dashboard del propietario ni en el historial hasta que se envían. Al enviarse, quedan con la hora en que se hicieron en la tienda.

## 3. Cómo funciona

1. **Mientras hay conexión**, el POS guarda en el equipo (en IndexedDB, dentro del navegador): los productos activos (sin costos), el descuento general con sus topes y la lista de vendedores. Lo refresca al abrir, al volver la conexión y cada 10 minutos.
2. **Detección de la pérdida de conexión.** `navigator.onLine` solo dice si hay red, no si el servidor responde. Por eso el POS se considera sin conexión cuando el navegador lo avisa **o** cuando una petición falla por red, se agota (12 s al confirmar una venta) o responde 502/503/504 o un 52x de Cloudflare. Mientras no hay conexión, o quedan ventas por enviar, consulta `/health` cada 20 segundos.
3. **Al confirmar una venta**, cada una lleva un identificador único (`uuid_cliente`).
   - Con conexión: se envía a `POST /ventas`, como siempre.
   - Sin conexión, o si el servidor no responde a tiempo: se guarda en la cola local con su payload completo, la hora real, los precios y el descuento que vio el cliente, y se imprime el ticket con el número local. La pantalla queda lista para la venta siguiente.
4. **Al volver la conexión** (el POS lo confirma con `/health`), se envían las ventas guardadas de la más antigua a la más reciente.
   - Si el servidor las acepta, salen de la cola.
   - Si el servidor ya tenía una (se perdió la respuesta de un envío anterior), la reconoce por su identificador y **no la duplica ni vuelve a descontar stock**.
   - Si la conexión se vuelve a caer, se detiene y reintenta más tarde; no se pierde nada.
   - Si la sesión venció (el token dura 8 horas), se detiene y pide iniciar sesión de nuevo; la cola se conserva.
   - Si el servidor **rechaza** una venta (sin stock, descuento fuera de los topes, producto desactivado…), queda como **"Necesita revisión"** con el motivo. No se reintenta sola ni frena a las demás.
5. **Quién envía qué.** Un vendedor envía solo las ventas que guardó él (así cada venta queda registrada por quien la hizo); un administrador envía las de todos. Las ventas de otra persona esperan a que inicie sesión en el equipo (o a que entre un administrador).

## 4. Garantías

| Garantía | Cómo se logra |
|---|---|
| Una venta no se duplica nunca | Cada venta tiene un `uuid_cliente` y la base tiene un índice único sobre él. Reenviar devuelve la venta existente (200) sin tocar el stock. También cubre dos envíos simultáneos (el índice deja pasar uno solo) |
| Una venta no se pierde | Se guarda en IndexedDB antes de mostrar el aviso al vendedor y sobrevive a cerrar la pestaña o reiniciar el equipo. Solo sale de la cola cuando el servidor la acepta o una persona la descarta confirmando |
| El servidor sigue siendo la autoridad | Valida stock, pagos (la suma debe igualar el total), topes, vendedor y cliente igual que una venta normal; el stock nunca queda negativo y no hay ventas parciales |
| El cliente paga lo que se le dijo | La venta conserva el precio y el descuento general que vio el cliente, aunque el catálogo o el descuento hayan cambiado mientras tanto |
| La venta cae en su día | Conserva la hora en que se hizo en la tienda. El servidor rechaza horas futuras (más de 5 minutos) y ventas de más de 7 días (`VENTAS_SIN_CONEXION_DIAS_MAX`) |
| Se puede auditar | Las ventas enviadas después quedan marcadas (`ventas.sin_conexion`, `ventas.sincronizada_en`) y el historial las rotula "Sin conexión" |

## 5. Decisiones de diseño

| Decisión | Razón |
|---|---|
| Guardar en IndexedDB y no en el Service Worker | Las ventas son datos de la aplicación, no archivos. El Service Worker sigue guardando solo la interfaz (para que la aplicación abra sin internet) y nunca respuestas de la API |
| Todas las ventas llevan `uuid_cliente`, también las normales | Si se pierde la respuesta de una venta normal, el POS no sabe si el servidor la registró. Guardarla y reenviarla con el mismo identificador es seguro |
| El precio de la línea y el descuento general viajan en la venta sin conexión | Si no, un cambio de precio durante el corte haría que los pagos no sumaran el total y la venta ya cobrada quedaría atascada. El riesgo (un usuario del POS podría fijar un precio a mano por la API) se acota con: solo se aceptan en ventas marcadas sin conexión, el servidor valida que sean ≥ 0, la hora tiene tope, y la venta queda marcada y auditable |
| Sin conexión no se asocia cliente | Evita guardar datos personales de clientes en el navegador del equipo (Habeas Data). Si la red se cae justo al confirmar una venta que ya tenía cliente, se guarda con su `cliente_id` (un número, no datos personales) |
| Los conflictos los resuelve una persona | La venta ya ocurrió: el cliente pagó y se llevó el producto. Descartarla o forzar stock negativo sería peor. Queda visible con el motivo; se corrige la causa (por ejemplo, registrar el stock que faltaba) y se reintenta |
| No se borra la cola al cerrar sesión | Cerrar sesión no debe perder ventas. Se envían al iniciar sesión con conexión. Por eso el POS pide confirmación al cerrar sesión sin conexión o con ventas guardadas |
| Descartar exige confirmar y solo existe para ventas con problema | Descartar borra una venta real; no se ofrece para las que están por enviarse |
| Consulta a `/health` y no solo `navigator.onLine` | El túnel o el servidor pueden estar caídos con la red de la tienda funcionando |
| Numeración local `SC-0001`… por equipo | El ticket de una venta sin conexión no puede llevar un número que todavía no existe. Al enviarse, la venta recibe su número normal y el historial la muestra como "Sin conexión" |

## 6. Qué se guarda en el equipo

| Dato | Contenido | Se borra |
|---|---|---|
| Catálogo | Productos activos: nombre, categoría, código de barras, tipo, precio, stock. **Sin costos ni recetas** | Se reemplaza completo en cada descarga |
| Configuración de descuentos | Descuento general y topes del vendedor | Se reemplaza en cada descarga |
| Vendedores | Id y nombre | Se reemplaza en cada descarga |
| Ventas pendientes | Productos, cantidades, precios, pagos, vendedor, hora e identificador. **Sin datos de clientes** | Al enviarse con éxito o al descartarlas una persona |
| Consecutivo local | El último `SC-####` usado | Nunca (es solo un contador) |

Todo vive en el navegador del equipo de la tienda (base `mm_pos_sin_conexion`). Conviene usar siempre el mismo navegador (Chrome o Edge); en una ventana privada puede no funcionar y el POS lo avisa.

## 7. Contrato del backend

`POST /ventas` acepta dos campos nuevos y un campo nuevo por línea. Todos son opcionales; quien no los envía vende como siempre.

| Campo | Qué es |
|---|---|
| `uuid_cliente` | Identificador de la venta (UUID). Reenviar el mismo devuelve la venta existente con **200** (la primera vez responde 201) |
| `sin_conexion` | `{ "fecha": "<ISO 8601 con zona horaria>" }`: marca la venta como hecha sin conexión y trae la hora real. Exige `uuid_cliente` |
| `detalles[].precio_unitario` | Precio que vio el cliente. Solo se acepta con `sin_conexion`; sin él responde 422 |
| `descuento` (`origen: general`) | Con `sin_conexion` se respeta el `tipo` y el `valor` enviados, aunque el general ya no esté activo o haya cambiado |

Respuestas: 201 venta creada; 200 venta ya registrada; 409 sin stock (o el descuento general cambió, en ventas normales); 422 fecha futura o con más de 7 días, pagos que no suman, descuento fuera de los topes, cliente o vendedor no válidos; 403 propietario. La respuesta (`VentaOut`) incluye `uuid_cliente` y `sin_conexion`; el historial (`VentaHistorialOut`) incluye `sin_conexion`.

**Migración 0008** (`backend/alembic/versions/0008_ventas_sin_conexion.py`): agrega a `ventas` las columnas opcionales `uuid_cliente` (UUID, índice único `ux_ventas_uuid_cliente`), `sin_conexion` (booleano, por defecto falso) y `sincronizada_en`. **No transforma datos**: las ventas anteriores quedan con `uuid_cliente` NULL (el índice único admite varios NULL). Se ensayó subir, bajar y volver a subir sobre una base con una venta previa.

## 8. Código

| Pieza | Dónde |
|---|---|
| Almacén IndexedDB (ventas, catálogo, meta) | `frontend/src/offline/almacen.js` |
| Copia del catálogo y búsqueda local | `frontend/src/offline/catalogo-local.js` |
| Cola de ventas, numeración local y armado del payload | `frontend/src/offline/cola-ventas.js` |
| Envío de la cola y clasificación de errores | `frontend/src/offline/sincronizador.js` |
| Estado de la conexión, cola y envío automático (proveedor de React) | `frontend/src/context/sin-conexion-context.jsx` |
| Barra de estado y lista de ventas guardadas | `frontend/src/components/estado-sincronizacion.jsx` |
| Qué cuenta como falla de conexión y el `uuid` | `frontend/src/utils/conexion.js` |
| Ticket de una venta sin conexión | `construirTicketLocal` en `frontend/src/utils/ticket.js` |
| Endpoint, idempotencia y validación de la hora | `backend/app/routers/ventas.py` |
| Agente de impresión (`referencia`) | `printer-agent/app/schemas.py`, `ticket.py` |

El `SinConexionProvider` solo se monta para los roles con acceso al POS (vendedor y administrador). Los componentes que lo usan funcionan también sin él (quedan "siempre en línea"), lo que permite probarlos sueltos.

## 9. Agente de impresión

El ticket de una venta sin conexión no tiene número de venta todavía. El agente acepta `venta_id` opcional y un campo nuevo `referencia` (letras, números y guion, hasta 30 caracteres, apto para nombre de archivo): imprime `Venta SC-0003` en lugar de `Venta #12`. **El agente del PC del POS debe actualizarse antes de usar el modo sin conexión** (con la versión anterior, el ticket de una venta sin conexión no se imprime y el POS avisa el error; la venta sí queda guardada). Los tickets de ventas normales no cambian y funcionan con ambas versiones.

## 10. Operación

**Lo que ve el vendedor**

- Una barra roja arriba: "Sin conexión con el servidor. Puedes seguir vendiendo…", con la antigüedad del catálogo guardado y el recordatorio de no cerrar sesión.
- Al confirmar una venta: "Venta SC-0003 guardada sin conexión. Se enviará sola cuando vuelva la red." y el ticket sale por la impresora.
- Al volver la conexión: una barra amarilla "Enviando ventas guardadas…" y luego un aviso verde "Se enviaron N ventas guardadas sin conexión".
- "Ver ventas guardadas": lista con su número, hora, total y productos; permite reimprimir el ticket.

**Cuando una venta queda en "Necesita revisión"** (lo más probable: stock insuficiente porque el inventario del sistema no estaba al día)

1. El vendedor avisa al administrador; la barra le muestra el motivo exacto.
2. El administrador corrige la causa: registra el stock que faltaba (ajuste de inventario o compra recibida), reactiva el producto, o ajusta los topes de descuento.
3. En "Ver ventas guardadas", pulsa **Reintentar**. Si ya no tiene arreglo (por ejemplo, la venta se registró a mano), **Descartar** la borra de la cola tras confirmar; esa venta no quedará registrada en el sistema.

**Si la sesión vence con ventas guardadas:** la barra lo dice y ofrece "Iniciar sesión de nuevo"; al entrar, se envían solas.

## 11. Límites conocidos

- **No hay inicio de sesión sin conexión.** Si se cierra sesión (o vence el token de 8 horas) durante un corte, no se puede volver a entrar hasta que vuelva la conexión. Con la sesión abierta se puede vender sin problema; la aplicación abre aunque se recargue la página sin internet (la interfaz queda guardada por el Service Worker).
- **El stock mostrado puede estar desactualizado.** Sin conexión no se bloquea una venta por stock: la decide el servidor al enviarla (conflicto si no alcanza). Es una decisión consciente: la venta física ya ocurrió.
- **Un solo equipo por cola.** La cola vive en el navegador de cada equipo; no se comparte entre equipos.
- **El reloj del equipo importa.** La hora de la venta es la del equipo de la tienda; si va muy adelantado, el servidor la rechaza (futuro). Mantener la hora automática.
- **Los totales del Dashboard no incluyen las ventas pendientes** hasta que se envían.
- **Navegadores.** Probado con Edge (Chromium). Requiere IndexedDB; en ventanas privadas de algunos navegadores no está disponible y el POS lo avisa.

## 12. Pruebas

| Capa | Qué cubre | Cantidad |
|---|---|---|
| Backend (`backend/tests/test_fase9_sin_conexion.py`) | Idempotencia y reenvío, carrera de dos envíos simultáneos, hora real (futuro, antigua, sin zona), precio y descuento general vistos por el cliente, reglas de stock, pagos y topes, historial, vendedor elegido | 26 |
| Agente (`printer-agent/tests/test_agente.py`) | Ticket con referencia local, validación del nombre, archivo del modo simulado | 8 |
| Frontend | Cola, catálogo y búsqueda local, sincronizador (orden, conexión, sesión vencida, conflictos, por usuario), proveedor (conexión, envío automático, ping), pantalla de pago sin conexión, búsqueda sin conexión, barra de estado, historial, cierre de sesión | 100 |
| Extremo a extremo (manual, con Edge real) | Service Worker, abrir la aplicación sin internet, vender, recargar con la cola y enviar al volver la red; reenvío tras perder la respuesta sin duplicar | — |

La guía de aceptación con el vendedor es la sección 8 de `10-pruebas-de-aceptacion.md`.

## 13. Despliegue

1. **Antes**, actualizar el agente de impresión en el PC del POS (`actualizar.bat`).
2. Aprobar la migración: `gh variable set MIGRACIONES_APROBADAS --body "0005,0006,0007,0008"` (la 0008 no transforma datos; aun así el despliegue continuo se detiene hasta que se apruebe). Hacerlo **antes** de fusionar a `main`: el workflow lee la variable al arrancar.
3. Fusionar a `dev` y, cuando se apruebe, a `main` (el servidor sigue `main`). El despliegue continuo hace respaldo, `migrate` y verifica `/api/health`.
4. La primera vez que cada equipo abre la aplicación con conexión, descarga el catálogo. Hay que **abrir el POS con conexión al menos una vez** antes de depender del modo sin conexión.
5. Probar el modo sin conexión en la tienda (sección 8 de `10`) antes del primer corte real.

## Control de versiones

| Versión | Fecha | Autor | Cambios |
|---|---|---|---|
| 1.0 | 14-10-2026 | Santiago Chávez López | Versión inicial: modo sin conexión (Fase 9), migración 0008, agente de impresión con referencia local y pruebas |
