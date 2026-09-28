# conftest.py – agrega la raíz del proyecto al sys.path
# Esto permite importar `app.*` desde cualquier test sin instalar el paquete.
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
