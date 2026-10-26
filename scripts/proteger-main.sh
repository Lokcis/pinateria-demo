#!/bin/sh
# Aplica la proteccion de la rama main en GitHub.
#
# REQUIERE GitHub Pro/Team (o repo publico): en repos privados con plan
# gratuito la API responde 403 "Upgrade to GitHub Pro". Los estudiantes pueden
# tener Pro gratis con el GitHub Student Developer Pack.
#
# Reglas (proyecto de un solo desarrollador, revision del propietario por fase):
#   - Todo entra por pull request (sin push directo), pero SIN exigir
#     aprobaciones: uno mismo no puede aprobar su propio PR.
#   - Deben pasar los tres jobs de CI (Backend, Printer agent, Frontend) y la
#     rama del PR debe estar al dia con main.
#   - Conversaciones de revision resueltas antes de fusionar.
#   - Sin force-push ni borrado de main, tambien para administradores.
#
# Uso:  scripts/proteger-main.sh            (repo detectado por gh)
set -eu

REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)

gh api -X PUT "repos/$REPO/branches/main/protection" --input - <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["Backend", "Printer agent", "Frontend"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 0,
    "dismiss_stale_reviews": true
  },
  "restrictions": null,
  "required_conversation_resolution": true,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON

echo "main protegida en $REPO"
