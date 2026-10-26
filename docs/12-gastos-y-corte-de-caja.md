# Gastos y corte de caja (Adendo v3)

**Versión 1.5 — 21-10-2026.** Qué se va a construir para llevar los gastos del negocio y el dinero de la caja: cómo funciona, quién puede hacer qué, qué tablas lleva y en qué fases se entrega. Implementa los requerimientos RF-059 a RF-075 y las historias HU-12 y HU-13 (ver `01` y `02`). **Estado: las tres fases están implementadas (G1 gastos, migración 0009; G2 caja y corte, migración 0010; G3 ganancia neta, sin migración) y están desplegadas en producción desde el 21-10-2026; falta la aceptación con el negocio.** Decisiones del negocio del 19-10-2026.

## 1. Qué resuelve

Hoy el sistema sabe cuánto se vende y cuánto cuesta lo vendido (Ganancias, Fase A3), pero no cuánto gasta el negocio ni cuánto efectivo debe haber en la caja. El negocio pidió una ventana de **Gastos** y, con ella, el **dinero en caja** y el **corte de caja**. Con esto:

- Cualquier gasto del negocio (arriendo, servicios, transporte, nómina, compras de mercancía…) queda registrado con su categoría y su forma de pago.
- Las compras a proveedores ya recibidas se ven en la misma lista, unificadas con los demás gastos.
- La ganancia deja de ser solo el margen bruto: se muestra la **ganancia neta**.
- Al abrir y cerrar la caja, el sistema calcula cuánto efectivo debería haber y lo compara con lo contado.

## 2. Decisiones del negocio (19-10-2026)

| Tema | Decisión |
|---|---|
| Categorías de gasto | **Editables**: pueden aparecer gastos nuevos, así que el administrador crea, renombra y desactiva categorías. |
| Quién ve e ingresa | El **administrador** ve e ingresa todo. El **propietario** solo ve. El **vendedor** solo ingresa, y puede editar o anular únicamente lo que él mismo registró. |
| Compras a proveedores | **Cuentan como gasto** y se **unifican** en la ventana de Gastos. |
| Ganancia | Se muestra la **ganancia neta**. |
| Forma de pago y caja | Cada gasto lleva su forma de pago, para la caja. Se agrega el apartado **Dinero en caja** para hacer el **corte de caja**. |
| Gastos recurrentes y comprobantes | Se dejan para una **Fase 2** (sección 10); en esta entrega solo gastos, caja y ganancia neta. |
| Borrar | Se **anula**, no se borra: queda el historial. |
| Sin conexión | Los gastos y la caja **solo se usan con conexión**; el modo sin conexión de las ventas (Fase 9) no cambia. |
| Exportar | Se puede **exportar** (CSV, que abre Excel). |
| Precio | Lo gestiona el desarrollador con el negocio; no está en este documento. |

## 3. Fases

El Adendo v3 se entrega en tres fases pequeñas (nombres G1 a G3 para no confundirlas con las Fases 0 a 9 ni con las A1 a A3 del Adendo v2).

| Fase | Qué entrega | RF | Migración |
|---|---|---|---|
| **G1 – Gastos** | Ventana Gastos: categorías editables, alta, edición y anulación con permisos por rol, compras recibidas unificadas (con su forma de pago), filtros, totales y exportación. | RF-059 a RF-066, RF-068, RF-075 | 0009 |
| **G2 – Caja y corte** | Apertura de caja, dinero en caja, ingresos y retiros, corte de caja con su historial y exportación. | RF-069 a RF-074 | 0010 |
| **G3 – Ganancia neta** | Ganancia neta y resultado de caja en Ganancias (administrador) y en el Dashboard (propietario). Sin tablas nuevas. | RF-067 | — |

Orden: G1 → G3 → G2 es posible (la ganancia neta solo necesita los gastos); el orden natural es G1, G2, G3. Cada fase se cierra con aceptación del negocio.

## 4. Quién puede hacer qué

| Acción | Administrador | Vendedor | Propietario |
|---|---|---|---|
| Registrar un gasto | Sí (con la fecha que elija, no futura) | Sí (siempre con la fecha de hoy) | No |
| Ver gastos | Todos | **Solo los suyos** | Todos (solo lectura) |
| Editar un gasto | Cualquiera | Solo los suyos, si su corte no está cerrado | No |
| Anular un gasto (con motivo) | Cualquiera | Solo los suyos, si su corte no está cerrado | No |
| Ver compras unificadas y totales por categoría | Sí | No | Sí |
| Crear, renombrar y desactivar categorías | Sí | No (solo las elige) | No |
| Exportar gastos y cortes | Sí | No | Sí |
| Ganancia neta y resultado de caja | Sí (pestaña Ganancias) | No | Sí (Dashboard) |
| Abrir caja, registrar ingresos y retiros, cerrar caja | Sí | Sí | No |
| Ver el historial de cortes | Todos | Los que abrió o cerró él | Todos (solo lectura) |

El vendedor nunca ve costos, ganancias, proveedores ni totales del negocio: solo su propia lista de gastos y la caja.

## 5. Cómo funciona

### 5.1 Gastos

1. El usuario abre **Gastos** y pulsa **Nuevo gasto**: categoría (de la lista), descripción, monto, forma de pago (efectivo, tarjeta o transferencia; en transferencia, la plataforma Nequi o Daviplata), a quién se pagó (opcional, texto libre) y fecha.
2. El monto va en pesos enteros; en **efectivo** debe ser múltiplo de $50, igual que las ventas (decisión 16 del Anexo B de `01`). Los textos se guardan con la primera letra en mayúscula (RF-058).
3. **Editar**: se cambian categoría, descripción, monto, forma de pago, beneficiario y (solo el administrador) fecha. Queda quién y cuándo lo editó por última vez.
4. **Anular**: pide un motivo. El gasto sigue en la lista, tachado, con quién lo anuló, cuándo y por qué, y deja de sumar en todos los totales. Un gasto anulado no se reactiva: si fue un error de la anulación, se registra de nuevo.
5. Un gasto no se borra nunca.

### 5.2 Compras unificadas

- Una compra a proveedor entra a la lista de Gastos **cuando se recibe**, en la categoría de sistema **Compra de mercancía**, con el total de la compra y la fecha de recepción. Las compras pendientes o canceladas no cuentan.
- Aparece como fila de solo lectura (con enlace a Compras); no se edita desde Gastos. Una compra ya recibida no se puede cancelar (la cancelación solo existe antes de recibirla), así que no hay que anularla.
- Al **recibir** una compra se pide su **forma de pago** (efectivo, tarjeta o transferencia con plataforma). Las compras recibidas antes de este cambio no tienen forma de pago: cuentan en los totales de gastos, pero no afectan la caja.
- Solo el administrador y el propietario ven las compras en esta lista; el vendedor no (el directorio de proveedores sigue siendo exclusivo del administrador, RF-021).

### 5.3 Ganancia neta

- **Ganancia neta** = margen bruto (Fase A3: ventas con descuento menos el costo de lo vendido) − **gastos operativos** vigentes del período.
- Los gastos operativos son todos los gastos **menos las compras de mercancía**: el costo de lo comprado ya entra en el margen cuando se vende (costo de lo vendido); contarlo también al comprarlo lo duplicaría y castigaría a la ganancia cada vez que se abastece el inventario.
- Además se muestra el **resultado de caja** del período = ventas cobradas − **todos** los gastos (incluidas las compras recibidas). Es una cifra de flujo de dinero, útil para ver cuánto entró y cuánto salió, no una ganancia contable.
- Las ventas sin costo cargado siguen quedando fuera del margen; si las hay, la ganancia neta lleva el aviso "incompleta, faltan costos".
- El período usa los mismos rangos del Dashboard (Hoy, Ayer, Semana, Mes, 3 meses, 6 meses, Año o personalizado) y la fecha del gasto en hora de Bogotá.

### 5.4 Caja y corte de caja

Hay **una sola caja** (la de la tienda). Solo puede haber un corte abierto a la vez.

1. **Abrir caja:** el usuario escribe el efectivo con que arranca (la base, múltiplo de $50). Queda registrada la hora y quién la abrió.
2. **Dinero en caja (en vivo).** Mientras está abierta, el apartado Caja muestra:

   `efectivo esperado = base + ventas en efectivo + ingresos − gastos en efectivo − compras recibidas en efectivo − retiros`

   - *Ventas en efectivo*: suma de los pagos en efectivo de las ventas hechas desde la apertura (el monto que abona a la venta; las vueltas ya están descontadas). Las ventas sin conexión cuentan por la hora en que se hicieron.
   - *Gastos y compras en efectivo*: los registrados (vigentes, no anulados) desde la apertura.
   - *Ingresos y retiros*: movimientos manuales con motivo (por ejemplo, "Consignación al banco" o "Retiro del propietario"); sin ellos, el corte siempre saldría descuadrado.
   - También muestra, solo como información, lo vendido por **tarjeta** y por **transferencia** (Nequi y Daviplata) en el mismo período, para compararlo con el datáfono y el banco.
3. **Cerrar caja (corte):** el usuario cuenta el efectivo y lo escribe (múltiplo de $50) con observaciones opcionales. El sistema calcula la **diferencia = contado − esperado** (positiva: sobra; negativa: falta) y guarda una **foto** de todas las cifras. El corte cerrado **no se modifica**.
4. **Seguridad del corte:**
   - Después del cierre, el vendedor ya no puede editar ni anular los gastos que cubre; el administrador sí puede, pero el corte conserva la foto de cuando se cerró.
   - Una venta hecha sin conexión que se envía **después** del cierre no altera el corte: se muestra en su ficha como "ventas sin conexión enviadas después del cierre". Por eso, **el POS no deja cerrar la caja si ese equipo tiene ventas guardadas sin enviar**.
5. **Historial de cortes:** lista con fecha, quién abrió y cerró, esperado, contado y diferencia; se puede abrir cada uno y exportar.

### 5.5 Sin conexión

Los gastos, la caja y el corte requieren conexión con el servidor. No se guardan en la cola del POS, no se usa IndexedDB para ellos y la cola de ventas de la Fase 9 no cambia (RF-068). Si no hay conexión, esas pantallas lo avisan y se pueden usar al volver.

### 5.6 Exportar

- **Gastos:** archivo CSV del rango y los filtros elegidos, con una fila por gasto o compra: fecha, origen (gasto o compra), categoría, descripción, beneficiario, forma de pago, plataforma, monto, estado (vigente o anulado), quién lo registró y motivo de anulación. Por defecto no incluye los anulados (se puede pedir).
- **Cortes de caja:** una fila por corte con las cifras de la foto.
- Formato: UTF-8 con BOM y punto y coma como separador, para que Excel en español lo abra con las tildes y las columnas bien.

## 6. Modelo de datos

El detalle de columnas, restricciones e índices está en `03`, sección 8 (**fuente de los nombres**). Resumen:

| Elemento | Qué es | Fase | Migración |
|---|---|---|---|
| `categorias_gasto` | Categorías editables; `es_sistema` marca "Compra de mercancía" (no se edita ni se desactiva). Se siembran categorías iniciales. | G1 | 0009 |
| `gastos` | Un gasto: fecha, categoría, descripción, beneficiario, monto, forma de pago y plataforma, quién lo registró, edición y anulación. | G1 | 0009 |
| `compras.metodo_pago`, `compras.plataforma`, `compras.recibida_en` | Cómo y cuándo se pagó y recibió una compra. Opcionales. | G1 | 0009 |
| `vw_gastos_unificados` | Vista que une gastos y compras recibidas. | G1 | 0009 |
| `cortes_caja` | Apertura y cierre de caja, con la foto del corte. | G2 | 0010 |
| `movimientos_caja` | Ingresos y retiros manuales de una caja abierta. | G2 | 0010 |

Ninguna migración transforma datos existentes: agregan tablas, columnas opcionales y la siembra de categorías. Aun así, antes de aplicarlas en producción se hace el respaldo manual de costumbre y se aprueban en `MIGRACIONES_APROBADAS` (el valor pasa a terminar en `,0009` y luego `,0010`).

## 7. API prevista

Los nombres siguen el estilo de los routers actuales. Abajo se anota lo que cambió al construir la G1, la G2 y la G3.

| Método y ruta | Quién | Qué hace |
|---|---|---|
| `GET /categorias-gasto` | Administrador, vendedor, propietario | Lista las categorías (el vendedor ve solo las activas). |
| `POST /categorias-gasto`, `PATCH /categorias-gasto/{id}` | Administrador | Crea, renombra, activa o desactiva. |
| `GET /gastos` | Administrador, vendedor (solo los suyos), propietario | Lista con filtros (rango, categoría, forma de pago, estado) y paginación; el administrador y el propietario reciben también las compras. |
| `POST /gastos` | Administrador, vendedor | Registra un gasto. |
| `PATCH /gastos/{id}` | Administrador; vendedor (propios, sin corte cerrado) | Edita. |
| `POST /gastos/{id}/anular` | Igual que editar | Anula con `motivo`. |
| `GET /gastos/resumen` | Administrador, propietario | Totales por categoría y por forma de pago, incluidas las compras. |
| `GET /gastos/exportar` | Administrador, propietario | CSV del rango y los filtros. |
| Recepción de compras (existente) | Administrador | Ahora recibe la forma de pago de la compra. |
| `GET /caja/actual` | Administrador, vendedor, propietario | Estado de la caja y efectivo esperado en vivo. |
| `POST /caja/abrir`, `POST /caja/movimientos`, `POST /caja/cerrar` | Administrador, vendedor | Abre con la base, registra ingresos y retiros, cierra con el efectivo contado. |
| `GET /caja/cortes`, `GET /caja/cortes/{id}`, `GET /caja/cortes/exportar` | Administrador, propietario (el vendedor, los suyos) | Historial, detalle y exportación. |
| `GET /ganancias` (existente) | Administrador, propietario | Agrega gastos operativos, ganancia neta y resultado de caja. |

Toda respuesta de gastos, compras y ganancias valida el rol en el JWT; un rol sin permiso recibe 403.

**Cómo quedó la G1 (lo que cambió respecto a la API prevista):**

- `GET /gastos/{id}` (administrador, vendedor y propietario): un gasto; el vendedor recibe 404 si no es suyo.
- Cada fila de `GET /gastos` trae `editable` (true solo para un gasto vigente que quien consulta puede modificar), quién lo registró, quién lo editó y quién lo anuló. La lista se pagina (`pagina`, `tamano_pagina`, hasta 200) y filtra por `desde`, `hasta`, `categoria_id`, `metodo_pago`, `estado` (vigente o anulado) y `origen` (gasto o compra).
- `GET /gastos/resumen` devuelve `total`, `total_compras` (la categoría de sistema: compras recibidas y gastos manuales de esa categoría), `total_operativo` (`total` menos `total_compras`, lo que restará la ganancia neta en la G3), y los totales por categoría y por forma de pago. Solo cuenta lo vigente.
- `GET /gastos/exportar` acepta los mismos filtros y `incluir_anulados`; el nombre del archivo viaja en `Content-Disposition` (expuesto por CORS para que el navegador lo lea). Las celdas de texto que empiezan por `=`, `+`, `-` o `@` salen con un apóstrofo delante para que Excel no las ejecute como fórmula.
- `PATCH /compras/{id}/recibir` ahora **exige un cuerpo** con `metodo_pago` (y `plataforma` en una transferencia); sin él responde 422 y la compra no se recibe.
- La compra recibida guarda `recibida_en` (hora de recepción); su fila en Gastos usa esa fecha en hora de Bogotá.

**Cómo quedó la G2 y la G3 (lo que cambió respecto a la API prevista):**

- `GET /caja/actual` devuelve `abierta`, el corte abierto y sus `cifras` en vivo (`base_inicial`, `ventas_efectivo`, `ingresos`, `gastos_efectivo`, `compras_efectivo`, `retiros`, `efectivo_esperado` y, solo como información, `ventas_tarjeta` y `ventas_transferencia`) con sus movimientos. `POST /caja/abrir` y `POST /caja/movimientos` devuelven ese mismo estado ya actualizado.
- `POST /caja/cerrar` devuelve la ficha del corte recién cerrado: la foto de las cifras, `efectivo_contado`, `diferencia`, los movimientos y `ventas_sin_conexion_tardias` (cantidad y total de las ventas hechas sin conexión durante el corte y enviadas después del cierre; no alteran la foto). Un segundo cierre, o cerrar sin caja abierta, responde 409; abrir con una abierta, también 409.
- `GET /caja/cortes` se pagina (`pagina`, `tamano_pagina`, hasta 200) y filtra por `desde` y `hasta` según la fecha de apertura en hora de Bogotá; el vendedor recibe solo los cortes que abrió o cerró él, y los demás responden 404. `GET /caja/cortes/exportar` es de administrador y propietario (el vendedor, 403) y trae una fila por corte **cerrado**, con las cifras de su foto. Las horas del CSV salen en hora de Bogotá.
- **Bloqueo del vendedor (RF-074):** si un corte cerrado cubre un gasto (su `creado_en` cae entre la apertura y el cierre), el vendedor recibe **403** al editarlo o anularlo; el administrador puede, y el corte conserva su foto. Cada fila de `GET /gastos` trae `cubierto_por_corte`, y `editable` ya lo tiene en cuenta. Un gasto registrado mientras la caja estaba cerrada (entre dos cortes) no queda cubierto por ninguno.
- **El reloj de la caja es el de la base de datos.** La apertura y el cierre usan `now()` de Postgres, igual que `ventas.fecha` y `gastos.creado_en`; por eso la compra recibida también guarda `recibida_en` con ese reloj (antes usaba el de la aplicación). Los límites del período (apertura y cierre) son inclusivos.
- `GET /ganancias` agrega `neta`: `margen_bruto`, `gastos_operativos`, `ganancia_neta`, `incompleta` (hay ventas sin costo), `ventas_cobradas`, `compras_recibidas`, `gastos_totales` y `resultado_de_caja`. Los gastos se filtran por su fecha contable (`fecha`) y las ventas por su hora, en el día de Bogotá.
- El POS no deja cerrar la caja mientras el equipo tenga ventas guardadas sin enviar (pendientes o en conflicto): lo valida la pantalla, porque esa cola vive en el navegador y el servidor no la ve. No se guarda nada de gastos ni caja en IndexedDB.

## 8. Pantallas

- **POS (administrador y vendedor):** grupo nuevo del menú, **Gastos y caja**, con **Gastos** y **Caja**. En el celular, "Gastos" queda en la barra inferior o en "Más".
- **Gastos:** lista con filtros por rango, categoría y forma de pago; tarjetas de totales; botón **Nuevo gasto**; fila tachada para los anulados; para el administrador, el botón **Categorías** y **Exportar**.
- **Caja:** estado (abierta o cerrada), efectivo esperado en vivo con su desglose, ingresos y retiros, botón **Cerrar caja** (conteo y diferencia) y el historial de cortes.
- **Ganancias (administrador):** líneas nuevas de gastos, ganancia neta y resultado de caja.
- **Dashboard del propietario:** vistas **Gastos** y **Caja** de solo lectura junto a Ventas y Ganancias, con la ganancia neta.

## 9. Garantías

| Garantía | Cómo se logra |
|---|---|
| Un gasto no se pierde ni se borra | Solo se anula, con motivo, quién y cuándo. |
| El vendedor solo toca lo suyo | El servidor filtra por `registrado_por_id`; cualquier otro gasto responde 404 o 403 aunque el vendedor conozca el id. |
| Los totales no se inflan | Los anulados no suman; las compras solo cuentan al recibirse; la ganancia neta no cuenta dos veces la mercancía. |
| El corte no se altera | Se guarda una foto al cerrar y el cierre no se puede repetir ni editar. |
| Una sola caja abierta | Índice único parcial sobre `cortes_caja` donde el estado es abierta. |
| La caja cuadra con lo que hay | Las fórmulas usan los pagos, gastos y movimientos del período, con pruebas automáticas con casos de números exactos. |
| Los permisos se prueban | Pruebas del 403 por rol en cada endpoint, como en las fases anteriores. |

## 10. Fuera de alcance (Fase 2)

Quedan para una fase posterior, si el negocio los necesita:

- **Gastos recurrentes** (por ejemplo, el arriendo mensual): una plantilla que genere el gasto cada mes, pendiente de confirmar, con una tarea programada.
- **Comprobantes**: adjuntar la foto o el PDF de la factura o el recibo (requiere guardar archivos en el servidor, limitar tipo y tamaño, controlar quién los ve e incluirlos en el respaldo).
- Imprimir el corte de caja en la Epson TM-T20II.
- Presupuestos o límites por categoría de gasto y gráficos adicionales.

## 11. Supuestos por confirmar

Para no frenar el diseño se adoptaron estos criterios; cada uno puede cambiarse si el negocio lo decide. **El 21-10-2026 se dieron todos por confirmados** (el 6, la ganancia neta sin las compras de mercancía, sin consultar a un contador porque no lo hay): si más adelante el negocio pide otro criterio, se cambia la regla.

| # | Tema | Criterio adoptado |
|---|---|---|
| 1 | "El admin solo ve" | Se entendió como el **propietario** (el administrador ve e ingresa, según el mismo mensaje). |
| 2 | Qué ve el vendedor | Solo sus propios gastos (necesario para poder editarlos o anularlos), sin totales del negocio ni compras. |
| 3 | Vendedor y corte cerrado | Si el corte que cubre un gasto ya se cerró, el vendedor no puede editarlo ni anularlo; el administrador sí. |
| 4 | Quién maneja la caja | El administrador y el vendedor abren, mueven y cierran la caja; el propietario solo consulta. El vendedor ve el efectivo esperado (no es un corte "a ciegas"). |
| 5 | Una sola caja | Se asume una caja y un solo corte abierto a la vez. |
| 6 | Ganancia neta y compras | La ganancia neta no resta las compras de mercancía (ya están en el costo de lo vendido) y se muestra aparte el resultado de caja con todos los gastos. Conviene confirmarlo con el contador del negocio. |
| 7 | Ingresos y retiros de caja | Se incluyen movimientos manuales con motivo; sin ellos el corte no cuadraría con consignaciones o retiros. |
| 8 | Montos | Pesos enteros; en efectivo, múltiplos de $50 (gastos, base, ingresos, retiros y efectivo contado). |
| 9 | Fecha del gasto | El vendedor registra con la fecha de hoy; el administrador puede elegir otra (no futura). La caja usa la hora real del registro, no la fecha elegida. |
| 10 | Categorías iniciales | Compra de mercancía (de sistema), Arriendo, Servicios públicos, Nómina, Transporte, Publicidad, Mantenimiento, Impuestos y Otros; todas editables menos la de sistema. |
| 11 | Compras anteriores | Las compras recibidas antes de la migración no tienen forma de pago: suman en los gastos pero no en la caja. |
| 12 | Exportar | CSV con punto y coma y BOM; no se incluye un formato `.xlsx`. |
| 13 | Beneficiario | Texto libre opcional (no se enlaza al directorio de proveedores, que solo ve el administrador). Si es una persona, solo su nombre: sin documentos de identidad. |
| 14 | Gastos manuales en "Compra de mercancía" | Se permite registrar a mano un gasto en la categoría de sistema (por ejemplo, mercancía comprada en el mercado sin orden de compra). Cuenta como mercancía: suma en el total y en el resultado de caja, pero no es gasto operativo, así que no resta de la ganancia neta. Si el negocio prefiere reservar la categoría solo para las compras a proveedores, se le quita de la lista del formulario. |
| 15 | Retiros y efectivo negativo | Un retiro no se limita por el efectivo esperado: puede dejarlo en negativo si la plata que se retira no estaba registrada, y el corte lo mostrará como diferencia. Es mejor dejar registrar la realidad que bloquear una operación del mostrador. |
| 16 | Hora de la caja | El período de un corte va de la apertura al cierre según el reloj de la base de datos, con los dos extremos incluidos. Una venta sin conexión cuenta por la hora en que se hizo; una hecha antes de abrir la caja y enviada después no entra en el corte. |
| 17 | Bloqueo por corte cerrado | Al vendedor se le responde 403 (el gasto es suyo, pero ya está cubierto) y se le indica que pida el cambio al administrador. Un gasto registrado con la caja cerrada nunca queda cubierto y el vendedor puede seguir corrigiéndolo. |
| 18 | Cierre con ventas sin enviar | Solo lo impide la pantalla del equipo donde se cierra (mira su cola). Si otro equipo tiene ventas guardadas sin enviar, el corte las informa después como "ventas sin conexión enviadas después del cierre". |
| 19 | Exportar cortes | El CSV trae solo los cortes cerrados del rango; el propietario y el administrador lo descargan, el vendedor no. |

## 12. Pruebas y despliegue

- **Pruebas automáticas:** permisos por rol y por dueño del gasto, anulación y totales, compras unificadas, fórmula del efectivo esperado con ventas en varios métodos, vueltas, gastos, compras e ingresos y retiros, foto del corte, un solo corte abierto, múltiplos de $50, ganancia neta y resultado de caja, exportación y que la cola de ventas sin conexión no cambie.
- **Aceptación con el negocio:** pasos en `10` (secciones 9 y 10), para ejecutar cuando cada fase esté desplegada.
- **Despliegue:** por el flujo normal (rama → PR a `dev` → PR a `main`). Cada migración se aprueba antes de fusionar a `main`. El agente de impresión no cambia.
- **Capacitación y manuales:** actualizados al terminar la G2: guía de capacitación (`09`, versión 1.5) y manuales PDF (`herramientas/manuales_pdf.py`, versión 1.2).

## Control de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 19-10-2026 | Santiago Chávez López | Primera versión: decisiones del negocio, fases G1 a G3, permisos, funcionamiento, modelo de datos, API prevista, supuestos y Fase 2. |
| 1.1 | 19-10-2026 | Santiago Chávez López | **Fase G1 implementada** (migración 0009, API de gastos y categorías, ventana Gastos, forma de pago al recibir compras): cambios respecto a la API prevista y supuesto 14. |
| 1.2 | 20-10-2026 | Santiago Chávez López | **Fases G2 y G3 implementadas** (migración 0010, API de caja y corte, apartado Caja del POS y del Dashboard, bloqueo del vendedor por corte cerrado, ganancia neta y resultado de caja): cambios respecto a la API prevista y supuestos 15 a 19. |
| 1.3 | 21-10-2026 | Santiago Chávez López | G1, G2 y G3 fusionadas a `dev`; migraciones 0009 y 0010 aprobadas en `MIGRACIONES_APROBADAS`; procedimiento y checklist de despliegue en `DEPLOY.md`. |
| 1.4 | 21-10-2026 | Santiago Chávez López | Supuestos 1 a 19 dados por confirmados (la ganancia neta sin las compras de mercancía, sin consulta a contador). |
| 1.5 | 21-10-2026 | Santiago Chávez López | Adendo v3 desplegado en producción; falta la aceptación. |
