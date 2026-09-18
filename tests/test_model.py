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


def test_bloqueados_aparece_en_un_cuello_de_botella():
    # sala 5x3 con una pared partida en dos, con una sola puerta en (2, 1)
    model = EvacuacionModel(
        ancho=5, alto=3, num_agentes=5, salidas=[(4, 1)], muros=[(2, 0), (2, 2)], rng=1
    )
    celdas = {c.coordinate: c for c in model.espacio.all_cells}
    celdas_del_lado_izquierdo = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 2)]

    # fuerzo a los 5 peatones al lado izquierdo, todos compitiendo por la
    # unica puerta (2, 1), para probar el bloqueo de forma determinista en
    # vez de depender de donde los ubica al azar el modelo al crearse.
    # Primero los saco a todos de su celda para no chocar entre si al
    # reubicarlos (dos peatones no pueden pisar la misma celda a la vez).
    for peaton in model.agents:
        peaton.cell = None
    for peaton, coordenada in zip(model.agents, celdas_del_lado_izquierdo):
        peaton.cell = celdas[coordenada]

    hubo_bloqueo_en_algun_paso = False
    for _ in range(30):
        if model.todos_evacuaron():
            break
        model.step()
        if model.cantidad_bloqueados() > 0:
            hubo_bloqueo_en_algun_paso = True

    assert hubo_bloqueo_en_algun_paso
    assert model.todos_evacuaron()

    df = model.datacollector.get_model_vars_dataframe()
    assert "bloqueados" in df.columns
    assert df["bloqueados"].max() > 0


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
