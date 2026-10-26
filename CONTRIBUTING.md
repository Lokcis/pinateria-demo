# Flujo de trabajo

```
rama de trabajo ──PR──▶ dev ──PR──▶ main ──▶ servidor
```

- Nada se sube directo a `main` ni `dev`: todo entra por pull request y con el CI en verde
  (Backend, Printer agent, Frontend; ver `.github/workflows/ci.yml`).
- Se fusiona con **merge commit** (los demás modos están desactivados). La rama de trabajo se
  borra al fusionar (`gh pr merge <n> --merge --delete-branch`); en el PR `dev` → `main` **no** se
  borra `dev`. El repositorio no permite auto-merge: se fusiona a mano con el CI en verde.
- `dev` es la integración; `main` es lo que se despliega en el servidor
  (ver `DEPLOY.md`). Cada fase se pasa a `main` cuando el propietario la aprueba.

## Activar el hook local (una vez por clon)

```bash
git config core.hooksPath .githooks
```

Rechaza `git push` directo a `main` y a `dev`. Un push a la rama que sigue el servidor dispara el despliegue continuo
(`DEPLOY.md`, sección 7), así que esto evita desplegar por accidente. Es solo una red de seguridad en tu equipo;
en una emergencia: `PERMITIR_PUSH_DIRECTO=1 git push ...`.

## Proteger `main` en GitHub

Requiere GitHub Pro (gratis con el *Student Developer Pack*) o repo público:

```bash
scripts/proteger-main.sh
```

Exige PR y CI verde, sin pedir aprobaciones (un solo desarrollador) y sin force-push.
Después de aplicarlo, los nombres de los jobs de CI no deben cambiar sin actualizar el script.
