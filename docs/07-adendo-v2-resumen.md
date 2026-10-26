# Adendo v2 — resumen de una página

Ampliación del alcance aprobada en octubre de 2026. No reemplaza nada de lo anterior. Detalle en `01` (sección 4.3 y anexos), `02` (HU-05 a HU-10), `03` (sección 7), `04` (secciones 5.1.1, 5.2.1, 5.4 y 5.5) y `05` (sección 3.3).

## Fases

| Fase | Contenido | RF | Fechas (estimadas) |
|---|---|---|---|
| **B1** – mejora independiente | Bandeja de notificaciones de stock bajo en el Dashboard y lista de compras exportable por WhatsApp. **Implementada el 08-10-2026** | 043 a 045 | 02 a 09 oct 2026 |
| **A1** – pagos y descuentos | Pagos mixtos, Nequi/Daviplata, vueltas, descuento general y manual con topes. **Implementada el 08-10-2026** (migración 0002) | 022 a 024, 026 a 028, 041, 042 | 05 a 16 oct 2026 |
| **A2** – clientes y vendedor | Clientes con Habeas Data, descuento por cliente, autorregistro por enlace y cambio de vendedor. **Implementada el 12-10-2026** (migración 0005) | 025, 029 a 036, 046 a 049 | 19 a 30 oct 2026 |
| **A3** – ganancias (**aprobada**) | Costo por producto, margen bruto y dashboard con gráficos. **Implementada el 08-10-2026** (migración 0004) | 037 a 040 | 02 a 13 nov 2026 |

## Decisiones

- **Pagos:** una venta tiene uno o más pagos (método y monto) cuya suma es igual al total. La plataforma de transferencia se llama `plataforma` (`nequi` o `daviplata`) para no chocar con la tabla `proveedores`. `ventas.metodo_pago` se elimina y migra a `pagos_venta` (migración 0002).
- **Vueltas:** solo en efectivo; se guarda el monto recibido y las vueltas, y el ticket los imprime.
- **Montos de los pagos (A1, 08-10-2026):** pesos enteros; el pago en efectivo y lo recibido en múltiplos de $50; tarjeta y transferencia, cualquier monto entero. En efectivo, si no se escribe lo recibido, se toma como pago exacto.
- **Descuento en el POS (A1, 08-10-2026):** el descuento general no está predefinido para todo el mundo: cada venta arranca sin descuento y el vendedor lo aplica con un botón a quien corresponda; un general en pesos mayor que el subtotal se limita al subtotal; si el general se apaga durante una venta que lo usa, el backend responde 409 y el POS recarga la configuración. El administrador lo configura en la pestaña "Descuentos".
- **Dashboard:** el total por método de pago se calcula por monto recibido.
- **Descuentos:** porcentaje o monto fijo, calculados sobre el subtotal; después se redondea a $50. Hay uno propio por cliente y uno general que el vendedor aplica a quien corresponda (excluyentes; el del cliente tiene prioridad). El vendedor puede cambiarlo o quitarlo en la venta, pero dentro de **dos topes configurables por el administrador** (porcentaje máximo y monto máximo; deben cumplirse ambos). Los topes no aplican al administrador ni a los descuentos del cliente y general.
- **Vendedor por venta:** un desplegable con vendedores y administradores activos; `ventas.usuario_id` es quien realizó la venta. **(A2, 12-10-2026)** `GET /ventas/vendedores`; por defecto la sesión, y el POS vuelve a ella después de cada venta para que nadie herede la venta de otro; el ticket imprime "Atendió: nombre" (campo opcional `vendedor` del agente). El historial de un vendedor muestra las ventas que quedaron a su nombre y las que él registró a nombre de otra persona (**13-10-2026**, migración 0007: `ventas.registrada_por_id`; se ve como "Registrada por").
- **Clientes:** nombre, documento, teléfono y correo; ficha con historial y total comprado; filtro por rangos de total comprado y de fechas. **(A2, 12-10-2026)** Pestaña "Clientes" para vendedor y administrador; alta rápida también desde la venta; el descuento propio del cliente se sugiere de una vez al elegirlo y reemplaza al general. Con un rango de fechas, solo cuentan las compras de ese rango.
- **Habeas Data (Ley 1581 de 2012):** autorización con evidencia (fecha, medio, versión de la política), registro de solicitudes con plazos legales y supresión por anonimización que conserva las ventas. **(A2, 12-10-2026)** Pestaña "Datos personales" del administrador; los plazos cuentan días hábiles sin festivos; la versión de la política es `POLITICA_DATOS_VERSION` ("borrador" hasta que haya texto definitivo).
- **Autorregistro:** enlace público con código aleatorio (regenerable por el administrador) donde el cliente acepta la política y escribe sus datos sin iniciar sesión. Sin guardar IP, con límite de envíos y respuestas neutras ante duplicados. **(A2, 12-10-2026)** Dirección `/registro/<código>`; el administrador lo copia, desactiva o regenera desde "Datos personales"; solo se puede publicar con los "Datos del negocio" completos (se editan en la aplicación); el cliente queda activo de inmediato y sin descuento.
- **Promociones (A2, 12-10-2026):** autorización APARTE de la de datos, con casilla propia desmarcada por defecto, en el POS y en el autorregistro; el listado de clientes filtra a quienes la aceptaron. Es la base para ofrecerles promociones por WhatsApp o llamada.
- **Ganancias en la interfaz (A3, 08-10-2026):** el administrador las ve en una pestaña "Ganancias" del POS con una tabla de costos editable; el propietario, en su Dashboard ("Ventas | Ganancias"), con los costos solo de lectura. El administrador puede completar con el costo actual solo las líneas de ventas pasadas sin costo.
- **Ganancias:** costo a mano (sugerido para anchetas); el costo se copia a cada línea de venta; el descuento se reparte entre las líneas en proporción a su subtotal. Solo administrador y propietario.
- **WhatsApp:** enlace que abre WhatsApp con el mensaje ya escrito; el usuario lo envía. No se usa la API de WhatsApp Business.
- **Lista de compras y bandeja (B1, 08-10-2026):** la lista incluye los productos justo en el mínimo (faltante 0) y los paquetes y anchetas como cualquier producto; una notificación de un producto ya repuesto sigue sin leer hasta que alguien la marque; el administrador ve la bandeja y la lista en una pestaña "Stock bajo" del POS (no tiene Dashboard).

## Nombres nuevos en la base de datos

Tablas: `pagos_venta`, `descuento_general`, `tope_descuento`, `clientes`, `enlace_autoregistro`, `solicitudes_titular`. Vistas: `vw_clientes_resumen` y `vw_margen_detalle`. Migraciones: 0002 (A1), 0004 (A3), 0005, 0006 y 0007 (A2; la 0005 en el diseño era la 0003). Tabla nueva de A2: `configuracion_negocio` (datos del responsable para la política). Detalle en `03`, sección 7.

## Supuestos por confirmar (Visión, Anexo B)

1. El descuento propio de un cliente se activa en A2, porque depende de que existan los clientes. **Implementado** (12-10-2026).
2. El vendedor crea y edita clientes; solo el administrador asigna descuentos, atiende solicitudes de Habeas Data y configura el descuento general y los topes. **Implementado** (12-10-2026).
3. "Por rangos" significa rangos de total comprado y de fechas de compra. **Implementado así** (12-10-2026): con fechas, el total cuenta solo las compras de ese rango; **Confirmado** (13-10-2026).
4. Valores de los topes: **decidido** (13-10-2026): no se fijan en el sistema; el administrador los define y los cambia cuando quiera en "Descuentos".
5. Si se aprueba A3, conviene crear las columnas de costo desde la migración 0002. **Decidido: A3 aprobada; las columnas se crean en la 0002** (08-10-2026).
6. El cliente autorregistrado queda activo de inmediato y sin descuento; pendiente de confirmar si un empleado debe aprobarlo. **Implementado sin aprobación** (12-10-2026).
7. La cantidad sugerida en la lista de compras es lo que falta para llegar al stock mínimo. **Confirmado e implementado en B1** (08-10-2026).

## Dependencias

- El enlace de autorregistro necesita una dirección estable: dominio propio con Named Tunnel (Fase 7).
- Política de tratamiento de datos, aviso de privacidad y formatos de autorización: **aprobados por el propietario el 12-10-2026 sin revisión de un abogado** (están en `08-politica-tratamiento-datos-borrador.md` y en el backend). Antes de usar el módulo con clientes reales: completar "Datos personales › Datos del negocio" en la aplicación e imprimir el cartel y los formatos.
- La migración 0002 transforma datos: respaldo previo y ensayo en staging.
