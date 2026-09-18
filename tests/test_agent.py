from mesa import Model

from src.agent import Peaton
from src.space import crear_espacio


def _celdas_por_coordenada(espacio):
    return {celda.coordinate: celda for celda in espacio.all_cells}


def test_el_peaton_se_mueve_hacia_la_celda_mas_cercana_a_la_salida():
    model = Model(rng=1)
    espacio = crear_espacio(5, 1, salidas=[(0, 0)], random=model.random)
    celdas = _celdas_por_coordenada(espacio)

    peaton = Peaton(model, celdas[(4, 0)])
    peaton.step()

    assert peaton.cell.coordinate == (3, 0)


def test_el_peaton_no_se_mueve_a_una_celda_ocupada():
    model = Model(rng=1)
    espacio = crear_espacio(5, 1, salidas=[(0, 0)], random=model.random)
    celdas = _celdas_por_coordenada(espacio)

    bloqueador = Peaton(model, celdas[(3, 0)])
    peaton = Peaton(model, celdas[(4, 0)])
    peaton.step()

    # (3, 0) esta ocupado por el bloqueador: el peaton se queda quieto,
    # y como (3, 0) SI lo hubiera acercado a la salida, cuenta como bloqueo
    # (congestion), no como que no tenia adonde ir.
    assert peaton.cell.coordinate == (4, 0)
    assert bloqueador.cell.coordinate == (3, 0)
    assert peaton.bloqueado
    assert not bloqueador.bloqueado


def test_el_peaton_no_se_bloquea_si_no_existe_forma_de_mejorar():
    model = Model(rng=1)
    # muro completo en x=2: todo lo que queda detras es inalcanzable
    espacio = crear_espacio(5, 1, salidas=[(0, 0)], muros=[(2, 0)], random=model.random)
    celdas = _celdas_por_coordenada(espacio)

    peaton = Peaton(model, celdas[(4, 0)])
    peaton.step()

    # no se mueve, pero no es "culpa" de nadie: no hay ninguna vecina,
    # libre u ocupada, que lo acerque a la salida.
    assert peaton.cell.coordinate == (4, 0)
    assert not peaton.bloqueado


def test_el_peaton_se_evacua_al_llegar_a_una_celda_de_salida():
    model = Model(rng=1)
    espacio = crear_espacio(5, 1, salidas=[(0, 0)], random=model.random)
    celdas = _celdas_por_coordenada(espacio)

    peaton = Peaton(model, celdas[(1, 0)])
    peaton.step()  # se mueve a (0, 0), la salida

    assert peaton.cell.coordinate == (0, 0)
    assert not peaton.evacuado

    peaton.step()  # esta parado en la salida: se evacua

    assert peaton.evacuado
    assert peaton.cell is None
    assert celdas[(0, 0)].is_empty  # la salida queda libre para otro peaton


def test_el_peaton_evacuado_no_hace_nada_en_los_pasos_siguientes():
    model = Model(rng=1)
    espacio = crear_espacio(5, 1, salidas=[(0, 0)], random=model.random)
    celdas = _celdas_por_coordenada(espacio)

    peaton = Peaton(model, celdas[(0, 0)])
    peaton.step()

    assert peaton.evacuado
    peaton.step()  # no deberia romper ni cambiar nada
    assert peaton.evacuado
    assert peaton.cell is None
