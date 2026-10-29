import random
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from iot.simulador_sensores import (
    construir_mensaje,
    conteos_en_un_instante,
    pesos_del_escenario,
    repartir,
)
from web.app import crear_app


def test_reparte_todo_el_total_en_proporcion_a_los_pesos():
    assert repartir(10, [1, 1], [100, 100]) == [5, 5]
    assert repartir(10, [3, 1], [100, 100]) == [8, 2]  # 7.5 y 2.5: el mayor resto decide


def test_el_total_se_conserva_aunque_no_sea_divisible():
    for total in range(1, 40):
        assert sum(repartir(total, [1, 2, 3, 5], [100, 100, 100, 100])) == total


def test_nunca_pasa_la_capacidad_de_una_zona_y_redistribuye_el_sobrante():
    resultado = repartir(10, [10, 1, 1], [3, 100, 100])

    assert resultado[0] == 3  # su tope
    assert sum(resultado) == 10  # lo que no entro se reparte entre las otras


def test_si_no_hay_lugar_para_todos_reparte_los_que_entran():
    assert repartir(50, [1, 1], [4, 6]) == [4, 6]


def test_una_zona_sin_capacidad_o_sin_peso_queda_vacia():
    assert repartir(9, [1, 1, 1], [0, 100, 100]) == [0, 5, 4]  # la zona sin lugar queda en 0
    assert repartir(9, [0, 1], [100, 100]) == [0, 9]


def test_el_escenario_concentrado_llena_mas_la_zona_elegida():
    ids, capacidades = ["A1", "B1", "C1"], [20, 20, 20]

    parejo = repartir(30, pesos_del_escenario("parejo", capacidades, ids), capacidades)
    concentrado = repartir(30, pesos_del_escenario("concentrado", capacidades, ids, "B1"), capacidades)

    assert parejo == [10, 10, 10]
    assert concentrado[1] > 2 * max(concentrado[0], concentrado[2])


def test_los_conteos_varian_entre_instantes_pero_el_total_se_mantiene():
    azar = random.Random(1)
    pesos, capacidades = [1.0, 1.0, 1.0], [50, 50, 50]

    instantes = [conteos_en_un_instante(30, pesos, capacidades, 0.3, azar) for _ in range(20)]

    assert all(sum(c) == 30 for c in instantes)
    assert len({tuple(c) for c in instantes}) > 1


def test_la_misma_semilla_genera_la_misma_secuencia():
    secuencias = []
    for _ in range(2):
        azar = random.Random(5)
        secuencias.append([conteos_en_un_instante(20, [1, 1], [50, 50], 0.2, azar) for _ in range(5)])

    assert secuencias[0] == secuencias[1]


def test_el_mensaje_omite_a_los_sensores_que_fallaron():
    ahora = datetime(2026, 11, 5, 20, 31, 7, tzinfo=timezone.utc)

    mensaje = construir_mensaje(2, 1, ["A1", "B1"], [7, 9], ahora, silenciadas={"B1"})

    assert mensaje["lecturas"] == [
        {"sensor": "sensor-a1", "zona": "A1", "personas": 7, "momento": "2026-11-05T20:31:07+00:00"}
    ]


def test_el_mensaje_del_simulador_es_aceptado_por_la_api(tmp_path):
    (tmp_path / "sala.txt").write_text("#######\n#.....S\n#.....#\n#######\n", encoding="utf-8")
    cliente = TestClient(crear_app(tmp_path))
    zonas = cliente.get("/api/recintos/sala/zonas", params={"columnas": 2, "filas": 1}).json()
    ids, capacidades = [z["id"] for z in zonas], [z["capacidad"] for z in zonas]
    conteos = conteos_en_un_instante(6, [1.0, 1.0], capacidades, 0.1, random.Random(1))

    mensaje = construir_mensaje(2, 1, ids, conteos, datetime.now(timezone.utc))
    respuesta = cliente.post("/api/sensores/sala", json=mensaje)

    assert respuesta.status_code == 200 and respuesta.json() == {"recibidas": 2}
    assert cliente.get("/api/sensores/sala").json()["total_vigente"] == 6
