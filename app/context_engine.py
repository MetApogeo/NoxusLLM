from typing import List, Dict, Any

def assemble_context(
    character_card: Dict[str, str],
    episodic_summary: str,
    world_events: List[Dict[str, Any]],
    chat_history: List[Dict[str, Any]],
    max_recent_messages: int = 6
) -> List[Dict[str, str]]:
    """
    Ensambla el prompt para el LLM respetando jerarquía:
    1. System Prompt (identidad inmutable)
    2. Resumen cronológico pasado (episodic)
    3. Eventos del mundo ordenados por turno
    4. Ventana deslizante (últimos N mensajes)
    """
    system_sections = [
        f"Eres {character_card['name']}.\n"
        f"Personalidad: {character_card['personality']}\n"
        f"Instrucción base: {character_card['system_prompt']}"
    ]

    if episodic_summary:
        system_sections.append(f"[MEMORIA PASADA]\n{episodic_summary}")

    if world_events:
        # Garantizar orden cronológico por turn_index
        sorted_events = sorted(world_events, key=lambda x: x["turn_index"])
        event_lines = [f"- (Turno {e['turn_index']}): {e['description']}" for e in sorted_events]
        system_sections.append("[EVENTOS DEL ENTORNO]\n" + "\n".join(event_lines))

    assembled = [{"role": "system", "content": "\n\n".join(system_sections)}]

    # Aplicar ventana deslizante (sliding window)
    windowed_messages = chat_history[-max_recent_messages:] if max_recent_messages > 0 else []

    for msg in windowed_messages:
        role = "assistant" if msg.get("is_character", False) else "user"
        sender = msg.get("sender_name", "Usuario")
        assembled.append({
            "role": role,
            "content": f"[{sender}]: {msg['content']}"
        })

    return assembled