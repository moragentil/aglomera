import random

from src.space import crear_espacio, distancia_a_salida, es_muro, es_salida


def _celdas_por_coordenada(espacio):
    return {celda.coordinate: celda for celda in espacio.all_cells}


def test_marca_salidas_y_muros():
    espacio = crear_espacio(
        5, 5, salidas=[(4, 2)], muros=[(2, 2)], random=random.Random(1)
    )
    celdas = _celdas_por_coordenada(espacio)

    assert es_salida(celdas[(4, 2)])
    assert not es_salida(celdas[(0, 0)])
    assert es_muro(celdas[(2, 2)])
    assert not es_muro(celdas[(4, 2)])


def test_floor_field_crece_en_linea_recta_desde_la_salida():
    espacio = crear_espacio(5, 1, salidas=[(0, 0)], random=random.Random(1))
    celdas = _celdas_por_coordenada(espacio)

    distancias = [distancia_a_salida(celdas[(x, 0)]) for x in range(5)]
    assert distancias == [0, 1, 2, 3, 4]


def test_floor_field_rodea_un_muro_en_el_camino_directo():
    # grilla 3x3, salida a la izquierda-medio, muro justo en el centro:
    # la distancia en linea recta a (2,1) seria 2, pero el muro obliga
    # a desviarse por arriba o por abajo, y el costo real es 4.
    espacio = crear_espacio(
        3, 3, salidas=[(0, 1)], muros=[(1, 1)], random=random.Random(1)
    )
    celdas = _celdas_por_coordenada(espacio)

    assert distancia_a_salida(celdas[(2, 1)]) == 4
    assert distancia_a_salida(celdas[(1, 1)]) == float("inf")


def test_floor_field_deja_inalcanzable_lo_que_queda_detras_de_una_pared_completa():
    espacio = crear_espacio(
        5, 3, salidas=[(0, 1)], muros=[(2, 0), (2, 1), (2, 2)], random=random.Random(1)
    )
    celdas = _celdas_por_coordenada(espacio)

    assert distancia_a_salida(celdas[(1, 1)]) == 1
    assert distancia_a_salida(celdas[(3, 1)]) == float("inf")
    assert distancia_a_salida(celdas[(4, 1)]) == float("inf")


def test_con_vecindad_moore_la_distancia_es_diagonal_no_manhattan():
    # mismo cuarto 3x3 abierto que el test de linea recta, pero con
    # diagonales habilitadas: a (2, 2) se llega en 2 pasos (diagonal),
    # no en 4 (Manhattan) como con von_neumann.
    espacio = crear_espacio(
        3, 3, salidas=[(0, 0)], random=random.Random(1), tipo_vecindad="moore"
    )
    celdas = _celdas_por_coordenada(espacio)

    assert distancia_a_salida(celdas[(2, 2)]) == 2


def test_con_vecindad_moore_un_muro_de_una_celda_no_fuerza_ningun_desvio():
    # el mismo escenario que "rodea_un_muro", pero con diagonales: el
    # peaton esquiva el muro central gratis, sin pagar el costo de 4 que
    # pagaba con von_neumann. Es justamente la razon por la que elegimos
    # von_neumann como default para los cuellos de botella.
    espacio = crear_espacio(
        3, 3, salidas=[(0, 1)], muros=[(1, 1)], random=random.Random(1), tipo_vecindad="moore"
    )
    celdas = _celdas_por_coordenada(espacio)

    assert distancia_a_salida(celdas[(2, 1)]) == 2
