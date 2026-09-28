from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import os

from app.database import (
    init_db,
    get_connection,
    get_messages,
    get_world_events,
    get_latest_summary,
    get_next_turn,
    insert_message,
)
from app.context_engine import assemble_context
from app.llm_mock import MockLLMService


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs("data", exist_ok=True)
    init_db()
    yield


app = FastAPI(title="Nexus Roleplay Engine (MVP)", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class MessagePayload(BaseModel):
    session_id: str
    character_id: str
    user_name: str
    content: str


class CharacterPayload(BaseModel):
    id: str
    name: str
    personality: str
    system_prompt: str


class SessionPayload(BaseModel):
    id: str
    title: str


# ---------------------------------------------------------------------------
# Endpoints de administración
# ---------------------------------------------------------------------------

@app.post("/api/characters", status_code=201)
def create_character(payload: CharacterPayload):
    """Crea o actualiza un personaje."""
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO characters (id, name, personality, system_prompt) VALUES (?, ?, ?, ?)",
            (payload.id, payload.name, payload.personality, payload.system_prompt),
        )
    return {"ok": True, "id": payload.id}


@app.post("/api/sessions", status_code=201)
def create_session(payload: SessionPayload):
    """Crea o actualiza una sesión."""
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO sessions (id, title) VALUES (?, ?)",
            (payload.id, payload.title),
        )
    return {"ok": True, "id": payload.id}


@app.get("/api/sessions/{session_id}/messages")
def list_messages(session_id: str):
    """Devuelve el historial de una sesión en orden cronológico."""
    with get_connection() as conn:
        messages = get_messages(conn, session_id)
    return {"session_id": session_id, "messages": messages}


# ---------------------------------------------------------------------------
# Endpoint principal: chat con streaming SSE
# ---------------------------------------------------------------------------

@app.post("/api/chat")
def chat_stream(payload: MessagePayload):
    """
    Recibe el mensaje del usuario, lo persiste y devuelve la respuesta
    del personaje como Server-Sent Events (SSE).
    """
    with get_connection() as conn:
        # Verificar que el personaje existe
        char = conn.execute(
            "SELECT * FROM characters WHERE id = ?", (payload.character_id,)
        ).fetchone()
        if not char:
            raise HTTPException(status_code=404, detail="Personaje no encontrado")

        char = dict(char)

        # Calcular turno cronológico del mensaje de usuario
        user_turn = get_next_turn(conn, payload.session_id)

        # Persistir mensaje del usuario
        insert_message(
            conn,
            session_id=payload.session_id,
            character_id=None,
            sender_name=payload.user_name,
            content=payload.content,
            is_character=False,
            turn_index=user_turn,
        )

        # Recuperar estado completo para ensamblar contexto
        history = get_messages(conn, payload.session_id)
        events = get_world_events(conn, payload.session_id)
        summary = get_latest_summary(conn, payload.session_id)

    # Ensamblar contexto fuera del bloque de conexión
    prompt_context = assemble_context(
        character_card=char,
        episodic_summary=summary,
        world_events=events,
        chat_history=history,
        max_recent_messages=6,
    )

    bot_turn = user_turn + 1

    def event_generator():
        chunks = []
        for chunk in MockLLMService.generate_stream(
            prompt_context, char["name"], char["personality"]
        ):
            chunks.append(chunk)
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"

        full_reply = "".join(chunks).strip()

        # Persistir respuesta del personaje una vez completada
        with get_connection() as save_conn:
            insert_message(
                save_conn,
                session_id=payload.session_id,
                character_id=payload.character_id,
                sender_name=char["name"],
                content=full_reply,
                is_character=True,
                turn_index=bot_turn,
            )

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
