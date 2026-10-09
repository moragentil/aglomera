"""Agente peatón: regla de decisión de movimiento tipo autómata celular
(Blue & Adler, 2001).

La decisión es sincrónica: cada peatón elige a qué celda querría moverse
mirando la misma "foto" del mundo (nadie se movió todavía este paso), sin
saber qué van a elegir los demás. Quién se mueve de verdad se resuelve
después, a nivel del modelo (ver EvacuacionModel.step), porque dos
peatones pueden querer la misma celda vacía al mismo tiempo — ahí es
donde entra la fricción, que es lo que permite estudiar de verdad "faster
is slower" (Helbing, Farkas & Vicsek, 2000): más agresividad puede
generar más conflictos simultáneos, y con fricción, más conflictos
significan más turnos perdidos para todos.

El flag `bloqueado` (que fija el modelo, no el propio peatón) distingue
tres razones para no moverse: que no haya adonde mejorar (óptimo local,
nadie tiene la culpa), que la mejor celda ya estuviera ocupada por alguien
que no se mueve este paso, o que haya perdido un conflicto/la fricción
contra otro peatón que quería la misma celda vacía.

Un peatón `agresivo` no tolera esperar: si su mejor opción está ocupada,
en vez de quedarse quieto elige cualquier celda libre vecina como destino
deseado, aunque no lo acerque a la salida — con el riesgo de terminar en
un conflicto con otro peatón que quiere esa misma celda lateral.

Un peatón `seguido` guarda en `historial` cada celda por la que pasó (el
modelo se encarga de agregarla cuando lo mueve), para poder dibujar su
recorrido completo en la visualización.

Con probabilidad `probabilidad_panico` (parámetro del modelo, no del
peatón), en un paso dado un peatón no piensa por sí mismo: en vez de
seguir el floor field, mira quién tiene cerca (radio
`RADIO_DE_PERCEPCION_DE_MANADA`) y se mueve hacia el centro de esa
multitud — imita a la manada, aunque eso signifique ignorar una salida
más cercana y vacía. Si no hay nadie cerca, no tiene manada que seguir y
decide racionalmente como cualquiera. Es el mecanismo de "herding" que
motiva el nivel ambicioso del TP.

Ojo con esto, porque no es un detalle menor: el pánico se sortea de
nuevo en CADA paso, para cada peatón — no es una etiqueta fija ("este
peatón es panicoso para siempre"). La primera version que probamos
hacia justamente eso, y un par de peatones panicosos cerca de una
salida terminaban persiguiendose mutuamente en un circulo infinito, sin
cruzar nunca: como ninguno de los dos "se le pasaba el panico", no
habia forma de que la simulacion terminara. Sorteándolo paso a paso, en
algun momento alguno de los dos actua racionalmente y rompe el ciclo.
"""

from mesa.discrete_space import CellAgent

from src.space import distancia_a_salida, es_muro, es_salida

RADIO_DE_PERCEPCION_DE_MANADA = 3


class Peaton(CellAgent):
    def __init__(self, model, cell, agresivo=False, seguido=False):
        super().__init__(model)
        self.cell = cell
        self.evacuado = False
        self.bloqueado = False
        self.agresivo = agresivo
        self.seguido = seguido
        self.historial = [cell.coordinate] if seguido else []
        self.salida_usada = None

    def evacuar_si_llego(self):
        """Si esta parado en una celda de salida, evacua y la libera.

        Guarda en salida_usada la coordenada de esa salida, para poder medir
        cuanta gente uso cada una."""
        if not self.evacuado and es_salida(self.cell):
            self.evacuado = True
            self.salida_usada = self.cell.coordinate
            self.cell = None
            self.bloqueado = False

    def decidir_movimiento(self):
        """Decide a que celda querria moverse este paso, sin moverse aun.

        Devuelve (celda_deseada, hay_progreso_posible). celda_deseada es
        None si prefiere quedarse quieto. El modelo es quien decide, mas
        adelante, si ese deseo se concreta o choca con el de otro peaton.
        """
        if self.evacuado:
            return None, False

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

        if self.model.random.random() < self.model.probabilidad_panico:
            celda_hacia_la_manada = self._elegir_celda_siguiendo_a_la_manada(candidatas_libres)
            if celda_hacia_la_manada is not None:
                return celda_hacia_la_manada, hay_progreso_posible

        mejor_distancia_libre = min(distancia_a_salida(c) for c in candidatas_libres)
        if mejor_distancia_libre >= distancia_actual:
            if self.agresivo:
                # no tolera esperar: prueba con cualquier celda libre,
                # aunque no lo acerque (y aunque eso lo meta en un
                # conflicto nuevo con otro peaton que la quiera tambien).
                return self.model.random.choice(candidatas_libres), hay_progreso_posible
            return None, hay_progreso_posible

        mejores = [
            c for c in candidatas_libres if distancia_a_salida(c) == mejor_distancia_libre
        ]
        return self.model.random.choice(mejores), hay_progreso_posible

    def _elegir_celda_siguiendo_a_la_manada(self, candidatas_libres):
        """De las candidatas libres, la que mas acerca al centro de la
        multitud cercana (no necesariamente a la salida). Devuelve None si
        no hay nadie mas dentro del radio de percepcion."""
        otros_peatones_cerca = [
            celda.coordinate
            for celda in self.cell.get_neighborhood(radius=RADIO_DE_PERCEPCION_DE_MANADA)
            for agente in celda.agents
            if agente is not self and not agente.evacuado
        ]
        if not otros_peatones_cerca:
            return None

        centro_x = sum(x for x, _ in otros_peatones_cerca) / len(otros_peatones_cerca)
        centro_y = sum(y for _, y in otros_peatones_cerca) / len(otros_peatones_cerca)

        def distancia_al_centro_de_la_manada(celda):
            x, y = celda.coordinate
            return (x - centro_x) ** 2 + (y - centro_y) ** 2

        mejor_distancia = min(distancia_al_centro_de_la_manada(c) for c in candidatas_libres)
        mejores = [
            c for c in candidatas_libres
            if distancia_al_centro_de_la_manada(c) == mejor_distancia
        ]
        return self.model.random.choice(mejores)
