"""Visualización de la grilla con Solara.

En vez de pelear con el sistema nuevo de renderizado de Mesa (SpaceRenderer,
que solo sabe dibujar "agentes" y no conoce nuestros muros/salidas, que son
propiedades de celda, no agentes), dibujamos la grilla a mano con
matplotlib: el piso/muros/salida son una imagen categórica de fondo
(imshow), y los peatones se superponen encima como círculos (scatter), no
como pixeles de la grilla. Así un peatón nunca tapa el color de la celda
en la que está parado, y dos peatones en celdas vecinas se distinguen como
individuos en vez de fundirse en un bloque sólido del mismo color.
"""

import matplotlib.pyplot as plt
import numpy as np
import solara
from matplotlib.colors import ListedColormap

from src.space import es_muro, es_salida

PISO, MURO, SALIDA = range(3)
COLORES = ListedColormap(["white", "black", "#2ca02c"])
COLOR_AGENTE = "#1f77b4"
FRACCION_DIAMETRO_CELDA = 0.75


def _grilla_de_estado(model):
    ancho, alto = model.espacio.dimensions
    grilla = np.full((alto, ancho), PISO)

    for celda in model.espacio.all_cells:
        x, y = celda.coordinate
        if es_muro(celda):
            grilla[y, x] = MURO
        elif es_salida(celda):
            grilla[y, x] = SALIDA

    return grilla


def _posiciones_de_agentes(model):
    xs, ys = [], []
    for peaton in model.agents:
        if peaton.cell is not None:
            x, y = peaton.cell.coordinate
            xs.append(x)
            ys.append(y)
    return xs, ys


def GrillaRecinto(model):
    grilla = _grilla_de_estado(model)
    xs, ys = _posiciones_de_agentes(model)

    fig, ax = plt.subplots()
    ax.imshow(grilla, cmap=COLORES, vmin=0, vmax=2, origin="lower")

    # El tamaño de los círculos en scatter se define en puntos, no en
    # unidades de la grilla, así que hay que convertir: cuánto mide en
    # pixeles una celda de la grilla en esta figura en particular, y de ahí
    # a puntos (72 puntos = 1 pulgada). fig.canvas.draw() fuerza a
    # matplotlib a calcular el layout antes de poder preguntar eso.
    fig.canvas.draw()
    ancho_celda_px = (
        ax.transData.transform((1, 0))[0] - ax.transData.transform((0, 0))[0]
    )
    diametro_pt = ancho_celda_px * (72 / fig.dpi) * FRACCION_DIAMETRO_CELDA

    ax.scatter(
        xs,
        ys,
        s=diametro_pt**2,
        color=COLOR_AGENTE,
        edgecolors="white",
        linewidths=0.6,
        zorder=3,
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
