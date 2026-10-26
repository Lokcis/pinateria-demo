# Tratamiento de datos personales — documentos (Ley 1581 de 2012)

**Versión:** 1.0 · 12-10-2026 · **Aprobado por el propietario el 12-10-2026, sin revisión de un abogado.** Redactado con base en el Anexo A del Documento de Visión.

> **Estado.** El propietario revisó y aprobó este texto el 12-10-2026 y decidió no pagar una revisión jurídica; también confirmó que el negocio **no** debe inscribir su base de datos en el RNBD (no alcanza el umbral de activos) y que **no** se registran prórrogas de los plazos. El sistema ya lo usa: el texto vive en `backend/app/services/politica_datos.py` y los datos del negocio los edita el administrador en la aplicación (sección 1). Si algún día hay un abogado disponible, esta es la versión a revisar.
>
> **Qué es y qué no es este documento.** Es un texto completo, escrito a partir de lo que exige la Ley 1581 de 2012 y sus decretos reglamentarios (hoy compilados en el Decreto 1074 de 2015). **No es asesoría jurídica y no lo firma un abogado.** Para un negocio pequeño que solo guarda nombre, documento, teléfono y correo para llevar el historial de compras, lo más importante es **cumplir lo que dice el texto**: pedir la autorización, guardar la prueba, atender las solicitudes a tiempo y no usar los datos para nada más. El sistema ya hace la parte técnica; lo que falta son estos textos.
>
> **Cómo conseguir una revisión sin pagar un abogado** (ver la sección 7): consultorio jurídico de una universidad, Cámara de Comercio y las guías gratuitas de la Superintendencia de Industria y Comercio (SIC).

## Contenido

1. Datos que hay que completar
2. Política de Tratamiento de Datos Personales
3. Aviso de privacidad (pantalla del POS y cartel de la tienda)
4. Formato de autorización (escrito) y guion de autorización verbal
5. Procedimiento interno de consultas y reclamos
6. Cláusula de encargo (entre el negocio y quien opera el sistema)
7. Cómo revisarlo sin pagar, y lista de verificación
8. Puntos que el sistema todavía no cubre

---

## 1. Datos que hay que completar

Los textos de abajo llevan `[…]` que el sistema reemplaza solo con estos datos, que el administrador escribe **una vez** en la aplicación: pestaña **Datos personales › Datos del negocio** (no hay que tocar el servidor):

| Dato | Valor |
|---|---|
| Nombre o razón social del responsable | campo "Nombre o razón social" |
| NIT o cédula | campo "NIT o cédula" (el que aparece en el ticket) |
| Dirección y ciudad | campo "Dirección y ciudad" |
| Teléfono de la tienda | campo "Teléfono de la tienda" |
| **Correo para solicitudes de datos** | campo "Correo para consultas y reclamos de datos". La ley exige publicar un correo de contacto del responsable; **cualquier correo que revises sirve** (tu Gmail, por ejemplo). No tiene que ser del dominio: el sistema no envía nada a esa dirección, solo la muestra en el aviso para que los clientes sepan a dónde escribir. |
| Persona que atiende las solicitudes (opcional; por defecto, el negocio) | campo "Quién atiende las solicitudes" |
| Fecha desde la que rige la política | campo "Fecha desde la que rige la política" (ej. 12-10-2026) |
| Versión del texto | campo "Versión de la política" (por defecto 1.0; súbela si el texto cambia) |

Mientras falte alguno de los seis primeros datos obligatorios, el sistema marca la política como **"borrador"** (cada autorización queda con esa versión), el POS avisa qué falta y el enlace de autorregistro no se puede publicar.

Mientras no exista el correo del dominio, la ley admite cualquier canal que el titular pueda usar y que deje constancia: sirve un correo personal del negocio o el WhatsApp/teléfono de la tienda **si se anota cada solicitud en el sistema** (pestaña "Datos personales"). Lo importante es que el canal sea real y que alguien lo revise.

---

## 2. Política de Tratamiento de Datos Personales

**Responsable del tratamiento:** `[nombre o razón social]`, identificado con `[NIT/cédula]`, con domicilio en `[dirección, ciudad]`, teléfono `[teléfono]` y correo `[correo]` (en adelante, "la Tienda").

### 2.1 Alcance y marco legal

Esta política aplica a los datos personales de los clientes que la Tienda registra en su sistema de ventas. Se expide en cumplimiento del artículo 15 de la Constitución Política, la Ley 1581 de 2012 y el Decreto 1074 de 2015 (que compila el Decreto 1377 de 2013).

### 2.2 Datos que se recolectan

- Nombre.
- Documento de identidad (opcional).
- Teléfono (opcional).
- Correo electrónico (opcional).
- El historial de compras que la Tienda registra al venderle (productos, fechas, valores y formas de pago).

La Tienda **no recolecta datos sensibles** (salud, origen étnico, orientación política o sexual, datos biométricos, entre otros) y **no registra datos de menores de edad**. Los datos marcados como opcionales no son necesarios para comprar: el cliente puede comprar sin registrarse.

### 2.3 Finalidades

Los datos se usan **únicamente** para:

1. Identificar al cliente y asociarle sus compras.
2. Aplicarle el descuento o beneficio que le corresponda como cliente registrado.
3. Consultar su historial de compras para atenderlo mejor.
4. Atender sus consultas, reclamos y solicitudes sobre sus datos.
5. Cumplir obligaciones legales, contables y tributarias de la Tienda.
6. **Solo si el cliente lo autoriza marcando la casilla aparte:** enviarle promociones y novedades de la Tienda. Puede retirar esta autorización en cualquier momento, sin que afecte sus compras ni sus descuentos.

La Tienda **no vende, alquila ni comparte** los datos con terceros para fines comerciales, y **no los usa para enviar publicidad** si el cliente no dio la autorización aparte para promociones.

### 2.4 Autorización

El tratamiento requiere la autorización previa, expresa e informada del titular. La Tienda la solicita al registrar al cliente, por escrito, de forma verbal o electrónica, y **conserva la prueba**: fecha, medio por el que se dio, versión de esta política que se le informó y empleado que la recogió. No se registra a nadie que no la dé. La autorización para recibir promociones es **otra, aparte**: tiene su propia casilla, viene desmarcada y se guarda con su fecha.

### 2.5 Derechos del titular

El titular de los datos tiene derecho a:

1. Conocer, actualizar y rectificar sus datos.
2. Pedir prueba de la autorización que dio.
3. Ser informado, si lo solicita, del uso que se ha dado a sus datos.
4. Presentar quejas ante la Superintendencia de Industria y Comercio (SIC) por infracciones a la ley, una vez agotado el trámite de consulta o reclamo ante la Tienda.
5. Revocar la autorización y pedir la supresión de sus datos, siempre que no exista un deber legal o contractual de conservarlos.
6. Acceder de forma gratuita a sus datos personales.

### 2.6 Cómo ejercer los derechos

Mediante solicitud dirigida a `[persona]`, por correo a `[correo]`, por teléfono o en la tienda (`[dirección]`). La Tienda responde:

- **Consultas:** en máximo **10 días hábiles** desde el recibo. Si no es posible, se informa el motivo y la nueva fecha, que no puede pasar de **5 días hábiles** más.
- **Reclamos** (actualizar, rectificar, suprimir o revocar): en máximo **15 días hábiles** desde el recibo. Si no es posible, se informa el motivo y la nueva fecha, que no puede pasar de **8 días hábiles** más.

El detalle del procedimiento está en la sección 5.

### 2.7 Supresión de datos

Cuando el titular pide la supresión, la Tienda reemplaza su nombre por "Cliente anonimizado" y borra su documento, teléfono, correo y descuento. **Las ventas ya hechas se conservan** como registro contable, pero sin ningún dato que identifique a la persona. La supresión puede negarse, con explicación, si la ley obliga a conservar la información.

### 2.8 Conservación

Los datos se conservan mientras el cliente siga registrado y el tiempo adicional que exijan las normas contables y tributarias. Pasado ese tiempo, o cuando el titular lo pida y proceda, se suprimen o anonimizan. Las copias de seguridad del sistema se conservan 14 días y se sobrescriben solas.

### 2.9 Seguridad

El sistema exige usuario y contraseña, separa lo que puede ver cada rol (el vendedor registra y consulta clientes; solo el administrador atiende solicitudes y asigna descuentos), cifra las contraseñas, transmite la información por conexión segura (HTTPS) y guarda copias de seguridad en una carpeta restringida. El personal que accede a los datos está obligado a mantenerlos confidenciales.

### 2.10 Encargados y terceros

La Tienda usa servicios tecnológicos para operar el sistema: un servidor propio, la persona que lo administra y el servicio de red de Cloudflare, que lleva el tráfico entre el navegador y el servidor y tiene infraestructura fuera de Colombia. Estos terceros actúan como **encargados** del tratamiento: solo procesan los datos siguiendo las instrucciones de la Tienda y bajo deber de confidencialidad. Fuera de ellos, los datos solo se entregan a autoridades que los pidan con base legal.

### 2.11 Vigencia y cambios

Esta política rige desde `[fecha]`. Si cambia de forma sustancial —por ejemplo, una nueva finalidad— la Tienda lo informará a los titulares antes de aplicarla y pedirá una nueva autorización cuando la ley lo exija. Cada versión queda identificada (1.0, 1.1…) y el sistema guarda con cada cliente la versión que aceptó.

---

## 3. Aviso de privacidad

### 3.1 Texto para el POS (se muestra antes de guardar al cliente)

> **Aviso de privacidad.** `[Nombre del negocio]` (NIT `[…]`) usará tus datos (nombre y, si los das, documento, teléfono y correo) solo para identificarte, asociar tus compras, aplicarte descuentos y consultar tu historial. No los vendemos ni los compartimos con terceros para publicidad. Los datos opcionales no son necesarios para comprar. Puedes conocer, actualizar, rectificar o suprimir tus datos, o revocar tu autorización, escribiendo a `[correo]` o preguntando en la tienda. Consulta la Política de Tratamiento de Datos completa en `[la tienda / enlace]`.

La casilla que marca el empleado dice: **"El cliente leyó o escuchó este aviso y autoriza el tratamiento de sus datos personales."** Debajo hay una segunda casilla, aparte y desmarcada: **"El cliente además autoriza que le envíen promociones y novedades de la tienda (opcional)."** En el formulario público del cliente, las mismas dos casillas dicen "He leído este aviso y autorizo…" y "Además, autorizo que me envíen promociones…".

### 3.2 Texto para el cartel de la tienda (papel, visible en el mostrador)

> **Tus datos, con respeto.**
> Si te registras como cliente guardamos tu nombre y, si quieres, tu documento, teléfono y correo, **solo** para llevar tus compras y darte descuentos. No los vendemos ni los usamos para publicidad. Puedes pedir que los veamos, los corrijamos o los borremos cuando quieras: `[correo]` · `[teléfono]` · en el mostrador.
> Política completa disponible en la tienda. Responsable: `[nombre]`, NIT `[…]`.

El cartel lleva además el **enlace de autorregistro y su código QR**, para que el cliente se registre solo desde su celular. Se genera con `docs/herramientas/qr_cartel.py` (ver `herramientas/README.md`): todo se calcula en el PC, porque el enlace lleva un código secreto y no debe pegarse en generadores de QR de internet. Si el administrador regenera el enlace en la aplicación, el anterior deja de funcionar y el cartel debe volver a imprimirse.

---

## 4. Autorización

### 4.1 Formato escrito (una hoja, por duplicado: una copia para el cliente)

> **AUTORIZACIÓN PARA EL TRATAMIENTO DE DATOS PERSONALES**
>
> Yo, ______________________________, identificado(a) con documento n.º ______________, autorizo de manera previa, expresa e informada a `[nombre del negocio]` (NIT `[…]`) para que recolecte, almacene y use mis datos personales (nombre, documento, teléfono y correo) con las siguientes finalidades: identificarme y asociar mis compras, aplicarme descuentos, consultar mi historial de compras y atender mis solicitudes.
>
> Fui informado(a) de que: (1) no estoy obligado(a) a dar los datos opcionales (documento, teléfono, correo) y puedo comprar sin registrarme; (2) tengo derecho a conocer, actualizar, rectificar y suprimir mis datos, a pedir prueba de esta autorización y a revocarla; (3) puedo ejercer estos derechos en `[correo]`, `[teléfono]` o en `[dirección]`; (4) la Política de Tratamiento de Datos está disponible en la tienda.
>
> Fecha: ____ / ____ / ________ Firma: ______________________
>
> Datos que autorizo guardar (marcar): ☐ nombre ☐ documento ☐ teléfono ☐ correo
>
> **Promociones (opcional, aparte):** ☐ Autorizo que me envíen promociones y novedades de la tienda por WhatsApp, llamada, mensaje de texto o correo. Puedo retirar esta autorización cuando quiera.
>
> Recibido por (empleado): ______________________

### 4.2 Guion para la autorización verbal

El empleado dice, **antes** de guardar al cliente:

> "Para registrarte como cliente guardamos tu nombre y, si quieres, tu documento, teléfono y correo. Los usamos solo para llevar tus compras y darte descuentos; no los vendemos ni los usamos para publicidad. Puedes pedir verlos, corregirlos o borrarlos cuando quieras, en la tienda o escribiendo a `[correo]`. ¿Autorizas que guardemos tus datos así?"

Si responde que sí, el empleado marca la casilla, elige "Verbal" y guarda. **Si dice que no o duda, no se registra** (la venta se hace igual, sin cliente).

Después, **como pregunta aparte**: "¿Quieres además que te avisemos de promociones y novedades de la tienda? Puedes decir que no y no pasa nada." Solo si dice que sí se marca la segunda casilla.

---

## 5. Procedimiento interno de consultas y reclamos

**Responsable de atender:** `[persona]`. **Dónde se anota todo:** pestaña "Datos personales" del sistema (la solicitud se registra desde la ficha del cliente y el sistema calcula la fecha límite).

1. **Recibir.** Cualquier empleado que reciba una petición sobre datos personales (de palabra, por correo, por teléfono) se la pasa **el mismo día** al responsable. Nunca se ignora ni se responde "eso no se puede".
2. **Verificar quién pide.** Solo el titular (o su apoderado con prueba) puede pedir. Se confirma con el documento o los datos del registro. No se entregan datos por teléfono a quien no pueda identificarse.
3. **Registrar** en el sistema: tipo (consulta, actualización, supresión, revocatoria), descripción y fecha. Queda la fecha límite: **10 días hábiles** para consultas y **15** para reclamos.
4. **Reclamo incompleto.** Si falta información para tramitarlo, se le pide al titular dentro de los **5 días** siguientes. Si en **2 meses** no la entrega, se entiende que desistió.
5. **Atender.**
   - *Consulta:* se le muestra o se le entrega copia de los datos que se tienen de él.
   - *Actualización o rectificación:* se corrige en la ficha del cliente.
   - *Revocatoria de la autorización:* se resuelve la solicitud en el sistema; el cliente deja de poder asociarse a ventas nuevas.
   - *Supresión:* se resuelve la solicitud en el sistema; el cliente queda anonimizado y se conservan las ventas sin sus datos.
6. **Responder** al titular por el mismo canal en que preguntó, y **anotar la respuesta** en el sistema al resolver.
7. **Si no se alcanza a responder a tiempo**, se le avisa antes del vencimiento el motivo y la nueva fecha (máximo 5 días hábiles más en consultas y 8 en reclamos). El sistema marca como "Vencida" toda solicitud pasada de fecha: revisar la pestaña **al menos una vez por semana**.
8. **Si lo que pide no se puede conceder** (por ejemplo, una obligación contable obliga a conservar algo), se rechaza explicando el motivo y se le dice que puede acudir a la SIC.

---

## 6. Cláusula de encargo (entre el negocio y quien opera el sistema)

Puede incluirse en el contrato o como una página firmada por ambos.

> **Encargo del tratamiento de datos personales.** `[Nombre del negocio]` (el "Responsable") encarga a `[nombre de quien opera el sistema]` (el "Encargado") el alojamiento, mantenimiento y soporte del sistema de ventas, lo que implica tratar los datos personales de los clientes del Responsable. El Encargado se obliga a: (1) tratar los datos solo siguiendo las instrucciones del Responsable y para operar el sistema; (2) no usarlos para fines propios ni entregarlos a terceros, salvo los proveedores de infraestructura indispensables, que deberán garantizar la misma confidencialidad; (3) mantener medidas de seguridad razonables (accesos por usuario y contraseña, conexión cifrada, copias de seguridad protegidas); (4) guardar confidencialidad sobre los datos, incluso al terminar el encargo; (5) avisar al Responsable sin demora si conoce un acceso no autorizado a los datos; (6) ayudar al Responsable a atender las consultas y reclamos de los titulares dentro de los plazos legales; y (7) al terminar el encargo, devolver o borrar los datos según indique el Responsable.
>
> Fecha: ____ / ____ / ________ Firma del Responsable: ______________ Firma del Encargado: ______________

---

## 7. Cómo revisarlo sin pagar, y lista de verificación

### 7.1 Opciones gratuitas o de bajo costo

1. **Consultorio jurídico de una universidad.** Las facultades de Derecho tienen consultorios jurídicos que prestan asesoría a personas y pequeños negocios sin recursos, a cargo de estudiantes con supervisión de docentes. Lleva este documento impreso y pide específicamente "revisión de política de tratamiento de datos (Ley 1581)". Pregunta por requisitos y si atienden consultas de este tipo (varían por universidad).
2. **Cámara de Comercio de tu ciudad.** Suele tener programas de apoyo al comerciante y charlas o asesorías sobre formalización y protección de datos; pregunta por ellos.
3. **La propia SIC.** La Superintendencia de Industria y Comercio es la autoridad en esta materia y publica en su sitio (sic.gov.co, sección de protección de datos personales) guías, cartillas y modelos para elaborar políticas y avisos de privacidad, además de atender consultas. Compara este borrador con esas guías: si coincide en lo esencial, vas por buen camino.
4. **El contador del negocio.** Para la pregunta del RNBD (punto 7.3) y el tiempo de conservación de los registros contables.

### 7.2 Lista de verificación antes de usar el módulo de clientes con personas reales

- [ ] Completé los datos de la sección 1 en "Datos personales › Datos del negocio".
- [ ] Hay un canal real para solicitudes (correo, teléfono o mostrador) y alguien lo revisa.
- [ ] El cartel (3.2) está impreso y visible en el mostrador.
- [ ] La política (sección 2) está disponible en la tienda (impresa) a quien la pida.
- [ ] Tengo impresos los formatos de autorización escrita (4.1) y los empleados saben el guion verbal (4.2).
- [ ] Los empleados saben que **sin autorización no se registra a nadie** y que cualquier petición sobre datos se pasa al responsable el mismo día.
- [ ] Firmé la cláusula de encargo (sección 6) con quien opera el sistema.
- [ ] (Opcional) Alguien revisó el texto: el propietario decidió usarlo sin revisión de abogado el 12-10-2026.
- [ ] En el POS, al registrar un cliente, aparece el aviso con los datos del negocio (sin "[pendiente]") y la versión "1.0".

### 7.3 Pregunta pendiente: ¿hay que registrar la base de datos ante la SIC?

El Registro Nacional de Bases de Datos (RNBD) obliga hoy a los responsables con activos totales superiores a 100.000 UVT y a las entidades públicas. **Decisión del propietario (12-10-2026): no aplica**, porque el negocio no tiene esos activos. Si el negocio crece o la norma cambia, hay que volver a mirarlo. Aunque no tenga que inscribirse, todo lo demás de este documento sí le aplica.

---

## 8. Puntos que el sistema todavía no cubre

- **Prórrogas de plazo:** el sistema calcula la fecha límite base (10 o 15 días hábiles sin festivos) y no registra las prórrogas (decisión del propietario). Si se prorroga, anótalo en la respuesta.
- **Cloudflare y transferencia internacional:** la política lo declara como encargado con infraestructura fuera de Colombia. Si en la revisión jurídica piden algo más (cláusula contractual o declaración), se agrega.
- **Descripción de las solicitudes:** decidido el 13-10-2026: el texto libre que se escribe al registrar una solicitud **se borra** al anonimizar al cliente (junto con el de sus demás solicitudes); se conservan el tipo, las fechas y la respuesta. Aun así, conviene no escribir allí datos personales innecesarios.
- **Enviar las promociones:** el sistema solo guarda quién autorizó (casilla aparte, con fecha) y permite filtrarlos en "Clientes"; no envía mensajes. Quien las ofrezca debe usar solo a esos clientes y respetar de inmediato a quien retire la autorización.

---

## Control de versiones

| Versión | Fecha | Autor | Cambios |
|---|---|---|---|
| 0.1 | 12-10-2026 | Santiago Chávez López | Borrador inicial: política, aviso de privacidad, autorización escrita y verbal, procedimiento de solicitudes, cláusula de encargo y lista de verificación. |
| 1.0 | 12-10-2026 | Santiago Chávez López | Aprobado por el propietario sin revisión de abogado; RNBD no aplica; sin prórrogas; casilla aparte de promociones; los datos del negocio salen del `.env`; el texto lo sirve el backend (POS y autorregistro). |
| 1.1 | 13-10-2026 | Santiago Chávez López | Los datos del negocio se editan en la aplicación ("Datos personales › Datos del negocio"), ya no en el `.env`; el correo puede ser cualquiera que se revise. |
| 1.2 | 13-10-2026 | Santiago Chávez López | Al resolver una supresión también se borra la descripción libre de las solicitudes del cliente. |
| 1.3 | 19-10-2026 | Santiago Chávez López | El cartel de la tienda lleva el enlace de autorregistro y su código QR (se genera localmente con `herramientas/qr_cartel.py`). |
