import time
from typing import List, Dict, Generator


class MockLLMService:
    """
    Motor simulado que genera respuestas en personaje sin llamadas de red.
    Puede reemplazarse por un cliente real (OpenAI, Groq, Gemini) en el futuro.
    """

    @staticmethod
    def generate_response(
        messages: List[Dict[str, str]],
        character_name: str,
        personality: str,
    ) -> str:
        """Genera una respuesta sintética basada en el último mensaje del usuario."""
        last_user_message = "..."
        for msg in reversed(messages):
            if msg["role"] == "user":
                last_user_message = msg["content"]
                break

        return (
            f"*{character_name} procesa las palabras con calma, "
            f"fiel a su esencia: {personality}.* "
            f"He escuchado lo que dices: \"{last_user_message}\". "
            f"La secuencia temporal permanece intacta y mis recuerdos, ordenados."
        )

    @classmethod
    def generate_stream(
        cls,
        messages: List[Dict[str, str]],
        character_name: str,
        personality: str,
    ) -> Generator[str, None, None]:
        """
        Simula streaming token a token (palabra por palabra con latencia artificial).
        El generador emite fragmentos de texto listos para SSE.
        """
        full_text = cls.generate_response(messages, character_name, personality)
        words = full_text.split(" ")
        for i, word in enumerate(words):
            time.sleep(0.05)  # Simula latencia de red natural
            # Añadir espacio entre palabras, no al final del último
            yield word if i == len(words) - 1 else f"{word} "
