"""Espacio físico del recinto: grilla, salidas, muros y floor field.

El floor field (Blue & Adler, 2001) es un mapa estático de distancia mínima
(en celdas) de cada celda transitable a la salida más cercana. Se calcula
una sola vez con un BFS multi-fuente desde todas las salidas; después cada
agente lo consulta en cada paso en vez de recalcular un camino propio.
"""

from collections import deque

from mesa.discrete_space import OrthogonalVonNeumannGrid


def crear_espacio(ancho, alto, salidas, muros=None, random=None):
    """Crea la grilla y marca salidas/muros como propiedades de cada celda."""
    salidas = set(salidas)
    muros = set(muros or [])

    espacio = OrthogonalVonNeumannGrid(
        (ancho, alto), torus=False, capacity=1, random=random
    )

    for celda in espacio.all_cells:
        celda.properties["es_salida"] = celda.coordinate in salidas
        celda.properties["es_muro"] = celda.coordinate in muros

    _calcular_floor_field(espacio)
    return espacio


def es_salida(celda):
    return celda.properties.get("es_salida", False)


def es_muro(celda):
    return celda.properties.get("es_muro", False)


def distancia_a_salida(celda):
    return celda.properties.get("distancia_a_salida", float("inf"))


def _calcular_floor_field(espacio):
    visitadas = set()
    cola = deque()

    for celda in espacio.all_cells:
        if es_salida(celda):
            celda.properties["distancia_a_salida"] = 0
            visitadas.add(celda.coordinate)
            cola.append(celda)

    while cola:
        actual = cola.popleft()
        for vecina in actual.neighborhood:
            if vecina.coordinate in visitadas or es_muro(vecina):
                continue
            vecina.properties["distancia_a_salida"] = distancia_a_salida(actual) + 1
            visitadas.add(vecina.coordinate)
            cola.append(vecina)
