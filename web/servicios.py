"""La lógica de la app web, sin nada de HTTP: correr una simulación paso a
paso, convertir su estado a datos simples y comparar recintos con varias
semillas. Las rutas (app.py) solo traducen pedidos a llamadas de acá.

Convención de coordenadas: el modelo usa y hacia ARRIBA (como el plano de
texto visto de abajo hacia arriba); un navegador dibuja con y hacia ABAJO.
Todo lo que sale de acá usa "fila": 0 es la fila de arriba, igual que el
índice de `filas` de un plano. Así el front no tiene que convertir nada.
"""

import math
import random
import statistics
import threading
from collections import OrderedDict
from dataclasses import dataclass
from uuid import uuid4

from src.model import EvacuacionModel
from src.space import crear_espacio, distancia_a_salida, es_muro, es_salida

MAXIMO_DE_SESIONES = 32
PUNTOS_MAXIMOS_DE_CURVA = 200


# ---------------------------------------------------------------- simulación


def celdas_alcanzables(recinto, tipo_vecindad):
    """Las celdas donde se puede ubicar a alguien: transitables y con camino a
    alguna salida (depende de la vecindad: con diagonales se llega a más)."""
    espacio = crear_espacio(
        **recinto.como_parametros(), tipo_vecindad=tipo_vecindad, random=random.Random(0)
    )
    return {
        celda.coordinate
        for celda in espacio.all_cells
        if not es_muro(celda) and not es_salida(celda) and distancia_a_salida(celda) != float("inf")
    }


def crear_modelo(recinto, parametros, semilla, seguir_un_peaton, posiciones_iniciales=None):
    """Un EvacuacionModel listo para correr. Falla con ValueError si hay más
    peatones pedidos que celdas con camino a una salida. Con
    `posiciones_iniciales`, los peatones se ubican ahí y `num_agentes` no se usa."""
    return EvacuacionModel(
        **recinto.como_parametros(),
        num_agentes=parametros.num_agentes,
        rng=semilla,
        tipo_vecindad=parametros.tipo_vecindad,
        probabilidad_agresivo=parametros.probabilidad_agresivo,
        probabilidad_friccion=parametros.probabilidad_friccion,
        probabilidad_panico=parametros.probabilidad_panico,
        seguir_un_peaton=seguir_un_peaton,
        posiciones_iniciales=posiciones_iniciales,
    )


def avanzar(modelo, cantidad):
    """Corre hasta `cantidad` pasos; se detiene antes si todos evacuaron."""
    for _ in range(cantidad):
        if not modelo.running:
            break
        modelo.step()


def estado_de_simulacion(modelo):
    """Lo que el navegador necesita para dibujar el paso actual."""
    alto = modelo.espacio.dimensions[1]

    agentes = []  # [columna, fila, 1 si esta bloqueado]
    for peaton in modelo.agents:
        if peaton.cell is None or peaton.seguido:
            continue  # los evacuados ya no estan; el seguido se manda aparte
        x, y = peaton.cell.coordinate
        agentes.append([x, alto - 1 - y, 1 if peaton.bloqueado else 0])

    seguido = None
    if modelo.peaton_seguido is not None:
        peaton = modelo.peaton_seguido
        seguido = {
            "evacuado": peaton.cell is None,
            "bloqueado": peaton.bloqueado,
            "historial": [[x, alto - 1 - y] for (x, y) in peaton.historial],
        }

    return {
        "paso": modelo.pasos_transcurridos,
        "total": len(modelo.agents),
        "evacuados": modelo.cantidad_evacuados(),
        "bloqueados": modelo.cantidad_bloqueados(),
        "terminada": modelo.todos_evacuaron(),
        "agentes": agentes,
        "seguido": seguido,
    }


class Sesiones:
    """Las simulaciones en curso, por id. Guarda a lo sumo `maximo`: al pasarse
    descarta la más vieja, así una pestaña olvidada no acumula memoria."""

    def __init__(self, maximo=MAXIMO_DE_SESIONES):
        self._maximo = maximo
        self._modelos = OrderedDict()
        self._candado = threading.Lock()

    def crear(self, modelo):
        sesion_id = uuid4().hex[:12]
        with self._candado:
            self._modelos[sesion_id] = modelo
            while len(self._modelos) > self._maximo:
                self._modelos.popitem(last=False)
        return sesion_id

    def obtener(self, sesion_id):
        with self._candado:
            return self._modelos.get(sesion_id)

    def eliminar(self, sesion_id):
        with self._candado:
            return self._modelos.pop(sesion_id, None) is not None


# --------------------------------------------------------------- comparación


@dataclass
class Corrida:
    pasos: int
    termino: bool
    evacuados_por_paso: list  # evacuados en el paso 0, 1, 2...
    congestion_maxima: int  # el mayor numero de bloqueados a la vez


def correr_una_vez(recinto, parametros, semilla, pasos_maximos):
    modelo = crear_modelo(recinto, parametros, semilla, seguir_un_peaton=False)
    evacuados = [modelo.cantidad_evacuados()]
    congestion = modelo.cantidad_bloqueados()
    while modelo.running and modelo.pasos_transcurridos < pasos_maximos:
        modelo.step()
        evacuados.append(modelo.cantidad_evacuados())
        congestion = max(congestion, modelo.cantidad_bloqueados())
    return Corrida(modelo.pasos_transcurridos, modelo.todos_evacuaron(), evacuados, congestion)


def percentil(valores, p):
    """Percentil p (0 a 100) por el método del rango más cercano."""
    ordenados = sorted(valores)
    posicion = max(1, math.ceil(p / 100 * len(ordenados)))
    return ordenados[posicion - 1]


def _curva_promedio(corridas, total):
    """Evacuados promedio en cada paso. Una corrida que ya terminó se queda en
    el total (si no, el promedio se inclinaría hacia las corridas lentas)."""
    largo = max(len(c.evacuados_por_paso) for c in corridas)
    promedio = []
    for paso in range(largo):
        suma = 0
        for c in corridas:
            serie = c.evacuados_por_paso
            suma += serie[paso] if paso < len(serie) else serie[-1]
        promedio.append(suma / len(corridas))

    # a lo sumo PUNTOS_MAXIMOS_DE_CURVA puntos, siempre incluyendo el ultimo
    salto = max(1, math.ceil(len(promedio) / PUNTOS_MAXIMOS_DE_CURVA))
    pasos = list(range(0, len(promedio), salto))
    if pasos[-1] != len(promedio) - 1:
        pasos.append(len(promedio) - 1)
    return {"pasos": pasos, "evacuados": [round(promedio[p], 2) for p in pasos], "total": total}


def resumen_de_recinto(etiqueta, recinto, corridas, total):
    pasos_de_las_que_terminaron = [c.pasos for c in corridas if c.termino]
    resumen = {
        "etiqueta": etiqueta,
        "ancho": recinto.ancho,
        "alto": recinto.alto,
        "salidas": len(recinto.salidas),
        "corridas": len(corridas),
        "terminaron": len(pasos_de_las_que_terminaron),
        "pasos_media": None,
        "pasos_desvio": None,
        "pasos_p95": None,
        "congestion_maxima_media": round(statistics.mean(c.congestion_maxima for c in corridas), 1),
        "congestion_maxima_pct": round(
            100 * statistics.mean(c.congestion_maxima for c in corridas) / total, 1
        ),
        "curva": _curva_promedio(corridas, total),
    }
    if pasos_de_las_que_terminaron:
        resumen["pasos_media"] = round(statistics.mean(pasos_de_las_que_terminaron), 1)
        resumen["pasos_desvio"] = round(
            statistics.stdev(pasos_de_las_que_terminaron) if len(pasos_de_las_que_terminaron) > 1 else 0.0, 1
        )
        resumen["pasos_p95"] = percentil(pasos_de_las_que_terminaron, 95)
    return resumen


def hallazgo(resumenes):
    """Qué recinto evacúa más rápido y cuánto. Solo compara los recintos en los
    que TODAS las corridas terminaron: si algunas no terminaron, el promedio de
    pasos no es comparable. None si no hay al menos dos comparables."""
    comparables = [r for r in resumenes if r["terminaron"] == r["corridas"]]
    if len(comparables) < 2:
        return None
    mejor = min(comparables, key=lambda r: r["pasos_media"])
    peor = max(comparables, key=lambda r: r["pasos_media"])
    if mejor is peor or peor["pasos_media"] == 0:
        return None
    return {
        "mejor": mejor["etiqueta"],
        "peor": peor["etiqueta"],
        "pasos_ahorrados": round(peor["pasos_media"] - mejor["pasos_media"], 1),
        "mejora_pct": round(100 * (peor["pasos_media"] - mejor["pasos_media"]) / peor["pasos_media"], 1),
    }


def comparar(planos, semillas, parametros, pasos_maximos):
    """`planos` es una lista de (etiqueta, Recinto). Cada recinto corre con las
    semillas 0..semillas-1, las mismas para todos: la única diferencia entre
    las corridas de dos recintos es el recinto."""
    resumenes = []
    for etiqueta, recinto in planos:
        corridas = [
            correr_una_vez(recinto, parametros, semilla, pasos_maximos) for semilla in range(semillas)
        ]
        resumenes.append(resumen_de_recinto(etiqueta, recinto, corridas, parametros.num_agentes))
    return {
        "semillas": list(range(semillas)),
        "pasos_maximos": pasos_maximos,
        "resultados": resumenes,
        "hallazgo": hallazgo(resumenes),
    }
