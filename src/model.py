"""Modelo de la simulación: crea el espacio y los peatones, y corre el loop.

Cada paso (step) activa a todos los peatones en orden aleatorio (activación
asincrónica: uno se mueve, "libera" o "toma" una celda, y el siguiente ya ve
ese cambio — es lo que hace que los cuellos de botella sean realistas).
Las métricas agregadas se registran con el DataCollector de Mesa.
"""

from mesa import Model
from mesa.datacollection import DataCollector

from src.agent import Peaton
from src.space import crear_espacio, es_muro, es_salida


class EvacuacionModel(Model):
    def __init__(self, ancho, alto, num_agentes, salidas, muros=None, rng=None):
        super().__init__(rng=rng)

        self.espacio = crear_espacio(ancho, alto, salidas, muros, random=self.random)
        self.pasos_transcurridos = 0

        self.datacollector = DataCollector(
            model_reporters={
                "evacuados": lambda m: m.cantidad_evacuados(),
                "restantes": lambda m: m.cantidad_restantes(),
            }
        )

        for celda in self._elegir_celdas_iniciales(num_agentes):
            Peaton(self, celda)

        self.datacollector.collect(self)

    def _elegir_celdas_iniciales(self, num_agentes):
        disponibles = [
            celda
            for celda in self.espacio.all_cells
            if not es_muro(celda) and not es_salida(celda)
        ]
        if num_agentes > len(disponibles):
            raise ValueError(
                f"Pediste {num_agentes} agentes pero solo hay "
                f"{len(disponibles)} celdas transitables disponibles."
            )
        return self.random.sample(disponibles, num_agentes)

    def cantidad_evacuados(self):
        return sum(1 for peaton in self.agents if peaton.evacuado)

    def cantidad_restantes(self):
        return len(self.agents) - self.cantidad_evacuados()

    def todos_evacuaron(self):
        return self.cantidad_restantes() == 0

    def step(self):
        self.agents.shuffle_do("step")
        self.pasos_transcurridos += 1
        self.datacollector.collect(self)
        if self.todos_evacuaron():
            self.running = False
