from experiments.run_batch import EXPERIMENTOS, correr_experimento


def test_cada_experimento_tiene_todo_lo_necesario_para_correr():
    for nombre, experimento in EXPERIMENTOS.items():
        assert experimento["descripcion"], nombre
        assert experimento["repeticiones"] >= 1, nombre
        assert experimento["pasos_maximos"] >= 1, nombre
        assert "num_agentes" in experimento["parametros"], nombre


def test_las_listas_de_salidas_y_muros_van_envueltas_en_otra_lista():
    # mesa.batch_run "barre" cualquier lista que reciba. Si salidas fuera
    # [(14, 5)] a secas, tomaria el (14, 5) como un valor a barrer en vez de
    # como una salida. Cada configuracion tiene que ser una lista de listas.
    for nombre, experimento in EXPERIMENTOS.items():
        for clave in ("salidas", "muros"):
            configuraciones = experimento["parametros"][clave]
            assert all(isinstance(c, list) for c in configuraciones), (nombre, clave)


def test_correr_experimento_barre_todas_las_combinaciones_con_cada_semilla():
    parametros = {
        "ancho": 5,
        "alto": 1,
        "muros": [[]],
        "salidas": [[(0, 0), (4, 0)]],
        "num_agentes": [1, 2],
    }

    df = correr_experimento(parametros, repeticiones=3, pasos_maximos=50, mostrar_progreso=False)

    assert df["RunId"].nunique() == 2 * 3  # 2 cantidades de agentes x 3 semillas
    assert set(df["num_agentes"]) == {1, 2}
    # la lista de salidas llego entera: hay una columna de evacuados por cada una
    assert {"evacuados_salida_0_0", "evacuados_salida_4_0"} <= set(df.columns)
    ultimos_pasos = df.sort_values("Step").groupby("RunId").tail(1)
    assert (ultimos_pasos["restantes"] == 0).all()
