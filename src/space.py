"""Espacio físico del recinto: grilla, salidas, muros y floor field.

El floor field (Blue & Adler, 2001) es un mapa estático de distancia mínima
(en celdas) de cada celda transitable a la salida más cercana. Se calcula
una sola vez con un BFS multi-fuente desde todas las salidas; después cada
agente lo consulta en cada paso en vez de recalcular un camino propio.
"""

from collections import deque

from mesa.discrete_space import OrthogonalMooreGrid, OrthogonalVonNeumannGrid

GRILLAS_POR_TIPO_DE_VECINDAD = {
    "von_neumann": OrthogonalVonNeumannGrid,  # 4 vecinas: arriba/abajo/izq/der
    "moore": OrthogonalMooreGrid,  # 8 vecinas: suma las 4 diagonales
}


def crear_espacio(ancho, alto, salidas, muros=None, random=None, tipo_vecindad="von_neumann"):
    """Crea la grilla y marca salidas/muros como propiedades de cada celda.

    `tipo_vecindad` controla si los peatones pueden moverse en diagonal
    ("moore") o solo en las 4 direcciones ortogonales ("von_neumann", el
    default). Con diagonales, la distancia del floor field se parece más a
    la distancia "Chebyshev" que a la "Manhattan": un obstáculo de una sola
    celda casi nunca fuerza un desvío real, porque se lo esquiva gratis en
    diagonal. Eso vuelve los cuellos de botella menos severos.
    """
    salidas = set(salidas)
    muros = set(muros or [])

    clase_de_grilla = GRILLAS_POR_TIPO_DE_VECINDAD[tipo_vecindad]
    espacio = clase_de_grilla((ancho, alto), torus=False, capacity=1, random=random)

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
