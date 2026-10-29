import pytest

from experiments.run_batch import SALA_CON_DOS_SALIDAS, SALA_CON_PUERTA
from src.model import EvacuacionModel
from src.recinto import Recinto, RecintoInvalido, cargar_recinto, leer_recinto_texto


def test_lee_ancho_alto_salidas_y_muros():
    recinto = leer_recinto_texto("..#\n.S.\n")

    assert (recinto.ancho, recinto.alto) == (3, 2)
    assert recinto.salidas == [(1, 0)]
    assert recinto.muros == [(2, 1)]


def test_la_primera_linea_del_archivo_es_la_fila_de_arriba():
    # el eje y de la grilla crece hacia arriba: la linea de arriba tiene y mas alto
    recinto = leer_recinto_texto("S.\n..\n..")

    assert recinto.alto == 3
    assert recinto.salidas == [(0, 2)]


def test_ignora_lineas_vacias_en_los_bordes():
    recinto = leer_recinto_texto("\n\n.S.\n...\n\n")

    assert (recinto.ancho, recinto.alto) == (3, 2)


def test_las_salidas_y_los_muros_salen_ordenados():
    recinto = leer_recinto_texto("S#S\n#.#\nS#.")

    assert recinto.salidas == sorted(recinto.salidas)
    assert recinto.muros == sorted(recinto.muros)


@pytest.mark.parametrize(
    "texto, fragmento_del_mensaje",
    [
        ("", "vacío"),
        ("\n\n", "vacío"),
        ("...\n..\n", "Línea 2"),  # filas de distinto largo
        ("...\n.x.\n", "Línea 2, columna 2"),  # caracter desconocido
        ("...\n...\n", "ninguna salida"),
        ("S..\n\n...\n", "Línea 2"),  # linea vacia en el medio
    ],
)
def test_un_plano_invalido_explica_que_esta_mal(texto, fragmento_del_mensaje):
    with pytest.raises(RecintoInvalido, match=fragmento_del_mensaje):
        leer_recinto_texto(texto)


def test_carga_por_nombre_y_por_ruta(tmp_path):
    por_nombre = cargar_recinto("sala_con_puerta")

    archivo = tmp_path / "mi_sala.txt"
    archivo.write_text(".S.\n", encoding="utf-8")
    por_ruta = cargar_recinto(archivo)

    assert por_nombre.ancho == 15
    assert por_ruta == Recinto(ancho=3, alto=1, salidas=[(1, 0)], muros=[])


def test_un_recinto_inexistente_avisa():
    with pytest.raises(FileNotFoundError, match="no_existe"):
        cargar_recinto("no_existe")


def test_la_sala_con_puerta_es_la_misma_que_estaba_escrita_en_el_codigo():
    # estos valores son los que antes estaban fijos en app.py y run_batch.py:
    # si cambian, cambian los resultados de los experimentos
    alto = 10
    assert SALA_CON_PUERTA == {
        "ancho": 15,
        "alto": alto,
        "salidas": [[(14, 5)]],
        "muros": [[(7, y) for y in range(alto) if y != 4]],
    }


def test_la_sala_de_dos_salidas_es_la_misma_que_estaba_escrita_en_el_codigo():
    assert SALA_CON_DOS_SALIDAS == {
        "ancho": 20,
        "alto": 11,
        "salidas": [[(0, 5), (19, 5)]],
        "muros": [[]],
    }


def test_un_recinto_cargado_alcanza_para_correr_una_evacuacion():
    recinto = cargar_recinto("sala_con_puerta")

    model = EvacuacionModel(**recinto.como_parametros(), num_agentes=20, rng=1)
    while model.running and model.pasos_transcurridos < 500:
        model.step()

    assert model.todos_evacuaron()


def test_no_coloca_peatones_en_zonas_encerradas_sin_camino_a_la_salida():
    # la columna del medio es un muro: la mitad derecha no tiene salida
    recinto = leer_recinto_texto("S.#..\n..#..")

    model = EvacuacionModel(**recinto.como_parametros(), num_agentes=3, rng=1)

    assert all(peaton.cell.coordinate[0] < 2 for peaton in model.agents)
    with pytest.raises(ValueError, match="camino a una salida"):
        EvacuacionModel(**recinto.como_parametros(), num_agentes=4, rng=1)
