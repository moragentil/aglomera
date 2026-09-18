from mesa import Model

from src.agent import Peaton
from src.space import crear_espacio


def _celdas_por_coordenada(espacio):
    return {celda.coordinate: celda for celda in espacio.all_cells}


def test_decidir_movimiento_elige_la_celda_mas_cercana_a_la_salida():
    model = Model(rng=1)
    espacio = crear_espacio(5, 1, salidas=[(0, 0)], random=model.random)
    celdas = _celdas_por_coordenada(espacio)

    peaton = Peaton(model, celdas[(4, 0)])
    celda_deseada, hay_progreso_posible = peaton.decidir_movimiento()

    assert celda_deseada.coordinate == (3, 0)
    assert hay_progreso_posible


def test_decidir_movimiento_no_elige_una_celda_ocupada():
    model = Model(rng=1)
    espacio = crear_espacio(5, 1, salidas=[(0, 0)], random=model.random)
    celdas = _celdas_por_coordenada(espacio)

    Peaton(model, celdas[(3, 0)])  # bloqueador
    peaton = Peaton(model, celdas[(4, 0)])
    celda_deseada, hay_progreso_posible = peaton.decidir_movimiento()

    # (3, 0) esta ocupado por el bloqueador. hay_progreso_posible sigue
    # siendo True porque SI existia una celda mejor, solo que ocupada.
    assert celda_deseada is None
    assert hay_progreso_posible


def test_decidir_movimiento_no_hay_progreso_posible_detras_de_un_muro_completo():
    model = Model(rng=1)
    # muro completo en x=2: todo lo que queda detras es inalcanzable
    espacio = crear_espacio(5, 1, salidas=[(0, 0)], muros=[(2, 0)], random=model.random)
    celdas = _celdas_por_coordenada(espacio)

    peaton = Peaton(model, celdas[(4, 0)])
    celda_deseada, hay_progreso_posible = peaton.decidir_movimiento()

    # no hay ninguna vecina, libre u ocupada, que lo acerque a la salida.
    assert celda_deseada is None
    assert not hay_progreso_posible


def test_peaton_paciente_no_elige_moverse_si_no_hay_mejora_disponible():
    model = Model(rng=1)
    # sala 3x3, salida a la izquierda-medio. El peaton en (2, 1) tiene su
    # mejor vecina, (1, 1), ocupada por el bloqueador. Sus otras vecinas,
    # (2, 0) y (2, 2), no lo acercan a la salida pero estan libres.
    espacio = crear_espacio(3, 3, salidas=[(0, 1)], random=model.random)
    celdas = _celdas_por_coordenada(espacio)

    Peaton(model, celdas[(1, 1)])  # bloqueador
    paciente = Peaton(model, celdas[(2, 1)])
    celda_deseada, hay_progreso_posible = paciente.decidir_movimiento()

    assert celda_deseada is None
    assert hay_progreso_posible


def test_peaton_agresivo_elige_una_celda_libre_aunque_no_mejore():
    model = Model(rng=1)
    espacio = crear_espacio(3, 3, salidas=[(0, 1)], random=model.random)
    celdas = _celdas_por_coordenada(espacio)

    Peaton(model, celdas[(1, 1)])  # bloqueador
    agresivo = Peaton(model, celdas[(2, 1)], agresivo=True)
    celda_deseada, hay_progreso_posible = agresivo.decidir_movimiento()

    # no espera: elige alguna de las vecinas libres, aunque no mejoren.
    assert celda_deseada.coordinate in {(2, 0), (2, 2)}
    assert hay_progreso_posible


def test_el_peaton_se_evacua_si_esta_parado_en_una_salida():
    model = Model(rng=1)
    espacio = crear_espacio(5, 1, salidas=[(0, 0)], random=model.random)
    celdas = _celdas_por_coordenada(espacio)

    peaton = Peaton(model, celdas[(0, 0)])
    assert not peaton.evacuado

    peaton.evacuar_si_llego()

    assert peaton.evacuado
    assert peaton.cell is None
    assert celdas[(0, 0)].is_empty  # la salida queda libre para otro peaton


def test_el_peaton_evacuado_no_decide_moverse_ni_se_reevacua():
    model = Model(rng=1)
    espacio = crear_espacio(5, 1, salidas=[(0, 0)], random=model.random)
    celdas = _celdas_por_coordenada(espacio)

    peaton = Peaton(model, celdas[(0, 0)])
    peaton.evacuar_si_llego()
    assert peaton.evacuado

    celda_deseada, hay_progreso_posible = peaton.decidir_movimiento()
    assert celda_deseada is None
    assert not hay_progreso_posible

    peaton.evacuar_si_llego()  # no deberia romper ni cambiar nada
    assert peaton.evacuado
    assert peaton.cell is None
