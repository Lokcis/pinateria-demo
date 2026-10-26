# Documentación del proyecto — Piñatería Demo

Documentación aprobada del Sistema de Ventas e Inventarios (POS + inventario + compras + dashboard PWA), con el estado real del código, el **Adendo v2** (ampliación de alcance) y el **Adendo v3** (gastos y corte de caja; las fases G1, G2 y G3 ya están construidas). Es confidencial: uso interno.

## Índice

| Documento | Versión | Qué responde |
|---|---|---|
| [01 – Visión y Alcance](01-vision-y-alcance.md) | 1.16 | ¿Qué se construye y para quién? Módulos, requerimientos funcionales (RF-001 a RF-075), requerimientos no funcionales, riesgos y los anexos de Habeas Data, supuestos y glosario |
| [02 – Historias de Usuario](02-historias-de-usuario.md) | 1.13 | ¿Cómo se comprueba que cada función está bien? HU-01 a HU-13 con criterios de aceptación |
| [03 – Diseño de Base de Datos](03-diseno-base-de-datos.md) | 1.12 | Tablas, columnas, relaciones, índices, DDL y la sección 7 del Adendo v2 (**fuente de los nombres de tablas y campos**) |
| [04 – Arquitectura Técnica](04-arquitectura-tecnica.md) | 1.11 | Componentes, flujos (venta, alertas, clientes, venta sin conexión), infraestructura, seguridad, respaldo y decisiones |
| [05 – Plan de Trabajo](05-plan-de-trabajo.md) | 1.10 | Fases 0 a 9, fases del adendo, cronograma, hitos, pruebas y riesgos |
| [06 – Estado de implementación](06-estado-de-implementacion.md) | — | Qué hay hoy en el código: fases, API y roles, servicios, tareas programadas, reglas y pruebas |
| [07 – Resumen del Adendo v2](07-adendo-v2-resumen.md) | — | Una página con las decisiones, fases A1 a A3, mejora B1 y supuestos por confirmar (B1, A1, A2 y A3 implementadas) |
| [08 – Tratamiento de datos personales](08-politica-tratamiento-datos-borrador.md) | 1.3 | Política de tratamiento, aviso de privacidad, autorización escrita y verbal (con la casilla aparte de promociones), procedimiento de solicitudes, cláusula de encargo y lista de verificación (Ley 1581). **Aprobado por el propietario el 12-10-2026, sin revisión de abogado** |
| [09 – Guía de capacitación](09-guia-de-capacitacion.md) | 1.7 | Fase 7: guía rápida del vendedor (para imprimir), guía del propietario y del administrador, guión de las sesiones y lista de verificación de la puesta en marcha |
| [10 – Pruebas de aceptación](10-pruebas-de-aceptacion.md) | 1.7 | Pasos para validar con el vendedor, el administrador y el propietario lo entregado en B1, A1, A2 y A3 (HU-05 a HU-10) y en la Fase 9 (HU-11, vender sin conexión), más las pruebas de campo |
| [11 – Modo sin conexión](11-modo-sin-conexion.md) | 1.0 | Fase 9: qué hace el POS cuando se cae internet, cómo está construido (cola local, envío sin duplicados, conflictos), límites, operación y despliegue |
| [12 – Gastos y corte de caja](12-gastos-y-corte-de-caja.md) | 1.5 | Adendo v3 (**G1, G2 y G3 desplegadas en producción el 21-10-2026; pendientes de aceptación**): ventana de Gastos con categorías editables y compras unificadas, ganancia neta, dinero en caja y corte de caja; permisos por rol, modelo de datos, API prevista, fases G1 a G3, supuestos y Fase 2 |
| Manuales de usuario (PDF) | — | No se incluyen en este repositorio público. Se generan con `herramientas/manuales_pdf.py` (ver `herramientas/README.md`). |
| Guía de pruebas de aceptación (PDF) | — | No se incluye: se genera a partir del documento 10 con `herramientas/md2pdf.py`. |
| [Tablero de tareas](tablero/tareas.csv) | — | 144 tarjetas (Kanban) con el estado de cada una; se puede importar a Trello |

Por fuera de esta carpeta, en la raíz del repositorio: [`DEPLOY.md`](../DEPLOY.md) (despliegue en el servidor), [`CONTRIBUTING.md`](../CONTRIBUTING.md) (flujo de Git y CI) y [`CLAUDE.md`](../CLAUDE.md) (contexto y convenciones para trabajar con asistentes de IA).

## Por dónde empezar

1. **Visión general:** `01` (secciones 2 y 4) y `04` (secciones 1 a 3).
2. **Quiero programar algo:** la historia en `02`, las tablas en `03` y el estado actual en `06` (para el modo sin conexión, `11`).
3. **Quiero saber qué viene:** `07`, la sección 3 de `05` y, para gastos y corte de caja, `12`.

## Convenciones

- **RF** (Requerimiento Funcional): frase numerada de lo que el sistema debe hacer. **HU** (Historia de Usuario): necesidad con criterios de aceptación.
- **Adendo v2:** ampliación del alcance que se suma a lo aprobado sin reemplazarlo; lo nuevo se marca con ese nombre.
- **Fases A1, A2, A3 y mejora B1:** las del Adendo v2. Se nombran así para no confundirlas con las Fases 0 a 9 del Plan de Trabajo (la Fase 9 es el modo sin conexión).
- **Adendo v3 y fases G1, G2 y G3:** gastos y corte de caja (documento 12). G1 gastos, G2 caja y corte, G3 ganancia neta. La 0009 (G1) y la 0010 (G2) están implementadas; la G3 no tiene migración.
- Los nombres de tablas y campos son los de la sección 7 de `03`. Si algo cambia en el código, se actualiza ahí primero.
- Zona horaria del negocio: `America/Bogota`. Formas de pago: `efectivo`, `tarjeta` y `transferencia` (Nequi y Daviplata se registran como transferencia, indicando la plataforma). Desde la Fase A1 una venta puede tener varios pagos (`pagos_venta`).

## Dónde están las demás copias

- **Archivos de Word (.docx):** en Google Drive, `Proyectos Programación › Piñatería Demo › Documentación › Fase 0`, y en el equipo del propietario en `Documentos\Proyectos\documentación pinateria-demo`. Los `.docx` se generan a partir de estos archivos Markdown con [`herramientas/`](herramientas/README.md).
- **Mantenimiento:** cuando cambie una decisión, se edita el Markdown de esta carpeta (queda el historial en Git) y se vuelven a generar los `.docx`. La tabla de "Control de Versiones" al final de cada documento registra el cambio.
