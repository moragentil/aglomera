"""Visualización de la grilla con Solara.

En vez de pelear con el sistema nuevo de renderizado de Mesa (SpaceRenderer,
que solo sabe dibujar "agentes" y no conoce nuestros muros/salidas, que son
propiedades de celda, no agentes), dibujamos la grilla a mano con
matplotlib: el piso/muros/salida son una imagen categórica de fondo
(imshow), y los peatones se superponen encima como círculos (scatter), no
como pixeles de la grilla. Así un peatón nunca tapa el color de la celda
en la que está parado, y dos peatones en celdas vecinas se distinguen como
individuos en vez de fundirse en un bloque sólido del mismo color.

Además, si el modelo tiene un `peaton_seguido` (ver model.py), se le
dibuja encima el camino recorrido (una línea) y un marcador más grande
con borde violeta en su posición actual, para poder seguirlo a simple
vista entre toda la multitud.
"""

import matplotlib.pyplot as plt
import numpy as np
import solara
from matplotlib.colors import ListedColormap

from src.space import es_muro, es_salida

PISO, MURO, SALIDA = range(3)
COLORES = ListedColormap(["white", "black", "#2ca02c"])
COLOR_AGENTE_LIBRE = "#1f77b4"
COLOR_AGENTE_BLOQUEADO = "#d62728"
COLOR_SEGUIDO = "#9467bd"
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
    libres = ([], [])
    bloqueados = ([], [])
    for peaton in model.agents:
        if peaton.cell is None or peaton.seguido:
            continue  # el seguido se dibuja aparte, con su propio marcador
        destino = bloqueados if peaton.bloqueado else libres
        x, y = peaton.cell.coordinate
        destino[0].append(x)
        destino[1].append(y)
    return libres, bloqueados


def GrillaRecinto(model):
    grilla = _grilla_de_estado(model)
    (libres_x, libres_y), (bloqueados_x, bloqueados_y) = _posiciones_de_agentes(model)

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
    kwargs_circulo = dict(
        s=diametro_pt**2, edgecolors="white", linewidths=0.6, zorder=3
    )

    # Los bloqueados (quieren avanzar pero la mejor celda esta ocupada) se
    # pintan de otro color: es lo que deja ver el arqueo a simple vista,
    # como un amontonamiento rojo justo en la puerta angosta.
    ax.scatter(libres_x, libres_y, color=COLOR_AGENTE_LIBRE, **kwargs_circulo)
    ax.scatter(bloqueados_x, bloqueados_y, color=COLOR_AGENTE_BLOQUEADO, **kwargs_circulo)

    seguido = model.peaton_seguido
    if seguido is not None and seguido.historial:
        xs_historial = [c[0] for c in seguido.historial]
        ys_historial = [c[1] for c in seguido.historial]
        ax.plot(xs_historial, ys_historial, color=COLOR_SEGUIDO, linewidth=1.5, zorder=4)

        if seguido.cell is not None:
            color_relleno = COLOR_AGENTE_BLOQUEADO if seguido.bloqueado else COLOR_AGENTE_LIBRE
            ax.scatter(
                [seguido.cell.coordinate[0]],
                [seguido.cell.coordinate[1]],
                s=diametro_pt**2 * 1.8,
                color=color_relleno,
                edgecolors=COLOR_SEGUIDO,
                linewidths=2.5,
                zorder=5,
            )

    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(
        f"Paso {model.pasos_transcurridos} — "
        f"evacuados: {model.cantidad_evacuados()} / {len(model.agents)} — "
        f"bloqueados: {model.cantidad_bloqueados()}"
    )

    elemento = solara.FigureMatplotlib(fig)
    plt.close(fig)
    return elemento
