import random

import pytest

from src.recinto import leer_recinto_texto
from src.zonas import nombre_de_zona, ubicar_por_zona, zonas_en_grilla

SALA = leer_recinto_texto(
    "#######S\n"
    "#......#\n"
    "#......#\n"
    "#......#\n"
)  # 8 de ancho x 4 de alto, una salida arriba a la derecha


def test_las_zonas_se_nombran_como_una_planilla():
    assert nombre_de_zona(0, 0) == "A1"
    assert nombre_de_zona(2, 1) == "C2"


def test_parte_el_recinto_en_sectores_sin_huecos_ni_solapamientos():
    zonas = zonas_en_grilla(SALA, columnas=3, filas=2)

    assert [z.id for z in zonas] == ["A1", "B1", "C1", "A2", "B2", "C2"]
    assert sum(z.ancho for z in zonas[:3]) == SALA.ancho  # una fila de sectores cubre todo el ancho
    assert sum(z.alto for z in (zonas[0], zonas[3])) == SALA.alto
    celdas_cubiertas = [c for z in zonas for c in z.celdas]
    assert len(celdas_cubiertas) == len(set(celdas_cubiertas))  # ninguna celda en dos zonas


def test_las_zonas_solo_incluyen_celdas_transitables():
    zonas = zonas_en_grilla(SALA, columnas=2, filas=2)
    celdas = {c for z in zonas for c in z.celdas}

    assert not celdas & set(SALA.muros)
    assert not celdas & set(SALA.salidas)
    assert len(celdas) == SALA.ancho * SALA.alto - len(SALA.muros) - len(SALA.salidas)


def test_una_zona_vecina_a_la_salida_de_arriba_tiene_su_coordenada_y_del_modelo():
    # el modelo cuenta y hacia arriba: la fila de arriba del plano es la y mas alta
    zona_de_arriba_a_la_derecha = zonas_en_grilla(SALA, columnas=2, filas=2)[1]

    assert all(y >= 2 for (_, y) in zona_de_arriba_a_la_derecha.celdas)  # filas 0-1 de pantalla = y 3-2
    assert all(x >= 4 for (x, _) in zona_de_arriba_a_la_derecha.celdas)


@pytest.mark.parametrize("columnas, filas", [(0, 1), (27, 1), (9, 1), (1, 0), (1, 5)])
def test_rechaza_una_division_imposible(columnas, filas):
    with pytest.raises(ValueError):
        zonas_en_grilla(SALA, columnas, filas)


def test_ubica_la_cantidad_medida_en_cada_zona_sin_repetir_celdas():
    zonas = zonas_en_grilla(SALA, columnas=2, filas=1)

    posiciones, avisos = ubicar_por_zona(zonas, {"A1": 5, "B1": 3}, azar=random.Random(1))

    assert avisos == [] and len(posiciones) == 8 and len(set(posiciones)) == 8
    en_a = [p for p in posiciones if p in zonas[0].celdas]
    en_b = [p for p in posiciones if p in zonas[1].celdas]
    assert (len(en_a), len(en_b)) == (5, 3)


def test_si_se_midieron_mas_personas_que_lugares_avisa_y_ubica_las_que_entran():
    zonas = zonas_en_grilla(SALA, columnas=1, filas=1)
    capacidad = zonas[0].capacidad

    posiciones, avisos = ubicar_por_zona(zonas, {"A1": capacidad + 10})

    assert len(posiciones) == capacidad
    assert "A1" in avisos[0] and str(capacidad) in avisos[0]


def test_respeta_las_celdas_permitidas_y_avisa_de_zonas_que_no_existen():
    zonas = zonas_en_grilla(SALA, columnas=1, filas=1)
    permitidas = set(zonas[0].celdas[:3])  # por ejemplo, solo 3 celdas tienen camino a una salida

    posiciones, avisos = ubicar_por_zona(zonas, {"A1": 5, "Z9": 2}, permitidas=permitidas)

    assert set(posiciones) <= permitidas and len(posiciones) == 3
    assert any("solo hay lugar para 3" in a for a in avisos)
    assert any("Z9" in a for a in avisos)


def test_la_misma_semilla_ubica_a_la_gente_en_los_mismos_lugares():
    zonas = zonas_en_grilla(SALA, columnas=2, filas=2)
    conteos = {"A1": 2, "B1": 3, "A2": 1, "B2": 4}

    primera, _ = ubicar_por_zona(zonas, conteos, azar=random.Random(7))
    segunda, _ = ubicar_por_zona(zonas, conteos, azar=random.Random(7))

    assert primera == segunda
