"""Corridas Monte Carlo: repite cada escenario con distintas semillas,
variando cantidad de agentes y configuración de salidas, para comparar
tiempos de evacuación. Guarda todo en un CSV en data/results/.

Se puede correr directo con `python experiments/run_batch.py`.
"""

import sys
from datetime import datetime
from pathlib import Path

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ_PROYECTO))

import pandas as pd  # noqa: E402
from mesa import batch_run  # noqa: E402

from src.model import EvacuacionModel  # noqa: E402

UNA_SALIDA_CENTRADA = [(19, 7)]
DOS_SALIDAS_EN_LOS_EXTREMOS = [(19, 0), (19, 14)]

# mesa.batch_run itera cualquier lista que le pases para
# decidir qué "barrer". Si le pasaras salidas=[(19, 7)] tal cual, pensaría
# que (19, 7) son DOS valores para barrer (19 y 7), no una salida. Por eso
# cada configuración de salidas va envuelta en una lista extra: la lista
# de afuera es lo que barre mesa, cada elemento de adentro es una
# configuración completa (una lista de coordenadas) que queda intacta.
PARAMETROS = {
    "ancho": 20,
    "alto": 15,
    "muros": [[]],  # sin muros por ahora; [[]] = "un solo valor fijo: []"
    "salidas": [UNA_SALIDA_CENTRADA, DOS_SALIDAS_EN_LOS_EXTREMOS],
    "num_agentes": [30, 60, 90],
}

REPETICIONES_POR_COMBINACION = 10
PASOS_MAXIMOS = 500


def main():
    resultados = batch_run(
        EvacuacionModel,
        parameters=PARAMETROS,
        rng=range(REPETICIONES_POR_COMBINACION),
        max_steps=PASOS_MAXIMOS,
        data_collection_period=1,  # guarda TODOS los pasos, no solo el final
        number_processes=1,  # secuencial: mas simple y sin sorpresas de multiprocessing
    )

    df = pd.DataFrame(resultados)

    carpeta_resultados = RAIZ_PROYECTO / "data" / "results"
    carpeta_resultados.mkdir(parents=True, exist_ok=True)

    marca_de_tiempo = datetime.now().strftime("%Y%m%d_%H%M%S")
    salida_csv = carpeta_resultados / f"batch_{marca_de_tiempo}.csv"
    df.to_csv(salida_csv, index=False)

    print(f"{len(df)} filas guardadas en {salida_csv}")


if __name__ == "__main__":
    main()
