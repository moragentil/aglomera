"""Punto de entrada para `solara run app.py`: visualizador interactivo."""

from mesa.visualization import Slider, SolaraViz

from src.model import EvacuacionModel
from src.visualization import GrillaRecinto

ALTO = 10

# Pared que parte el cuarto en dos, con una unica puerta angosta en y=4:
# todos los peatones del lado izquierdo tienen que pasar por ahi, uno a la
# vez, antes de llegar a la salida del lado derecho. Es el escenario
# clasico para observar "arqueo" (Helbing, Farkas & Vicsek, 2000): la
# gente se bloquea mutuamente en la puerta en vez de fluir ordenadamente.
MURO_CON_PUERTA = [(7, y) for y in range(ALTO) if y != 4]

# "von_neumann" (4 direcciones) o "moore" (8, con diagonales). Esta version
# de Mesa no trae un selector desplegable para parametros de texto, asi que
# para compararlos hay que cambiar esta linea a mano y reiniciar la app
# (o usar experiments/run_batch.py, que si puede barrer ambos valores).
TIPO_VECINDAD = "moore"

model_params = {
    "ancho": 15,
    "alto": ALTO,
    "salidas": [(14, 5)],
    "muros": MURO_CON_PUERTA,
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
    ancho=15,
    alto=ALTO,
    num_agentes=40,
    salidas=[(14, 5)],
    muros=MURO_CON_PUERTA,
    rng=1,
    tipo_vecindad=TIPO_VECINDAD,
)

page = SolaraViz(
    modelo_inicial,
    components=[GrillaRecinto],
    model_params=model_params,
    name="Evacuación de multitudes",
)
