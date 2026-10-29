"""Zonas de un recinto: sectores en los que un sensor cuenta personas.

Un sensor real no sabe de coordenadas: cuenta cuánta gente hay en un sector
("la zona B1 tiene 12 personas"). Este módulo hace de traductor entre las dos
cosas: parte el recinto en una grilla de sectores con nombre, y dado un conteo
por sector decide en qué celdas concretas poner a esa gente.

Los sectores se nombran como en una planilla: la letra es la columna (A, B,
C...) y el número es la fila contada desde arriba (1, 2...). Por ejemplo, en un
recinto partido en 3 columnas y 2 filas: A1 B1 C1 / A2 B2 C2.

Este módulo no conoce el modelo, la web ni los sensores: solo geometría.
"""

import random
from dataclasses import dataclass

MAXIMO_DE_COLUMNAS = 26  # una letra por columna


@dataclass(frozen=True)
class Zona:
    id: str
    columna: int  # primera columna del sector, de izquierda a derecha
    fila: int  # primera fila del sector, de arriba hacia abajo
    ancho: int
    alto: int
    celdas: tuple  # celdas transitables (x, y) del modelo: sin paredes ni salidas

    @property
    def capacidad(self):
        return len(self.celdas)


def nombre_de_zona(columna, fila):
    return f"{chr(ord('A') + columna)}{fila + 1}"


def _limites(total, partes):
    """Dónde empieza cada parte al repartir `total` celdas en `partes` partes
    lo más parejas posible: sin huecos ni solapamientos."""
    return [round(i * total / partes) for i in range(partes + 1)]


def zonas_en_grilla(recinto, columnas, filas):
    """Parte el recinto en columnas x filas sectores, de arriba a la izquierda
    hacia abajo a la derecha. Falla con ValueError si no se puede."""
    if not 1 <= columnas <= min(MAXIMO_DE_COLUMNAS, recinto.ancho):
        raise ValueError(
            f"Las columnas deben estar entre 1 y {min(MAXIMO_DE_COLUMNAS, recinto.ancho)} "
            f"(el recinto mide {recinto.ancho} de ancho); pediste {columnas}."
        )
    if not 1 <= filas <= recinto.alto:
        raise ValueError(f"Las filas deben estar entre 1 y {recinto.alto}; pediste {filas}.")

    no_transitables = set(recinto.muros) | set(recinto.salidas)
    x_limites = _limites(recinto.ancho, columnas)
    y_limites = _limites(recinto.alto, filas)

    zonas = []
    for fila in range(filas):
        for columna in range(columnas):
            x0, x1 = x_limites[columna], x_limites[columna + 1]
            y0, y1 = y_limites[fila], y_limites[fila + 1]
            celdas = tuple(
                (x, recinto.alto - 1 - fila_pantalla)  # el modelo cuenta y hacia arriba
                for fila_pantalla in range(y0, y1)
                for x in range(x0, x1)
                if (x, recinto.alto - 1 - fila_pantalla) not in no_transitables
            )
            zonas.append(Zona(nombre_de_zona(columna, fila), x0, y0, x1 - x0, y1 - y0, celdas))
    return zonas


def ubicar_por_zona(zonas, conteos, permitidas=None, azar=None):
    """Elige en qué celdas poner a la gente medida en cada zona.

    `conteos` es {id de zona: personas}. `permitidas` (opcional) es el conjunto
    de celdas donde se puede poner a alguien, por ejemplo las que tienen camino
    a una salida. Devuelve (posiciones, avisos): las celdas elegidas, sin
    repetir, y un texto por cada zona donde no entró todo lo medido.
    """
    azar = azar or random.Random()
    ids = {zona.id for zona in zonas}
    posiciones, avisos = [], []

    for zona in zonas:  # en orden: el resultado no depende del orden del diccionario
        personas = conteos.get(zona.id, 0)
        if personas <= 0:
            continue
        candidatas = [c for c in zona.celdas if permitidas is None or c in permitidas]
        entran = min(personas, len(candidatas))
        if entran < personas:
            avisos.append(
                f"Zona {zona.id}: se midieron {personas} personas pero solo hay lugar para "
                f"{len(candidatas)}; se ubicaron {entran}."
            )
        posiciones.extend(azar.sample(candidatas, entran))

    desconocidas = sorted(set(conteos) - ids)
    if desconocidas:
        avisos.append(f"Se ignoraron zonas que no existen en este recinto: {', '.join(desconocidas)}.")
    return posiciones, avisos
