"""
Tests de persistencia e integridad de la base de datos.
Usa una BD temporal en memoria para no contaminar datos reales.
"""
import sqlite3
import pytest

from app.database import init_db, get_connection, get_next_turn, insert_message, get_messages

TEST_DB = ":memory:"


@pytest.fixture
def db_conn():
    """Fixture que entrega una conexión limpia en memoria por cada test."""
    conn = sqlite3.connect(TEST_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    # Inicializa el esquema directamente sobre esta conexión
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS characters (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        personality TEXT NOT NULL,
        system_prompt TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        character_id TEXT,
        sender_name TEXT NOT NULL,
        content TEXT NOT NULL,
        is_character BOOLEAN NOT NULL,
        turn_index INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES sessions(id)
    );
    CREATE TABLE IF NOT EXISTS world_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        turn_index INTEGER NOT NULL,
        description TEXT NOT NULL,
        is_public BOOLEAN DEFAULT 1,
        FOREIGN KEY (session_id) REFERENCES sessions(id)
    );
    CREATE TABLE IF NOT EXISTS episodic_summaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        summary TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES sessions(id)
    );
    """)
    # Insertar datos mínimos para tests
    conn.execute("INSERT INTO sessions (id, title) VALUES ('s1', 'Test Session')")
    conn.execute("INSERT OR REPLACE INTO characters (id, name, personality, system_prompt) VALUES ('c1', 'Eldrin', 'Misterioso', 'Habla en tono oscuro.')")
    conn.commit()
    yield conn
    conn.close()


def test_first_turn_is_one(db_conn):
    """El primer mensaje de una sesión vacía debe tener turn_index = 1."""
    turn = get_next_turn(db_conn, "s1")
    assert turn == 1


def test_turn_increments_strictly(db_conn):
    """Cada mensaje consecutivo debe incrementar el turn_index en 1."""
    for expected_turn in range(1, 6):
        turn = get_next_turn(db_conn, "s1")
        assert turn == expected_turn
        insert_message(db_conn, "s1", None, "User", f"msg {expected_turn}", False, turn)
        db_conn.commit()


def test_messages_persist_and_order(db_conn):
    """Los mensajes deben recuperarse en orden cronológico estricto."""
    for i in range(1, 4):
        insert_message(db_conn, "s1", None, "User", f"contenido {i}", False, i)
    db_conn.commit()

    messages = get_messages(db_conn, "s1")
    assert len(messages) == 3
    for i, msg in enumerate(messages, start=1):
        assert msg["turn_index"] == i
        assert f"contenido {i}" in msg["content"]


def test_character_message_flag(db_conn):
    """is_character debe persistirse correctamente para ambos tipos de remitente."""
    insert_message(db_conn, "s1", None, "Jugador", "hola", False, 1)
    insert_message(db_conn, "s1", "c1", "Eldrin", "saludos", True, 2)
    db_conn.commit()

    messages = get_messages(db_conn, "s1")
    assert messages[0]["is_character"] == 0
    assert messages[1]["is_character"] == 1
