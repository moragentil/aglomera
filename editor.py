"""Punto de entrada del editor visual de recintos: `solara run editor.py`.

Se dibuja el recinto con el mouse y se guarda en recintos/, listo para usarlo
en el simulador con AGLOMERA_RECINTO=<nombre> (ver app.py).
"""

from src.editor_ui import Page  # noqa: F401  (Solara busca el componente `Page`)
