"""
Seed script: inicializa la base de datos con un personaje y una sesión de prueba.
Ejecutar una sola vez antes de levantar el servidor.
"""
import os
from app.database import init_db, get_connection


def run_seed():
    os.makedirs("data", exist_ok=True)
    init_db()

    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO characters (id, name, personality, system_prompt) VALUES (?, ?, ?, ?)",
            (
                "char_eldrin",
                "Eldrin el Mago",
                "Misterioso, calmado, analítico y cínico",
                (
                    "Responde siempre manteniendo una atmósfera de fantasía oscura. "
                    "Usa metáforas arcanas y nunca reveles toda la verdad de una sola vez."
                ),
            ),
        )

        conn.execute("""
        INSERT OR REPLACE INTO sessions (id, title)
        VALUES ('session_demo_1', 'Campaña en el Bosque Prohibido')
        """)

        conn.execute("""
        INSERT OR IGNORE INTO world_events (session_id, turn_index, description)
        VALUES
            ('session_demo_1', 1, 'El grupo cruzó la puerta este de la fortaleza en ruinas.'),
            ('session_demo_1', 3, 'Se desató una tormenta de nieve mágica que cubrió el sendero.')
        """)

    print("[OK] Base de datos inicializada.")
    print("     Personaje: Eldrin el Mago (char_eldrin)")
    print("     Sesion:    Campania en el Bosque Prohibido (session_demo_1)")
    print("     Eventos:   2 eventos de mundo cargados")


if __name__ == "__main__":
    run_seed()
