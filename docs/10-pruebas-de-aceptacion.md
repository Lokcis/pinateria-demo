# Guía de pruebas de aceptación

**Versión 1.7 — 25-10-2026.** Pasos para validar con el vendedor, el administrador y el propietario lo entregado en las fases A1, A2, A3 y la mejora B1 del Adendo v2 (HU-05 a HU-10) y en la Fase 9 (HU-11, vender sin conexión). Las secciones 9 y 10 (HU-12 y HU-13, Adendo v3: gastos y corte de caja) se hacen con las fases G1 a G3, desplegadas en producción desde el 21-10-2026. Cada paso sale de los criterios de aceptación del documento 02. Se marca ✔ si pasa o ✘ si falla, y se anota lo observado.

## 0. Antes de empezar

- **Dónde:** en producción (el servidor sigue `main` desde el 14-10-2026), con `https://pos.demo.example.com`. La sección 8 (sin conexión) se hace en la tienda, con el PC del POS.
- **Quién:** el vendedor hace los pasos de venta y clientes; el administrador, los de configuración; el propietario, los del Dashboard desde su celular.
- **Las ventas de prueba no se borran.** Como estas pruebas se hacen ya en producción (decidido el 14-10-2026), quedan en el historial, el Dashboard y las ganancias. Usa productos y clientes marcados "PRUEBA" con montos mínimos (por ejemplo, $50), anota cuántas ventas de prueba se hicieron (sección 11) y desactiva esos productos y clientes al terminar. Si se prefiere no mezclar datos, las secciones 1 a 7 se pueden ensayar antes en un entorno local con `scripts.seed_demo` (nunca en producción).
- **Productos de prueba que se necesitan:** uno simple con stock, uno con stock justo en el mínimo, un paquete y una ancheta con receta, y uno sin costo.
- **Usuarios de prueba:** un vendedor, un administrador y el propietario.
- Antes de las pruebas de impresión, el agente de impresión del PC del POS debe estar actualizado (con la Fase 9 acepta `referencia`) y corriendo.

## 1. HU-05 — Pagos mixtos y vueltas (vendedor)

| # | Paso | Resultado esperado | ✔/✘ | Notas |
|---|---|---|---|---|
| 1.1 | Arma una venta de $20.000. Paga $12.000 en efectivo y deja $5.000 por Nequi | No deja confirmar y muestra cuánto **falta** ($3.000) | ✔ | |
| 1.2 | Cambia el segundo pago a $8.000 por Nequi | Deja confirmar; la suma es el total | ✔ | |
| 1.3 | Agrega un pago de $10.000 en transferencia y no elijas plataforma | Obliga a elegir **Nequi o Daviplata** | ✔ | |
| 1.4 | Paga $20.000 en efectivo con $50.000 recibidos | Muestra vueltas de $30.000 | ✔ | |
| 1.5 | Escribe como recibido un valor menor al monto | No lo acepta | ✔ | |
| 1.6 | Confirma una venta con pagos mixtos y revisa el ticket | Cada pago con su método (y plataforma), lo recibido y las vueltas | ✔ | El ticket debe tener el logo. Mejora pedida (no es falla): el ticket debe llevar el logo; requiere cambiar el agente de impresión. Logo agregado al ticket; falta verlo impreso en la Epson real. |
| 1.7 | Confirma la venta y mide el tiempo | Se confirma en menos de 2 segundos | ✔ | |
| 1.8 | (Propietario) Mira el resumen de hoy en el Dashboard | El total por método suma el monto de cada pago, no el número de ventas | ✔ | |

## 2. HU-06 — Descuentos (administrador y vendedor)

| # | Paso | Resultado esperado | ✔/✘ | Notas |
|---|---|---|---|---|
| 2.1 | (Admin) En **Descuentos**, activa el descuento general | Se guarda; el vendedor no puede cambiarlo | ✔ | |
| 2.2 | (Vendedor) Abre una venta nueva | Arranca **sin** descuento; aparece "Aplicar descuento general" | ✔ | |
| 2.3 | (Admin) Fija un tope (por ejemplo 10 % y $5.000) | Se guarda | ✔ | |
| 2.4 | (Vendedor) Escribe un descuento manual por encima del tope | Muestra el límite vigente y no deja confirmar | ✔ | |
| 2.5 | (Vendedor) Escribe uno dentro del tope y confirma | La venta queda con origen manual; el ticket muestra subtotal, descuento y total | ✔ | |
| 2.6 | (Vendedor) Aplica el descuento general | Funciona sin toparse con los límites | ✔ | |
| 2.7 | Verifica el total de una venta con descuento | Descuento sobre el subtotal y luego redondeo a $50 | ✔ | |
| 2.8 | (Admin) Asigna un descuento propio a un cliente; (vendedor) elige ese cliente en la venta | Se sugiere solo; no se suma con el general | ✔ | |
| 2.9 | (Vendedor) Intenta cambiar el descuento general o asignar uno a un cliente | No puede (la pantalla no se lo ofrece o recibe error de permiso) | ✔ | |

## 3. HU-07 — Clientes y Habeas Data

**Prerrequisito:** el administrador completó "Datos del negocio" en **Datos personales** (si falta algo, la política queda como "borrador" y el enlace no se puede generar).

| # | Paso | Resultado esperado | ✔/✘ | Notas |
|---|---|---|---|---|
| 3.1 | (Vendedor) Crea un cliente **sin** marcar la autorización | No lo guarda | ✔ | |
| 3.2 | Crea un cliente con autorización y medio verbal | Queda guardado; la ficha muestra fecha, medio, versión de política y quién la recogió | ✔ | No dice quien la agregó. Falla: la ficha no dice quién recogió la autorización. Corregido en el PR. → Aprobado por el desarrollador el 25-10-2026 sin repetir la prueba en producción. La corrección se verifica al desplegarla. |
| 3.3 | Crea otro con el mismo documento; otro con teléfono de 5 dígitos | Rechaza el documento repetido y el teléfono inválido (7 a 15 dígitos) | ✔ | |
| 3.4 | Busca por parte del nombre, por documento y por teléfono | Responde casi al instante | ✔ | |
| 3.5 | Marca la casilla de promociones en uno y deja otra sin marcar | Por defecto viene desmarcada; el listado filtra por quienes aceptaron | ✔ | |
| 3.6 | Asocia el cliente a una venta | Queda asociado; aparece en su historial y en su total comprado | ✔ | |
| 3.7 | Filtra el listado por total comprado y por fechas | Con fechas, solo cuentan las compras de ese rango | ✔ | |
| 3.8 | (Admin) Desactiva un cliente e intenta asociarlo a una venta | No lo permite | ✔ | |
| 3.9 | (Admin) Registra una solicitud de consulta y una de supresión | Cada una con su fecha límite (10 y 15 días hábiles) | ✔ | |
| 3.10 | (Admin) Resuelve la supresión de un cliente de prueba que tenga una solicitud con descripción escrita | Queda "Cliente anonimizado", sin documento ni teléfono; la descripción de sus solicitudes desaparece; sus ventas se conservan | ✔ | |
| 3.11 | (Vendedor) Intenta ver o gestionar las solicitudes | No tiene acceso | ✔ | |
| 3.12 | (Admin) Genera el enlace de autorregistro y ábrelo en el celular **sin sesión** | Abre el formulario con el aviso y la política | ✔ | |
| 3.13 | Intenta enviar sin marcar la aceptación | No deja enviar | ✔ | |
| 3.14 | Envía con datos nuevos | Mensaje de éxito; el cliente aparece con origen autorregistro, medio electrónico y sin descuento | ✔ | |
| 3.15 | Vuelve a enviar con el mismo documento o teléfono | Mismo mensaje de éxito y no se crea ni cambia nada | ✔ | No debería impedirlo para evitar usuario repetidos? Es a propósito: el formulario público responde igual exista o no el cliente, para no revelar quién está registrado (Habeas Data); no se crea ni cambia nada, así que no hay duplicados. |
| 3.16 | (Admin) Desactiva el enlace y ábrelo; luego regenéralo y abre el anterior | En ambos casos, mensaje claro de que no funciona | ✔ | |
| 3.17 | Envía el formulario muchas veces seguidas | Se frena por el límite de envíos | ✔ | |

## 4. HU-08 — Cambio de vendedor

| # | Paso | Resultado esperado | ✔/✘ | Notas |
|---|---|---|---|---|
| 4.1 | Abre una venta y mira el desplegable **Vendedor** | Trae al usuario de la sesión; solo vendedores y administradores activos (no el propietario ni inactivos) | ✔ | |
| 4.2 | Elige otro vendedor, confirma la venta | Queda a nombre del elegido en **Ventas de hoy** (de ese vendedor) y en el ticket ("Atendió") | ✔ | |
| 4.3 | Haz otra venta sin tocar el desplegable | Vuelve a ser la persona de la sesión; la venta anterior no cambió | ✔ | |
| 4.4 | (Vendedor) Registra una venta a nombre del administrador y abre **Ventas de hoy** con tu usuario | La ves, con la leyenda "Registrada por" y tu nombre; otra persona que no la registró ni figura como vendedor no la ve | ✔ | |

## 5. HU-09 — Ganancias (administrador y propietario)

| # | Paso | Resultado esperado | ✔/✘ | Notas |
|---|---|---|---|---|
| 5.1 | (Admin) En **Ganancias**, carga el costo de un producto | Se guarda | ✔ | |
| 5.2 | Mira el costo de una ancheta | Aparece un costo sugerido (suma de sus componentes) que se puede ajustar | ✔ | |
| 5.3 | Vende el producto; luego cambia su costo | El margen de la venta ya hecha no cambia | ✔ | |
| 5.4 | Mira un producto sin costo en el panel | Se informa "sin costo" y no entra al margen | ✔ | |
| 5.5 | Verifica un margen a mano: subtotal − descuento − costo × cantidad | Coincide con lo que muestra el panel | ✔ | |
| 5.6 | (Propietario) Abre su Dashboard › **Ganancias** desde el celular | Margen por período y por producto, con gráficos; los costos son de solo lectura | ✔ | |
| 5.7 | (Vendedor) Busca costos o ganancias | No aparecen en ninguna pantalla | ✔ | |

## 6. HU-10 — Bandeja y lista de compras (propietario y administrador)

| # | Paso | Resultado esperado | ✔/✘ | Notas |
|---|---|---|---|---|
| 6.1 | Baja el stock de un producto por debajo de su mínimo y espera hasta 15 minutos | Aparece una notificación y el contador de no leídas sube | ✔ | |
| 6.2 | Marca una como leída y luego todas | Las leídas dejan de contar | ✔ | |
| 6.3 | Mientras la alerta siga sin leer, no deben aparecer avisos repetidos del mismo producto | Un solo aviso por producto | ✔ | |
| 6.4 | Abre la **lista de compras** | Cada producto con stock, mínimo y faltante (mínimo menos stock); los que están justo en el mínimo, con faltante 0 | ✔ | |
| 6.5 | (Propietario, desde el celular) Pulsa el botón de WhatsApp | Abre WhatsApp con la lista como mensaje | ✔ | |
| 6.6 | Repite en el computador y prueba **Copiar texto** | Funciona en los dos | ✔ | |
| 6.7 | (Vendedor) Intenta abrir la bandeja o la lista | No tiene acceso | ✔ | |

## 7. Pruebas de campo adicionales

| # | Paso | Resultado esperado | ✔/✘ | Notas |
|---|---|---|---|---|
| 7.1 | Abre el Dashboard por el túnel desde el celular con **datos móviles** (no con el wifi de la tienda) | Carga en menos de 10 segundos (HU-03) | ✔ | |
| 7.2 | Imprime un ticket con pagos mixtos, descuento, cliente y vendedor | Se imprime completo en la Epson | ✔ | |
| 7.3 | Escanea un código de barras con el lector | Agrega el producto al carrito | ✔ | |
| 7.4 | Revisa la interfaz en el celular (375 px) | Barra inferior, panel de venta a pantalla completa, sin desbordes | ✔ | |
| 7.5 | Instala la app en el celular del propietario | Se abre como aplicación | ✔ | cuando entro a la parte de ventas se expande y los precios se salen de la tarjeta de la venta. Falla de interfaz en celular: en "Ventas de hoy" el total se salía de la tarjeta. Corregido en el PR. → Aprobado por el desarrollador el 25-10-2026 sin repetir la prueba en producción. La corrección se verifica al desplegarla. |
| 7.6 | Desde otro equipo de la red de la tienda, abre `http://<IP del servidor>` (puerto 80) | **No** responde | ✔ | |

## 8. HU-11 — Vender sin conexión (Fase 9)

Se hace en la tienda, con el PC del POS, el lector y la impresora. Antes: el agente de impresión actualizado, el POS abierto **con conexión** al menos una vez (para que guarde el catálogo) y la migración 0008 desplegada. Para cortar internet: desconectar el cable o el wifi del PC (no apagar el servidor).

| # | Paso | Resultado esperado | ✔/✘ | Notas |
|---|---|---|---|---|
| 8.1 | Con internet, abre el POS y espera 1 minuto. Luego **desconecta** el PC de internet | Aparece la barra roja "Sin conexión con el servidor. Puedes seguir vendiendo…" y la antigüedad del catálogo guardado | ✔ | Toca interactuar con otro apartado. Probar en Chrome o Edge: en Opera el aviso de desconexión puede no dispararse al instante. |
| 8.2 | Busca un producto por nombre y otro con el lector | Los encuentra en el catálogo guardado; la lista avisa que el stock puede estar desactualizado | ✔ | |
| 8.3 | Arma una venta con pagos mixtos (efectivo con vueltas + Nequi) y confirma | "Venta SC-0001 guardada sin conexión"; el ticket sale con **Venta SC-0001**, los pagos y las vueltas | ✔ | |
| 8.4 | Haz otra venta con el descuento general (si está activo) o un descuento manual | Se guarda como SC-0002; el ticket muestra el descuento | ✔ | no se debería guardar la info de descuentos? porque sin conexión deja descontar sin tope. A revisar como vendedor con topes configurados: el POS valida el tope con la copia guardada, el tope no aplica al administrador y sin topes no hay límite. |
| 8.5 | Mira el selector de cliente | No se puede elegir cliente; explica que sin conexión la venta no lleva cliente | ✔ | |
| 8.6 | Pulsa **Ver ventas guardadas** | Lista SC-0001 y SC-0002 con total, productos y "Por enviar"; se puede reimprimir un ticket; no se puede descartar | ✔ | debemos poner que en vez de failed to fetch un try catch de no hay conexión no se puede conectar o algo así. El mensaje "Failed to fetch" se cambió por "No hay conexión…" y el del agente de impresión. Corregido en el PR. |
| 8.7 | Intenta **cerrar sesión** y cancela | Pide confirmación y avisa que sin conexión no se puede volver a entrar | ✔ | |
| 8.8 | **Recarga la página** (F5) sin internet | La aplicación abre con la sesión iniciada y las 2 ventas siguen guardadas | ✔ | |
| 8.9 | (Administrador) Cambia el precio de un producto vendido, desde otro equipo con internet | Nada cambia en el equipo sin conexión | ✔ | |
| 8.10 | **Reconecta** internet | En menos de un minuto: "Enviando ventas guardadas…" y "Se enviaron 2 ventas guardadas sin conexión" | ✔ | |
| 8.11 | Abre **Ventas de hoy** | Las 2 ventas aparecen con su número definitivo, la **hora en que se hicieron** (no la del envío) y la marca "Sin conexión"; el total del día las incluye | ✔ | |
| 8.12 | Revisa el precio de la venta SC-0001 | Es el que vio el cliente (no el nuevo del paso 8.9) | ✔ | |
| 8.13 | Revisa el stock de los productos vendidos en Inventario | Bajó una sola vez por venta | ✔ | |
| 8.14 | Con un producto con **1 unidad** en el sistema, corta internet y vende **2** | Se guarda sin problema | ✔ | |
| 8.15 | Reconecta | Queda como **"Necesita revisión"** con el motivo (stock insuficiente); las demás ventas sí se enviaron | ✔ | |
| 8.16 | (Administrador) Registra el stock que faltaba y, en "Ver ventas guardadas", pulsa **Reintentar** | La venta se registra y sale de la lista | ✔ | |
| 8.17 | Repite el 8.14 y esta vez pulsa **Descartar** | Pide confirmación; al confirmar, la venta desaparece y no queda registrada | ✔ | |
| 8.18 | Corta internet, vende, y espera a que la sesión venza (o borra el token); reconecta | La barra dice "Tu sesión venció"; al iniciar sesión de nuevo, la venta se envía sola | ✔ | |

## 9. HU-12 — Gastos (Adendo v3, fases G1 y G3)

**Ejecutable:** G1, G2 y G3 están desplegadas desde el 21-10-2026. Usa gastos de prueba de $50, descripción "Prueba…" y categoría "Prueba"; **no se borran**: al final se anulan con el motivo "Prueba de aceptación". Se necesitan el administrador, dos vendedores (A y B) y el propietario.

| # | Paso | Resultado esperado | ✔/✘ | Notas |
|---|---|---|---|---|
| 9.1 | (Administrador) Abre **Gastos** y revisa las categorías | Están las iniciales (Compra de mercancía, Arriendo, Servicios públicos, Nómina, Transporte, Publicidad, Mantenimiento, Impuestos y Otros); "Compra de mercancía" no se puede editar ni desactivar | ✔ | Aprobado por el desarrollador el 25-10-2026 sin repetir la prueba en producción. |
| 9.2 | Crea la categoría "prueba" | Queda como "Prueba" (primera letra en mayúscula) y se ofrece al registrar un gasto | ✔ | |
| 9.3 | Registra un gasto en efectivo de $50, categoría Prueba, descripción "Prueba gasto 1" | Aparece en la lista con fecha de hoy y suma al total | ✔ | |
| 9.4 | Intenta registrar un gasto en efectivo de $75 | Lo rechaza: en efectivo van múltiplos de $50 | ✔ | |
| 9.5 | Registra una transferencia de $1.230 sin plataforma y luego con Nequi | Sin plataforma lo rechaza; con Nequi lo acepta (cualquier monto entero) | ✔ | |
| 9.6 | Registra un gasto con fecha de ayer y luego uno con fecha de mañana | El de ayer sí; el de mañana no | ✔ | |
| 9.7 | (Vendedor A) Registra un gasto en efectivo de $50 | Se registra con la fecha de hoy; no hay selector de fecha | ✔ | |
| 9.8 | (Vendedor A) Mira la lista | Solo ve el suyo; no hay totales del negocio, ni compras, ni Exportar, ni Categorías | ✔ | |
| 9.9 | (Vendedor B) Mira la lista | No ve el gasto de A (y pedirlo directamente responde que no existe o que no tiene permiso) | ✔ | |
| 9.10 | (Vendedor A) Edita su gasto (monto a $100) | Cambia y queda marcado como editado | ✔ | |
| 9.11 | (Vendedor A) Intenta anular sin motivo y luego con motivo | Sin motivo lo pide; con motivo el gasto queda tachado con quién, cuándo y por qué, y deja de sumar | ✔ | |
| 9.12 | (Administrador) Edita y anula el gasto del vendedor B | Puede | ✔ | |
| 9.13 | (Propietario) Abre Gastos en el Dashboard | Ve todos los gastos y los totales; no hay botones de registrar, editar ni anular | ✔ | |
| 9.14 | (Administrador) Crea una compra de un producto de prueba y recíbela con forma de pago **efectivo** | Pide la forma de pago al recibir y el stock sube | ✔ | |
| 9.15 | Abre Gastos | La compra aparece como fila de solo lectura "Compra de mercancía", con la fecha de hoy y sumada al total; una compra pendiente no aparece | ✔ | |
| 9.16 | (Vendedor) Abre Gastos | No ve la compra ni los gastos de otras personas | ✔ | |
| 9.17 | Filtra por rango, categoría y forma de pago | La lista y los totales por categoría y por forma de pago cambian y cuadran | ✔ | |
| 9.18 | **Exportar** (administrador y luego propietario) y abre el archivo en Excel | CSV con las mismas filas, tildes y columnas bien; sin anulados salvo que se pidan; el vendedor no tiene el botón | ✔ | |
| 9.19 | Corta internet en el PC del POS y abre Gastos | Avisa que requiere conexión; una venta sin conexión se guarda y se envía como siempre | ✔ | |
| 9.20 | (Administrador, G3) Abre **Ganancias** | Ganancia neta = margen bruto − gastos operativos (sin la compra de mercancía) y resultado de caja = ventas cobradas − todos los gastos; aviso "incompleta" si hay ventas sin costo | ✔ | |
| 9.21 | (Propietario, G3) Abre su Dashboard | Ve lo mismo en solo lectura | ✔ | |
| 9.22 | Anula los gastos de prueba con el motivo "Prueba de aceptación" | Quedan anulados y fuera de los totales | ✔ | |

## 10. HU-13 — Dinero en caja y corte de caja (Adendo v3, Fase G2)

**Ejecutable (G2 desplegada el 21-10-2026):** se hace en la tienda, con el PC del POS y la impresora. Antes de empezar, las ventas de prueba son de $50 y no se borran.

| # | Paso | Resultado esperado | ✔/✘ | Notas |
|---|---|---|---|---|
| 10.1 | (Vendedor) Abre **Caja** e intenta abrirla con $50.025 y luego con $50.000 | Con $50.025 la rechaza (múltiplo de $50); con $50.000 queda abierta, con efectivo esperado de $50.000 | ✔ | |
| 10.2 | Intenta abrir otra caja | No deja: ya hay una abierta | ✔ | |
| 10.3 | Haz una venta en efectivo de $100 con $200 recibidos | El esperado sube $100 (no $200: las vueltas no cuentan) | ✔ | |
| 10.4 | Haz una venta mixta: $50 en efectivo y el resto por Nequi | El esperado sube solo $50; el Nequi aparece como información | ✔ | |
| 10.5 | Registra un gasto de $50 en efectivo y otro por transferencia | El esperado baja $50 por el de efectivo; el de transferencia no lo cambia | ✔ | |
| 10.6 | (Administrador) Recibe una compra pagada en efectivo | El esperado baja el total de la compra | ✔ | |
| 10.7 | Registra un ingreso de $50 y un retiro de $50 con motivo | El esperado sube y baja; los movimientos quedan con motivo y quién | ✔ | |
| 10.8 | (Administrador) Anula el gasto en efectivo del paso 10.5 | El esperado vuelve a subir $50 | ✔ | |
| 10.9 | Corta internet, haz una venta en efectivo (queda guardada sin conexión) e intenta cerrar la caja | El POS no deja cerrarla mientras haya ventas guardadas sin enviar | ✔ | |
| 10.10 | Reconecta, espera el envío y cierra la caja contando el efectivo (múltiplo de $50) con observaciones | Calcula la diferencia (contado − esperado), el corte queda cerrado con sus cifras y no se puede cerrar de nuevo ni editar | ✔ | |
| 10.11 | (Vendedor) Intenta editar un gasto cubierto por el corte cerrado; luego el administrador lo anula | El vendedor no puede; el administrador sí, y las cifras del corte cerrado no cambian | ✔ | |
| 10.12 | Mira el historial de cortes con el administrador, el propietario y el vendedor | Administrador y propietario ven todos; el vendedor, los que abrió o cerró; el detalle y **Exportar** funcionan | ✔ | |
| 10.13 | (Propietario) Intenta abrir, mover o cerrar la caja | No tiene botones; solo consulta | ✔ | |
| 10.14 | Corta internet y abre Caja | Avisa que requiere conexión | ✔ | |
| 10.15 | Intenta registrar un retiro sin motivo y otro de $75 con motivo | Los rechaza: el motivo es obligatorio y el monto va en múltiplos de $50 | ✔ | |
| 10.16 | (Administrador) Abre la ficha de un corte ya cerrado | Muestra las cifras tal como estaban al cerrar, los ingresos y retiros, quién abrió y quién cerró, y la diferencia; no hay forma de modificarla | ✔ | |

## 11. Cierre

- **Resultado (ejecución del 25-10-2026):** 114 pasos ✔ y 0 ✘. Los pasos 3.2, 7.5 y 9.1 los aprobó el desarrollador sin repetirlos en producción: 3.2 y 7.5 fallaron en la ejecución y se corrigieron en el PR; 9.1 no se comprobó. Lo que falle se anota como incidencia y se corrige por pull request (`dev` → `main`, con el CI en verde) y se vuelve a probar.
- **Datos de prueba:** decidido el 13-10-2026: se crea una **base de producción vacía** y se carga el catálogo real a mano (las ventas de prueba no se pueden borrar). Es una operación destructiva con respaldo previo y confirmación expresa; el procedimiento está en `DEPLOY.md`, sección 8 ("Paso a producción").
- **Aceptación del desarrollador:** Santiago Chávez López, 26-10-2026 (firma puesta por su indicación).
- **Aceptación del negocio:** vendedor ______________________ propietario ______________________ fecha ____ / ____ / ________

## Control de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 13-10-2026 | Santiago Chávez López | Primera versión: pasos de aceptación de HU-05 a HU-10 y pruebas de campo. |
| 1.1 | 13-10-2026 | Santiago Chávez López | Decisión sobre los datos de prueba: base de producción vacía (procedimiento en `DEPLOY.md`, sección 8). |
| 1.2 | 13-10-2026 | Santiago Chávez López | Pasos nuevos: lo que el vendedor registra a nombre de otro aparece en su historial (4.4) y la supresión borra la descripción de las solicitudes (3.10). |
| 1.3 | 14-10-2026 | Santiago Chávez López | Fase 9: sección 8 (HU-11, vender sin conexión); la sección 0 pasa a producción y el cierre pasa a ser la sección 9. |
| 1.4 | 19-10-2026 | Santiago Chávez López | Adendo v3: secciones 9 (HU-12, gastos) y 10 (HU-13, dinero en caja y corte), escritas pero no ejecutables hasta que se desplieguen G1 a G3; el cierre pasa a ser la sección 11. |
| 1.5 | 20-10-2026 | Santiago Chávez López | Adendo v3: las secciones 9 y 10 quedan ejecutables al desplegar G1, G2 y G3; dos pasos nuevos de caja (10.15 y 10.16). |
| 1.6 | 21-10-2026 | Santiago Chávez López | Las secciones 9 y 10 se pasan en el primer despliegue del Adendo v3 (G1, G2 y G3 juntas); se genera la versión imprimible en PDF (`manuales/guia-de-pruebas-de-aceptacion.pdf`). |
| 1.7 | 25-10-2026 | Santiago Chávez López | Textos al día tras el despliegue del Adendo v3 y resultados de la ejecución del 25-10-2026 (114 pasos aprobados; 3.2 y 7.5 corregidos en el PR y el logo del ticket en el PR). 26-10-2026: pasos 8.1 y 8.4 revisados por el desarrollador y firma del desarrollador en la sección 11; falta la del negocio. |
