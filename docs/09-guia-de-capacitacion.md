# Guía de capacitación y puesta en marcha

**Versión 1.3 — 19-10-2026.** Material de la Fase 7: guía rápida del vendedor (para imprimir), guía del propietario, guión de las sesiones y lista de verificación de la puesta en marcha. Los nombres de pestañas y botones son los de la aplicación; si algo cambia en la interfaz, se corrige aquí.

Dirección de la aplicación: `https://pos.demo.example.com`

## 1. Guía rápida del vendedor

### 1.1 Antes de abrir la tienda

1. Enciende el PC del POS y la impresora (Epson TM-T20II) y entra a la dirección de la aplicación.
2. Inicia sesión con **tu** usuario. No uses el de otra persona: la venta queda a nombre de quien tiene la sesión (se puede cambiar por venta, ver 1.4).
3. Comprueba que el **agente de impresión** esté corriendo (su ventana minimizada; arranca solo al iniciar Windows). Si el ticket no sale, ver 1.8.

### 1.2 Hacer una venta (pestaña "Nueva venta")

1. Busca el producto por nombre, o escanea el código de barras con el lector (el cursor debe estar en el buscador).
2. Toca el producto para agregarlo. Ajusta cantidades en el carrito; las piñatas se pueden vender por unidad, por paquete o como ancheta.
3. (Opcional) Elige el **cliente** si la persona está registrada (ver 1.5).
4. (Opcional) Aplica un **descuento** (ver 1.3).
5. Elige cómo paga (ver 1.6) y pulsa **Confirmar venta**.
6. Sale el ticket. Si no sale, la venta **sí quedó registrada**: usa **Reintentar impresión**.

El total se redondea al múltiplo de $50 más cercano; el ticket muestra "Ajuste por redondeo".

En el celular, el panel de la venta se abre desde la barra inferior (cantidad de artículos y total).

### 1.3 Descuentos

- **General:** solo si el administrador lo activó. Se aplica a quien corresponde (clientes sin registro); no viene puesto por defecto.
- **Del cliente:** si el cliente tiene descuento propio, se sugiere solo al elegirlo. Puedes quitarlo.
- **Manual:** lo escribes tú (% o $), pero hay **topes** fijados por el administrador. Si te pasas, la aplicación no lo deja.
- El descuento se calcula sobre el subtotal y después se redondea a $50.

### 1.4 Quién vendió

El desplegable **Vendedor** trae tu nombre. Si otra persona atendió al cliente, cámbialo antes de confirmar: la venta queda a su nombre y el ticket dice "Atendió: …". Después de cada venta vuelve a ti.

### 1.5 Clientes y autorización de datos personales

Pestaña **Clientes**: busca por nombre, documento o teléfono. Para registrar a alguien nuevo:

1. Pídele sus datos (nombre; documento y teléfono si los da; correo opcional).
2. **Antes de guardar, léele o muéstrale el aviso de privacidad** (cartel en el mostrador) y pregunta si autoriza el tratamiento de sus datos. Sin autorización **no se registra**.
3. Marca la casilla de autorización y el medio (verbal, escrito o electrónico).
4. La casilla de **promociones es aparte**: márcala solo si el cliente dice que sí quiere recibirlas. Por defecto está desmarcada y no debes insistir.
5. Alternativa: el cliente se registra solo desde su celular, escaneando el **código QR del cartel** (o con el enlace `/registro/<código>`); allí lee el aviso y acepta él mismo.

Si un cliente pide ver, corregir o borrar sus datos, o retirar su autorización: **no lo resuelvas tú**; anota su nombre y teléfono y avisa al administrador (hay un procedimiento con plazos legales).

### 1.6 Formas de pago

- **Efectivo:** escribe el monto recibido; la aplicación calcula las **vueltas** (el ticket las imprime).
- **Tarjeta.**
- **Transferencia:** elige **Nequi** o **Daviplata**; es obligatorio.
- **Pago mixto:** agrega varios pagos (por ejemplo, $20.000 en efectivo y el resto por Nequi). La suma debe ser **exactamente el total**; si no, no deja confirmar.

### 1.7 Ventas de hoy y errores

- **Ventas de hoy** muestra lo que quedó hoy a tu nombre y también lo que tú registraste a nombre de otra persona (dice "Registrada por" cuando la registró alguien distinto del vendedor); desde ahí puedes **Reimprimir ticket**.
- Una venta mal hecha no se borra: avisa al administrador.
- Si falta o sobra producto en el inventario, usa **Inventario** (ajuste manual con motivo); no vendas "a ojo" algo que no está registrado.

### 1.8 Si algo falla

| Síntoma | Qué hacer |
|---|---|
| No sale el ticket | Revisa que la impresora tenga papel y esté encendida; pulsa **Reintentar impresión**. Si sigue, el agente no está corriendo: abre `iniciar.bat` en la carpeta `printer-agent`. |
| La aplicación no carga | Revisa el internet de la tienda. Si ya tenías la aplicación abierta con la sesión iniciada, sigue vendiendo: lee el apartado 1.9 (modo sin conexión). Si no abre ni siquiera la pantalla de inicio de sesión, sin internet no hay manera de entrar: anota la venta en papel (producto, valor, forma de pago) y regístrala cuando vuelva. |
| "Sesión vencida" | Vuelve a iniciar sesión (dura 8 horas). |
| No encuentro un producto | Prueba con otra palabra o el código; si no existe, avisa al administrador. |

### 1.9 Si se cae internet (modo sin conexión)

La aplicación sigue vendiendo aunque se caiga internet. Lo que tienes que saber:

- Arriba aparece una barra roja: **"Sin conexión con el servidor. Puedes seguir vendiendo…"**. Vende como siempre: busca por nombre o con el lector, cobra y confirma.
- Al confirmar, verás **"Venta SC-0001 guardada sin conexión"** y el ticket sale con ese número (no es el número definitivo de la venta). **No cobres dos veces ni anotes la venta en papel**: ya está guardada en el equipo.
- Sin conexión no se pueden elegir clientes ni ver "Ventas de hoy", el inventario ni las demás pestañas: solo se vende.
- **No cierres sesión mientras no haya conexión**: sin internet no se puede volver a entrar. Si lo intentas, la aplicación te lo advierte.
- Cuando vuelva internet, las ventas se envían solas (verás "Enviando ventas guardadas…" y luego "Se enviaron N ventas"). No tienes que hacer nada. Si quieres, pulsa **Enviar ahora**.
- Si una venta queda como **"Necesita revisión"** (por ejemplo, porque el sistema decía que no había stock), avisa al administrador y muéstrale el motivo que aparece en "Ver ventas guardadas": él corrige el inventario y tú pulsas **Reintentar**.
- Si al volver internet dice **"Tu sesión venció"**, pulsa "Iniciar sesión de nuevo": las ventas guardadas se envían al entrar. No se pierden.
- El catálogo guardado se actualiza solo cuando hay internet. Abre la aplicación con internet al empezar el día para que tenga los precios al día.

### 1.10 Gastos (cuando se active la Fase G1)

- Si pagaste algo con plata del negocio (domicilio, bolsas, un favor…), anótalo en **Gastos** (menú "Gastos y caja"; en el celular, **Más › Gastos**): **Nuevo gasto**, categoría, qué se pagó, monto en pesos enteros y forma de pago. En efectivo el monto va en **múltiplos de $50**; en transferencia, elige Nequi o Daviplata. Se guarda con la fecha de hoy.
- Solo ves **tus** gastos. Puedes **Editar** o **Anular** los tuyos; anular pide el motivo y el gasto no se borra (queda tachado con tu nombre).
- Los gastos necesitan internet: sin conexión la pantalla lo avisa. Las ventas sin conexión siguen igual.

### 1.11 Caja y corte (cuando se active la Fase G2)

- Al empezar el turno abre la caja en **Caja** (menú "Gastos y caja"; en el celular, **Más › Caja**): escribe el efectivo con que arranca, la **base**, en múltiplos de $50. Solo puede haber una caja abierta: si otra persona ya la abrió, sigues con esa.
- Mientras trabajas, la pantalla muestra el **efectivo esperado**: la base, más las ventas en efectivo y los ingresos, menos los gastos en efectivo, las compras pagadas en efectivo y los retiros. Las vueltas no cuentan: solo lo que abona a la venta. Lo vendido con tarjeta y por Nequi o Daviplata sale aparte, para compararlo con el datáfono y el banco.
- Si entra o sale plata de la caja sin ser una venta ni un gasto (cambio, consignación al banco, retiro del dueño), regístrala con **Registrar ingreso** o **Registrar retiro** y su motivo; si no, el corte saldrá descuadrado.
- Al terminar, **cuenta el efectivo**, pulsa **Cerrar caja** y escribe lo contado (múltiplos de $50). La pantalla muestra la diferencia: **sobra** o **falta**. El corte queda guardado y ya no se puede cambiar.
- **Antes de cerrar**, mira que no tengas ventas guardadas sin enviar (aviso amarillo de arriba): el POS no deja cerrar la caja mientras las haya, para que no queden por fuera del corte.
- Después del cierre ya no puedes editar ni anular los gastos que entraron en ese corte; si hay un error, pídele el cambio al administrador.
- La caja necesita internet; sin conexión la pantalla lo avisa. Las ventas sin conexión siguen igual.

## 2. Guía del propietario

El propietario usa el **Dashboard** (desde el celular también). Solo consulta; no vende ni modifica datos.

- **Ventas:** elige el rango (Hoy, Ayer, Semana, Mes, 3 meses, 6 meses, Año o personalizado). Ve el total, cuántas ventas, el desglose por forma de pago y los productos más vendidos.
- **Ganancias** (pestaña junto a "Ventas"): margen por período y por producto, y la tabla de costos en solo lectura. Las ventas sin costo cargado no entran en la ganancia hasta que el administrador complete los costos.
- **Ganancia neta** (dentro de "Ganancias"): el margen bruto menos los gastos operativos (los que no son compra de mercancía, porque esa ya está en el costo de lo vendido) y, aparte, el **resultado de caja**: lo cobrado menos todos los gastos, compras incluidas. El resultado de caja es una cifra de flujo de dinero, no una ganancia contable. Si faltan costos, avisa que la neta está incompleta.
- **Caja** (pestaña junto a "Gastos"): si la caja está abierta, el efectivo esperado con su desglose; el historial de cortes con la diferencia de cada uno, su ficha y el botón **Exportar**. Solo consulta: no abre, mueve ni cierra la caja.
- **Gastos** (pestaña junto a "Ganancias"): todos los gastos y las compras recibidas del rango, con los totales por categoría y por forma de pago, y el botón **Exportar** (archivo que abre Excel). Solo consulta: no registra ni modifica.
- **Stock bajo** (botón con contador): la bandeja de alertas (marcar una o todas como leídas) y la **lista de compras**, que se puede enviar por WhatsApp o copiar como texto.
- **Instalarla en el celular:** abrir la dirección en Chrome → menú → "Añadir a la pantalla de inicio" (es una PWA).

Decisiones que le tocan al propietario (las ejecuta el administrador): topes y descuento general, descuento propio de clientes frecuentes, y la atención de solicitudes de datos personales.

## 3. Guía del administrador (en síntesis)

Cada tarea y dónde se hace (menú lateral en computador; "Más" en el celular):

| Tarea | Dónde |
|---|---|
| Crear usuarios, roles, restablecer contraseñas | Negocio › **Usuarios** |
| Productos, precios, recetas de anchetas | **Inventario** |
| Registrar mercancía que llega | Inventario y compras › **Compras** (la recepción suma al stock y pregunta cómo se pagó; la compra aparece en Gastos) |
| Costos de los productos y completar ventas anteriores | Negocio › **Ganancias** |
| Descuento general y topes del vendedor | Negocio › **Descuentos** |
| Datos del negocio, enlace de autorregistro, solicitudes de titulares | Clientes › **Datos personales** |
| Registrar, corregir y anular gastos; ver totales; exportar | Gastos y caja › **Gastos** (se ve todo, también las compras recibidas) |
| Crear, renombrar y desactivar categorías de gasto | Gastos y caja › **Gastos** › **Categorías** ("Compra de mercancía" no se toca) |
| Abrir, mover y cerrar la caja; revisar el historial de cortes y exportarlo; corregir un gasto que ya cubre un corte cerrado | Gastos y caja › **Caja** (el administrador sí puede corregir un gasto de un corte cerrado; el corte conserva su foto) |
| Respaldos | Automáticos a las 2:30 a. m.; se conservan 14 días |

## 4. Guión de las sesiones

### 4.1 Sesión presencial con el vendedor (aprox. 2 horas, antes de abrir)

1. (10 min) Recorrido: iniciar sesión, secciones, cerrar sesión, cambiar contraseña.
2. (30 min) Ventas guiadas: unidad, paquete, ancheta; lector de código de barras; búsqueda por nombre.
3. (20 min) Pagos: efectivo con vueltas, tarjeta, Nequi/Daviplata, pago mixto.
4. (15 min) Descuentos y cambio de vendedor.
5. (25 min) Clientes: buscar, registrar con autorización (**practicar cómo se pide**), casilla de promociones y enlace de autorregistro.
6. (10 min) Ticket: reimprimir y qué hacer si no sale.
7. (10 min) Fallas comunes (tabla 1.8) y a quién llamar.
8. (15 min, cuando se active la G1 y la G2) Gastos y caja: registrar un gasto, abrir la caja, registrar un retiro y hacer un corte de práctica (apartados 1.10 y 1.11).

**Criterio de éxito (RNF):** el vendedor hace sin ayuda una venta con pago mixto y un descuento, y registra un cliente con autorización, en menos de 30 minutos de entrenamiento.

### 4.2 Sesión con el propietario (aprox. 45 min, remota o en tienda)

1. Dashboard: rangos, desglose, más vendidos.
2. Ganancias, la ganancia neta, el resultado de caja y qué significa "sin costo".
3. Bandeja de stock bajo y lista de compras por WhatsApp.
4. Descuentos y solicitudes de datos: qué decide él y qué ejecuta el administrador.
5. Instalar la PWA en su celular.

## 5. Lista de verificación de la puesta en marcha

**Servidor y aplicación**

- [ ] Despliegue de `dev` en verde en GitHub Actions y migraciones 0005 a 0010 aplicadas (las 0009 y 0010 son del Adendo v3).
- [ ] `nginx -s reload` sin errores tras el cambio de `limit_req`.
- [ ] El puerto 80 del servidor ya **no** responde desde fuera; solo el dominio por el túnel.
- [ ] Uptime Kuma monitorea `http://nginx:8080/api/health`.
- [ ] Respaldo del día generado (carpeta `./backups`) y verificado.
- [ ] En producción **no** se corrió `scripts.seed_demo`.
- [ ] Fase 9: agente de impresión actualizado en el PC del POS (acepta `referencia`) y migración 0008 aprobada y desplegada.
- [ ] Fase 9: el POS se abrió **con conexión** al menos una vez en el equipo de la tienda (descarga el catálogo guardado).
- [ ] Fase 9: prueba de corte en la tienda (sección 8 de `10-pruebas-de-aceptacion.md`): vender sin conexión, imprimir con número `SC-####` y comprobar que se envía sola al volver.
- [ ] Adendo v3: respaldo manual hecho, `MIGRACIONES_APROBADAS` con la 0009 y la 0010, PR `dev` → `main` fusionado y el checklist de staging de `DEPLOY.md` (puntos "Adendo v3") pasado.

**Datos**

- [ ] Catálogo de productos cargado (precios, categorías, stock inicial y stock mínimo).
- [ ] Costos cargados (para que las ganancias tengan sentido).
- [ ] Usuarios reales creados (vendedor, propietario, administrador); contraseñas de prueba cambiadas.
- [ ] "Datos del negocio" completos (la política deja de ser "borrador").
- [ ] Enlace de autorregistro generado y probado desde un celular.

**PC del POS**

- [ ] Agente de impresión actualizado (`actualizar.bat`) y con el dominio en `AGENTE_ORIGENES_PERMITIDOS`.
- [ ] Inicio automático del agente activado (`inicio-automatico.bat`).
- [ ] Ticket de prueba impreso, con el logo arriba, pagos, descuento y "Atendió" (el logo llega al actualizar el agente con `actualizar.bat`).
- [ ] Lector de código de barras probado.

**Papel**

- [ ] Formatos de autorización escrita y de solicitudes impresos (documento 08).
- [ ] Esta guía rápida (sección 1) impresa junto al POS.

**Pruebas de campo**

- [ ] Dashboard por el túnel desde el celular con datos móviles: carga en menos de 10 s (HU-03).
- [ ] Lista de compras enviada por WhatsApp.
- [ ] Venta completa con cliente y vendedor distinto.
- [ ] Gastos y caja (cuando se activen G1 y G2): un gasto de prueba, una caja abierta, un retiro y un corte; el propietario ve el corte y la ganancia neta.

**Lanzamiento**

- [ ] Fecha y hora de baja demanda, con el desarrollador disponible el primer día.
- [ ] Aprobación del propietario y PR `dev` → `main`; el servidor pasa a seguir `main`.

## Control de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 13-10-2026 | Santiago Chávez López | Primera versión: guía rápida del vendedor, guía del propietario y del administrador, guión de sesiones y lista de verificación de la puesta en marcha. |
| 1.1 | 13-10-2026 | Santiago Chávez López | "Ventas de hoy" del vendedor incluye lo que registró a nombre de otra persona. |
| 1.2 | 14-10-2026 | Santiago Chávez López | Modo sin conexión (Fase 9): apartado 1.9 de la guía del vendedor, fila de "La aplicación no carga" y puntos nuevos de la lista de verificación. |
| 1.3 | 19-10-2026 | Santiago Chávez López | El cartel lleva el enlace de autorregistro y su código QR; herramientas para generar el PDF de los manuales y el cartel. |
| 1.4 | 19-10-2026 | Santiago Chávez López | Gastos (Fase G1): apartado 1.10 de la guía del vendedor, pestaña Gastos del propietario y tareas nuevas del administrador. Caja y corte (G2) se agregan al terminarla. |
| 1.5 | 20-10-2026 | Santiago Chávez López | Caja y corte (Fase G2): apartado 1.11 de la guía del vendedor, pestaña Caja y ganancia neta del propietario, tarea nueva del administrador y puntos en el guión y la lista de verificación. |
| 1.6 | 21-10-2026 | Santiago Chávez López | Lista de verificación al día: migraciones 0005 a 0010 y punto del despliegue del Adendo v3. |
| 1.7 | 21-10-2026 | Santiago Chávez López | Se quita de la lista de verificación el cartel del aviso de privacidad con QR (no se va a usar). |
