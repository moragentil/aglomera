"""Agente peatón: regla de movimiento tipo autómata celular (Blue & Adler, 2001).

En cada paso, el peatón mira sus celdas vecinas transitables y se mueve a la
que esté libre y tenga menor distancia al floor field (ver src/space.py). Si
ninguna vecina lo acerca a la salida, o las que lo acercan están todas
ocupadas, se queda quieto ese paso: así es como emergen los cuellos de
botella, sin que nadie programe "hacer cola" explícitamente.
"""

from mesa.discrete_space import CellAgent

from src.space import distancia_a_salida, es_muro, es_salida


class Peaton(CellAgent):
    def __init__(self, model, cell):
        super().__init__(model)
        self.cell = cell
        self.evacuado = False

    def step(self):
        if self.evacuado:
            return

        if es_salida(self.cell):
            self.evacuado = True
            self.cell = None  # libera la celda de salida para el que sigue
            return

        siguiente_celda = self._elegir_siguiente_celda()
        if siguiente_celda is not None:
            self.cell = siguiente_celda

    def _elegir_siguiente_celda(self):
        distancia_actual = distancia_a_salida(self.cell)

        candidatas = [
            vecina
            for vecina in self.cell.neighborhood
            if not es_muro(vecina) and not vecina.is_full
        ]
        if not candidatas:
            return None

        mejor_distancia = min(distancia_a_salida(c) for c in candidatas)
        if mejor_distancia >= distancia_actual:
            return None  # ninguna vecina disponible lo acerca a la salida

        mejores = [c for c in candidatas if distancia_a_salida(c) == mejor_distancia]
        return self.model.random.choice(mejores)
