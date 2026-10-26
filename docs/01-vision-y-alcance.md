  
**PIÑATERÍA DEMO**

Sistema de Ventas e Inventarios

**Documento de Visión y Alcance**

Versión 1.13 (incluye Adendo v2, Fase 9 y Adendo v3)

2026

*Confidencial – Uso interno*

# Tabla de Contenido

# 1. Información General del Proyecto

| Nombre del proyecto | Sistema de Ventas e Inventarios – Piñatería Demo |
| :---- | :---- |
| **Versión del documento** | 1.4 (incluye Adendo v2) |
| **Fecha de elaboración** | 2026 |
| **Autor** | Santiago Chávez López |
| **Estado** | Versión 1.0 implementada (Fases 0 a 6); Adendo v2: B1, A1, A2 y A3 implementadas |
| **Clasificación** | Confidencial – Uso interno |

# 2. Visión del Producto

## 2.1 Descripción del negocio

Piñatería Demo es un comercio minorista especializado en artículos para fiestas y celebraciones. Su catálogo incluye dulces, anchetas, peluches, decoraciones, globos, piñatas y artículos de cotillón, con más de 150 referencias activas de alta rotación, con crecimiento continuo del catálogo.

El negocio opera con 1 a 4 empleados según la demanda y actualmente gestiona sus ventas e inventarios de forma manual mediante cuadernos de registro, lo que genera dificultades de visibilidad y control para el propietario, quien supervisa el negocio de forma remota.

## 2.2 Declaración de visión

*"Desarrollar un sistema web integral que permita al propietario de Piñatería Demo controlar en tiempo real las ventas, el inventario y las compras a proveedores desde cualquier lugar, eliminando la dependencia de registros manuales y habilitando la toma de decisiones basada en datos."*

## 2.3 Problema que resuelve

El propietario no puede supervisar el negocio en tiempo real al estar en una ciudad diferente. Los problemas concretos son:

* Desconocimiento del stock disponible, generando quiebres de inventario o sobrecompras.

* Imposibilidad de verificar las ventas del día sin llamar directamente a los empleados.

* Ausencia de alertas de inventario bajo que anticipe la necesidad de reabastecimiento.

* Dependencia de un software de terceros sin soporte claro.

* Dificultad para planificar compras a proveedores a distancia con información confiable.

## 2.4 Propuesta de valor

* Acceso remoto en tiempo real al estado del negocio desde cualquier dispositivo.

* POS ágil y simple para los empleados en tienda desde el computador.

* Control de inventario con alertas automáticas de stock mínimo.

* Registro de compras a proveedores para trazabilidad completa del inventario.

* Sistema propio, sin dependencia de terceros desconocidos.

# 3. Usuarios del Sistema

## 3.1 Perfil: Propietario / Administrador

| Ubicación de uso | Remoto y eventual presencia en tienda |
| :---- | :---- |
| **Dispositivo principal** | Smartphone y computador personal |
| **Frecuencia de uso** | Varias veces al día para supervisión |
| **Nivel técnico** | Medio – estudiante de Ingeniería de Sistemas |
| **Necesidades clave** | Supervisión de ventas, alertas de stock, gestión de compras y reportes |

Nota v1.4: el sistema implementa tres roles: **administrador** (control total, incluidos proveedores, compras, usuarios y configuración), **vendedor** (POS e inventario) y **propietario** (supervisión de solo lectura desde el Dashboard). El propietario y el administrador pueden ser la misma persona con cuentas distintas.

## 3.2 Perfil: Vendedor / Empleado

| Ubicación de uso | Punto de venta en tienda física |
| :---- | :---- |
| **Dispositivo principal** | PC de escritorio con conexión a internet |
| **Frecuencia de uso** | Continua durante la jornada laboral |
| **Nivel técnico** | Básico – no se asume experiencia con software de gestión |
| **Necesidades clave** | Registrar ventas rápidamente, consultar precios y stock |

# 4. Alcance del Proyecto

## 4.1 Módulos incluidos en el alcance (v1.0)

### Módulo 1 – Punto de Venta (POS)

* Registro de ventas por unidad, por paquete o por ancheta (kits predefinidos).

* Soporte para múltiples formas de pago: efectivo, tarjeta y transferencia (los pagos por Nequi o Daviplata se registran como transferencia).

* Confirmación de venta en pantalla, con opción de impresión de factura.

* Impresión de la factura de venta en la impresora térmica Epson TM-T20II.

* Registro de productos en la venta de forma híbrida: mediante lector de código de barras USB (para aquellos artículos que ya lo traigan de fábrica) o mediante un buscador rápido en pantalla (por nombre o categoría) para los productos que no tengan código (como mermas, peluches o anchetas).

* Descuento automático del inventario al registrar una venta.

* Historial de ventas del día consultable por el empleado.

### Módulo 2 – Inventario

* Catálogo de más de 150 productos organizados por categorías, sin límite fijo de referencias.

* Consulta de stock actual en tiempo real.

* Configuración de stock mínimo por producto con alerta automática al propietario.

* Ajustes manuales de inventario (merma, correcciones, donaciones).

### Módulo 3 – Compras a Proveedores

* Registro de órdenes de compra y entrada de mercancía.

* Actualización automática del stock al registrar una entrada de mercancía.

* Directorio de proveedores con información de contacto, visible únicamente para el rol Administrador (el vendedor no tiene acceso a esta información).

* Historial de compras por proveedor y por producto.

### Módulo 4 – Panel de Supervisión (Dashboard)

* Resumen del día: ventas totales, número de transacciones, forma de pago más usada.

* Estado del inventario: productos en alerta de stock bajo.

* Acceso desde dispositivo móvil vía Progressive Web App (PWA).

* Notificaciones de alerta de inventario bajo.

### Módulo 5 – Administración

* Gestión de usuarios y roles (administrador y vendedor).

* Creación, edición y desactivación de productos.

* Gestión de categorías de productos.

* Configuración de precios y unidades de medida.

## 4.2 Fuera del alcance (v1.0)

Los siguientes elementos quedan explícitamente excluidos de la primera versión del sistema:

* Integración con pasarelas de pago electrónico (solo registro manual de la forma de pago).

* Facturación electrónica DIAN.

* Módulo de nómina o gestión de empleados.

* Tienda en línea o e-commerce.

* Integración con contabilidad externa.

* App nativa para Android o iOS (se usará PWA).

Aclaración v1.4 (Adendo v2): al registrar una transferencia se indica la plataforma (Nequi o Daviplata) para efectos de control. Sigue siendo un registro manual: no existe ninguna integración con esas plataformas ni con pasarelas de pago.

Aclaración v1.11 (Fase 9): el modo sin conexión del punto de venta (guardar las ventas en el equipo cuando se cae internet y enviarlas al volver la conexión) se incorporó al alcance; ver la sección 4.5 y el documento 11. Sigue fuera del alcance iniciar sesión sin conexión, asociar clientes sin conexión y consultar el historial, el inventario o el Dashboard sin conexión.

Aclaración v1.13 (Adendo v3): se incorporan al alcance el registro de gastos y el corte de caja (sección 4.6 y documento 12). Sigue fuera del alcance la contabilidad completa y la integración con contabilidad externa; la nómina se registra solo como un gasto de la categoría "Nómina", sin gestión de empleados. Los gastos recurrentes y los comprobantes adjuntos quedan para una Fase 2.

## 4.3 Alcance del Adendo v2 (versión 1.4)

El **Adendo v2** es una ampliación del alcance aprobada después de la retroalimentación del cliente. No reemplaza ni borra nada de lo aprobado en las versiones anteriores: agrega capacidades nuevas, que en todos los documentos del proyecto se marcan como "Adendo v2". Se entrega en tres fases propias (A1 a A3) y una mejora independiente (B1), todas separadas de las Fases 0 a 8 del Plan de Trabajo:

| Fase del adendo | Contenido | Requerimientos | Fechas estimadas |
| :---- | :---- | :---- | :---- |
| **A1 – Pagos y descuentos** | Pagos mixtos, plataformas de transferencia (Nequi y Daviplata), vueltas en efectivo, descuento general, descuento manual en la venta con topes configurables y cálculo de descuento sobre el subtotal. **Implementada (08-10-2026).** | RF-022 a RF-024, RF-026 a RF-028, RF-041, RF-042 | 05 a 16 oct 2026 |
| **A2 – Clientes y vendedor** | Registro de clientes con cumplimiento de Habeas Data, descuento por cliente, asociación del cliente a la venta, ficha con historial y total comprado, filtro por rangos, enlace público de autorregistro y cambio de vendedor por venta. **Implementada (12-10-2026).** | RF-025, RF-029 a RF-036, RF-046 a RF-049 | 19 a 30 oct 2026 |
| **A3 – Ganancias (aprobada)** | Costo por producto, margen bruto con descuentos aplicados y dashboard de ganancias con gráficos. **Implementada (08-10-2026).** | RF-037 a RF-040 | 02 a 13 nov 2026 |
| **Mejora B1 – Bandeja y lista de compras** | Bandeja de notificaciones de stock bajo en el Dashboard y lista de compras exportable por WhatsApp. **Implementada (08-10-2026).** | RF-043 a RF-045 | 02 a 09 oct 2026 |

Las fechas son estimadas y están sujetas a la aprobación del propietario. La Fase A3 era opcional y el propietario la aprobó el 08-10-2026. El descuento propio de un cliente (RF-025) se activa en la Fase A2, porque depende de que exista el registro de clientes; en la Fase A1 funcionan el descuento general y el descuento manual.

### Punto de Venta (ampliación)

* **Pagos mixtos:** una venta puede tener varios pagos, cada uno con su método (efectivo, tarjeta o transferencia) y su monto. La suma de los pagos debe ser igual al total de la venta.

* **Transferencia:** al elegir transferencia se indica la plataforma, Nequi o Daviplata. Siguen siendo registros manuales: no hay integración con las plataformas de pago (ver 4.2).

* **Vueltas:** en un pago en efectivo se registra cuánto entregó el cliente y el sistema muestra cuánto se le debe devolver; el ticket impreso incluye ambos valores.

* **Cambio de vendedor:** un desplegable durante la venta permite cambiar el usuario que vende (vendedores y administradores activos). El vendedor se asigna por venta, no por producto, y la venta queda registrada a nombre del vendedor elegido.

### Módulo de Descuentos

* Un descuento propio por cliente registrado y un descuento general para los clientes sin registro. Ambos pueden ser un porcentaje o un monto fijo.

* El descuento se calcula sobre el subtotal de la venta y, después, el total se redondea al múltiplo de $50.

* El descuento general no se aplica solo a todas las ventas: el vendedor lo aplica a quien corresponda. El descuento propio del cliente se sugiere al asociarlo (Fase A2).

* El vendedor puede cambiar o quitar el descuento durante la venta, porque depende de la situación de esa venta. La venta guarda de dónde salió el descuento (cliente, general o manual).

* El descuento manual del vendedor tiene **topes configurables**: un porcentaje máximo y un monto máximo, que el administrador define y que el vendedor no puede superar (rige el más restrictivo). Los topes no aplican al administrador ni a los descuentos que define el propio administrador (el del cliente y el general).

* Solo el administrador define el descuento propio de cada cliente, el descuento general y los topes.

### Módulo de Clientes

* Alta, edición y desactivación de clientes (nombre, documento, teléfono y correo), con búsqueda por nombre, documento o teléfono.

* Asociación del cliente a la venta.

* Ficha del cliente con su historial de ventas y el total comprado; listado filtrable por rangos (de total comprado y de fechas de compra).

* **Autorregistro por enlace:** el negocio comparte un enlace público (por WhatsApp o en un cartel) con el que el cliente entra sin iniciar sesión, lee el aviso de privacidad, acepta el tratamiento de sus datos y escribe él mismo su nombre, documento, teléfono y correo. Queda registrado con la evidencia de su aceptación. El administrador puede consultar, desactivar o regenerar el enlace.

* Cumplimiento de la Ley 1581 de 2012 (Habeas Data): autorización previa del titular, evidencia de la autorización, atención de consultas y reclamos y supresión de datos (ver el Anexo A).

### Módulo de Ganancias (aprobado)

* Campo de costo por producto, ingresado a mano. Para las anchetas el sistema muestra un costo sugerido a partir de los costos de sus componentes, que también se puede ajustar a mano.

* Margen bruto = precio de venta menos costo de compra, con los descuentos aplicados.

* Dashboard de ganancias con gráficos. Los costos y las ganancias solo los ven el administrador y el propietario; el vendedor nunca.

### Bandeja de notificaciones y lista de compras (Mejora B1)

* **Bandeja de notificaciones** en el Dashboard con las alertas de stock bajo: contador de no leídas, lista con el producto, su stock y su mínimo, y opción de marcar una o todas como leídas. La ven el propietario y el administrador.

* **Lista de compras:** se arma con los productos en alerta de stock bajo y la cantidad que falta para llegar al stock mínimo.

* **Exportar por WhatsApp:** un botón abre WhatsApp con la lista ya escrita en un mensaje, para que el usuario elija el chat y lo envíe; también se puede copiar como texto. El mensaje queda escrito y el usuario lo envía; el sistema no manda nada por su cuenta.

La mejora B1 completa el RF-008 (alerta de stock bajo al propietario), que hasta ahora solo se veía al abrir el Dashboard, y es independiente de las fases A1 a A3.

## 4.4 Estado de implementación (versión 1.4)

Al 01 de octubre de 2026 están implementados y en la rama principal los cinco módulos de la versión 1.0 y las pruebas de integración de la Fase 6, que el propietario declaró completada el 01-10-2026.

| Módulo | Estado | Detalles de lo implementado |
| :---- | :---- | :---- |
| 1 – Punto de Venta | Implementado (Fase 1, 27-09-2026) | Ventas por unidad, paquete y ancheta; efectivo, tarjeta y transferencia; búsqueda híbrida por lector o texto; total redondeado al múltiplo de $50 más cercano, con la línea "Ajuste por redondeo" en el ticket solo cuando ocurre; historial de ventas del día con la hora de Bogotá (America/Bogota); impresión a través del agente local de la Epson TM-T20II. |
| 2 – Inventario | Implementado (Fase 2, 27-09-2026) | Catálogo con filtro y paginación, stock mínimo, ajustes manuales con motivo e historial, edición, desactivación y reactivación de productos, y productos compuestos (paquetes y anchetas) con receta definida desde la interfaz (Fase 6). |
| 3 – Compras a Proveedores | Implementado (Fase 3, 29-09-2026) | Órdenes de compra con recepción y cancelación (la recepción suma el stock), directorio de proveedores solo para el administrador (el vendedor recibe 403), teléfono de proveedor con solo dígitos (7 a 15) y bloqueo para eliminar proveedores con compras. |
| 4 – Dashboard | Implementado (Fase 4, 29-09-2026) | Resumen por rango de fechas (ventas, transacciones, forma de pago, productos más vendidos, serie diaria y compras recibidas), alertas de stock bajo (revisión cada 15 minutos) y PWA instalable cuyo service worker solo guarda la interfaz y nunca las respuestas de la API. |
| 5 – Administración | Implementado (Fase 5, 29-09-2026) | Usuarios con tres roles (administrador, vendedor y propietario); contraseña de 8 a 72 caracteres con cambio por el propio usuario; un administrador no puede desactivarse ni quitarse el rol; categorías (no se eliminan si tienen productos). |
| Infraestructura | Operativa | Docker Compose con base de datos, Redis, migraciones, backend, Celery (worker y beat), Nginx, Cloudflare Tunnel y Uptime Kuma; respaldo diario de PostgreSQL a las 2:30 a. m. (hora de Bogotá) con conservación de 14 días; integración continua en GitHub Actions (Backend, agente de impresión y Frontend). |

En esta versión la documentación y el código están alineados. Lo pendiente de la versión 1.0 es lo previsto en las Fases 7 y 8 (capacitación, carga del catálogo, producción y acompañamiento).

**Actualización v1.8 (12-10-2026).** Del Adendo v2 están implementadas B1 (bandeja de notificaciones y lista de compras), A1 (pagos mixtos y descuentos, migración 0002) y A3 (ganancias, migración 0004), junto con la corrección de seguridad de la búsqueda de productos. Desde el 12-10-2026 corren en el servidor (rama `dev`, como staging) con las migraciones 0002 y 0004 aplicadas y los datos migrados verificados contra el ensayo. Faltan las pruebas en staging, la aceptación con el vendedor y el propietario y el paso a `main`. La Fase A2 (clientes y vendedor) no tiene código. El detalle técnico está en el documento 06.

## 4.5 Alcance de la Fase 9: modo sin conexión (versión 1.11)

El servidor está fuera de la tienda, así que una caída de internet en la tienda impedía vender. La Fase 9 lo resuelve sin cambiar cómo vende el vendedor:

* El POS guarda en el equipo una copia del catálogo, del descuento general y de los vendedores, que se actualiza cada vez que hay conexión.

* Sin conexión, la venta se arma, se cobra y se imprime con normalidad (con un número local `SC-0001`) y se guarda en una cola en el equipo.

* Al volver la conexión, las ventas guardadas se envían solas, de la más antigua a la más reciente, sin duplicarse y conservando la hora, los precios y el descuento que vio el cliente.

* Si el servidor rechaza una venta (por ejemplo, por falta de stock), queda visible con el motivo para que el administrador la resuelva y se reintente; nunca se pierde en silencio.

* Los datos de clientes no se guardan en el equipo: sin conexión no se asocia cliente a la venta.

El diseño, las decisiones, los límites y la operación están en el documento 11.

## 4.6 Alcance del Adendo v3: gastos y corte de caja (versión 1.13)

El negocio pidió una ventana de **Gastos** (19-10-2026). Lo aprobado:

* **Gastos** con categorías editables por el administrador, descripción, monto, forma de pago (efectivo, tarjeta o transferencia con plataforma), fecha y a quién se pagó (opcional).

* **Permisos:** el administrador ve e ingresa; el propietario solo ve; el vendedor solo ingresa y puede editar o anular lo que él mismo registró.

* **Anulación en lugar de borrado**, con motivo; lo anulado no suma en los totales.

* **Compras a proveedores unificadas:** las compras recibidas cuentan como gasto (categoría "Compra de mercancía") y se ven en la misma ventana; al recibir una compra se registra su forma de pago.

* **Ganancia neta** (margen bruto menos gastos operativos) y resultado de caja en Ganancias y en el Dashboard.

* **Caja y corte de caja:** apertura con la base, dinero en caja en vivo, ingresos y retiros manuales, y corte con el efectivo contado y la diferencia.

* **Exportar** a CSV (se abre en Excel).

* **Solo con conexión:** los gastos y la caja no se usan sin conexión; la cola de ventas de la Fase 9 no cambia.

* **Fase 2 (no incluida):** gastos recurrentes y comprobantes adjuntos.

Se entrega en tres fases (G1 gastos, G2 caja y corte, G3 ganancia neta). El diseño, los permisos, las fórmulas y los supuestos están en el documento 12.

# 5. Requerimientos Funcionales

La siguiente tabla presenta los requerimientos funcionales principales priorizados para la versión 1.0:

| ID | Requerimiento | Módulo | Prioridad |
| :---- | :---- | :---- | :---- |
| RF-001 | El sistema debe permitir registrar una venta seleccionando productos del catálogo | POS | **Alta** |
| RF-002 | El sistema debe soportar ventas de productos individuales, en paquete y en ancheta | POS | **Alta** |
| RF-003 | El sistema debe registrar la forma de pago de cada venta | POS | **Alta** |
| RF-004 | El sistema debe descontar automáticamente del inventario los productos vendidos | POS | **Alta** |
| RF-005 | El sistema debe mostrar confirmación de venta en pantalla al vendedor | POS | **Alta** |
| RF-006 | El sistema debe mantener un catálogo de productos con nombre, precio, categoría y stock | Inventario | **Alta** |
| RF-007 | El sistema debe permitir configurar un stock mínimo por producto | Inventario | **Alta** |
| RF-008 | El sistema debe enviar alerta al propietario cuando un producto alcance el stock mínimo | Inventario | **Alta** |
| RF-009 | El sistema debe permitir ajustes manuales de inventario con motivo registrado | Inventario | **Media** |
| RF-010 | El sistema debe permitir registrar entradas de mercancía por compra a proveedor | Compras | **Alta** |
| RF-011 | El sistema debe actualizar automáticamente el stock al registrar una entrada de mercancía | Compras | **Alta** |
| RF-012 | El sistema debe mantener un directorio de proveedores | Compras | **Media** |
| RF-013 | El sistema debe mostrar al propietario un resumen de ventas del día en tiempo real | Dashboard | **Alta** |
| RF-014 | El sistema debe ser accesible desde dispositivo móvil sin instalar aplicación nativa | Dashboard | **Alta** |
| RF-015 | El sistema debe permitir gestionar usuarios con roles diferenciados | Admin | **Alta** |
| RF-016 | El sistema debe permitir crear, editar y desactivar productos del catálogo | Admin | **Alta** |
| RF-017 | El sistema debe permitir gestionar categorías de productos | Admin | **Media** |
| RF-018 | El sistema debe registrar el historial completo de ventas con fecha, hora y vendedor | POS | **Media** |
| RF-019 | El sistema debe permitir agregar productos a la venta de forma híbrida, ya sea por lectura de código de barras o por búsqueda rápida manual por texto o categoría. | POS | **Media** |
| RF-020 | El sistema debe permitir imprimir la factura de venta en la impresora térmica Epson TM-T20II | POS | **Alta** |
| RF-021 | El sistema debe restringir el acceso al directorio de proveedores exclusivamente al rol Administrador | Compras | **Alta** |

### Estado de los requerimientos RF-001 a RF-021 (v1.4)

Todos los requerimientos de la versión 1.0 están implementados: RF-001 a RF-005 y RF-018 a RF-020 en la Fase 1 (POS); RF-006 a RF-009 en la Fase 2 (Inventario); RF-010 a RF-012 y RF-021 en la Fase 3 (Compras); RF-013 y RF-014 en la Fase 4 (Dashboard); RF-015 a RF-017 en la Fase 5 (Administración). El Adendo v2 modifica el alcance de RF-003 (la forma de pago pasa a ser uno o varios pagos, RF-022) y de RF-013 (la forma de pago más usada se calcula por monto recibido, RF-041). La mejora B1 completa además RF-008: las alertas de stock bajo se muestran en una bandeja del Dashboard y alimentan una lista de compras (RF-043 a RF-045).

Estado de los requerimientos del Adendo v2 (v1.8): implementados RF-022 a RF-024, RF-026 a RF-028, RF-041 y RF-042 (Fase A1), RF-037 a RF-040 (Fase A3) y RF-043 a RF-045 (mejora B1); pendientes RF-025, RF-029 a RF-036 y RF-046 a RF-049 (Fase A2).

### Requerimientos del Adendo v2

| ID | Requerimiento | Módulo | Prioridad | Fase |
| :---- | :---- | :---- | :---- | :---- |
| RF-022 | El sistema debe permitir que una venta tenga uno o varios pagos, cada uno con su método y su monto, y exigir que la suma sea igual al total de la venta | POS | **Alta** | A1 |
| RF-023 | El sistema debe solicitar la plataforma (Nequi o Daviplata) cuando el método de un pago sea transferencia | POS | **Alta** | A1 |
| RF-024 | El sistema debe registrar, en los pagos en efectivo, el monto recibido y calcular, mostrar e imprimir las vueltas que se deben devolver al cliente | POS | **Alta** | A1 |
| RF-025 | El sistema debe permitir asignar a cada cliente registrado un descuento propio, en porcentaje o en monto fijo | Descuentos | **Alta** | A2 |
| RF-026 | El sistema debe permitir configurar un descuento general, en porcentaje o en monto fijo, para los clientes sin registro | Descuentos | **Alta** | A1 |
| RF-027 | El sistema debe permitir al vendedor cambiar o quitar el descuento sugerido durante la venta, dentro de los topes configurados (RF-042), y registrar su origen (cliente, general o manual) | Descuentos | **Alta** | A1 |
| RF-028 | El sistema debe calcular el descuento sobre el subtotal de la venta y redondear el total después del descuento | Descuentos | **Media** | A1 |
| RF-029 | El sistema debe permitir crear, editar y desactivar clientes con nombre, documento, teléfono y correo | Clientes | **Alta** | A2 |
| RF-030 | El sistema debe permitir buscar clientes por nombre, documento o teléfono | Clientes | **Alta** | A2 |
| RF-031 | El sistema debe permitir asociar un cliente a una venta | Clientes | **Alta** | A2 |
| RF-032 | El sistema debe mostrar en la ficha del cliente su historial de ventas y el total comprado | Clientes | **Media** | A2 |
| RF-033 | El sistema debe permitir filtrar los clientes por rangos de total comprado y de fechas de compra | Clientes | **Media** | A2 |
| RF-034 | El sistema debe exigir la autorización de tratamiento de datos personales antes de registrar un cliente y guardar su evidencia (fecha, medio, versión de la política y empleado) | Clientes | **Alta** | A2 |
| RF-035 | El sistema debe permitir atender los derechos del titular (consulta, actualización, supresión y revocatoria) y llevar el registro de las solicitudes con su plazo | Clientes | **Alta** | A2 |
| RF-036 | El sistema debe permitir elegir durante la venta, mediante un desplegable, el vendedor que la realiza, y registrar la venta a su nombre | POS | **Alta** | A2 |
| RF-037 | El sistema debe permitir registrar a mano el costo de cada producto y mostrar un costo sugerido para las anchetas a partir de sus componentes | Ganancias | **Media** | A3 |
| RF-038 | El sistema debe calcular el margen bruto (precio de venta menos costo de compra, con descuentos aplicados) por venta, producto y periodo | Ganancias | **Media** | A3 |
| RF-039 | El sistema debe mostrar el margen bruto en un dashboard con gráficos | Ganancias | **Media** | A3 |
| RF-040 | El sistema debe restringir los costos y las ganancias a los roles administrador y propietario | Ganancias | **Alta** | A3 |
| RF-041 | El resumen del día debe calcular el total por método de pago a partir de los pagos recibidos (por monto) | Dashboard | **Alta** | A1 |
| RF-042 | El sistema debe permitir al administrador configurar topes máximos (porcentaje y monto) para el descuento manual del vendedor y rechazar los descuentos que superen cualquiera de ellos | Descuentos | **Alta** | A1 |
| RF-043 | El sistema debe mostrar al propietario y al administrador una bandeja de notificaciones de stock bajo en el Dashboard, con contador de no leídas y opción de marcarlas como leídas | Dashboard | **Media** | B1 |
| RF-044 | El sistema debe generar una lista de compras con los productos en stock bajo y la cantidad que falta para llegar al stock mínimo | Dashboard | **Media** | B1 |
| RF-045 | El sistema debe permitir exportar la lista de compras a WhatsApp (abriendo WhatsApp con el mensaje escrito) y copiarla como texto | Dashboard | **Media** | B1 |
| RF-046 | El sistema debe ofrecer un enlace público con el que el cliente pueda registrar él mismo sus datos (nombre, documento, teléfono y correo) sin iniciar sesión | Clientes | **Alta** | A2 |
| RF-047 | El formulario público debe mostrar el aviso de privacidad y la política de tratamiento de datos y exigir su aceptación antes de enviar, guardando la evidencia (fecha, medio electrónico y versión de la política) | Clientes | **Alta** | A2 |
| RF-048 | El sistema debe permitir al administrador consultar, copiar, desactivar y regenerar el enlace de autorregistro | Clientes | **Media** | A2 |
| RF-049 | El enlace público debe estar protegido contra abusos (límite de envíos y campo trampa) y no debe mostrar ni modificar los datos de clientes existentes | Clientes | **Alta** | A2 |
| RF-050 | El punto de venta debe permitir registrar ventas cuando no hay conexión con el servidor, guardándolas en el equipo y mostrando al vendedor que quedaron guardadas sin conexión | POS | **Alta** | Fase 9 |
| RF-051 | El punto de venta debe buscar productos y calcular el total sin conexión con una copia del catálogo, del descuento general y de los vendedores guardada en el equipo, que se actualiza cada vez que hay conexión | POS | **Alta** | Fase 9 |
| RF-052 | Las ventas guardadas sin conexión deben enviarse solas, de la más antigua a la más reciente, al volver la conexión, sin duplicarse aunque se reenvíen (identificador único por venta) | POS | **Alta** | Fase 9 |
| RF-053 | La venta enviada después debe conservar la hora en que se hizo, los precios y el descuento general que vio el cliente; el servidor rechaza horas futuras y ventas de más de 7 días | POS | **Alta** | Fase 9 |
| RF-054 | Si el servidor rechaza una venta guardada (por ejemplo, por falta de stock) debe quedar visible con el motivo, sin perderse ni frenar a las demás, y poder reintentarse, reimprimirse o descartarse tras confirmar | POS | **Alta** | Fase 9 |
| RF-055 | El ticket de una venta hecha sin conexión debe imprimirse con un número local (por ejemplo, SC-0001) en lugar del número de venta | POS | **Media** | Fase 9 |
| RF-056 | Sin conexión no se debe asociar un cliente a la venta ni guardar datos personales de clientes en el equipo | POS | **Alta** | Fase 9 |
| RF-057 | El punto de venta debe avisar al perder y al recuperar la conexión, indicar cuántas ventas esperan y pedir confirmación antes de cerrar sesión sin conexión o con ventas guardadas | POS | **Media** | Fase 9 |
| RF-058 | Todo nombre y texto descriptivo que se registre (productos, categorías, proveedores y su contacto, clientes, usuarios, descripciones, notas y motivos) debe guardarse con la primera letra en mayúscula y el resto en minúscula, sin espacios sobrantes; no se modifican los datos exactos (usuario de acceso, correo, documento, teléfono, dirección y código de barras) | General | **Media** | — |

### Requerimientos del Adendo v3

| ID | Requerimiento | Módulo | Prioridad | Fase |
| :---- | :---- | :---- | :---- | :---- |
| RF-059 | El sistema debe permitir registrar un gasto con fecha, categoría, descripción, monto, forma de pago (con la plataforma si es transferencia) y, opcionalmente, a quién se pagó | Gastos | **Alta** | G1 |
| RF-060 | El sistema debe permitir al administrador crear, renombrar, activar y desactivar las categorías de gasto; la categoría "Compra de mercancía" es de sistema y no se modifica | Gastos | **Alta** | G1 |
| RF-061 | El administrador debe poder ver, registrar, editar y anular todos los gastos; el propietario solo consultarlos; y el vendedor solo registrar gastos y ver, editar y anular los que él mismo registró | Gastos | **Alta** | G1 |
| RF-062 | Un gasto no se borra: se anula con un motivo obligatorio, queda visible con quién y cuándo lo anuló y deja de sumar en los totales | Gastos | **Alta** | G1 |
| RF-063 | Las compras a proveedores recibidas deben aparecer en la ventana de Gastos (categoría "Compra de mercancía", solo lectura) y sumar al total de gastos, visibles solo para el administrador y el propietario | Gastos | **Alta** | G1 |
| RF-064 | Al recibir una compra se debe registrar su forma de pago (efectivo, tarjeta o transferencia con plataforma) y la fecha de recepción | Compras | **Media** | G1 |
| RF-065 | El sistema debe listar los gastos con filtros por rango de fechas (los del Dashboard), categoría, forma de pago y estado, y mostrar los totales por categoría y por forma de pago | Gastos | **Alta** | G1 |
| RF-066 | El sistema debe permitir exportar los gastos (con las compras) del rango y los filtros elegidos a un archivo CSV que abra Excel; lo pueden hacer el administrador y el propietario | Gastos | **Media** | G1 |
| RF-067 | El sistema debe mostrar la ganancia neta (margen bruto menos gastos operativos, sin las compras de mercancía) y el resultado de caja (ventas cobradas menos todos los gastos) en Ganancias y en el Dashboard | Ganancias | **Alta** | G3 |
| RF-068 | Los gastos y la caja deben usarse solo con conexión: no se guardan en la cola del modo sin conexión y esa cola no cambia | Gastos | **Media** | G1 |
| RF-069 | El sistema debe permitir abrir la caja con el efectivo inicial; solo puede haber una caja abierta a la vez | Caja | **Alta** | G2 |
| RF-070 | El sistema debe calcular y mostrar en vivo el dinero en caja: base más ventas en efectivo más ingresos, menos gastos en efectivo, compras en efectivo y retiros | Caja | **Alta** | G2 |
| RF-071 | El sistema debe permitir registrar ingresos y retiros manuales de caja, con motivo | Caja | **Media** | G2 |
| RF-072 | El sistema debe permitir el corte de caja: registrar el efectivo contado, calcular la diferencia contra el esperado, guardar observaciones y una foto inmutable de las cifras, y mostrar como información lo vendido por tarjeta y transferencia | Caja | **Alta** | G2 |
| RF-073 | El sistema debe guardar el historial de cortes y permitir consultarlo y exportarlo | Caja | **Media** | G2 |
| RF-074 | Un corte cerrado no se puede modificar; el vendedor no puede editar ni anular gastos que cubre un corte cerrado; y el POS no debe dejar cerrar la caja si el equipo tiene ventas guardadas sin enviar | Caja | **Alta** | G2 |
| RF-075 | Los montos van en pesos enteros y, en efectivo, deben ser múltiplos de $50 (gastos, base, ingresos, retiros y efectivo contado) | Gastos y caja | **Media** | G1 y G2 |

Estado del Adendo v3 (v1.16, 21-10-2026): RF-059 a RF-075 están diseñados (documento 12) y **las tres fases están implementadas**: la G1 (RF-059 a RF-066, RF-068 y la parte de gastos de RF-075), la G2 (RF-069 a RF-074 y la parte de caja de RF-075) y la G3 (RF-067). Están desplegado en producción el 21-10-2026; falta la aceptación con el negocio.

# 6. Requerimientos No Funcionales

## 6.1 Rendimiento

* El tiempo de respuesta de cualquier operación del POS no debe superar 2 segundos en condiciones normales de red.

* El sistema debe soportar al menos 4 usuarios concurrentes sin degradación perceptible.

* Adendo v2: registrar una venta con pagos mixtos y descuento mantiene el límite de 2 segundos, y la búsqueda de clientes por nombre, documento o teléfono debe responder en menos de 1 segundo.

## 6.2 Disponibilidad

* El sistema debe estar disponible durante todo el horario comercial de la tienda.

* En caso de pérdida momentánea de conexión a internet en tienda, el sistema debe notificar claramente al usuario.

* Desde la Fase 9, una pérdida de conexión no impide vender: el punto de venta guarda las ventas en el equipo y las envía al volver la conexión (ver sección 4.5 y el documento 11).

## 6.3 Seguridad

* El acceso al sistema requiere autenticación con usuario y contraseña.

* Los roles deben restringir el acceso: el vendedor no debe acceder al panel administrativo, al dashboard del propietario, ni a la información de proveedores.

* Toda comunicación debe realizarse sobre HTTPS.

* Las contraseñas deben almacenarse con hash seguro (bcrypt).

* Adendo v2: los costos de los productos y las ganancias solo son visibles para los roles administrador y propietario, nunca para el vendedor; el descuento general, el descuento propio de cada cliente y los topes del descuento manual solo los configura el administrador.

* Adendo v2: el tratamiento de los datos personales de los clientes debe cumplir la Ley 1581 de 2012 (ver el Anexo A).

* Adendo v2: el formulario público de autorregistro no requiere sesión; por eso debe exigir un enlace con código aleatorio, limitar la cantidad de envíos por dirección, no revelar si un documento o teléfono ya está registrado y no almacenar la dirección IP del cliente.

## 6.4 Usabilidad

* La interfaz del POS debe ser operable por un empleado sin capacitación técnica previa en menos de 30 minutos de entrenamiento.

* El dashboard del propietario debe ser legible desde un smartphone en menos de 10 segundos de carga.

## 6.5 Mantenibilidad

* El sistema debe estar contenedorizado con Docker para facilitar actualizaciones y backups.

* La base de datos debe tener respaldo automático diario.

# 7. Arquitectura Técnica de Alto Nivel

| Frontend | React.js + Tailwind CSS – Progressive Web App (PWA) |
| :---- | :---- |
| **Backend** | Python + FastAPI – API REST |
| **Base de datos** | PostgreSQL – base de datos relacional principal |
| **Caché / Colas** | Redis – caché de sesiones y colas de tareas asíncronas |
| **Tareas asíncronas** | Celery – envío de alertas y generación de reportes |
| **Servidor web** | Nginx – reverse proxy, SSL y entrega de archivos estáticos |
| **Infraestructura** | Ubuntu Server – servidor propio del propietario |
| **Contenedores** | Docker + Docker Compose – orquestación de servicios |
| **Acceso remoto** | Cloudflare Tunnel – solución a CG-NAT, dominio y SSL gratuitos. Actualización v1.8: desde el 12-10-2026 se usa un Named Tunnel con dominio propio (`demo.example.com`; el sistema se abre en `pos.demo.example.com`), con dirección estable |
| **Integración y despliegue continuos** | GitHub Actions ejecuta en cada pull request las pruebas de Backend, del agente de impresión y de Frontend (integración continua, implementada). Actualización v1.8: el despliegue continuo (CD) al servidor está implementado con un workflow de GitHub Actions y un runner en el servidor (despliega al fusionar en la rama que sigue el servidor, con el CI en verde, respaldo previo y aprobación manual de las migraciones); falta su primera ejecución real |
| **Monitoreo** | Uptime Kuma – monitoreo de disponibilidad del servicio |
| **Impresora** | Epson TM-T20II – impresora térmica para impresión de la factura de venta (conexión USB) |
| **Lector de código de barras** | Lector USB tipo pistola (plug and play, emulación de teclado) para búsqueda rápida de productos en el POS |

La solución de Cloudflare Tunnel elimina la necesidad de IP pública fija y resuelve la restricción de CG-NAT del proveedor de internet residencial actual, permitiendo acceso seguro al sistema desde cualquier red sin requerir cambios en la configuración del ISP.

# 8. Riesgos Identificados

| Riesgo | Mitigación | Impacto |
| :---- | :---- | :---- |
| Corte de internet en tienda impide uso del POS | **Mitigado en la Fase 9:** modo sin conexión (cola local de ventas en el equipo, envío automático al volver la red). Complementos: router 4G de respaldo y no cerrar sesión durante el corte (sin conexión no se puede iniciar sesión) | **Alto** |
| Servidor doméstico sin UPS sufre corte de luz | Adquirir UPS básico para el servidor; configurar inicio automático post-corte | **Alto** |
| Migración de datos del software anterior | Inicio con catálogo nuevo; importar historial solo si hay exportación disponible | **Medio** |
| Resistencia al cambio por parte de los empleados | Capacitación presencial en tienda antes del lanzamiento; interfaz POS lo más simple posible | **Medio** |
| Falla del disco del servidor | Backups diarios automáticos a almacenamiento externo o nube | **Alto** |
| Datos personales de clientes tratados sin cumplir la Ley 1581 de 2012 (Adendo v2) | Autorización obligatoria y con evidencia, registro de solicitudes con plazos, anonimización a solicitud y documentos de política y aviso de privacidad (Anexo A) | **Alto** |
| Abuso del formulario público de autorregistro (spam, robots o intento de descubrir clientes existentes) (Adendo v2) | Enlace con código aleatorio que el administrador puede regenerar, límite de envíos, campo trampa y respuestas neutras que no revelan datos existentes | **Medio** |
| Error en la migración de pagos que transforma las ventas existentes (Adendo v2) | Respaldo manual previo, ensayo completo en staging y verificación de que la suma de pagos de cada venta iguala su total | **Alto** |
| Pagos mixtos mal cuadrados o descuentos manuales sin control (Adendo v2) | El sistema impide confirmar una venta cuyos pagos no igualen el total y registra el origen del descuento y el vendedor; el descuento manual del vendedor está limitado por topes de porcentaje y de monto que configura el administrador | **Medio** |
| Margen de ganancias incorrecto por productos sin costo (Adendo v2) | Los productos sin costo se excluyen del margen y se reportan como "sin costo" | **Medio** |
| Incompatibilidad o falla de la impresora térmica o el lector de código de barras | Verificar previamente la compatibilidad de drivers con la Epson TM-T20II y el lector de código de barras; mantener repuesto disponible | **Medio** |

# 9. Próximos Pasos

Una vez aprobado este documento, el proyecto continúa con las siguientes fases de documentación y planificación:

| # | Entregable | Descripción |
| :---- | :---- | :---- |
| **1** | **Documento de Arquitectura Técnica** | Diagrama detallado de componentes, flujo de datos y modelo de base de datos |
| **2** | **Historias de Usuario** | Casos de uso detallados por módulo con criterios de aceptación |
| **3** | **Diseño de Base de Datos** | Modelo entidad-relación y esquema PostgreSQL |
| **4** | **Configuración del servidor** | Setup de Ubuntu Server, Docker, Nginx y Cloudflare Tunnel |
| **5** | **Desarrollo – Módulo POS** | Primera funcionalidad operativa: registro de ventas |

Actualización v1.4: los entregables 1 a 5 de la tabla anterior están completados y las Fases 0 a 6 del Plan de Trabajo también (la Fase 6 se declaró completada el 01-10-2026). Los pasos que siguen son:

| # | Entregable | Descripción |
| :---- | :---- | :---- |
| **6** | **Adendo v2 – Fase A1** | Pagos mixtos, vueltas y descuentos (05 a 16 oct 2026, estimado). Implementada el 08-10-2026 |
| **7** | **Adendo v2 – Fase A2** | Clientes con Habeas Data, descuento por cliente y cambio de vendedor (19 a 30 oct 2026, estimado) |
| **8** | **Fases 7 y 8 del Plan de Trabajo** | Capacitación, carga del catálogo, puesta en producción con dominio propio y despliegue continuo, y acompañamiento |
| **9** | **Adendo v2 – Mejora B1** | Bandeja de notificaciones y lista de compras por WhatsApp (02 a 09 oct 2026, estimado). Implementada el 08-10-2026 |
| **10** | **Adendo v2 – Fase A3 (aprobada)** | Ganancias y dashboard (02 a 13 nov 2026, estimado). Implementada el 08-10-2026 |

# Control de Versiones

| Versión | Fecha | Autor | Cambios |
| :---- | :---- | :---- | :---- |
| 1.0 | 2026 | Santiago Chávez López | Versión inicial del documento |
| 1.1 | 2026 | Santiago Chávez López | Ajustes según retroalimentación del cliente: catálogo de más de 150 productos, impresión de factura en Epson TM-T20II, lectura de código de barras en el POS y restricción del acceso a proveedores al rol Administrador. |
| 1.2 | 22-8-2026 | Santiago Chávez López | Ajustes de la lectura de código para una lectura híbrida. |
| 1.3 | 25-9-2026 | Santiago Chávez López | Formas de pago del POS: efectivo, tarjeta y transferencia; los pagos por Nequi o Daviplata se registran como transferencia. |
| 1.4 | 01-10-2026 | Santiago Chávez López | **Adendo v2:** pagos mixtos con plataforma de transferencia y vueltas, cambio de vendedor por venta, registro de clientes con Habeas Data, descuentos por cliente y general, y módulo de ganancias (opcional); RF-022 a RF-049; fases A1 a A3 y mejora B1 (bandeja de notificaciones y lista de compras por WhatsApp, RF-043 a RF-045) y enlace público de autorregistro de clientes (RF-046 a RF-049). Actualización con el estado implementado (sección 4.4), la aclaración de los tres roles, el dominio propio y el despliegue continuo. Anexos A (Habeas Data), B (supuestos) y C (glosario). |
| 1.5 | 08-10-2026 | Santiago Chávez López | **Adendo v2 (Fase A1):** Anexo B: la Fase A3 se aprueba y las columnas de costo se crean en la migración 0002 (supuesto 5); nuevo supuesto 16 sobre los montos de los pagos (pesos enteros; efectivo en múltiplos de $50) y 17: el descuento general es opcional (el vendedor lo aplica a quien corresponda; no se predefine en todas las ventas), con el ajuste en el módulo de Descuentos. |
| 1.6 | 08-10-2026 | Santiago Chávez López | **Adendo v2 (Fase A3):** Anexo B, supuestos 18 (pestaña "Ganancias" del administrador) y 19 (completar el costo de las ventas pasadas sin costo). |
| 1.7 | 10-10-2026 | Santiago Chávez López | Revisión de estado: la Fase A3 deja de figurar como opcional (aprobada); B1, A1 y A3 marcadas como implementadas (secciones 4.3, 4.4 y entregables) y estado de los requerimientos del Adendo v2. |
| 1.8 | 12-10-2026 | Santiago Chávez López | Revisión de estado: el dominio propio con Named Tunnel ya está en uso; el despliegue continuo está implementado (primera ejecución pendiente); B1, A1 y A3 corren en el servidor (rama `dev`) con las migraciones 0002 y 0004 aplicadas. |
| 1.9 | 12-10-2026 | Santiago Chávez López | Revisión de estado: la Fase A2 queda implementada (incluido el autorregistro por enlace, RF-046 a RF-049); el propietario aprueba la política de datos sin revisión de abogado y confirma que no aplica el RNBD; nueva autorización aparte para promociones. |
| 1.10 | 13-10-2026 | Santiago Chávez López | Anexo B: se confirma la interpretación de "por rangos" (punto 3) y que los topes de descuento los fija y modifica el administrador (punto 6). |
| 1.11 | 14-10-2026 | Santiago Chávez López | **Fase 9 (modo sin conexión):** sección 4.5, RF-050 a RF-057, riesgo de corte de internet mitigado y aclaración del alcance; paso a producción hecho (servidor en `main`, base nueva). |
| 1.12 | 14-10-2026 | Santiago Chávez López | RF-058: los nombres y textos descriptivos se guardan con la primera letra en mayúscula y el resto en minúscula. |
| 1.14 | 19-10-2026 | Santiago Chávez López | **Adendo v3 (Fase G1):** implementada; RF-059 a RF-066, RF-068 y parte de RF-075 con código. |
| 1.15 | 20-10-2026 | Santiago Chávez López | **Adendo v3 (Fases G2 y G3):** implementadas; RF-067 y RF-069 a RF-074 con código y la parte de caja de RF-075. |
| 1.16 | 21-10-2026 | Santiago Chávez López | **Adendo v3:** desplegado en producción (G1, G2 y G3). |
| 1.13 | 19-10-2026 | Santiago Chávez López | **Adendo v3 (gastos y corte de caja):** sección 4.6, RF-059 a RF-075, aclaración del alcance (4.2), supuestos 20 a 26 del Anexo B y términos nuevos del glosario. Diseño completo en el documento 12; sin código. |

# Anexo A. Protección de datos personales (Habeas Data) — Adendo v2

El registro de clientes (Módulo de Clientes) obliga a tratar datos personales. Este anexo resume qué exige la ley colombiana y cómo lo cumple el sistema. Es una guía técnica de cumplimiento y **no es asesoría jurídica**: se recomienda que un abogado revise los textos finales antes de entrar en producción.

## A.1 Marco legal

* Constitución Política, artículo 15 (derecho al Habeas Data).

* Ley Estatutaria 1581 de 2012: régimen general de protección de datos personales.

* Decreto 1377 de 2013, que reglamenta parcialmente la ley y hoy está compilado en el Decreto 1074 de 2015: autorización, aviso de privacidad y políticas de tratamiento.

* Autoridad de control: Superintendencia de Industria y Comercio (SIC).

## A.2 Roles

* **Responsable del tratamiento:** Piñatería Demo (el propietario), que decide para qué se usan los datos.

* **Encargado del tratamiento:** quien opera el sistema por cuenta del negocio (el desarrollador, que aloja el servidor). Conviene dejar por escrito un contrato o cláusula de encargo con las obligaciones de seguridad y confidencialidad.

## A.3 Datos tratados y finalidades

* **Datos:** nombre, documento de identidad (opcional), teléfono (opcional) y correo (opcional). No se recolectan datos sensibles. No se deben registrar menores de edad.

* **Finalidades propuestas:** identificar al cliente y asociarle sus compras, aplicarle el descuento que corresponda y consultar su historial de compras. Cualquier uso adicional (por ejemplo, enviar publicidad) requiere definirlo con el propietario y pedir una autorización separada.

## A.4 Cómo lo implementa el sistema

| Obligación legal | Medida en el sistema | RF |
| :---- | :---- | :---- |
| Autorización previa, expresa e informada del titular, que debe poder probarse | No se puede guardar un cliente sin marcar la autorización. Se registran la fecha, el medio (escrito, electrónico o verbal), la versión de la política aceptada y el empleado que la recogió. El POS muestra el aviso de privacidad antes de guardar. | RF-034 |
| Autorización cuando el cliente se registra solo por el enlace público | El formulario muestra el aviso de privacidad y la política vigente y no se puede enviar sin marcar la aceptación. Se guardan la fecha, el medio (electrónico) y la versión de la política. No se almacena la dirección IP ni otros datos que el cliente no escribió, por minimización de datos. | RF-046, RF-047 |
| Informar la finalidad, los derechos y el canal de atención (aviso de privacidad) | Texto del aviso en la pantalla de alta, en un cartel en la tienda y en el formato de autorización. | RF-034 |
| Derechos de conocer, actualizar y rectificar | La ficha del cliente permite consultar y editar sus datos. | RF-029, RF-035 |
| Derecho a revocar la autorización y a la supresión | La revocatoria bloquea el uso del cliente en ventas nuevas. La supresión anonimiza el registro (nombre genérico y sin documento, teléfono ni correo) y conserva las ventas como registro contable. | RF-035 |
| Atender consultas y reclamos en los plazos de ley | Cada solicitud se registra con su fecha límite y su estado. Plazos: consultas, 10 días hábiles prorrogables 5; reclamos (actualización, rectificación, supresión o revocatoria), 15 días hábiles prorrogables 8. | RF-035 |
| Seguridad y confidencialidad | Acceso por roles (el vendedor solo registra y consulta; el administrador gestiona solicitudes y descuentos), tráfico por HTTPS, contraseñas con bcrypt y respaldos en una carpeta restringida del servidor. | RNF 6.3 |

## A.5 Documentos que debe tener el negocio

* **Política de Tratamiento de Información** (manual interno de políticas y procedimientos).

* **Aviso de privacidad** corto, para la pantalla del POS y para la tienda.

* **Formato de autorización** (versión escrita y guion para la autorización verbal).

* **Procedimiento de consultas y reclamos**, con el canal de atención (correo o teléfono de la tienda) y la persona responsable.

* Verificar con el contador o el abogado si el negocio debe inscribir sus bases de datos en el Registro Nacional de Bases de Datos (RNBD) de la SIC. Hoy la obligación aplica a los responsables con activos totales superiores a 100.000 UVT y a las entidades públicas; es probable que la tienda no esté obligada, pero el resto de las obligaciones sí le aplican.

## A.6 Puntos para revisión jurídica

* El tráfico del sistema pasa por Cloudflare (tercero con infraestructura fuera de Colombia): evaluar si se requiere declarar una transmisión o transferencia internacional y qué contrato aplica.

* Retención de los respaldos de PostgreSQL (14 días) que contienen datos de clientes anonimizados o suprimidos después de la copia.

# Anexo B. Supuestos y decisiones por confirmar (Adendo v2)

Para no frenar el diseño, estos puntos se resolvieron con el siguiente criterio. Cada uno puede cambiarse si el propietario lo decide.

| # | Tema | Criterio adoptado |
| :---- | :---- | :---- |
| 1 | Descuento por cliente y fases | Se activa en la Fase A2, porque requiere el registro de clientes. En la Fase A1 funcionan el descuento general y el manual. |
| 2 | Quién gestiona clientes | El vendedor y el administrador crean, editan y buscan clientes. Solo el administrador asigna el descuento propio, desactiva clientes, atiende solicitudes de Habeas Data y configura el descuento general. |
| 3 | "Filtro por rangos" de clientes | **Confirmado (13-10-2026):** rangos de total comprado y de fechas de compra. Con fechas, el total y el número de ventas cuentan solo las compras de ese rango. |
| 4 | Descuento y margen por producto | El descuento de la venta se reparte entre las líneas en proporción a su subtotal (ver el Diseño de Base de Datos, sección 7.8). |
| 5 | Costo de las ventas | Decidido (08-10-2026): la Fase A3 se aprueba y las columnas de costo se crean desde la Fase A1 (migración 0002), así cada venta guarda el costo vigente y las ventas del periodo intermedio también tienen margen. |
| 6 | Tope del descuento manual | Decidido: dos topes configurables por el administrador (porcentaje máximo y monto máximo) que el vendedor debe cumplir ambos. Quedan sin límite hasta que se configuren. **Decidido (13-10-2026):** los valores no se fijan en el sistema; el administrador los define y los cambia cuando quiera en la pestaña "Descuentos". |
| 7 | Ventas anteriores al adendo | La migración conserva sus pagos con el método original; las transferencias antiguas quedan sin plataforma (no se registraba). |
| 8 | Dominio y despliegue continuo | Resuelto (12-10-2026): el dominio propio ya está comprado y funciona con un Named Tunnel de Cloudflare; el despliegue continuo (CD) está implementado y pendiente de su primera ejecución. Detalle técnico en el documento 04 y en `DEPLOY.md`. |
| 9 | Lista de compras (B1) | La cantidad sugerida de cada producto es lo que falta para llegar al stock mínimo (stock mínimo menos stock actual); el propietario decide cuánto comprar realmente. |
| 10 | WhatsApp (B1) | Se usa un enlace que abre WhatsApp con el mensaje ya escrito (mensaje prellenado); el usuario elige el chat y lo envía. Si la lista es muy larga se ofrece copiarla como texto. |
| 11 | Quién ve la bandeja (B1) | Propietario y administrador; el vendedor no la ve (sí conserva la insignia "Stock bajo" en Inventario). |
| 12 | Autorregistro: estado inicial (A2) | El cliente que se registra por el enlace queda activo de inmediato, marcado como "autorregistro" para distinguirlo de los que registra un empleado, y sin descuento propio (lo asigna el administrador). Pendiente de confirmar si se prefiere que un empleado lo apruebe antes de activarlo. |
| 13 | Autorregistro: enlace (A2) | Un solo enlace permanente con un código aleatorio, que el administrador puede copiar, desactivar o regenerar (al regenerarlo, el anterior deja de funcionar). No incluye código QR. |
| 14 | Autorregistro y duplicados (A2) | Si el documento o el teléfono ya existen, el formulario responde con un mensaje neutro y no revela ni modifica los datos del cliente existente: cualquier corrección la hace un empleado. |
| 15 | Autorregistro y dominio (A2) | El enlace necesita una dirección estable: requería un dominio propio con Named Tunnel, que ya existe (12-10-2026): la dirección es estable. |
| 16 | Montos de los pagos (A1) | Decidido (08-10-2026): los pagos van en pesos enteros; el pago en efectivo y el monto recibido deben ser múltiplos de $50 (las vueltas se dan en monedas); tarjeta y transferencia aceptan cualquier monto entero. |
| 17 | Descuento general opcional (A1) | Decidido (08-10-2026): el descuento general no está predefinido para todo el mundo. Cada venta arranca sin descuento y el vendedor lo aplica con un botón solo a quien corresponda; los topes no lo limitan. |
| 18 | Dónde ve las ganancias el administrador (A3) | Decidido (08-10-2026): el administrador no tiene Dashboard; ve las ganancias y la tabla de costos en una pestaña "Ganancias" del punto de venta. El propietario las ve en su Dashboard (vista "Ventas | Ganancias") y los costos solo en lectura. |
| 19 | Ventas sin costo anteriores a la carga de costos (A3) | Decidido (08-10-2026): el administrador puede completar, con el costo actual del producto, solo las líneas de ventas pasadas que no tienen costo (pide confirmación; es una aproximación). Las líneas que ya tienen costo no se tocan. |
| 20 | Gastos: permisos (Adendo v3) | Decidido (19-10-2026): el administrador ve e ingresa; el propietario solo ve; el vendedor solo ingresa y edita o anula únicamente lo suyo (por eso ve su propia lista, sin totales ni compras). Supuesto adoptado: "el admin solo ve" se entendió como el propietario. |
| 21 | Compras y gastos (Adendo v3) | Decidido (19-10-2026): las compras recibidas cuentan como gasto y se unifican en la ventana de Gastos. Supuesto adoptado: la ganancia neta no las resta (ya están en el costo de lo vendido) y se muestra aparte el resultado de caja con todos los gastos; conviene confirmarlo con el contador. |
| 22 | Categorías de gasto (Adendo v3) | Decidido (19-10-2026): son editables por el administrador. Las categorías iniciales sugeridas están en el documento 12; "Compra de mercancía" es de sistema. |
| 23 | Anulación (Adendo v3) | Decidido (19-10-2026): los gastos se anulan con un motivo, no se borran. |
| 24 | Caja y corte (Adendo v3) | Decidido (19-10-2026): cada gasto lleva su forma de pago y hay un apartado de dinero en caja con corte. Supuestos adoptados: una sola caja; el administrador y el vendedor la abren y cierran; ingresos y retiros manuales con motivo; el corte guarda una foto inmutable. |
| 25 | Sin conexión y exportar (Adendo v3) | Decidido (19-10-2026): los gastos y la caja solo con conexión; se exporta a CSV (UTF-8 con BOM y punto y coma). |
| 26 | Fase 2 (Adendo v3) | Decidido (19-10-2026): los gastos recurrentes y los comprobantes adjuntos quedan para una fase posterior. La lista completa de supuestos está en la sección 11 del documento 12. |

# Anexo C. Glosario

| Término | Significado |
| :---- | :---- |
| RF | Requerimiento Funcional: una frase que describe algo que el sistema debe hacer (por ejemplo, "RF-022: permitir varios pagos en una venta"). Todos los RF están numerados en la sección 5. |
| HU | Historia de Usuario: describe una necesidad desde el punto de vista de quien usa el sistema, con sus criterios de aceptación. |
| Adendo v2 | Ampliación del alcance que se agrega a los documentos aprobados sin modificar lo anterior; lo nuevo se marca con ese nombre. |
| Fases A1, A2 y A3 | Las tres fases del Adendo v2. Se nombran así para no confundirlas con las Fases 0 a 8 del Plan de Trabajo. |
| Vueltas | Dinero que se devuelve al cliente cuando paga en efectivo más de lo que debe. |
| Margen bruto | Precio de venta menos el costo de compra del producto, con los descuentos ya aplicados. |
| Prorrateo | Repartir un monto entre varias partes en proporción a su tamaño. |
| Habeas Data | Derecho de las personas a conocer, actualizar y rectificar la información que sobre ellas guardan las empresas. |
| Receta (BOM) | Lista de productos y cantidades con las que se arma una ancheta o un paquete. |
| Adendo v3 | Ampliación del alcance con los gastos del negocio, el dinero en caja y el corte de caja (documento 12). |
| Fases G1, G2 y G3 | Las tres fases del Adendo v3: G1 gastos, G2 caja y corte, G3 ganancia neta. |
| Gasto operativo | Gasto del negocio que no es compra de mercancía (arriendo, servicios, nómina, transporte…). La compra de mercancía ya entra en el costo de lo vendido. |
| Ganancia neta | Margen bruto menos los gastos operativos del período. |
| Resultado de caja | Ventas cobradas menos todos los gastos del período, incluidas las compras recibidas; es una cifra de flujo de dinero, no una ganancia contable. |
| Corte de caja | Cierre de la caja: se cuenta el efectivo y se compara con el que el sistema calcula; la diferencia es el faltante o el sobrante. |
