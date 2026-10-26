"""Pruebas del endpoint de solo lectura de categorias (soporte de RF-016: selector del formulario de alta)."""

from fastapi.testclient import TestClient

from tests.conftest import obtener_token


def test_lista_categorias_ordenadas_por_nombre(client: TestClient, db_session, usuario_vendedor):
    from app.models.categoria import Categoria

    db_session.add_all([Categoria(nombre="Zeta"), Categoria(nombre="Alfa")])
    db_session.commit()

    token = obtener_token(client, usuario_vendedor.username)
    respuesta = client.get("/categorias", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    nombres = [c["nombre"] for c in respuesta.json()]
    assert nombres == sorted(nombres)
    assert "Alfa" in nombres and "Zeta" in nombres


def test_requiere_autenticacion(client: TestClient):
    respuesta = client.get("/categorias")
    assert respuesta.status_code == 401
