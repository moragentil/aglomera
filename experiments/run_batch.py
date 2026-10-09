"""Corridas Monte Carlo: repite cada escenario con distintas semillas y guarda
el historial completo de cada corrida en un CSV dentro de data/results/.

Cada comparación que se cita en el README y en el guion de la defensa es un
experimento con nombre (ver EXPERIMENTOS), así se puede regenerar con un
comando:

    python experiments/run_batch.py --listar
    python experiments/run_batch.py friccion
    python experiments/run_batch.py              # corre todos
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ_PROYECTO))

import pandas as pd  # noqa: E402
from mesa import batch_run  # noqa: E402

from src.model import EvacuacionModel  # noqa: E402

# mesa.batch_run itera cualquier lista que le pases para
# decidir qué "barrer". Si le pasaras salidas=[(19, 7)] tal cual, pensaría
# que (19, 7) son DOS valores para barrer (19 y 7), no una salida. Por eso
# cada configuración de salidas (y de muros) va envuelta en una lista extra:
# la lista de afuera es lo que barre mesa, cada elemento de adentro es una
# configuración completa que queda intacta. Un valor fijo también se escribe
# así: [[]] = "un solo valor: la lista vacía". Los números y los textos
# sueltos (ancho, tipo_vecindad) no necesitan el envoltorio.

# El escenario de app.py: sala partida por una pared con una puerta de una celda.
ALTO_SALA_CON_PUERTA = 10
SALA_CON_PUERTA = {
    "ancho": 15,
    "alto": ALTO_SALA_CON_PUERTA,
    "salidas": [[(14, 5)]],
    "muros": [[(7, y) for y in range(ALTO_SALA_CON_PUERTA) if y != 4]],
}

# Sala abierta con una salida en cada punta, para ver el efecto del pánico.
SALA_CON_DOS_SALIDAS = {
    "ancho": 20,
    "alto": 11,
    "salidas": [[(0, 5), (19, 5)]],
    "muros": [[]],
}

EXPERIMENTOS = {
    "salidas": {
        "descripcion": "Una salida central vs dos en los extremos, con 30, 60 y 90 agentes",
        "parametros": {
            "ancho": 20,
            "alto": 15,
            "muros": [[]],
            "salidas": [[(19, 7)], [(19, 0), (19, 14)]],
            "num_agentes": [30, 60, 90],
        },
        "repeticiones": 10,
        "pasos_maximos": 500,
    },
    "friccion": {
        "descripcion": "Efecto de la fricción en la sala con puerta (100 agentes)",
        "parametros": {
            **SALA_CON_PUERTA,
            "num_agentes": 100,
            "probabilidad_friccion": [0.0, 0.3, 0.6],
        },
        "repeticiones": 15,
        "pasos_maximos": 1000,
    },
    "vecindad": {
        "descripcion": "Von Neumann (4 direcciones) vs Moore (8) en la sala con puerta (100 agentes)",
        "parametros": {
            **SALA_CON_PUERTA,
            "num_agentes": 100,
            "tipo_vecindad": ["von_neumann", "moore"],
        },
        "repeticiones": 15,
        "pasos_maximos": 1000,
    },
    "panico": {
        "descripcion": "Efecto del pánico/manada en la sala de dos salidas (80 agentes)",
        "parametros": {
            **SALA_CON_DOS_SALIDAS,
            "num_agentes": 80,
            # 1.0 es el pánico total: se espera que no termine nunca, y por
            # eso pasos_maximos corta la corrida.
            "probabilidad_panico": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
        },
        "repeticiones": 20,
        "pasos_maximos": 1000,
    },
}


def correr_experimento(parametros, repeticiones, pasos_maximos, mostrar_progreso=True):
    """Corre todas las combinaciones de `parametros`, cada una con
    `repeticiones` semillas, y devuelve un DataFrame con una fila por paso."""
    resultados = batch_run(
        EvacuacionModel,
        # seguir a un peaton solo sirve para dibujarlo: en un batch es costo puro
        parameters={**parametros, "seguir_un_peaton": False},
        rng=range(repeticiones),
        max_steps=pasos_maximos,
        data_collection_period=1,  # guarda TODOS los pasos, no solo el final
        number_processes=1,  # secuencial: mas simple y sin sorpresas de multiprocessing
        display_progress=mostrar_progreso,
    )
    return pd.DataFrame(resultados)


def guardar_resultados(df, nombre):
    carpeta_resultados = RAIZ_PROYECTO / "data" / "results"
    carpeta_resultados.mkdir(parents=True, exist_ok=True)

    marca_de_tiempo = datetime.now().strftime("%Y%m%d_%H%M%S")
    salida_csv = carpeta_resultados / f"batch_{nombre}_{marca_de_tiempo}.csv"
    df.to_csv(salida_csv, index=False)
    return salida_csv


def main():
    parser = argparse.ArgumentParser(description="Corridas Monte Carlo del simulador de evacuación")
    parser.add_argument(
        "experimentos",
        nargs="*",
        help="nombres de los experimentos a correr (por defecto, todos)",
    )
    parser.add_argument("--listar", action="store_true", help="muestra los experimentos y sale")
    args = parser.parse_args()

    if args.listar:
        for nombre, experimento in EXPERIMENTOS.items():
            print(f"{nombre:10s} {experimento['descripcion']}")
        return

    desconocidos = [n for n in args.experimentos if n not in EXPERIMENTOS]
    if desconocidos:
        parser.error(f"experimento desconocido: {', '.join(desconocidos)} (usá --listar)")

    for nombre in args.experimentos or EXPERIMENTOS:
        experimento = EXPERIMENTOS[nombre]
        print(f"== {nombre}: {experimento['descripcion']}")
        df = correr_experimento(
            experimento["parametros"],
            experimento["repeticiones"],
            experimento["pasos_maximos"],
        )
        salida_csv = guardar_resultados(df, nombre)
        print(f"{len(df)} filas guardadas en {salida_csv}")


if __name__ == "__main__":
    main()
