# Despliegue en el servidor (Ubuntu + Docker)

> **Nota del repositorio público:** esta guía es una referencia de cómo se desplegó el sistema. Los dominios, nombres y datos son de demostración (`demo.example.com`); el workflow de despliegue continuo se incluye como ejemplo inactivo en `deploy/despliegue.yml.example`.


Arquitectura: `Cloudflare Tunnel → nginx (:8080) → frontend estático + /api → backend (FastAPI)`.
El TLS lo termina Cloudflare. Postgres y Redis no se exponen a la red.

> **Staging antes de producción.** Se prueba primero con la rama `dev`
> (`git checkout dev && git pull`) y el dominio real de Cloudflare. Si todo va bien, se fusiona
> `dev` → `main` por pull request y el servidor pasa a `main` (`git checkout main && git pull`).
> Con datos de prueba: antes de usar el sistema con datos reales, empieza con una base nueva
> siguiendo la sección 8 (borra solo el volumen de Postgres; **no** uses `docker compose down -v`) y crea el admin de nuevo.

## 1. Primer despliegue

```bash
git clone https://github.com/<tu-usuario>/pinateria-demo.git
cd pinateria-demo

# Variables (contraseña de la base, clave de sesión, token del túnel)
cp .env.example .env
nano .env            # SECRET_KEY:  openssl rand -base64 48

# Frontend: se compila con la API en /api (mismo dominio, sin CORS)
cd frontend
echo "VITE_API_BASE_URL=/api" > .env.production
npm ci && npm run build
cd ..

# Levantar todo. El servicio `migrate` aplica Alembic antes de arrancar el backend.
docker compose up -d --build
docker compose ps
```

Crear el primer administrador (pide la contraseña de forma oculta):

```bash
docker compose exec backend python -m scripts.seed --username admin --nombre "Administrador"
```

Solo en **staging** (nunca con datos reales) se pueden cargar productos de ejemplo:
`docker compose exec backend python -m scripts.seed_demo`.

## 2. Cloudflare Tunnel (Named Tunnel)

El sistema se publica con un **Named Tunnel** (`pinateria-demo-server`) del dominio `demo.example.com`
(plan Free de Cloudflare). En Cloudflare Zero Trust → Networks → Tunnels, el túnel tiene un *Public hostname*:

| Hostname | Service |
|---|---|
| `pos.demo.example.com` | `http://nginx:8080` |

El `CLOUDFLARE_TUNNEL_TOKEN` de ese túnel va en `.env` (créalo/edítalo con `nano`; no lo pegues en chats ni en
logs). El servicio `cloudflared` de `docker-compose.yml` lo usa y llega a Nginx por la red interna de Docker,
por eso el *Service* es `nginx:8080` y no `localhost`.

> **El servidor no debe tener un `docker-compose.override.yml`.** Antes se usaba uno para levantar un *quick tunnel*
> (`trycloudflare.com`, dirección que cambia en cada arranque). Con el Named Tunnel ya no hace falta, y un override
> cambiaría lo que `docker compose up` levanta. Si aparece alguno, apártalo (por ejemplo, renómbralo a `.bak`): el
> workflow de despliegue continuo se detiene mientras exista.

Comprueba el túnel con `curl -s https://pos.demo.example.com/api/health` (debe responder 200).

## 3. Verificar

```bash
curl -s http://localhost:8080/api/health     # {"status":"ok",...}
docker compose logs migrate                  # "Running upgrade ... -> 0001, 0002, 0004, 0005" (o ya al día)
docker compose logs -f backend
```

Abrir el dominio público e iniciar sesión. Nginx solo escucha en `127.0.0.1:8080`, así que no es accesible por la IP del servidor desde la red; para probarlo desde otro equipo usa un túnel SSH: `ssh -L 8080:localhost:8080 usuario@servidor` y abre `http://localhost:8080/`.

## 4. Actualizar

Con el despliegue continuo activo (sección 7) esto lo hace GitHub Actions al fusionar en la rama que sigue el
servidor. A mano, para cuando el CD esté pausado o falle:

```bash
git pull
cd frontend && npm ci && npm run build && cd ..   # solo si cambió el frontend
docker compose up -d --build
docker compose exec -T nginx nginx -s reload   # si el backend se recreó, Nginx debe volver a resolverlo (si no: 502)
```

`docker compose up` corre el servicio `migrate`, que **aplica solo** las migraciones nuevas. Si la
actualización trae una migración que transforma datos, sigue antes los pasos de abajo.

### Actualizar a la versión con el Adendo v2 (migraciones 0002 y 0004)

La **0002** transforma datos: crea un pago por cada venta existente y elimina `ventas.metodo_pago`.
La **0004** solo crea una vista. Orden recomendado:

1. **Ensayo** con una copia de la base de producción: restaura un respaldo reciente en una base temporal
   del mismo Postgres (por ejemplo `pinateria_demo_ensayo`) y aplica ahí las migraciones con una imagen
   construida desde `dev` en un *worktree* aparte. No cambies de rama la carpeta de producción para el
   ensayo: Nginx monta archivos de ese árbol. Borra la base temporal al terminar. Comandos y consultas de
   verificación en "Ensayo de una migración que transforma datos", justo abajo.
2. **Respaldo manual** en producción justo antes (ver "Respaldos de PostgreSQL") y una copia fuera del servidor.
3. **Actualizar el agente de impresión en el PC del POS** (`git pull` en `printer-agent` y reiniciarlo): acepta el
   formato de ticket anterior y el nuevo, así no se cae la impresión mientras se actualiza el servidor.
4. En el servidor: `git pull`, compilar el frontend y `docker compose up -d --build`.
5. Verificar `docker compose logs migrate` (`0001 -> 0002` y `0002 -> 0004`) y que "Ventas de hoy" y el Dashboard
   muestren las ventas anteriores con su método de pago.
6. Como administrador: configurar los topes en la pestaña **Descuentos** (quedan sin límite hasta entonces) y cargar los
   costos en **Ganancias › Costos**.

Si algo sale mal, **restaura el respaldo** (ver "Respaldos de PostgreSQL"). `alembic downgrade` existe pero pierde
datos (los pagos mixtos se reducen a un método y se descartan descuentos y costos): pide confirmación antes.

### Actualizar a la versión con la Fase A2 (migración 0005)

La **0005** (clientes, solicitudes de titulares y `ventas.cliente_id`) y la **0006** (datos del negocio) no transforman
datos: solo crean tablas, columnas opcionales y una vista. Aun así el despliegue continuo se detiene hasta que se aprueben
(`gh variable set MIGRACIONES_APROBADAS --body "0005,0006"` y volver a ejecutar). Orden:

1. Respaldo manual justo antes (como siempre antes de una migración).
2. **Actualizar el agente de impresión en el PC del POS** (acepta el campo opcional `vendedor`; uno viejo lo ignora).
3. Aprobar las migraciones y desplegar. `docker compose logs migrate` debe mostrar `0004 -> 0005` y `0005 -> 0006`.
4. **Completar los datos del negocio desde la aplicación** (no hace falta tocar el servidor ni el `.env`): como
   administrador, en la pestaña **Datos personales › Datos del negocio**: nombre, NIT o cédula, dirección, teléfono, correo
   para solicitudes de datos (cualquier correo sirve) y fecha desde la que rige la política (opcionales: quién atiende las
   solicitudes y la versión, por defecto `1.0`). Mientras falte alguno, la política queda como "borrador" y el enlace de
   autorregistro no se puede publicar.
5. **Nginx:** esta versión agrega una zona `limit_req` para `/api/publico/` (el límite de envíos del autorregistro). No se pudo
   probar `nginx -t` fuera del servidor: tras desplegar, revisa `docker compose logs nginx` y que `nginx -s reload` no falle.
6. Después, en esa misma pestaña, generar el enlace de autorregistro; e imprimir el cartel y los
   formatos de `docs/08-politica-tratamiento-datos-borrador.md`.

### Actualizar a la versión con la migración 0007 (quién registró la venta)

La **0007** solo agrega `ventas.registrada_por_id` (opcional, con su índice); no transforma datos. Aun así, el CD se detiene hasta que se apruebe:

```bash
gh variable set MIGRACIONES_APROBADAS --body "0005,0006,0007"
```

**Apruébala antes de fusionar** el PR que la trae: el workflow lee la variable cuando arranca, no al llegar a su paso de revisión (si se aprueba después, hay que usar *Re-run all jobs*). Las ventas anteriores quedan con la columna en NULL (se entienden registradas por su vendedor). Si el servidor va a pasar a producción con una base nueva (sección 8), la 0007 se aplica sola junto con las demás.

### Actualizar a la versión con la Fase 9 (migración 0008 y modo sin conexión)

La **0008** agrega tres columnas opcionales a `ventas` (`uuid_cliente`, `sin_conexion`, `sincronizada_en`) y un índice único; no transforma datos (las ventas anteriores quedan con `uuid_cliente` en NULL). Aun así, el CD se detiene hasta que se apruebe:

```bash
gh variable set MIGRACIONES_APROBADAS --body "0005,0006,0007,0008"
```

**Apruébala antes de fusionar** el PR que la trae (el workflow lee la variable cuando arranca). Orden:

1. **Actualizar el agente de impresión** en el PC del POS (`actualizar.bat` y reiniciar el agente): acepta `referencia` en lugar de `venta_id` para imprimir el ticket de las ventas hechas sin conexión.
2. Aprobar la migración y fusionar (`dev` → `main`: el servidor sigue `main`).
3. En cada equipo, **abrir el POS con conexión al menos una vez** para que descargue el catálogo guardado.
4. Probar en la tienda el modo sin conexión (sección 8 de `docs/10-pruebas-de-aceptacion.md`) antes del primer corte real.

Detalle y límites del modo sin conexión: `docs/11-modo-sin-conexion.md`.

### Actualizar a la versión con el Adendo v3 (migraciones 0009 y 0010: gastos y caja)

La **0009** (G1: categorías de gasto con su siembra, `gastos`, tres columnas opcionales en `compras` y la vista `vw_gastos_unificados`) y la **0010** (G2: `cortes_caja` y `movimientos_caja`) no transforman datos: solo crean tablas, columnas opcionales y una vista. La G3 (ganancia neta) no tiene migración. El CD se detiene hasta que se aprueben; el 21-10-2026 la variable ya quedó así:

```bash
gh variable set MIGRACIONES_APROBADAS --body "0005,0006,0007,0008,0009,0010"
```

Esa aprobación debe estar **antes** de fusionar el PR `dev` → `main` (el workflow lee la variable cuando arranca). Orden:

1. **Respaldo manual** justo antes (ver "Respaldos de PostgreSQL"). El agente de impresión **no cambia**.
2. Revisar que el PR `dev` → `main` solo lleve el Adendo v3 y que Backend, Frontend y Printer agent estén en verde; fusionar con merge commit.
3. Mirar el despliegue en Actions: debe terminar en verde y `docker compose logs migrate` debe mostrar `0008 -> 0009` y `0009 -> 0010`. Después, `curl -fsS http://localhost:8080/api/health`.
4. La recepción de una compra cambió su contrato (ahora pide la forma de pago): el frontend y el servidor se despliegan juntos. Una pestaña que estaba abierta con la versión anterior recibe 422 al recibir una compra hasta que se recargue; avisa a quien use el POS que recargue la página.
5. En cada equipo del POS, recargar la aplicación (con conexión). Las ventas guardadas sin conexión no cambian.
6. Como administrador, comprobar que aparecen las categorías iniciales en **Gastos** (Compra de mercancía, Arriendo, Servicios públicos, Nómina, Transporte, Publicidad, Mantenimiento, Impuestos y Otros) y que **Caja** abre con el estado "cerrada".
7. Pasar las secciones 9 y 10 de `docs/10-pruebas-de-aceptacion.md` (con datos "PRUEBA" de montos mínimos: no se borran) y los puntos "Adendo v3" del checklist de staging.

Si algo sale mal, restaura el respaldo; `alembic downgrade` existe (0010 → 0009 → 0008) pero **pierde** los gastos, las categorías, los cortes y la forma de pago de las compras: pide confirmación antes.

### Ensayo de una migración que transforma datos (0002)

Detalle del paso 1 anterior. La copia se restaura en una base temporal del mismo Postgres; producción sigue funcionando mientras tanto: no se tocan la base `pinateria_demo` ni la carpeta del despliegue.

> No hagas `git checkout dev` en la carpeta del despliegue para ensayar: Nginx monta `nginx/nginx.conf` y `frontend/dist` desde ese árbol. El código de `dev` se toma de un *worktree* aparte.

**1. Respaldo manual.** Cópialo también fuera del servidor (ver "Respaldos de PostgreSQL").

```bash
docker compose exec celery_worker celery -A main.celery call respaldos.respaldar_base_de_datos
ls -lh backups/                                     # espera a que aparezca el .dump nuevo (pertenece a root)
RESPALDO=backups/pinateria_demo_AAAAMMDD_HHMMSS.dump  # el que se acaba de generar
```

**2. Restaurar la copia** en la base `pinateria_demo_ensayo` y guardar el método de pago de cada venta.
Los `.dump` los genera `pg_dump` 17 (imagen del backend), pero el `pg_restore` del contenedor `db` es el 15 y los rechaza
con `unsupported version (1.16) in file header`; por eso se restaura con el `pg_restore` del backend (servicio `migrate`,
que ya tiene `DATABASE_URL`; solo se cambia el nombre de la base, sin mostrar la contraseña). Termina con un error
**inofensivo**, `unrecognized configuration parameter "transaction_timeout"` (`errors ignored on restore: 1`, código de
salida 1): es el `SET` que Postgres 17 pone al inicio del archivo. Cualquier otro error sí hay que revisarlo.

```bash
docker compose exec db sh -c 'createdb -U "$POSTGRES_USER" pinateria_demo_ensayo'
# pg_restore del contenedor del backend (cliente de Postgres 17): el del contenedor `db` (15) no lee estos .dump.
docker compose run --rm --no-deps -v "$PWD/$RESPALDO:/tmp/respaldo.dump:ro" migrate \
  sh -c 'pg_restore --no-owner --dbname "${DATABASE_URL%/*}/pinateria_demo_ensayo" /tmp/respaldo.dump'
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d pinateria_demo_ensayo' <<'SQL'
SELECT version_num FROM alembic_version;  -- 0001 (si la tabla no existe, ver el paso 3)
CREATE TABLE _antes AS SELECT id, metodo_pago, total FROM ventas;
SELECT metodo_pago, count(*), sum(total) FROM ventas WHERE total > 0 GROUP BY 1 ORDER BY 1;
SQL
```

**3. Construir el backend de `dev` desde un *worktree* y migrar solo la base de ensayo.** La URL de la base (con la contraseña) se toma del contenedor del backend sin mostrarla; solo cambia el nombre de la base. No imprimas `URL_ENSAYO`.

```bash
git fetch origin
git worktree add ../demo-ensayo origin/dev
docker build -t demo-ensayo ../demo-ensayo/backend

URL_ENSAYO=$(docker compose exec -T backend printenv DATABASE_URL | sed 's#/[^/]*$#/pinateria_demo_ensayo#')
RED=$(docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' pinateria_demo_db | awk '{print $1}')
docker run --rm --network "$RED" -e DATABASE_URL="$URL_ENSAYO" \
  -e REDIS_URL=redis://redis:6379/0 -e SECRET_KEY=ensayo \
  demo-ensayo alembic upgrade head
```

Si en el paso 2 la tabla `alembic_version` no existía, la base se creó con el `schema.sql` (ver el paso 5 de esta guía):
antes del `upgrade head` marca la copia con `alembic stamp 0001`, con el mismo `docker run` cambiando el final por
`demo-ensayo alembic stamp 0001`. **Nunca** `stamp head`. Haz lo mismo después en producción (paso 5).

Debe mostrar `Running upgrade 0001 -> 0002` y `Running upgrade 0002 -> 0004`. Las migraciones corren en una sola transacción: si algo falla, la base de ensayo queda como estaba. En ese caso no sigas con el despliegue; guarda la salida y corrige desde el equipo de desarrollo.

**4. Verificar.** Cada consulta debe dar el resultado del comentario:

```bash
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d pinateria_demo_ensayo' <<'SQL'
SELECT version_num FROM alembic_version;  -- 0004
-- Ventas cuyo pago no conserva el método o el total de antes: 0
SELECT count(*) AS discrepancias
  FROM _antes a LEFT JOIN pagos_venta p ON p.venta_id = a.id
 WHERE a.total > 0
   AND (p.id IS NULL OR p.metodo_pago <> a.metodo_pago OR p.monto <> a.total);
-- Ventas con más de un pago: 0
SELECT count(*) AS con_varios_pagos
  FROM (SELECT venta_id FROM pagos_venta GROUP BY venta_id HAVING count(*) > 1) x;
-- Ventas en $0 con pago: 0
SELECT count(*) AS en_cero_con_pago
  FROM pagos_venta p JOIN _antes a ON a.id = p.venta_id WHERE a.total = 0;
-- Totales por método: iguales a los del paso 2
SELECT metodo_pago, count(*), sum(monto) FROM pagos_venta GROUP BY 1 ORDER BY 1;
-- La vista de ganancias (0004) responde
SELECT count(*) FROM vw_margen_detalle;
SQL
```

**5. Limpiar.** Borra solo la base de ensayo, no la real:

```bash
docker compose exec db sh -c 'dropdb -U "$POSTGRES_USER" pinateria_demo_ensayo'
git worktree remove ../demo-ensayo
docker image rm demo-ensayo
```

Si todo cuadra, sigue con los pasos 2 a 6 de "Actualizar a la versión con el Adendo v2".

### Cambio del puerto de Nginx (80 → 8080)

Si el servidor ya estaba desplegado con Nginx en el puerto 80, haz el cambio en este orden para limitar la caída a unos segundos:

1. En Cloudflare Zero Trust → Tunnels → *Public hostname*, cambia **Service** a `http://nginx:8080`.
2. En el servidor: `git pull` y `docker compose up -d` (recrea Nginx con el puerto nuevo).
3. Verifica `curl -s http://localhost:8080/api/health` y el dominio público. En Uptime Kuma actualiza la URL a `http://nginx:8080/api/health`.
4. Comprueba que ya no responde en el puerto 80: `curl -sI http://IP-DEL-SERVIDOR/` debe fallar desde otro equipo.

## 5. Si la base ya se creó con el `schema.sql` anterior

Antes el `schema.sql` se cargaba solo al crear el volumen; ahora el esquema lo
gestiona Alembic. Si tu base **ya tiene las tablas** (y datos que quieres
conservar) pero no tiene historial de Alembic, márcala con la versión que
corresponde al `schema.sql` (la **0001**) y deja que Alembic aplique el resto:

```bash
docker compose run --rm migrate alembic current      # vacío = sin historial
docker compose run --rm migrate alembic stamp 0001
docker compose up -d --build                         # migrate aplica 0002 y 0004 (haz antes el respaldo del paso 4)
```

**Nunca** uses `alembic stamp head` en una base creada con el `schema.sql`: la marcaría con
migraciones que no se aplicaron (0002 y 0004) y el backend fallaría.

Si no hay datos que conservar, es más simple recrear el volumen
(**borra la base**): `docker compose down -v && docker compose up -d --build`.

## 6. Equipo POS (tienda)

El agente de impresión **no** corre en el servidor: va en el PC del POS
(ver `printer-agent/README.md`). Se actualiza **antes** que el servidor cuando cambia el
formato del ticket (como en el Adendo v2). Se instala y actualiza con los scripts `.bat` de `printer-agent/`
(`instalar.bat`, `iniciar.bat`, `actualizar.bat`, `inicio-automatico.bat`; ver `printer-agent/README.md`). En su `.env`, agrega el dominio público a
`AGENTE_ORIGENES_PERMITIDOS`, por ejemplo:

```
AGENTE_ORIGENES_PERMITIDOS=https://pos.demo.example.com,http://localhost:5173
```

## 7. Despliegue continuo (GitHub Actions)

El workflow de ejemplo `deploy/despliegue.yml.example` (no activo en este repositorio público; cópialo a `.github/workflows/` en tu propio repositorio privado) actualiza el servidor solo cuando se fusiona en la rama que el
servidor sigue. Se dispara **únicamente con `push` a `dev` o `main`**, nunca con `pull_request`: el código de un PR
no corre en el servidor.

```
push a dev/main ─▶ 1. espera el CI de ese commit ─▶ 2. revisa (solo lectura) ─▶ 3. despliega
                      (ubuntu-latest)                  (runner del servidor)     (runner del servidor)
```

1. **Esperar el CI.** Si el CI (Backend, Printer agent, Frontend) del mismo commit no termina en verde, no se despliega
   (si se canceló porque llegó un commit más nuevo, simplemente se omite).
2. **Revisar.** Solo lectura: la rama del servidor debe coincidir con la del push (un push a `main` no hace nada si el servidor
   sigue en `dev`); no debe existir `docker-compose.override.yml`; y cada migración nueva debe estar **aprobada** (abajo).
3. **Desplegar**, en `~/proyectos/pinateria-demo`:
   1. Respaldo por Celery (`respaldos.respaldar_base_de_datos`, espera el resultado) y comprueba que el `.dump` nuevo exista y no esté vacío.
   2. `git fetch` y `git merge --ff-only <commit del CI>`: avanza exactamente al commit verificado y solo hacia adelante.
   3. Si cambió `frontend/` desde el último despliegue: `npm ci` y `npm run build` en una carpeta temporal (`dist-nuevo`) y, solo si compila, se copia a `frontend/dist`; así un build fallido no deja a Nginx sin archivos. Requiere `frontend/.env.production` y Node 20.19+ o 22.12+ (Vite 8).
   4. `docker compose up -d --build` y `nginx -s reload` (Nginx conserva la IP del backend que resolvió al arrancar; si el backend se recrea y Nginx no se recarga, responde 502).
   5. Espera a que `migrate` termine con código 0.
   6. `curl -f http://localhost:8080/api/health`.
   7. Guarda el commit desplegado en `.git/demo-ultimo-despliegue` (de ahí se calcula qué cambió en el siguiente despliegue).

Solo corre un despliegue a la vez y nunca se cancela el que está en curso (si llegan varios `push`, GitHub conserva el más reciente).

**Si algo falla**, el workflow muestra `docker compose ps` y los logs de `migrate`, `backend`, `celery_worker`, `celery_beat` y
`nginx`, y se detiene. **No restaura ni revierte nada solo.** Diagnostica con esos logs (ver la sesión del servidor en
`CLAUDE.md`); si hace falta restaurar un respaldo, es una decisión manual (sección "Respaldos de PostgreSQL"). Para reintentar
sin cambios: *Re-run failed jobs* en la pestaña Actions. El flujo tiene prohibido `docker compose down -v`, `docker volume rm`,
`docker system prune`, `git reset --hard`, `alembic downgrade` y `alembic stamp`; una prueba del backend
(`tests/test_workflow_despliegue.py`) falla si aparece alguno.

### Aprobar una migración

Una migración que transforma datos no puede aplicarse sola. Por simplicidad y seguridad, **cualquier migración nueva**
detiene el despliegue **antes de tocar el servidor** hasta que la apruebes. Para aprobarla:

1. Haz el respaldo manual y ensáyala en staging (sección 4, "Ensayo de una migración que transforma datos").
2. Registra su número en la variable del repositorio (el mensaje del workflow trae el comando exacto):

   ```bash
   gh variable set MIGRACIONES_APROBADAS --body "0005"      # varias: "0005,0006" (se conservan las anteriores)
   ```

3. En Actions, abre la ejecución que falló y pulsa *Re-run all jobs*.

> **Por qué una variable y no un *environment* con revisores:** el repositorio es privado en el plan Free y GitHub no ofrece
> revisores de *environments* ahí (como tampoco la protección de ramas, ver `CONTRIBUTING.md`). Si algún día se pasa a GitHub
> Pro, se puede agregar `environment: produccion` con revisores al trabajo `desplegar` y conservar esta variable como segunda llave.

### El runner del servidor

El trabajo corre en un *runner* **self-hosted** instalado en `~/actions-runner`, como servicio de systemd con arranque automático,
etiquetas `self-hosted, Linux, X64` y la propia `demo-servidor` (los trabajos del servidor piden las cuatro, así que un runner ajeno con las etiquetas por defecto no los recibe) y con el usuario del servidor (que está en el grupo `docker`). Si hay que instalarlo de nuevo, agrega la etiqueta al configurarlo (`./config.sh ... --labels demo-servidor`) o después con `gh api -X POST repos/<dueño>/<repo>/actions/runners/<id>/labels -f 'labels[]=demo-servidor'`.

```bash
cd ~/actions-runner
sudo ./svc.sh status                          # estado del servicio
systemctl list-units 'actions.runner.*'       # nombre completo del servicio
sudo journalctl -u 'actions.runner.*' -n 50   # sus últimos registros
sudo ./svc.sh stop                            # pausar el CD (los trabajos esperan en cola hasta que vuelva)
sudo ./svc.sh start
```

Para instalarlo de nuevo: GitHub → Settings → Actions → Runners → *New self-hosted runner* (Linux x64) y seguir sus comandos
(`./config.sh --url ... --token ...`; el token vale una hora y no se guarda), luego `sudo ./svc.sh install <usuario>` y
`sudo ./svc.sh start`. Necesita `git`, Docker Compose, `curl` y `node`/`npm` en el `PATH` **del servicio** (systemd no lee
`~/.bashrc`: si `npm` viene de `nvm`, agrega su carpeta en `~/actions-runner/.path` y reinicia el servicio).

**Riesgo que se acepta:** un runner con un usuario del grupo `docker` equivale a acceso de administrador al servidor. Se
mitiga así: el repositorio es **privado** y un solo colaborador; el workflow no se dispara con `pull_request` (no hay PRs de forks
ni código ajeno en el servidor); los trabajos del servidor no usan acciones de terceros (`uses:`) y no manejan secretos. Si algún
día el repositorio se hace público o se agregan colaboradores, hay que revisar esto antes (en un repositorio público no se
debe usar un runner self-hosted).

### Primera vez

1. El primer merge con este workflow conviene que traiga **solo cambios de documentación**: el despliegue no debería cambiar nada
   (sin migraciones, sin frontend, imágenes idénticas) y sirve de prueba sin riesgo.
2. Antes de fusionar, deja `MIGRACIONES_APROBADAS` vacía o sin crear (sin migraciones nuevas no se usa).
3. Tras fusionar a `dev`, mira la ejecución en Actions: debe terminar en verde y `docker compose ps` seguir igual.

## 8. Paso a producción (de `dev` a `main`, con base vacía)

Hoy el servidor sigue `dev` y su base tiene **datos de prueba** (las pruebas de aceptación dejan ventas que no se pueden borrar). Para abrir
con datos reales se cambia el servidor a `main` y se empieza con una **base nueva**. Esta sección es para la sesión del servidor; el workflow
de despliegue continuo **no** hace nada de esto (ver sección 7: un push a `main` no despliega mientras el servidor siga en `dev`).

**Condiciones previas (todas):** pruebas de aceptación hechas (`docs/10-pruebas-de-aceptacion.md`), aprobación del propietario, CI en verde y el
PR `dev` → `main` fusionado por pull request.

> **Pide confirmación al usuario antes del paso 3 (borra la base) y antes de cualquier otro comando destructivo.** No leas ni muestres el `.env`.

### 1. Respaldo manual de la base de pruebas

Por si algo sale mal. Ver "Respaldos de PostgreSQL":

```bash
docker compose exec celery_worker celery -A main.celery call respaldos.respaldar_base_de_datos
ls -lh backups/ | head
```

### 2. Cambiar el servidor a `main`

```bash
git status                              # debe estar limpio
git fetch origin
git checkout main                       # si no existe local: git checkout -b main origin/main
git merge --ff-only origin/main
git log --oneline -3
```

Si hay `docker-compose.override.yml`, apártalo (ver sección 2). Si `frontend/package-lock.json` cambió respecto a `dev`, compila el frontend como
lo hace el CD (en `dist-nuevo`, y solo si compila se copia a `dist`):

```bash
cd frontend && npm ci && rm -rf dist-nuevo && npm run build -- --outDir dist-nuevo --emptyOutDir \
  && mkdir -p dist && find dist -mindepth 1 -delete && cp -a dist-nuevo/. dist/ && rm -rf dist-nuevo && cd ..
```

### 3. Base nueva (destructivo: confirmar primero)

Se borra **solo el volumen de Postgres**. **No uses `docker compose down -v`**: borraría también el volumen de Uptime Kuma
(sus monitores), el de Redis y el estado de Celery Beat. Los respaldos de `./backups` no se tocan.

```bash
docker compose down                                                        # sin -v
docker volume ls | grep postgres_data                                      # confirma el nombre (p. ej. <proyecto>_postgres_data)
docker volume rm <nombre-del-volumen-postgres>
docker compose up -d --build                                               # `migrate` crea el esquema (0001 a 0006) en la base vacía
docker compose ps                                                          # migrate: Exited (0); el resto, healthy/running
docker compose exec -T nginx nginx -s reload
curl -fsS http://localhost:8080/api/health
```

Una base vacía no necesita aprobar migraciones: las aplica `migrate` completas desde cero. **No** corras `scripts.seed_demo`.

### 4. Datos reales

En este orden, con el usuario:

1. Primer administrador: `docker compose exec backend python -m scripts.seed --username <usuario> --nombre "<nombre>"` (pide la contraseña de forma oculta).
2. Como administrador: crear los usuarios reales (vendedor y propietario) en **Usuarios**.
3. **Datos personales › Datos del negocio** (todos los campos obligatorios) y, después, generar el enlace de autorregistro. Es un enlace **nuevo**: el cartel con su QR se imprime
   hasta este punto.
4. Descuentos: activar el general si se va a usar y fijar los topes del vendedor.
5. Catálogo: categorías, productos (precios, stock inicial, stock mínimo) y recetas de paquetes y anchetas, a mano. Luego los costos en **Ganancias**.
6. Proveedores y, si ya hay mercancía por recibir, la primera compra.

### 5. Marcar el commit desplegado y comprobar

```bash
git rev-parse HEAD > .git/demo-ultimo-despliegue     # el CD compara desde aquí en el siguiente push a main
```

- Pasa el "Checklist de staging" completo.
- Una venta real de prueba con el vendedor (cobrar, imprimir) y su respaldo posterior; si es de prueba, que sea la única y se anote.
- Uptime Kuma sigue monitoreando `http://nginx:8080/api/health` (su volumen no se tocó).
- Anota en `docs/06` la fecha del paso.

### 6. Después

- Un push a `dev` **ya no despliega** (el servidor sigue `main`). Si se quiere volver a probar en el servidor, hay que cambiar de rama a mano
  y recordar que la base es la real.
- Los pasos siguientes a `main` se hacen por pull request `dev` → `main`; el CD despliega solo en `main`.
- `main` puede traer commits que `dev` no tiene (como el de Dependabot): sincronízalos con un PR `main` → `dev` cuando convenga.
- Si hay que volver atrás: `docker compose stop backend celery_worker celery_beat` y restaurar un respaldo ("Respaldos de PostgreSQL"); es una decisión manual.

## Checklist de staging

- [ ] `docker compose ps`: todos los servicios *healthy* / *running* (`migrate` termina en *Exited (0)*).
- [ ] `curl -s http://localhost:8080/api/health` responde `{"status":"ok",...}`.
- [ ] Iniciar sesión con el admin creado, desde el dominio de Cloudflare y desde el móvil.
- [ ] Una venta completa; aparece en "Ventas de hoy"; el stock baja.
- [ ] Adendo v2: venta con pagos mixtos (efectivo con vueltas + Nequi) y con descuento; el ticket imprime los pagos.
- [ ] Adendo v2: las ventas anteriores a la migración 0002 conservan su método de pago.
- [ ] Adendo v2: bandeja de "Stock bajo" y lista de compras por WhatsApp desde el celular.
- [ ] Adendo v2: Ganancias (propietario y administrador); el vendedor no ve costos.
- [ ] Fase 9: con el agente actualizado, cortar internet en el PC del POS, vender (el ticket sale como `Venta SC-0001`), reconectar y comprobar que la venta aparece en "Ventas de hoy" con su hora y la marca "Sin conexión".
- [ ] Adendo v3 (G1): `docker compose logs migrate` muestra `0008 -> 0009` y `0009 -> 0010`; en **Gastos** están las nueve categorías iniciales y "Compra de mercancía" no se puede editar ni desactivar.
- [ ] Adendo v3 (G1): como administrador registra un gasto en efectivo de $50 y anúlalo con motivo; como vendedor, el gasto solo se ve en su propia lista (no el de otra persona) y no aparecen compras ni totales.
- [ ] Adendo v3 (G1): recibe una compra de prueba: pide la forma de pago, sube el stock y aparece en Gastos como fila de solo lectura.
- [ ] Adendo v3 (G2): como vendedor abre la **Caja** con $50.000, haz una venta en efectivo con vueltas (el esperado sube lo que abona, no lo recibido), un gasto en efectivo y un retiro con motivo; cierra contando el efectivo y comprueba la diferencia; el vendedor ya no puede editar el gasto del corte y el administrador sí.
- [ ] Adendo v3 (G2): sin conexión, el POS no deja cerrar la caja mientras haya ventas guardadas sin enviar; con la conexión de vuelta, se envían y deja cerrar.
- [ ] Adendo v3 (G2): como propietario, en el Dashboard las pestañas **Gastos** y **Caja** solo consultan (sin botones de registrar, abrir ni cerrar) y **Exportar** descarga un CSV que abre en Excel.
- [ ] Adendo v3 (G3): en **Ganancias** (administrador y propietario) aparecen la ganancia neta y el resultado de caja; el vendedor no los ve.
- [ ] Respaldo manual: genera un `.dump` en `./backups/` (ver "Respaldos de PostgreSQL").
- [ ] Respaldo diario: hay un `.dump` por cada madrugada en `./backups/` (también después de recrear `celery_beat`).
- [ ] Despliegue continuo: un merge a la rama del servidor termina en verde en Actions y deja un respaldo nuevo (sección 7).
- [ ] Reiniciar el servidor: los servicios levantan solos (`restart: always`).
- [ ] Uptime Kuma (`127.0.0.1:3001`): registrar `http://nginx:8080/api/health` y el agente de impresión del POS.
- [ ] En el PC del POS: `AGENTE_ORIGENES_PERMITIDOS` con el dominio público y una venta imprime (hardware).

## Notas

- Uptime Kuma queda en `127.0.0.1:3001` (acceso por SSH: `ssh -L 3001:localhost:3001 usuario@servidor`,
  o publícalo con un segundo *Public hostname* del túnel protegido con Cloudflare Access).
- `/docs` de FastAPI ya no se expone públicamente. Para probar la API en staging:
  `docker compose exec backend curl -s localhost:8000/openapi.json`.

## Respaldos de PostgreSQL

Celery Beat genera un respaldo **todos los días a las 2:30 a. m. (hora de Bogotá)** en
`./backups/` (archivos `pinateria_demo_AAAAMMDD_HHMMSS.dump`). Cada respaldo se verifica con
`pg_restore --list` antes de darlo por bueno y se conservan 14 días (`RESPALDOS_DIAS_RETENCION`).
Un respaldo fallido nunca borra los anteriores; el error queda en `docker compose logs celery_worker`.

**Carpeta y permisos.** El worker corre como `root` dentro del contenedor, así que los `.dump` nacen con dueño `root`
(el código los deja con permiso de lectura `0644`). Para que el usuario del servidor pueda copiarlos y borrarlos, y nadie
más los vea (contienen datos personales), haz **una vez** que la carpeta sea suya y privada:

```bash
sudo chown "$USER": backups && chmod 700 backups       # root del contenedor puede escribir igual
sudo chown "$USER": backups/*.dump 2>/dev/null || true # los respaldos que ya existían
```

**Por qué podía faltar un día.** Celery Beat recuerda cuándo corrió cada tarea en un archivo. Si ese archivo se pierde (antes
estaba en `/tmp` del contenedor, que se borra al recrearlo, y cada despliegue lo recrea) y Beat arranca después de las 2:30 a. m.,
da por pasada la hora de ese día y no corre el respaldo hasta la madrugada siguiente. Ahora el archivo vive en el volumen
`celery_beat_data` (`/data/celerybeat-schedule`): al reiniciar, Beat ve que el respaldo de hoy no se hizo y lo ejecuta de
inmediato. Para comprobarlo: `ls -lt backups/ | head` debe mostrar un `.dump` por día (hora UTC `07:30`, 2:30 en Bogotá).

Correr uno ahora (por ejemplo, para probar):

```bash
docker compose exec celery_worker celery -A main.celery call respaldos.respaldar_base_de_datos
ls -lh backups/
```

Restaurar (**sobrescribe los datos actuales**; detén el backend primero):

```bash
docker compose stop backend celery_worker celery_beat
docker compose run --rm --no-deps -v "$PWD/backups:/app/backups:ro" migrate \
  sh -c 'pg_restore --clean --if-exists --no-owner --dbname "$DATABASE_URL" /app/backups/pinateria_demo_AAAAMMDD_HHMMSS.dump'
docker compose start backend celery_worker celery_beat
```

Se restaura con el `pg_restore` del contenedor del backend (servicio `migrate`, que ya tiene `DATABASE_URL`) y **no** con el del
contenedor `db`: los `.dump` los genera `pg_dump` 17 y el `pg_restore` de Postgres 15 los rechaza (`unsupported version (1.16)
in file header`). Al final sale un error **inofensivo**, `unrecognized configuration parameter "transaction_timeout"`
(`errors ignored on restore: 1`, código de salida 1); cualquier otro error sí hay que revisarlo.

**Importante:** `./backups` está en el mismo disco del servidor. Si el disco falla, se pierde
la base *y* los respaldos. Copia esa carpeta a otro lugar (disco externo o nube, p. ej. con
`rclone`) — es la mitigación de "falla del disco" del documento de Visión y Alcance.
