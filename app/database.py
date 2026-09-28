import sqlite3
from typing import List, Dict, Any, Optional

DB_PATH = "data/nexus.db"


def get_connection(db_path: str = None) -> sqlite3.Connection:
    """Devuelve una conexión con row_factory y FK activadas."""
    if db_path is None:
        db_path = DB_PATH  # leído en tiempo de llamada, no de importación
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: str = DB_PATH):
    """Crea todas las tablas si no existen."""
    with get_connection(db_path) as conn:
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


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------

def create_character(conn: sqlite3.Connection, id: str, name: str, personality: str, system_prompt: str):
    conn.execute(
        "INSERT OR REPLACE INTO characters (id, name, personality, system_prompt) VALUES (?, ?, ?, ?)",
        (id, name, personality, system_prompt),
    )


def create_session(conn: sqlite3.Connection, id: str, title: str):
    conn.execute(
        "INSERT OR REPLACE INTO sessions (id, title) VALUES (?, ?)",
        (id, title),
    )


def get_messages(conn: sqlite3.Connection, session_id: str) -> List[Dict[str, Any]]:
    """Devuelve todos los mensajes de una sesión ordenados cronológicamente."""
    rows = conn.execute(
        "SELECT sender_name, content, is_character, turn_index FROM messages "
        "WHERE session_id = ? ORDER BY turn_index ASC",
        (session_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_world_events(conn: sqlite3.Connection, session_id: str) -> List[Dict[str, Any]]:
    rows = conn.execute(
        "SELECT turn_index, description FROM world_events WHERE session_id = ?",
        (session_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_latest_summary(conn: sqlite3.Connection, session_id: str) -> str:
    row = conn.execute(
        "SELECT summary FROM episodic_summaries WHERE session_id = ? ORDER BY id DESC LIMIT 1",
        (session_id,),
    ).fetchone()
    return row[0] if row else ""


def get_next_turn(conn: sqlite3.Connection, session_id: str) -> int:
    """Calcula el próximo turn_index garantizando secuencia estricta."""
    last = conn.execute(
        "SELECT MAX(turn_index) FROM messages WHERE session_id = ?",
        (session_id,),
    ).fetchone()[0]
    return 1 if last is None else last + 1


def insert_message(
    conn: sqlite3.Connection,
    session_id: str,
    character_id: Optional[str],
    sender_name: str,
    content: str,
    is_character: bool,
    turn_index: int,
):
    conn.execute(
        """INSERT INTO messages
           (session_id, character_id, sender_name, content, is_character, turn_index)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (session_id, character_id, sender_name, content, int(is_character), turn_index),
    )
