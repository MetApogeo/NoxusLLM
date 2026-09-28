from app.context_engine import assemble_context

def test_sliding_window_limits_messages():
    character = {
        "name": "Eldrin",
        "personality": "Mago sabio y callado",
        "system_prompt": "Habla en tono místico."
    }
    
    # Simulamos 10 mensajes en el historial
    chat_history = [
        {"sender_name": "Jugador", "content": f"Mensaje {i}", "is_character": False}
        for i in range(10)
    ]

    # Pedimos una ventana de solo 4 mensajes
    result = assemble_context(
        character_card=character,
        episodic_summary="",
        world_events=[],
        chat_history=chat_history,
        max_recent_messages=4
    )

    # El resultado debe tener 1 system prompt + 4 mensajes de chat = 5
    assert len(result) == 5
    assert result[0]["role"] == "system"
    assert "[Jugador]: Mensaje 6" in result[1]["content"]
    assert "[Jugador]: Mensaje 9" in result[-1]["content"]

def test_world_events_maintain_chronological_order():
    character = {"name": "Bot", "personality": "Neutro", "system_prompt": "Test"}
    
    # Eventos enviados deliberadamente desordenados
    unordered_events = [
        {"turn_index": 5, "description": "El puente colapsó."},
        {"turn_index": 2, "description": "Llovió intensamente."},
        {"turn_index": 8, "description": "Llegó el mensajero."}
    ]

    result = assemble_context(
        character_card=character,
        episodic_summary="",
        world_events=unordered_events,
        chat_history=[]
    )

    system_prompt = result[0]["content"]
    
    pos_turn_2 = system_prompt.find("Turno 2")
    pos_turn_5 = system_prompt.find("Turno 5")
    pos_turn_8 = system_prompt.find("Turno 8")

    # Verificar que aparecen en orden secuencial estricto en el texto
    assert pos_turn_2 < pos_turn_5 < pos_turn_8