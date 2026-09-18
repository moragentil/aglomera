"""Agente peatón: regla de movimiento tipo autómata celular (Blue & Adler, 2001).

En cada paso, el peatón mira sus celdas vecinas transitables y se mueve a la
que esté libre y tenga menor distancia al floor field (ver src/space.py). Si
ninguna vecina lo acerca a la salida, o las que lo acercan están todas
ocupadas, se queda quieto ese paso: así es como emergen los cuellos de
botella, sin que nadie programe "hacer cola" explícitamente.

El flag `bloqueado` distingue las dos razones posibles para no moverse:
que no haya adonde mejorar (óptimo local, nadie tiene la culpa) o que sí
haya una celda mejor pero esté ocupada (congestión real, causada por otro
peatón). Esa segunda es la que interesa para medir el fenómeno de arqueo.
"""

from mesa.discrete_space import CellAgent

from src.space import distancia_a_salida, es_muro, es_salida


class Peaton(CellAgent):
    def __init__(self, model, cell):
        super().__init__(model)
        self.cell = cell
        self.evacuado = False
        self.bloqueado = False

    def step(self):
        if self.evacuado:
            self.bloqueado = False
            return

        if es_salida(self.cell):
            self.evacuado = True
            self.cell = None  # libera la celda de salida para el que sigue
            self.bloqueado = False
            return

        siguiente_celda, bloqueado = self._elegir_siguiente_celda()
        self.bloqueado = bloqueado
        if siguiente_celda is not None:
            self.cell = siguiente_celda

    def _elegir_siguiente_celda(self):
        distancia_actual = distancia_a_salida(self.cell)
        vecinas_transitables = [v for v in self.cell.neighborhood if not es_muro(v)]

        mejor_distancia_alcanzable = min(
            (distancia_a_salida(v) for v in vecinas_transitables),
            default=distancia_actual,
        )
        hay_progreso_posible = mejor_distancia_alcanzable < distancia_actual

        candidatas_libres = [v for v in vecinas_transitables if not v.is_full]
        if not candidatas_libres:
            return None, hay_progreso_posible

        mejor_distancia_libre = min(distancia_a_salida(c) for c in candidatas_libres)
        if mejor_distancia_libre >= distancia_actual:
            # ninguna vecina libre lo acerca. Si igual habia una mejor
            # ocupada, es congestion (bloqueado); si no la habia ni ocupada
            # ni libre, es un optimo local sin culpables.
            return None, hay_progreso_posible

        mejores = [
            c for c in candidatas_libres if distancia_a_salida(c) == mejor_distancia_libre
        ]
        return self.model.random.choice(mejores), False
