"""
Tests de integración para los endpoints HTTP de FastAPI.
Utiliza TestClient para simular peticiones sin levantar un servidor real.
La BD se redirige a un archivo temporal aislado por cada test.
"""
import os
import pytest
from fastapi.testclient import TestClient

import app.database as db_module
from app.main import app


# ---------------------------------------------------------------------------
# Fixture: redirige DB_PATH a un archivo temporal único por test
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(tmp_path, monkeypatch):
    """
    Crea un TestClient con su propia BD aislada en un directorio temporal.
    El esquema se inicializa antes de cada test para garantizar estado limpio.
    """
    tmp_db = str(tmp_path / "test_nexus.db")
    monkeypatch.setattr(db_module, "DB_PATH", tmp_db)
    db_module.init_db(tmp_db)
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers de setup
# ---------------------------------------------------------------------------

def seed_character_and_session(client: TestClient):
    client.post("/api/characters", json={
        "id": "c1",
        "name": "Eldrin",
        "personality": "Misterioso",
        "system_prompt": "Habla en tono de fantasía oscura.",
    })
    client.post("/api/sessions", json={
        "id": "s1",
        "title": "Campaña de prueba",
    })


def send_chat(client: TestClient, content: str):
    return client.post("/api/chat", json={
        "session_id": "s1",
        "character_id": "c1",
        "user_name": "Jugador",
        "content": content,
    })


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_create_character_returns_201(client):
    response = client.post("/api/characters", json={
        "id": "c_test",
        "name": "Mago",
        "personality": "Calmado",
        "system_prompt": "Actúa con sobriedad.",
    })
    assert response.status_code == 201
    assert response.json()["id"] == "c_test"


def test_create_session_returns_201(client):
    response = client.post("/api/sessions", json={
        "id": "s_test",
        "title": "Sesión de prueba",
    })
    assert response.status_code == 201


def test_chat_with_unknown_character_returns_404(client):
    client.post("/api/sessions", json={"id": "s1", "title": "Test"})
    response = client.post("/api/chat", json={
        "session_id": "s1",
        "character_id": "no_existe",
        "user_name": "Jugador",
        "content": "Hola",
    })
    assert response.status_code == 404


def test_chat_stream_returns_sse_data(client):
    """El endpoint /api/chat debe devolver chunks SSE terminando en [DONE]."""
    seed_character_and_session(client)
    response = send_chat(client, "¿Quién eres?")

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    body = response.text
    assert "data:" in body
    assert "[DONE]" in body


def test_messages_are_persisted_after_chat(client):
    """Después de un chat, el historial debe contener exactamente 2 mensajes."""
    seed_character_and_session(client)
    send_chat(client, "Empieza la aventura.")

    history = client.get("/api/sessions/s1/messages").json()["messages"]
    assert len(history) == 2
    assert history[0]["is_character"] == 0   # mensaje del usuario
    assert history[1]["is_character"] == 1   # respuesta del bot
    # El turno del bot debe ser mayor que el del usuario
    assert history[1]["turn_index"] > history[0]["turn_index"]


def test_turn_index_increments_across_multiple_messages(client):
    """Los turn_index deben crecer estrictamente con cada intercambio."""
    seed_character_and_session(client)

    for i in range(3):
        send_chat(client, f"Mensaje {i}")

    history = client.get("/api/sessions/s1/messages").json()["messages"]
    # 3 intercambios = 6 mensajes (3 usuario + 3 bot)
    assert len(history) == 6
    turns = [m["turn_index"] for m in history]
    assert turns == sorted(turns), "Los turn_index no están en orden creciente"
    assert len(turns) == len(set(turns)), "Hay turn_index duplicados"
