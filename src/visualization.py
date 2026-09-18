"""Visualización de la grilla con Solara.

En vez de pelear con el sistema nuevo de renderizado de Mesa (SpaceRenderer,
que solo sabe dibujar "agentes" y no conoce nuestros muros/salidas, que son
propiedades de celda, no agentes), dibujamos la grilla a mano como una
imagen categórica con matplotlib: cada celda es un pixel de un color según
su estado. Es más simple y más fácil de verificar visualmente.
"""

import matplotlib.pyplot as plt
import numpy as np
import solara
from matplotlib.colors import ListedColormap
from matplotlib.patches import Rectangle

from src.space import es_muro, es_salida

PISO, MURO, SALIDA, AGENTE = range(4)
COLORES = ListedColormap(["white", "black", "#2ca02c", "#1f77b4"])
COLOR_BORDE_SALIDA = "#146c2e"


def _grilla_de_estado(model):
    ancho, alto = model.espacio.dimensions
    grilla = np.full((alto, ancho), PISO)
    coordenadas_de_salida = []

    for celda in model.espacio.all_cells:
        x, y = celda.coordinate
        if es_muro(celda):
            grilla[y, x] = MURO
        elif es_salida(celda):
            grilla[y, x] = SALIDA
            coordenadas_de_salida.append((x, y))

    for peaton in model.agents:
        if peaton.cell is not None:
            x, y = peaton.cell.coordinate
            grilla[y, x] = AGENTE

    return grilla, coordenadas_de_salida


def GrillaRecinto(model):
    grilla, coordenadas_de_salida = _grilla_de_estado(model)

    fig, ax = plt.subplots()
    ax.imshow(grilla, cmap=COLORES, vmin=0, vmax=3, origin="lower")

    # El peatón se pinta encima de la salida y la tapa (mismo pixel). El
    # contorno se dibuja aparte, por arriba de todo, para que la salida
    # siga siendo identificable aunque haya alguien parado ahí.
    for x, y in coordenadas_de_salida:
        ax.add_patch(
            Rectangle(
                (x - 0.5, y - 0.5),
                1,
                1,
                fill=False,
                edgecolor=COLOR_BORDE_SALIDA,
                linewidth=2.5,
            )
        )

    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(
        f"Paso {model.pasos_transcurridos} — "
        f"evacuados: {model.cantidad_evacuados()} / {len(model.agents)}"
    )

    elemento = solara.FigureMatplotlib(fig)
    plt.close(fig)
    return elemento
