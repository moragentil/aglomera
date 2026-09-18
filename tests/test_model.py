import pytest

from src.model import EvacuacionModel


def test_crea_la_cantidad_de_agentes_pedida_sin_pisar_muros_ni_salidas():
    model = EvacuacionModel(
        ancho=5, alto=5, num_agentes=10, salidas=[(4, 4)], muros=[(2, 2)], rng=1
    )

    assert len(model.agents) == 10
    for peaton in model.agents:
        assert peaton.cell.coordinate != (2, 2)
        assert peaton.cell.coordinate != (4, 4)


def test_no_permite_mas_agentes_que_celdas_disponibles():
    with pytest.raises(ValueError):
        EvacuacionModel(ancho=2, alto=1, num_agentes=5, salidas=[(1, 0)], rng=1)


def test_step_avanza_el_contador_de_pasos_y_mueve_agentes():
    model = EvacuacionModel(ancho=5, alto=1, num_agentes=1, salidas=[(0, 0)], rng=1)
    peaton = next(iter(model.agents))
    celda_inicial = peaton.cell.coordinate

    model.step()

    assert model.pasos_transcurridos == 1
    assert peaton.cell.coordinate != celda_inicial


def test_todos_evacuaron_al_final_de_un_pasillo_recto():
    model = EvacuacionModel(ancho=5, alto=1, num_agentes=3, salidas=[(0, 0)], rng=1)

    for _ in range(20):
        if model.todos_evacuaron():
            break
        model.step()

    assert model.todos_evacuaron()
    assert model.cantidad_evacuados() == 3
    assert model.cantidad_restantes() == 0


def test_el_datacollector_registra_evacuados_crecientes_por_paso():
    model = EvacuacionModel(ancho=5, alto=1, num_agentes=3, salidas=[(0, 0)], rng=1)

    for _ in range(20):
        if model.todos_evacuaron():
            break
        model.step()

    df = model.datacollector.get_model_vars_dataframe()

    assert df["evacuados"].is_monotonic_increasing
    assert df["evacuados"].iloc[-1] == 3
    assert df["restantes"].iloc[-1] == 0
