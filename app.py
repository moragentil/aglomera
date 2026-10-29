"""Punto de entrada para `solara run app.py`: visualizador interactivo.

El recinto se lee de un archivo de la carpeta recintos/ (ver src/recinto.py
para el formato). Por defecto es `sala_con_puerta`; para probar otro:

    AGLOMERA_RECINTO=dos_salidas venv/bin/solara run app.py

También acepta la ruta a un archivo propio. Si es una imagen dibujada (negro
pared, verde salida), AGLOMERA_ANCHO_CELDAS dice cuántas celdas de ancho tiene
el recinto (ver src/recinto_imagen.py):

    AGLOMERA_RECINTO=recintos/auditorio.png AGLOMERA_ANCHO_CELDAS=40 venv/bin/solara run app.py
"""

import os

from mesa.visualization import Slider, SolaraViz

from src.model import EvacuacionModel
from src.recinto import cargar_recinto
from src.visualization import GrillaRecinto

# sala_con_puerta: una pared parte el cuarto en dos, con una unica puerta
# angosta: todos los peatones del lado izquierdo tienen que pasar por ahi,
# uno a la vez, antes de llegar a la salida del lado derecho. Es el
# escenario clasico para observar "arqueo" (Helbing, Farkas & Vicsek, 2000):
# la gente se bloquea mutuamente en la puerta en vez de fluir ordenadamente.
ANCHO_EN_CELDAS = os.environ.get("AGLOMERA_ANCHO_CELDAS")
RECINTO = cargar_recinto(
    os.environ.get("AGLOMERA_RECINTO", "sala_con_puerta"),
    int(ANCHO_EN_CELDAS) if ANCHO_EN_CELDAS else None,
)

# "von_neumann" (4 direcciones) o "moore" (8, con diagonales). Esta version
# de Mesa no trae un selector desplegable para parametros de texto, asi que
# para compararlos hay que cambiar esta linea a mano y reiniciar la app
# (o usar experiments/run_batch.py, que si puede barrer ambos valores).
TIPO_VECINDAD = "moore"

# lo que EvacuacionModel necesita para armar el recinto: ancho, alto, salidas, muros
parametros_del_recinto = RECINTO.como_parametros()

model_params = {
    **parametros_del_recinto,
    "rng": 1,
    "tipo_vecindad": TIPO_VECINDAD,
    "num_agentes": Slider("Cantidad de peatones", value=40, min=5, max=120, step=5),
    "probabilidad_agresivo": Slider(
        "Probabilidad de ser agresivo", value=0.0, min=0.0, max=1.0, step=0.1
    ),
    "probabilidad_friccion": Slider(
        "Probabilidad de fricción", value=0.0, min=0.0, max=1.0, step=0.1
    ),
    # Tope en 0.9, no en 1.0 a proposito: en panico total (sin ningun
    # momento de lucidez) la simulacion puede no terminar nunca, porque
    # un par de peatones pueden quedar persiguiendose mutuamente para
    # siempre en vez de cruzar la salida. Ver Peaton.decidir_movimiento.
    "probabilidad_panico": Slider(
        "Probabilidad de pánico (manada)", value=0.0, min=0.0, max=0.9, step=0.1
    ),
}

modelo_inicial = EvacuacionModel(
    **parametros_del_recinto,
    num_agentes=40,
    rng=1,
    tipo_vecindad=TIPO_VECINDAD,
)

page = SolaraViz(
    modelo_inicial,
    components=[GrillaRecinto],
    model_params=model_params,
    name="Evacuación de multitudes",
)
