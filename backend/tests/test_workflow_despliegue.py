"""Guardia del workflow de despliegue continuo: las reglas de seguridad no se pueden quitar sin que falle el CI."""

import re
from pathlib import Path

import pytest
import yaml

RUTA = Path(__file__).resolve().parents[2] / "deploy" / "despliegue.yml.example"
# `demo-servidor` es la etiqueta propia del runner del servidor: un runner ajeno con las etiquetas por defecto no recibe el trabajo.
SELF_HOSTED = ["self-hosted", "Linux", "X64", "demo-servidor"]

# Comandos que el flujo de despliegue tiene prohibido (CLAUDE.md, reglas de seguridad del servidor).
PROHIBIDOS = [
    r"down\s+-v", r"down\s+--volumes", r"volume\s+(rm|prune)", r"system\s+prune", r"(image|container)\s+prune",
    r"reset\s+--hard", r"checkout\s+-f", r"clean\s+-[a-z]*f", r"git\s+push",r"--force", r"rm\s+-[a-z]*r",
    r"alembic\s+(downgrade|stamp)", r"pg_restore", r"docker\s+compose\s+(config|restart)", r"printenv", r"\benv\b\s*\|",
]


@pytest.fixture(scope="module")
def flujo():
    return yaml.safe_load(RUTA.read_text(encoding="utf8"))


def _comandos(flujo) -> str:
    return "\n".join(paso["run"] for job in flujo["jobs"].values() for paso in job["steps"] if "run" in paso)


def test_solo_se_dispara_con_push_a_dev_o_main(flujo):
    disparadores = flujo.get("on", flujo.get(True))  # PyYAML lee la clave `on` como True

    assert set(disparadores) == {"push"}, "nunca pull_request: el codigo de un PR no debe correr en el servidor"
    assert set(disparadores["push"]["branches"]) <= {"dev", "main"}


def test_un_despliegue_a_la_vez_y_sin_cancelar_el_que_corre(flujo):
    assert flujo["concurrency"]["cancel-in-progress"] is False
    assert flujo["concurrency"]["group"]


def test_el_servidor_solo_ejecuta_despues_de_esperar_el_ci(flujo):
    jobs = flujo["jobs"]

    assert jobs["esperar-ci"]["runs-on"] == "ubuntu-latest"
    assert jobs["revisar"]["needs"] == "esperar-ci"
    assert jobs["desplegar"]["needs"] == "revisar"
    assert jobs["revisar"]["runs-on"] == SELF_HOSTED
    assert jobs["desplegar"]["runs-on"] == SELF_HOSTED


def test_el_runner_del_servidor_no_usa_acciones_de_terceros(flujo):
    for nombre, job in flujo["jobs"].items():
        if job["runs-on"] == SELF_HOSTED:
            assert not any("uses" in paso for paso in job["steps"]), f"{nombre} usa una accion en el servidor"


def test_el_flujo_no_contiene_comandos_prohibidos(flujo):
    # Unica excepcion: la carpeta temporal donde se compila el frontend antes de reemplazar `dist`.
    comandos = _comandos(flujo).replace("rm -rf dist-nuevo", "")

    for patron in PROHIBIDOS:
        assert not re.search(patron, comandos), f"comando prohibido en el despliegue: {patron}"


def test_nunca_toca_el_env(flujo):
    # Solo se nombra frontend/.env.production, que es publico (VITE_API_BASE_URL=/api).
    assert not re.findall(r"\.env(?!\.production)", _comandos(flujo))


def test_hace_las_comprobaciones_del_plan(flujo):
    comandos = _comandos(flujo)

    for esperado in (
        "respaldos.respaldar_base_de_datos",
        "git merge --ff-only",
        "npm ci",
        "--outDir dist-nuevo",  # compilar aparte: un build fallido no debe vaciar lo que sirve Nginx
        "docker compose up -d --build",
        "nginx -s reload",  # sin esto Nginx conserva la IP vieja del backend y responde 502
        "pinateria_demo_migrate",
        "http://localhost:8080/api/health",
        "MIGRACIONES_APROBADAS",
        "docker compose ps",
        "docker compose logs",
    ):
        assert esperado in comandos, f"falta en el despliegue: {esperado}"
