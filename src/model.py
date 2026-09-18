"""Modelo de la simulación: crea el espacio y los peatones, y corre el loop.

Cada paso (step) tiene tres fases, porque la activación es sincrónica (a
diferencia de un simple agents.shuffle_do("step"), donde cada agente ya ve
lo que hicieron los anteriores en el mismo paso):

1. Evacuar: cualquiera parado en una celda de salida se va, sin conflicto
   posible (nadie mas quiere "salir" de esa celda).
2. Decidir: todos los peatones activos eligen, mirando la misma foto del
   mundo (nadie se movio todavia), a que celda querrian moverse.
3. Resolver: si dos o mas peatones quieren la MISMA celda vacia, es un
   conflicto real. Con probabilidad `probabilidad_friccion` nadie de ese
   grupo se mueve este paso (fricción); si no, se elige a uno al azar.

Esta separación es la que hace posible que la fricción tenga sentido:
bajo activación asincrónica (turno por turno) nunca hay dos peatones
compitiendo por la misma celda al mismo tiempo, porque el orden de turnos
ya resuelve la disputa de antemano.

Si `seguir_un_peaton` está activo (default), el primer peatón creado
queda marcado como `seguido` y el modelo le va agregando cada celda por
la que pasa a `peaton.historial`, para poder dibujar su recorrido en la
visualización.
"""

from mesa import Model
from mesa.datacollection import DataCollector

from src.agent import Peaton
from src.space import crear_espacio, es_muro, es_salida


class EvacuacionModel(Model):
    def __init__(
        self,
        ancho,
        alto,
        num_agentes,
        salidas,
        muros=None,
        rng=None,
        probabilidad_agresivo=0.0,
        probabilidad_friccion=0.0,
        tipo_vecindad="von_neumann",
        seguir_un_peaton=True,
    ):
        super().__init__(rng=rng)

        self.espacio = crear_espacio(
            ancho, alto, salidas, muros, random=self.random, tipo_vecindad=tipo_vecindad
        )
        self.pasos_transcurridos = 0
        self.probabilidad_friccion = probabilidad_friccion
        self.peaton_seguido = None

        self.datacollector = DataCollector(
            model_reporters={
                "evacuados": lambda m: m.cantidad_evacuados(),
                "restantes": lambda m: m.cantidad_restantes(),
                "bloqueados": lambda m: m.cantidad_bloqueados(),
            }
        )

        for i, celda in enumerate(self._elegir_celdas_iniciales(num_agentes)):
            agresivo = self.random.random() < probabilidad_agresivo
            seguido = seguir_un_peaton and i == 0
            peaton = Peaton(self, celda, agresivo=agresivo, seguido=seguido)
            if seguido:
                self.peaton_seguido = peaton

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

    def cantidad_bloqueados(self):
        return sum(1 for peaton in self.agents if peaton.bloqueado)

    def todos_evacuaron(self):
        return self.cantidad_restantes() == 0

    def step(self):
        for peaton in self.agents:
            peaton.evacuar_si_llego()

        pretendientes_por_celda = {}
        for peaton in self.agents:
            if peaton.evacuado:
                continue
            celda_deseada, hay_progreso_posible = peaton.decidir_movimiento()
            if celda_deseada is None:
                peaton.bloqueado = hay_progreso_posible
            else:
                pretendientes_por_celda.setdefault(celda_deseada, []).append(peaton)

        for celda, pretendientes in pretendientes_por_celda.items():
            hay_conflicto = len(pretendientes) > 1
            si_hay_friccion = hay_conflicto and self.random.random() < self.probabilidad_friccion
            ganador = None if si_hay_friccion else self.random.choice(pretendientes)

            for peaton in pretendientes:
                if peaton is ganador:
                    peaton.cell = celda
                    peaton.bloqueado = False
                    if peaton.seguido:
                        peaton.historial.append(celda.coordinate)
                else:
                    peaton.bloqueado = True

        self.pasos_transcurridos += 1
        self.datacollector.collect(self)
        if self.todos_evacuaron():
            self.running = False
