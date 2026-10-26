**PIÑATERÍA DEMO**

Sistema de Ventas e Inventarios

**Historias de Usuario y Criterios de Aceptación**

Versión 1.10 (incluye Adendo v2, Fase 9 y Adendo v3)

2026

*Confidencial – Uso interno*

# 1. Introducción y Marco Metodológico

La Piñatería Demo se encuentra en una coyuntura de modernización tecnológica, transitando de un sistema de registro manual en cuadernos hacia una arquitectura digital centralizada. Esta transición es estratégica: busca eliminar la asimetría de información entre el Propietario (que supervisa de forma remota) y la operativa diaria del Vendedor en la tienda física.

La implementación de Historias de Usuario (HU) permite traducir las necesidades de negocio en requerimientos técnicos verificables, garantizando que el desarrollo se mantenga alineado con los objetivos de control de stock y visibilidad financiera.

Para este proyecto se ha seleccionado un enfoque ágil basado en Kanban con entregas incrementales. Esta metodología es fundamental para mitigar la resistencia al cambio en el personal de tienda, cuyo perfil técnico es básico. Al entregar funcionalidades operativas de manera gradual (comenzando por el POS), el personal puede asimilar la herramienta sin verse abrumado por la complejidad total del sistema.

La estructura que se presenta a continuación asegura la trazabilidad técnica, vinculando cada historia con los Requerimientos Funcionales (RF) definidos en el Documento de Visión (v1.4) y el Plan de Trabajo (v1.2).

**Versión 1.1.** Esta versión (a) agrega a cada historia HU-01 a HU-04 una nota con lo que quedó implementado en las Fases 1 a 6 y (b) incorpora el **Adendo v2** —una ampliación del alcance que no reemplaza nada de lo aprobado—: las historias HU-05 a HU-10 (pagos mixtos y vueltas, descuentos, clientes con Habeas Data, cambio de vendedor, ganancias y bandeja de notificaciones con lista de compras), que cubren los requerimientos RF-022 a RF-049 y se entregan en las fases A1, A2 y A3 y en la mejora B1.

**Versión 1.2.** Agrega a HU-10 la nota de lo implementado en la mejora B1.

**Versión 1.3.** Agrega a HU-05 y HU-06 la nota de lo implementado en la Fase A1.

**Versión 1.4.** Agrega a HU-09 la nota de lo implementado en la Fase A3.

**Versión 1.5.** La Fase A3 deja de figurar como opcional: el propietario la aprobó.

# 2. Estructura de la Plantilla Estándar

Considerando que el proyecto es ejecutado por un único desarrollador, la plantilla de HU se ha optimizado para maximizar la claridad técnica y minimizar la ambigüedad en los criterios de aceptación, reduciendo así la necesidad de reprocesos.

| Campo | Descripción |
| :---- | :---- |
| ID de la Historia | Identificador único vinculado al Requerimiento Funcional (ej. HU-00X – RF-XXX). |
| Título | Nombre descriptivo de la funcionalidad. |
| Narrativa | Estructura estándar: Como Rol, Quiero Acción, Para Beneficio. |
| Criterios de Aceptación | Lista de condiciones binarias (Pasa/No Pasa) para validar la funcionalidad. |
| Prioridad | Nivel de importancia según el Documento de Visión (Alta/Media/Baja). |
| Notas Técnicas | Especificaciones de implementación (DB, Hardware, Protocolos). |

Esta estandarización permite que cada incremento de software sea evaluado objetivamente durante las revisiones quincenales con el propietario.

# 3. Especificación de Historias de Usuario Clave

## 3.1  HU-01: Proceso de Venta Híbrida en el POS

*RF-001, RF-019, RF-020*

El sistema debe equilibrar la velocidad necesaria para productos de alta rotación con la flexibilidad para artículos artesanales (anchetas) o mermas que carecen de etiquetas.

**Narrativa**

Como **Vendedor**, quiero procesar ventas utilizando tanto el lector de códigos de barras como la búsqueda manual por texto, para garantizar que ningún producto quede fuera del registro por falta de etiquetado.

**Criterios de Aceptación**

* Validar que al escanear un código de barras, el producto se agregue al carrito de compras de forma inmediata (sin clics adicionales).

* Confirmar que el buscador manual retorne coincidencias parciales por nombre o categoría en menos de 1 segundo.

* Verificar que la transacción finalice correctamente y dispare la orden de impresión a la Epson TM-T20II en menos de 2 segundos.

* Validar que el stock en la base de datos PostgreSQL disminuya exactamente en la cantidad vendida al confirmar el pago.

**Prioridad**

Alta (proceso base) / Media (buscador híbrido).

**Notas Técnicas**

El lector USB tipo pistola opera bajo emulación de teclado (HID); el frontend debe capturar el evento onKeyPress y limpiar el buffer tras cada lectura. La comunicación con la Epson TM-T20II se realizará mediante el driver térmico estándar sobre protocolo USB.

**Estado de implementación (v1.1) — Fase 1**

* Implementada y cerrada el 27-09-2026. El total de la venta se redondea al múltiplo de $50 más cercano y el ticket impreso muestra la línea "Ajuste por redondeo" solo cuando el redondeo ocurre.

* El historial de ventas del día (RF-018) usa la zona horaria America/Bogota. La impresión ocurre después de que el backend confirma la venta: si el agente de impresión falla, la venta queda registrada y el ticket se puede reimprimir.

* **Adendo v2:** esta historia se amplía con los pagos mixtos y las vueltas (HU-05), los descuentos (HU-06), el cliente asociado (HU-07) y la elección del vendedor (HU-08). Los criterios anteriores siguen vigentes.

## 3.2  HU-02: Registro de Productos con Atributos Flexibles

*RF-006, RF-016*

Dada la naturaleza del inventario (más de 150 productos), la base de datos debe permitir el crecimiento del catálogo sin restricciones técnicas por ausencia de códigos de fábrica.

**Narrativa**

Como **Administrador**, quiero registrar nuevos artículos definiendo el código de barras como un campo opcional, para agilizar el ingreso de mercancía artesanal o sin etiquetas.

**Criterios de Aceptación**

* Verificar que el formulario de creación permita guardar un producto dejando el campo codigo_barras vacío.

* Confirmar que el sistema arroje un error de validación si los campos nombre, precio, categoría o stock_inicial están ausentes.

* Validar que el registro sea persistido correctamente en PostgreSQL y sea inmediatamente visible en el POS.

**Prioridad**

Alta.

**Notas Técnicas**

El esquema de la tabla productos en PostgreSQL debe definir la columna codigo_barras como VARCHAR con restricción NULL permitida, mientras que los campos obligatorios deben llevar la restricción NOT NULL.

**Estado de implementación (v1.1) — Fases 2, 5 y 6**

* Implementada: alta, edición, desactivación y reactivación de productos (RF-016), con código de barras opcional y único cuando existe.

* Fase 6: los productos tipo paquete o ancheta se arman con una receta que se define desde Inventario (casilla "Producto compuesto"). La ficha del producto muestra de qué artículos está compuesto y, al desactivar un producto que forma parte de una ancheta, el sistema avisa cuáles lo usan; su stock se sigue descontando al armar la ancheta.

## 3.3  HU-03: Supervisión Remota vía Dashboard PWA

*RF-013, RF-014*

La visibilidad remota es el valor central para el propietario remoto, quien requiere supervisión sin las complicaciones de instalación de apps nativas o configuraciones de red complejas.

**Narrativa**

Como **Propietario**, quiero acceder a un panel de control desde mi smartphone, para monitorear las ventas y recibir alertas de stock bajo en tiempo real desde fuera de la tienda.

**Criterios de Aceptación**

* Verificar que el Dashboard cargue en menos de 10 segundos desde una red móvil externa.

* Confirmar que se visualicen las ventas totales del día actual actualizadas automáticamente.

* Validar que las alertas de stock bajo se generen cuando la cantidad sea menor o igual al stock_minimo configurado.

* Garantizar el acceso remoto, validando que la arquitectura Cloudflare Tunnel permite el ingreso seguro a pesar del CG-NAT del proveedor residencial.

**Prioridad**

Alta.

**Notas Técnicas**

Implementación de Progressive Web App (PWA) con Service Workers para caché de interfaz. Se requiere Redis y Celery para la gestión de colas de tareas asíncronas encargadas del envío de notificaciones y procesamiento de alertas.

**Estado de implementación (v1.1) — Fase 4**

* Implementada el 29-09-2026: resumen por rango de fechas, alertas de stock bajo (revisión cada 15 minutos) y PWA instalable. El service worker solo guarda la interfaz y nunca las respuestas de la API.

* Pendiente de verificación en campo: la prueba de carga en menos de 10 segundos desde una red móvil externa, usando el túnel de Cloudflare.

* **Adendo v2:** el total por método de pago del resumen se calcula por monto recibido a partir de los pagos de cada venta (RF-041, HU-05); en la Fase A3 se agrega un dashboard de ganancias (HU-09).

* **Adendo v2 (mejora B1):** las alertas de stock bajo se muestran además en una bandeja de notificaciones y alimentan una lista de compras exportable por WhatsApp (HU-10).

## 3.4  HU-04: Restricción de Información Sensible de Proveedores

*RF-012, RF-021*

La protección de la cadena de suministro es crítica para la competitividad del negocio, limitando el acceso a datos de costos y contactos comerciales.

**Narrativa**

Como **Administrador**, quiero restringir el acceso al módulo de proveedores, para asegurar que el personal de ventas no pueda visualizar información estratégica de costos y contactos.

**Criterios de Aceptación**

* Validar que un usuario con rol "Vendedor" no visualice el botón o enlace a "Proveedores" en la interfaz.

* Confirmar que cualquier intento de acceso directo vía URL (ej. /api/v1/suppliers) por un "Vendedor" retorne un código de estado 403 Forbidden.

* Asegurar que el usuario "Administrador" pueda realizar CRUD completo sobre el directorio de proveedores.

**Prioridad**

Alta.

**Notas Técnicas**

Uso de Control de Acceso Basado en Roles (RBAC). En el backend (FastAPI), implementar la verificación mediante Dependency Injection en los endpoints sensibles, validando el role dentro del payload del JWT.

## 3.5  HU-05: Pagos Mixtos, Plataforma de Transferencia y Vueltas (Adendo v2)

*RF-022, RF-023, RF-024, RF-041 — Fase A1*

Hasta ahora una venta tenía un único método de pago. Es común que un cliente pague una parte en efectivo y otra por Nequi, Daviplata o tarjeta, y que pague en efectivo con un billete mayor al valor y requiera vueltas.

**Narrativa**

Como **Vendedor**, quiero registrar varios pagos en una misma venta y, cuando el pago es en efectivo, ver cuánto me entregó el cliente y cuánto debo devolverle, para cobrar correctamente sin hacer cuentas a mano.

**Criterios de Aceptación**

* Verificar que se puedan agregar uno o más pagos a la venta, cada uno con método (efectivo, tarjeta o transferencia) y monto, y que el sistema no permita confirmar la venta si la suma de los pagos es distinta del total (mostrando cuánto falta o sobra).

* Confirmar que al elegir transferencia el sistema obligue a elegir la plataforma: Nequi o Daviplata.

* Validar que, en un pago en efectivo, se ingrese el monto recibido, que no pueda ser menor al monto del pago, y que el sistema muestre las vueltas (monto recibido menos monto del pago).

* Verificar que el ticket impreso liste cada pago con su método (y plataforma) y, en efectivo, el monto recibido y las vueltas.

* Comprobar que el resumen del día del Dashboard agrupe el total por método de pago usando el monto de cada pago (no el número de ventas).

* Confirmar que las ventas anteriores al adendo conserven su método de pago original tras la migración y que la venta con pagos mixtos siga confirmándose en menos de 2 segundos.

**Prioridad**

Alta.

**Notas Técnicas**

Tabla pagos_venta (ver Diseño de Base de Datos, sección 7.3); ventas.metodo_pago se elimina y su contenido se migra. La validación de que la suma de los pagos es igual al total se hace en la misma transacción que crea la venta. El payload del agente de impresión se extiende con la lista de pagos y las vueltas.

**Estado de implementación (v1.3) — Fase A1**

* Implementada el 08-10-2026 (migración 0002). La confirmación de pago arranca con un pago en efectivo por el total; se pueden agregar pagos (el nuevo se llena con lo que falta) y la pantalla muestra cuánto falta o sobra. En efectivo, si no se escribe lo recibido, se toma como pago exacto.

* Los pagos van en pesos enteros; el pago en efectivo y lo recibido deben ser múltiplos de $50. Tarjeta y transferencia aceptan cualquier monto entero. Una venta con total $0 no lleva pagos.

* El Dashboard y el historial del día suman por método el monto de cada pago. El ticket imprime subtotal, descuento, ajuste por redondeo, total y cada pago con su plataforma, lo recibido y las vueltas. El agente de impresión acepta también el formato anterior, para poder actualizarlo antes que el servidor.

* Las ventas anteriores conservan su método en un pago (las transferencias, sin plataforma). La migración se ensayó (subida y bajada) sobre una base temporal con datos; falta el ensayo en staging con una copia real.

## 3.6  HU-06: Descuentos por Cliente, General y Manual (Adendo v2)

*RF-025, RF-026, RF-027, RF-028, RF-042 — Fases A1 y A2*

El propietario quiere premiar a clientes frecuentes y ofrecer un descuento general, pero el vendedor necesita flexibilidad para ajustarlo según la situación de cada venta.

**Narrativa**

Como **Administrador**, quiero definir un descuento general y uno propio para cada cliente registrado; y como **Vendedor**, quiero que el sistema sugiera el descuento que corresponde y poder cambiarlo o quitarlo durante la venta.

**Criterios de Aceptación**

* Verificar que solo el administrador pueda configurar el descuento general (porcentaje o monto fijo, activo o apagado) y asignar el descuento propio de un cliente; el vendedor que lo intente recibe 403.

* Confirmar que, al asociar un cliente con descuento propio, se sugiera ese descuento; que el descuento general no se aplique solo a todas las ventas, sino que el vendedor pueda aplicarlo a quien corresponda cuando está activo (decisión del 08-10-2026); y que nunca se sumen los dos (el del cliente tiene prioridad).

* Validar que el vendedor pueda cambiar o quitar el descuento durante la venta y que la venta quede marcada con origen manual.

* Verificar que solo el administrador pueda configurar los topes del descuento manual (porcentaje máximo y monto máximo, cada uno opcional), que el vendedor no pueda aplicar un descuento que supere cualquiera de los dos y que el sistema le indique el límite vigente; y que los topes no limiten al administrador ni a los descuentos sugeridos (del cliente y general).

* Verificar que el descuento se calcule sobre el subtotal de la venta, que el total se redondee a múltiplo de $50 después de descontar, que un porcentaje no supere 100 y que el descuento no pueda ser mayor al subtotal.

* Comprobar que la venta guarde el origen, el tipo, el valor y el monto del descuento, y que el ticket muestre subtotal, descuento y total.

**Prioridad**

Alta.

**Notas Técnicas**

Tablas descuento_general y tope_descuento, columnas descuento_\* de ventas y detalle_ventas.descuento_prorrateado (ver Diseño de Base de Datos, secciones 7.4, 7.4.1 y 7.7). El descuento propio del cliente depende de HU-07, por lo que se activa en la Fase A2; en la Fase A1 funcionan el descuento general y el manual. Los topes de descuento manual son configurables por el administrador (RF-042); los valores concretos los define el propietario (Visión, Anexo B).

**Estado de implementación (v1.3) — Fase A1**

* Implementada el 08-10-2026. El administrador configura el descuento general y los topes en la pestaña "Descuentos" del punto de venta; los topes quedan sin límite hasta que se configuren.

* Cada venta arranca sin descuento. Si el descuento general está activo, el POS muestra el botón "Aplicar descuento general" para usarlo solo con quien corresponda (origen general, sin topes). El vendedor también puede escribir un descuento manual en porcentaje o en pesos (origen manual); al vendedor se le muestra su límite y no puede confirmar si lo supera; al administrador no lo limitan los topes. "Quitar" deja la venta sin descuento.

* Un descuento general en pesos mayor que el subtotal se limita al subtotal. Si el administrador apaga el descuento general mientras se hace una venta que lo usa, el backend responde que cambió y el POS recarga la configuración.

* El descuento se reparte entre las líneas y cada línea guarda el costo vigente del producto (columna de la Fase A3, creada en la 0002).

* **Fase A2 (12-10-2026):** el descuento propio del cliente se asigna en la ficha del cliente (solo administrador, `PUT /clientes/{id}/descuento`). Al elegir en la venta un cliente que lo tiene, el POS lo sugiere de una vez (origen cliente, sin topes) y reemplaza al general; el vendedor puede cambiarlo (pasa a manual, con topes) o quitarlo. El servidor usa el descuento que tiene el cliente en ese momento, no el que mande el POS.

## 3.7  HU-07: Registro de Clientes con Cumplimiento de Habeas Data (Adendo v2)

*RF-029 a RF-035, RF-046 a RF-049 — Fase A2*

Registrar clientes permite asociar compras, aplicar descuentos y consultar su historial, pero implica tratar datos personales y cumplir la Ley 1581 de 2012 (Visión, Anexo A).

**Narrativa**

Como **Vendedor**, quiero registrar, buscar y asociar clientes a mis ventas; como **Administrador**, quiero atender los derechos de los titulares de los datos; y como **Cliente**, quiero poder registrar yo mismo mis datos desde un enlace, aceptando el tratamiento de mis datos, para agilizar el registro y que todo quede conforme a la ley.

**Criterios de Aceptación**

* Verificar que no se pueda guardar un cliente sin marcar la autorización de tratamiento de datos, y que se registren la fecha, el medio (escrito, electrónico o verbal), la versión de la política y el empleado que la recogió.

* Confirmar que se puedan crear, editar y desactivar clientes (nombre, documento, teléfono y correo), que el documento no se repita, que el teléfono tenga solo dígitos (7 a 15) y que un cliente con ventas nunca se elimine.

* Validar que la búsqueda por nombre (coincidencia parcial), documento o teléfono responda en menos de 1 segundo.

* Comprobar que se pueda asociar un cliente a la venta y que un cliente desactivado o con la autorización revocada no pueda asociarse.

* Verificar que la ficha del cliente muestre su historial de ventas (fecha, total, vendedor y pagos) y el total comprado, y que el listado se pueda filtrar por rangos de total comprado y de fechas de compra.

* Confirmar que el administrador pueda registrar solicitudes de consulta, actualización, supresión y revocatoria con su fecha límite legal; que al resolver una supresión los datos personales queden anonimizados y las ventas se conserven; y que el vendedor reciba 403 en la gestión de solicitudes.

* Verificar que el enlace público abra un formulario sin pedir inicio de sesión, que muestre el aviso de privacidad y la política vigente y que no permita enviar sin marcar la aceptación.

* Confirmar que, al enviarlo, el cliente quede registrado con origen autorregistro, medio electrónico, fecha y versión de la política, sin descuento propio, y que se pueda asociar a una venta como cualquier otro cliente.

* Validar que el administrador pueda consultar, copiar, desactivar y regenerar el enlace, y que un enlace desactivado o regenerado deje de funcionar con un mensaje claro.

* Comprobar que, si el documento o el teléfono ya existen, el formulario responda de forma neutra sin revelar ni modificar los datos existentes, y que el límite de envíos y el campo trampa bloqueen el uso abusivo.

**Prioridad**

Alta.

**Notas Técnicas**

Tablas clientes y solicitudes_titular y vista vw_clientes_resumen (ver Diseño de Base de Datos, secciones 7.5, 7.6 y 7.9). Plazos legales: consultas, 10 días hábiles prorrogables 5; reclamos, 15 días hábiles prorrogables 8. Los textos del aviso de privacidad y de la política se elaboran con el propietario antes del lanzamiento (Visión, Anexo A.5). El autorregistro usa la tabla enlace_autoregistro y la columna clientes.origen_registro (Diseño de Base de Datos, secciones 7.5 y 7.5.1) y un endpoint público protegido por un código aleatorio en el enlace; la página pública es una ruta del frontend que no exige sesión. No se guarda la dirección IP del cliente.

**Estado de implementación (v1.6) — Fase A2**

* Implementada el 12-10-2026 (migración 0005), incluido el autorregistro por enlace (RF-046 a RF-049).

* Pestaña "Clientes" (vendedor y administrador): búsqueda por nombre (parcial), documento o teléfono; alta que exige marcar la autorización y elegir el medio (el servidor guarda fecha, versión de la política `POLITICA_DATOS_VERSION` y empleado); edición, baja y alta; ficha con la evidencia de la autorización, total comprado y historial (fecha, total, vendedor y pagos); filtros por total comprado y por fechas de compra (con fechas, solo cuentan las compras de ese rango). El alta también está disponible desde la venta.

* Pestaña "Datos personales" (solo administrador): las solicitudes se registran desde la ficha con su fecha límite (consulta, 10 días hábiles; reclamos, 15, sin descontar festivos) y se atienden con respuesta obligatoria. Resolver una supresión pide confirmación y anonimiza al cliente conservando sus ventas; resolver una revocatoria bloquea su uso en ventas nuevas. Una solicitud cerrada no se reabre. El vendedor recibe 403 en todas las rutas de solicitudes.

* Un cliente desactivado, con la autorización revocada o anonimizado no se asocia a la venta (422).

* **Actualización (13-10-2026):** al resolver una supresión también se borra la descripción libre de todas las solicitudes del cliente (podía contener datos personales); el tipo, las fechas y la respuesta se conservan.

* Aviso y política: el alta (POS) y el formulario público muestran el aviso de privacidad y, desplegable, la política completa; el texto lo arma el backend y la versión que queda como evidencia es la que se mostró ("borrador" mientras falten datos en "Datos personales › Datos del negocio", que el administrador edita en la aplicación). Las promociones son una casilla aparte, desmarcada por defecto, con su fecha; se pueden dar o retirar después, y revocar la autorización o suprimir al cliente las retira. El listado filtra a quienes las aceptaron.

* Autorregistro: el administrador genera, copia, desactiva y regenera el enlace desde "Datos personales" (sin los datos del negocio no se puede publicar). La página `/registro/<código>` no pide sesión, no deja enviar sin aceptar, guarda origen autorregistro, medio electrónico, fecha y versión, sin descuento propio y sin guardar la IP. Un duplicado (documento o teléfono) o el campo trampa reciben la misma respuesta de agradecimiento y no crean ni modifican nada; un enlace desactivado o regenerado responde con un mensaje claro; hay límite de envíos en Nginx y en el backend.

## 3.8  HU-08: Cambio de Vendedor por Venta (Adendo v2)

*RF-036 — Fase A2*

En el PC del punto de venta puede haber una sola sesión abierta mientras atienden distintas personas. La venta debe quedar a nombre de quien la realizó.

**Narrativa**

Como **Vendedor o Administrador**, quiero elegir en la pantalla de venta quién realiza esa venta, para que cada venta quede registrada a nombre de la persona que la hizo.

**Criterios de Aceptación**

* Verificar que el POS muestre un desplegable con los vendedores y administradores activos, con el usuario de la sesión seleccionado por defecto.

* Confirmar que, al confirmar la venta, esta quede asignada al vendedor elegido y que así aparezca en el historial de ventas y en el ticket.

* Validar que el vendedor se asigne por venta y no por producto, y que cambiarlo no afecte otras ventas.

* Comprobar que los usuarios inactivos y los de rol propietario no aparezcan en el desplegable y que el servidor rechace una venta asignada a un usuario inválido.

* Verificar que el historial de un vendedor muestre las ventas que quedaron a su nombre y también las que él registró a nombre de otra persona (decisión del 13-10-2026), con la leyenda "Registrada por" cuando quien la registró no es el vendedor, y que no muestre las de nadie más.

**Prioridad**

Alta.

**Notas Técnicas**

No requiere cambios de esquema: ventas.usuario_id pasa a significar "vendedor que realizó la venta". Se agrega un endpoint de lectura con la lista de usuarios elegibles, accesible para el rol vendedor.

**Estado de implementación (v1.6) — Fase A2**

* Implementada el 12-10-2026. `GET /ventas/vendedores` lista a los vendedores y administradores activos; `POST /ventas` acepta `vendedor_id` (si falta, es el usuario de la sesión) y responde 422 si el usuario no existe, está inactivo o es propietario.

* En el POS el desplegable "Vendedor" arranca con la sesión y vuelve a ella después de cada venta, para que nadie herede la venta de otro. El ticket imprime "Atendió: nombre" (campo opcional `vendedor` del agente de impresión, que sigue aceptando el formato anterior) y el historial de ventas lo muestra. El historial de un vendedor muestra las ventas que quedaron a su nombre, aunque las haya registrado otra sesión.

* **Actualización (13-10-2026, migración 0007):** `ventas.registrada_por_id` guarda quién tenía la sesión al registrar la venta. El historial del vendedor suma las ventas que él registró a nombre de otra persona y las muestra con "Registrada por: nombre" cuando es alguien distinto del vendedor. Las ventas anteriores a la 0007 quedan sin ese dato y se entienden registradas por su vendedor. El administrador sigue viendo todas.

## 3.9  HU-09: Módulo de Ganancias (Adendo v2)

*RF-037, RF-038, RF-039, RF-040 — Fase A3*

El propietario quiere saber cuánto gana realmente, no solo cuánto vende. El propietario aprobó la Fase A3 el 08-10-2026.

**Narrativa**

Como **Propietario**, quiero ver el margen bruto de mis ventas por producto y por periodo en un dashboard con gráficos, para saber qué productos dejan más ganancia.

**Criterios de Aceptación**

* Verificar que el administrador pueda registrar a mano el costo de cada producto y que, para una ancheta, el sistema muestre un costo sugerido (suma de los costos de sus componentes) que también se pueda ajustar a mano.

* Confirmar que cada línea vendida guarde el costo vigente y que cambiar el costo de un producto después no altere el margen de las ventas pasadas.

* Validar que el margen bruto de una línea sea el subtotal menos el descuento prorrateado menos el costo por la cantidad, y que los productos sin costo se excluyan del margen y se informen como "sin costo".

* Comprobar que el dashboard muestre el margen por periodo y por producto con gráficos.

* Verificar que el vendedor reciba 403 al consultar costos y ganancias y que no vea el costo en ninguna pantalla; solo el administrador y el propietario acceden.

**Prioridad**

Media.

**Notas Técnicas**

Columnas costo_unitario de productos y detalle_ventas y vista vw_margen_detalle (Diseño de Base de Datos, secciones 7.7 y 7.9). Se recomienda crear las columnas de costo desde la Fase A1 para que las ventas intermedias también tengan margen (Visión, Anexo B).

**Estado de implementación (v1.4) — Fase A3**

* Implementada el 08-10-2026. Las columnas de costo se crearon en la migración 0002 (desde A1 cada venta guarda el costo vigente) y la vista vw_margen_detalle en la 0004.

* El administrador carga los costos en una tabla (pestaña "Ganancias" › Costos del punto de venta): costo editable en la fila, costo sugerido para paquetes y anchetas (suma del costo de sus componentes por la cantidad de la receta; si a un componente le falta el costo, se avisa) y filtro "sin costo". El propietario ve la tabla sin editarla.

* El dashboard de ganancias (pestaña "Ganancias" del administrador y vista "Ventas | Ganancias" del Dashboard del propietario) muestra margen bruto, porcentaje, vendido y costo del rango, el margen por período (las pérdidas hacia abajo) y por producto. Las líneas sin costo se informan aparte; el ajuste por redondeo no entra en el margen.

* El administrador puede completar, con el costo actual, solo las líneas de ventas pasadas que no tienen costo (pide confirmación; es una aproximación para las ventas hechas antes de cargar los costos).

* El vendedor recibe 403 en costos y ganancias y ninguna respuesta que él ve incluye costos (verificado con pruebas).

## 3.10  HU-10: Bandeja de Notificaciones y Lista de Compras por WhatsApp (Adendo v2, mejora B1)

*RF-043, RF-044, RF-045 — Mejora B1*

Hoy las alertas de stock bajo solo se ven al abrir el Dashboard y no se guardan en ninguna pantalla. El propietario necesita una bandeja que le recuerde qué hay que comprar y una forma rápida de pasar esa lista a quien hace las compras.

**Narrativa**

Como **Propietario o Administrador**, quiero ver en el Dashboard una bandeja con las alertas de stock bajo y exportar la lista de lo que hay que comprar por WhatsApp, para decidir y hacer las compras sin revisar producto por producto.

**Criterios de Aceptación**

* Verificar que la bandeja muestre las notificaciones de stock bajo de la más reciente a la más antigua y que el Dashboard muestre el contador de no leídas.

* Confirmar que se pueda marcar una notificación como leída o todas a la vez, y que las leídas dejen de contar.

* Validar que un producto no genere avisos duplicados mientras tenga una alerta sin leer (comportamiento ya existente de la tarea programada).

* Comprobar que la lista de compras incluya cada producto activo en stock bajo con su stock actual, su stock mínimo y la cantidad faltante (stock mínimo menos stock actual), calculada al abrirla.

* Verificar que el botón de WhatsApp abra WhatsApp con la lista escrita como mensaje, en celular y en computador, y que exista la opción de copiarla como texto.

* Confirmar que el vendedor reciba 403 al consultar la bandeja y la lista de compras.

**Prioridad**

Media.

**Notas Técnicas**

Sin cambios de esquema: la bandeja usa la tabla notificaciones y su columna leida, y la lista de compras se calcula con la vista vw_alertas_stock_bajo. Endpoints para propietario y administrador: GET /notificaciones, PATCH /notificaciones/{id}/leida, PATCH /notificaciones/leer-todas y GET /dashboard/lista-compras. La exportación usa un enlace https://wa.me con el mensaje codificado; el usuario elige el chat y envía el mensaje. Para listas muy largas, que superen el límite práctico de una URL, se ofrece copiar el texto.

**Estado de implementación (v1.2) — Mejora B1**

* Implementada el 08-10-2026. El propietario ve en el Dashboard un botón "Stock bajo" con el contador de no leídas, que abre la bandeja y la lista de compras. El administrador, que no tiene Dashboard, las ve en una pestaña "Stock bajo" del punto de venta. El vendedor no las ve y la API le responde 403.

* La lista de compras incluye los productos que están justo en el mínimo (faltante 0, "en el mínimo") y los paquetes y anchetas como cualquier otro producto. El mensaje de WhatsApp va agrupado por categoría y, si el enlace supera 2000 caracteres, solo se ofrece copiar el texto.

* Una notificación sigue sin leer hasta que alguien la marca, aunque el producto ya se haya repuesto; la lista de compras sí refleja el stock del momento.

* Pendiente de verificación en campo: abrir WhatsApp con la lista desde el celular del propietario y desde el computador.

## 3.11  HU-11: Vender sin Conexión (Fase 9)

*RF-050 a RF-057 — Fase 9*

El servidor está fuera de la tienda: si se cae internet en la tienda (o el servidor o el túnel), el POS dejaba de poder vender. La tienda no puede cerrar la caja por un corte de internet.

**Narrativa**

Como **Vendedor**, quiero seguir vendiendo cuando no hay conexión con el servidor y que mis ventas se registren solas cuando vuelva, para no perder ventas ni tener que anotarlas en papel.

**Criterios de Aceptación**

* Verificar que, sin conexión, el POS avise con claridad ("Sin conexión con el servidor. Puedes seguir vendiendo…"), siga buscando productos en el catálogo guardado y deje armar la venta, cobrar con pagos mixtos y vueltas, aplicar descuentos y elegir el vendedor.

* Confirmar que al confirmar la venta sin conexión se guarde en el equipo, se muestre "Venta SC-0001 guardada sin conexión" y el ticket se imprima con ese número local; la pantalla queda lista para la siguiente venta.

* Validar que la venta guardada sobreviva a cerrar la pestaña, recargar la página o reiniciar el equipo, y que la aplicación abra aunque no haya internet (con la sesión iniciada).

* Comprobar que al volver la conexión las ventas guardadas se envíen solas, de la más antigua a la más reciente, queden con la hora en que se hicieron y se marquen "Sin conexión" en "Ventas de hoy".

* Verificar que reenviar una venta que el servidor ya recibió (se perdió la respuesta) no la duplique ni descuente el stock otra vez.

* Confirmar que la venta conserve el precio y el descuento general que vio el cliente, aunque el precio o el descuento hayan cambiado durante el corte.

* Validar que, si el servidor rechaza una venta guardada (por ejemplo, sin stock suficiente), quede como "Necesita revisión" con el motivo, no frene a las demás y se pueda reintentar (tras corregir la causa), reimprimir o descartar (con confirmación).

* Comprobar que sin conexión no se pueda asociar un cliente a la venta y que no se guarden datos de clientes en el equipo.

* Verificar que cerrar sesión sin conexión, o con ventas guardadas, pida confirmación y explique que sin conexión no se puede volver a entrar; y que, con la sesión vencida, la barra pida iniciar sesión de nuevo y las ventas se envíen al hacerlo.

* Confirmar que un vendedor envíe solo las ventas que guardó él y que un administrador envíe las de todos.

**Prioridad**

Alta.

**Notas Técnicas**

Cada venta lleva un `uuid_cliente` (índice único en `ventas`); `POST /ventas` devuelve la venta existente con 200 si ya la tenía. La cola, el catálogo y la configuración viven en IndexedDB (`frontend/src/offline/`). La venta sin conexión viaja con `sin_conexion.fecha` y el precio de cada línea. Migración 0008. El agente de impresión acepta `referencia` en lugar de `venta_id`. Diseño completo en el documento 11.

**Estado de implementación (v1.9) — Fase 9**

* Implementada el 14-10-2026 (migración 0008). Verificada de extremo a extremo con un navegador real: la aplicación abre sin internet, la venta se guarda y se imprime con su número local, sobrevive a recargar la página y se envía sola al volver la conexión; un reenvío tras perder la respuesta no duplica la venta.

* Desplegada en producción el 14-10-2026 (migración 0008 aprobada y agente de impresión actualizado). Aceptada en la tienda el 14-10-2026 (prueba de corte de la sección 8 del documento 10, confirmada por el desarrollador).

## 3.12  HU-12: Gastos del Negocio (Adendo v3)

*RF-059 a RF-068 y RF-075 — Fases G1 y G3*

El negocio necesita saber cuánto gasta el negocio, no solo cuánto vende: arriendo, servicios, transporte, nómina y las compras de mercancía, cada uno con su forma de pago, para conocer la ganancia real y saber cuánto efectivo sale de la caja.

**Narrativa**

Como **Administrador**, quiero registrar, ver y corregir los gastos del negocio por categoría y forma de pago; como **Propietario**, quiero consultarlos y ver la ganancia neta; y como **Vendedor**, quiero anotar los gastos de caja que pago durante mi turno y corregir los que yo mismo anoté, para saber cuánto gana realmente el negocio.

**Criterios de Aceptación**

* Verificar que el administrador y el vendedor puedan registrar un gasto con categoría, descripción, monto, forma de pago (con Nequi o Daviplata si es transferencia), fecha y beneficiario opcional, y que un gasto en efectivo exija un múltiplo de $50.

* Confirmar que el vendedor solo vea, edite y anule los gastos que él registró (los de otras personas responden 404 o 403 aunque conozca el id), que no vea totales, compras ni ganancias, y que registre siempre con la fecha de hoy.

* Validar que el administrador pueda editar y anular cualquier gasto y elegir una fecha anterior (no futura), y que el propietario solo pueda consultar (registrar, editar y anular responden 403).

* Comprobar que anular exija un motivo, que el gasto siga visible tachado con quién, cuándo y por qué, que deje de sumar en los totales y que no se pueda borrar ni reactivar.

* Verificar que el administrador pueda crear, renombrar y desactivar categorías, que "Compra de mercancía" no se pueda modificar, que una categoría desactivada no se ofrezca para gastos nuevos pero conserve los antiguos y que los nombres queden con la primera letra en mayúscula.

* Confirmar que al recibir una compra se pida su forma de pago y que las compras recibidas aparezcan (solo para el administrador y el propietario) como filas de solo lectura de la categoría "Compra de mercancía", con su fecha de recepción, sumando al total de gastos; las pendientes y las canceladas no.

* Validar los filtros por rango (Hoy, Ayer, Semana, Mes, 3 meses, 6 meses, Año y personalizado), categoría, forma de pago y estado, y los totales por categoría y por forma de pago.

* Comprobar que Exportar genere un CSV (UTF-8 con BOM, punto y coma) con las mismas filas y filtros, que Excel lo abra con las tildes y las columnas bien, y que lo puedan hacer el administrador y el propietario pero no el vendedor.

* Verificar que Ganancias (administrador) y el Dashboard (propietario) muestren la ganancia neta (margen bruto menos gastos operativos, sin compras) y el resultado de caja (ventas cobradas menos todos los gastos), con el aviso "incompleta" si hay ventas sin costo.

* Confirmar que sin conexión las pantallas de gastos avisen que requieren conexión y que la cola de ventas sin conexión siga funcionando igual.

**Prioridad**

Alta.

**Notas Técnicas**

`categorias_gasto`, `gastos`, las columnas nuevas de `compras` y la vista `vw_gastos_unificados` (migración 0009; ver `03`, sección 8). Los permisos por rol y por dueño del gasto se validan en el servidor, no solo en la interfaz. El CSV lo genera el backend. Diseño completo en el documento 12.

**Estado de implementación (v1.11)**

* **Fase G1 implementada (19-10-2026) y desplegado en producción el 21-10-2026; pendiente de aceptación con el negocio:** categorías editables, gastos con permisos por rol y por dueño (404 en lo ajeno), anulación con motivo, compras recibidas unificadas con su forma de pago, filtros, totales, CSV y aviso de que requiere conexión. Pruebas automáticas en `backend/tests/test_g1_gastos.py` y `frontend/src/components/gastos.test.jsx`.
* **Fase G3 (ganancia neta y resultado de caja) implementada (20-10-2026) y desplegado en producción el 21-10-2026; pendiente de aceptación:** `GET /ganancias` agrega la ganancia neta (margen bruto menos gastos operativos, sin las compras de mercancía) y el resultado de caja, con el aviso de neta incompleta si faltan costos; se ven en Ganancias (administrador) y en el Dashboard (propietario). Pruebas en `backend/tests/test_g3_ganancia_neta.py` y `frontend/src/components/ganancias.test.jsx`.

## 3.13  HU-13: Dinero en Caja y Corte de Caja (Adendo v3)

*RF-069 a RF-075 — Fase G2*

Al terminar el turno o el día hay que saber cuánto efectivo debería haber en la caja y compararlo con lo que realmente hay, para detectar faltantes o sobrantes.

**Narrativa**

Como **Vendedor o Administrador**, quiero abrir la caja con su base, ver cuánto efectivo debería haber y hacer el corte contando lo que hay; y como **Propietario**, quiero consultar los cortes, para controlar el efectivo del negocio.

**Criterios de Aceptación**

* Verificar que se pueda abrir la caja con una base (múltiplo de $50) y que no se pueda abrir otra mientras haya una abierta.

* Confirmar que el apartado Caja muestre en vivo el efectivo esperado (base + ventas en efectivo + ingresos − gastos en efectivo − compras en efectivo − retiros) con su desglose, que se actualice al vender o registrar un gasto, que las vueltas no se resten dos veces y que los gastos anulados no cuenten.

* Validar que se puedan registrar ingresos y retiros con motivo (monto múltiplo de $50) y que afecten el esperado.

* Comprobar que lo vendido por tarjeta y por transferencia (Nequi y Daviplata) se muestre solo como información.

* Verificar el corte: al escribir el efectivo contado (múltiplo de $50) y las observaciones, el sistema calcula la diferencia (contado − esperado), cierra la caja y guarda la foto de las cifras; un corte cerrado no se puede modificar ni cerrar de nuevo.

* Confirmar que, con el corte cerrado, el vendedor no pueda editar ni anular los gastos que cubre, y que el administrador sí pueda sin alterar la foto del corte.

* Validar que el POS no deje cerrar la caja mientras ese equipo tenga ventas guardadas sin enviar (modo sin conexión), y que una venta sin conexión enviada después del cierre no altere el corte y aparezca como aviso en su ficha.

* Comprobar el historial de cortes (el administrador y el propietario ven todos; el vendedor, los que abrió o cerró), su detalle y su exportación a CSV.

* Verificar que el propietario solo pueda consultar (abrir, mover y cerrar la caja responden 403) y que sin conexión las pantallas de caja avisen que requieren conexión.

**Prioridad**

Alta.

**Notas Técnicas**

`cortes_caja` y `movimientos_caja` (migración 0010; ver `03`, sección 8). El efectivo esperado lo calcula el servidor con las ventas por `ventas.fecha` (la hora real, también las hechas sin conexión), los gastos por `creado_en` y las compras por `recibida_en`. Solo puede haber un corte abierto (índice único parcial). Diseño completo en el documento 12.

**Estado de implementación (v1.12)**

* **Fase G2 implementada (20-10-2026) y desplegado en producción el 21-10-2026; pendiente de aceptación con el negocio:** apertura con la base, efectivo esperado en vivo con su desglose, ingresos y retiros con motivo, cierre con el conteo y la diferencia, foto inmutable del corte, historial con ficha y exportación a CSV, bloqueo del vendedor sobre los gastos que cubre un corte cerrado (403) y del cierre mientras el equipo tenga ventas guardadas sin enviar, y aviso de las ventas sin conexión enviadas después del cierre. El propietario solo consulta. Pruebas automáticas en `backend/tests/test_g2_caja.py` y `frontend/src/components/caja.test.jsx`.

# 4. Garantía de Calidad y Definición de "Terminado" (DoD)

Para considerar una Historia de Usuario como finalizada, debe cumplir estrictamente con los siguientes criterios transversales, basados en los estándares de calidad del Plan de Trabajo v1.1:

* **Validación de Lógica:** la funcionalidad cumple al 100% con la narrativa y los Requerimientos Funcionales (RF) mapeados.

* **Entorno de Staging:** el código ha sido desplegado y probado en un contenedor Docker sobre Ubuntu Server, en un entorno espejo al de producción.

* **Rendimiento POS:** se ha verificado mediante pruebas de estrés básico que las operaciones de venta no superan los 2 segundos de respuesta.

* **Integridad de Hardware:** se ha confirmado la impresión física correcta en la Epson TM-T20II y la entrada de datos del lector USB (emulación HID).

* **Seguridad:** los endpoints cuentan con protección JWT y los roles de usuario están correctamente segregados.

* **Respaldo y Monitoreo:** el servicio está registrado y activo, y los respaldos se verifican periódicamente.

  * El servicio está registrado y activo en el dashboard de Uptime Kuma.

  * Se ha verificado la ejecución del script de respaldo automático de PostgreSQL y la generación del archivo .dump correspondiente.

* **Documentación:** se ha entregado la guía rápida de uso para el vendedor (formato digital/impreso).

* **Adendo v2:** las migraciones que transforman datos (la 0002) se ensayan en staging con una copia de la base y se genera un respaldo manual antes de aplicarlas en producción; se verifica con pruebas automáticas que la suma de los pagos de cada venta es igual a su total; los permisos por rol (costos, descuentos y datos de clientes) tienen pruebas que confirman el 403 del vendedor; y el módulo de clientes no se pone en producción sin el aviso de privacidad y la política de tratamiento de datos aprobados por el propietario.

# Control de Versiones

| Versión | Fecha | Autor | Cambios |
| :---- | :---- | :---- | :---- |
| 1.0 | 2026 | Santiago Chávez López | Versión inicial: HU-01 a HU-04 con criterios de aceptación y definición de terminado. |
| 1.1 | 01-10-2026 | Santiago Chávez López | **Adendo v2:** HU-05 a HU-10 (pagos mixtos y vueltas, descuentos, clientes con Habeas Data, cambio de vendedor, ganancias y bandeja de notificaciones con lista de compras). Notas de estado de implementación en HU-01 a HU-04 y criterio adicional en la definición de terminado. |
| 1.2 | 08-10-2026 | Santiago Chávez López | **Adendo v2 (mejora B1):** nota de estado de implementación en HU-10 (bandeja en el Dashboard y pestaña "Stock bajo" del administrador, productos en el mínimo y compuestos en la lista de compras). |
| 1.3 | 08-10-2026 | Santiago Chávez López | **Adendo v2 (Fase A1):** notas de estado de implementación en HU-05 (pagos mixtos, montos en pesos enteros y efectivo en múltiplos de $50, ticket) y HU-06 (pestaña "Descuentos", descuento general opcional que aplica el vendedor, límite visible para el vendedor); ajuste del criterio del descuento sugerido. |
| 1.4 | 08-10-2026 | Santiago Chávez López | **Adendo v2 (Fase A3):** nota de estado de implementación en HU-09 (tabla de costos, dashboard de ganancias, completar el costo de ventas pasadas, pestaña "Ganancias" del administrador). |
| 1.5 | 10-10-2026 | Santiago Chávez López | Revisión de estado: HU-09 deja de figurar como opcional (Fase A3 aprobada). |
| 1.6 | 12-10-2026 | Santiago Chávez López | **Adendo v2 (Fase A2):** notas de estado de implementación en HU-06 (descuento propio del cliente), HU-07 (clientes, ficha, filtros, solicitudes de titulares, política y aviso, promociones aparte y autorregistro por enlace) y HU-08 (vendedor por venta). |
| 1.7 | 13-10-2026 | Santiago Chávez López | **Adendo v2 (Fase A2):** HU-07: los datos del negocio para la política se editan en la aplicación ("Datos del negocio"), no en el servidor. |
| 1.8 | 13-10-2026 | Santiago Chávez López | **Adendo v2 (Fase A2):** HU-08: el historial del vendedor incluye lo que registró a nombre de otra persona (migración 0007); HU-07: la supresión borra la descripción de las solicitudes del cliente. |
| 1.9 | 14-10-2026 | Santiago Chávez López | **Fase 9:** HU-11 (vender sin conexión) con sus criterios de aceptación y su estado de implementación. |
| 1.11 | 19-10-2026 | Santiago Chávez López | **Adendo v3 (Fase G1):** HU-12 implementada salvo la ganancia neta (G3). |
| 1.12 | 20-10-2026 | Santiago Chávez López | **Adendo v3 (Fases G2 y G3):** HU-13 implementada y HU-12 completa con la ganancia neta. |
| 1.13 | 21-10-2026 | Santiago Chávez López | **Adendo v3:** HU-12 y HU-13 desplegadas en producción; falta la aceptación. |
| 1.10 | 19-10-2026 | Santiago Chávez López | **Adendo v3:** HU-12 (gastos del negocio) y HU-13 (dinero en caja y corte de caja) con sus criterios de aceptación; diseñadas, sin código. |
