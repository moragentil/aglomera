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


def test_el_peaton_seguido_registra_su_recorrido_paso_a_paso():
    model = EvacuacionModel(ancho=5, alto=1, num_agentes=3, salidas=[(0, 0)], rng=1)

    seguido = model.peaton_seguido
    assert seguido is not None
    assert seguido.seguido
    assert len(seguido.historial) == 1  # la celda inicial

    for _ in range(10):
        if model.todos_evacuaron():
            break
        celda_anterior = seguido.cell.coordinate if seguido.cell is not None else None
        model.step()
        if celda_anterior is not None and not seguido.evacuado:
            assert seguido.historial[-1] == seguido.cell.coordinate

    # se movio mas de una vez: el historial creció mas alla de la celda inicial
    assert len(seguido.historial) > 1


def test_seguir_un_peaton_false_no_marca_a_nadie():
    model = EvacuacionModel(
        ancho=5, alto=1, num_agentes=3, salidas=[(0, 0)], rng=1, seguir_un_peaton=False
    )

    assert model.peaton_seguido is None
    assert all(not peaton.seguido for peaton in model.agents)


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


def test_probabilidad_agresivo_asigna_el_flag_a_los_peatones():
    model_paciente = EvacuacionModel(
        ancho=5, alto=5, num_agentes=10, salidas=[(4, 4)], rng=1, probabilidad_agresivo=0.0
    )
    assert all(not peaton.agresivo for peaton in model_paciente.agents)

    model_agresivo = EvacuacionModel(
        ancho=5, alto=5, num_agentes=10, salidas=[(4, 4)], rng=1, probabilidad_agresivo=1.0
    )
    assert all(peaton.agresivo for peaton in model_agresivo.agents)


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


def _preparar_conflicto_por_una_celda(probabilidad_friccion):
    # grilla 3x2, salida en (1, 0). Los muros en (0, 0) y (2, 0) dejan a
    # (0, 1) y (2, 1) con una unica vecina transitable cada uno: (1, 1).
    # Los dos peatones van a querer, sin ninguna otra opcion, esa misma
    # celda vacia al mismo tiempo: un conflicto real y determinista.
    model = EvacuacionModel(
        ancho=3,
        alto=2,
        num_agentes=2,
        salidas=[(1, 0)],
        muros=[(0, 0), (2, 0)],
        rng=1,
        probabilidad_friccion=probabilidad_friccion,
    )
    celdas = {c.coordinate: c for c in model.espacio.all_cells}
    peaton_a, peaton_b = model.agents
    peaton_a.cell = None
    peaton_b.cell = None
    peaton_a.cell = celdas[(0, 1)]
    peaton_b.cell = celdas[(2, 1)]
    return model, peaton_a, peaton_b


def test_conflicto_sin_friccion_deja_pasar_a_uno_solo():
    model, peaton_a, peaton_b = _preparar_conflicto_por_una_celda(probabilidad_friccion=0.0)

    model.step()

    movidos = [p for p in (peaton_a, peaton_b) if p.cell is not None and p.cell.coordinate == (1, 1)]
    bloqueados = [p for p in (peaton_a, peaton_b) if p.bloqueado]

    assert len(movidos) == 1
    assert len(bloqueados) == 1


def test_conflicto_con_friccion_total_no_deja_pasar_a_nadie():
    model, peaton_a, peaton_b = _preparar_conflicto_por_una_celda(probabilidad_friccion=1.0)

    model.step()

    assert peaton_a.cell.coordinate == (0, 1)
    assert peaton_b.cell.coordinate == (2, 1)
    assert peaton_a.bloqueado
    assert peaton_b.bloqueado


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
