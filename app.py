"""Punto de entrada para `solara run app.py`: visualizador interactivo."""

from mesa.visualization import Slider, SolaraViz

from src.model import EvacuacionModel
from src.visualization import GrillaRecinto

model_params = {
    "ancho": 15,
    "alto": 10,
    "salidas": [(14, 5)],
    "muros": [],
    "rng": 1,
    "num_agentes": Slider("Cantidad de peatones", value=40, min=5, max=120, step=5),
}

modelo_inicial = EvacuacionModel(
    ancho=15, alto=10, num_agentes=40, salidas=[(14, 5)], muros=[], rng=1
)

page = SolaraViz(
    modelo_inicial,
    components=[GrillaRecinto],
    model_params=model_params,
    name="Evacuación de multitudes",
)
