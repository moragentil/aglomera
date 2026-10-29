import pytest
from fastapi.testclient import TestClient

from src.recinto import CARPETA_RECINTOS
from web import servicios
from web.app import crear_app

SALA_SIMPLE = ["#####", "#...S", "#...#", "#####"]


@pytest.fixture
def carpeta(tmp_path):
    (tmp_path / "chica.txt").write_text("\n".join(SALA_SIMPLE) + "\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def cliente(carpeta):
    return TestClient(crear_app(carpeta))


@pytest.fixture
def cliente_real():
    """Con los recintos de ejemplo del repo (sala_con_puerta, dos_salidas...)."""
    return TestClient(crear_app(CARPETA_RECINTOS))


# ------------------------------------------------------------------ recintos


def test_lista_los_recintos_guardados_con_su_resumen(cliente):
    respuesta = cliente.get("/api/recintos")

    assert respuesta.status_code == 200
    assert respuesta.json() == [
        {"nombre": "chica", "ancho": 5, "alto": 4, "salidas": 1, "paredes": 13, "filas": SALA_SIMPLE}
    ]


def test_un_archivo_roto_no_tira_abajo_la_lista(carpeta, cliente):
    (carpeta / "rota.txt").write_text("..x..\n", encoding="utf-8")

    nombres = [r["nombre"] for r in cliente.get("/api/recintos").json()]

    assert nombres == ["chica"]


def test_obtiene_un_recinto_por_nombre_y_avisa_si_no_existe(cliente):
    assert cliente.get("/api/recintos/chica").json()["filas"] == SALA_SIMPLE
    assert cliente.get("/api/recintos/no_existe").status_code == 404


@pytest.mark.parametrize("nombre", ["con espacio", "a.b", "..%2F..%2Fetc"])
def test_rechaza_nombres_que_podrian_salirse_de_la_carpeta(cliente, nombre):
    assert cliente.get(f"/api/recintos/{nombre}").status_code in (404, 422)


def test_validar_un_plano_bueno_y_uno_sin_salida(cliente):
    bueno = cliente.post("/api/validar", json={"filas": SALA_SIMPLE}).json()
    malo = cliente.post("/api/validar", json={"filas": ["###", "#.#", "###"]}).json()

    assert bueno["valido"] and bueno["salidas"] == 1 and (bueno["ancho"], bueno["alto"]) == (5, 4)
    assert not malo["valido"] and "ninguna salida" in malo["mensaje"]


def test_guardar_un_recinto_nuevo_y_volver_a_leerlo(cliente):
    respuesta = cliente.post("/api/recintos", json={"nombre": "nueva", "filas": SALA_SIMPLE})

    assert respuesta.status_code == 201
    assert cliente.get("/api/recintos/nueva").json()["filas"] == SALA_SIMPLE


def test_guardar_no_pisa_un_recinto_salvo_que_se_pida(cliente):
    pedido = {"nombre": "chica", "filas": SALA_SIMPLE}

    assert cliente.post("/api/recintos", json=pedido).status_code == 409
    assert cliente.post("/api/recintos", json={**pedido, "sobrescribir": True}).status_code == 201


def test_guardar_rechaza_un_plano_invalido_o_un_nombre_peligroso(cliente):
    sin_salida = cliente.post("/api/recintos", json={"nombre": "x", "filas": ["###", "#.#", "###"]})
    nombre_malo = cliente.post("/api/recintos", json={"nombre": "../afuera", "filas": SALA_SIMPLE})

    assert sin_salida.status_code == 422 and "ninguna salida" in sin_salida.json()["detail"]
    assert nombre_malo.status_code == 422


# ------------------------------------------------------------- simulaciones


def crear(cliente, **extra):
    pedido = {"plano": {"recinto": "chica"}, "parametros": {"num_agentes": 4, **extra}}
    return cliente.post("/api/simulaciones", json=pedido)


def test_crear_una_simulacion_devuelve_el_plano_y_el_estado_inicial(cliente):
    respuesta = crear(cliente)
    datos = respuesta.json()

    assert respuesta.status_code == 201
    assert datos["plano"]["filas"] == SALA_SIMPLE
    estado = datos["estado"]
    assert (estado["paso"], estado["total"], estado["evacuados"]) == (0, 4, 0)
    assert len(estado["agentes"]) + 1 == 4  # el seguido va aparte
    assert estado["seguido"]["evacuado"] is False


def test_los_agentes_vienen_en_coordenadas_de_pantalla_y_sobre_piso(cliente):
    estado = crear(cliente).json()["estado"]

    for columna, fila, bloqueado in estado["agentes"]:
        assert SALA_SIMPLE[fila][columna] == "."  # fila 0 = la de arriba, igual que `filas`
        assert bloqueado in (0, 1)
    columna, fila = estado["seguido"]["historial"][0]
    assert SALA_SIMPLE[fila][columna] == "."


def test_avanzar_y_llegar_al_final(cliente):
    sesion = crear(cliente).json()["id"]

    estado = None
    for _ in range(40):
        estado = cliente.post(f"/api/simulaciones/{sesion}/pasos", json={"cantidad": 5}).json()
        if estado["terminada"]:
            break

    assert estado["terminada"] and estado["evacuados"] == estado["total"] == 4
    assert estado["agentes"] == []
    assert estado["seguido"]["evacuado"] is True
    # una vez terminada, pedir mas pasos no cambia nada
    de_nuevo = cliente.post(f"/api/simulaciones/{sesion}/pasos", json={"cantidad": 5}).json()
    assert de_nuevo["paso"] == estado["paso"]


def test_la_misma_semilla_da_exactamente_la_misma_simulacion(cliente):
    estados = []
    for _ in range(2):
        sesion = crear(cliente, num_agentes=5, semilla=7).json()["id"]
        estados.append(cliente.post(f"/api/simulaciones/{sesion}/pasos", json={"cantidad": 3}).json())

    assert estados[0] == estados[1]


def test_simular_un_plano_que_todavia_no_se_guardo(cliente):
    pedido = {"plano": {"filas": SALA_SIMPLE, "etiqueta": "Mi diseño"}, "parametros": {"num_agentes": 3}}

    respuesta = cliente.post("/api/simulaciones", json=pedido)

    assert respuesta.status_code == 201
    assert respuesta.json()["plano"]["etiqueta"] == "Mi diseño"


def test_pide_mas_peatones_de_los_que_entran(cliente):
    respuesta = crear(cliente, num_agentes=100)

    assert respuesta.status_code == 422
    assert "celdas transitables" in respuesta.json()["detail"]


def test_un_plano_necesita_recinto_o_filas_pero_no_los_dos(cliente):
    ninguno = cliente.post("/api/simulaciones", json={"plano": {}})
    los_dos = cliente.post("/api/simulaciones", json={"plano": {"recinto": "chica", "filas": SALA_SIMPLE}})

    assert ninguno.status_code == 422 and los_dos.status_code == 422


def test_parametros_fuera_de_rango_se_rechazan(cliente):
    assert crear(cliente, probabilidad_friccion=1.5).status_code == 422
    assert crear(cliente, tipo_vecindad="hexagonal").status_code == 422


def test_una_simulacion_inexistente_o_borrada_da_404(cliente):
    sesion = crear(cliente).json()["id"]

    assert cliente.delete(f"/api/simulaciones/{sesion}").status_code == 204
    assert cliente.get(f"/api/simulaciones/{sesion}").status_code == 404
    assert cliente.post("/api/simulaciones/inventada/pasos", json={"cantidad": 1}).status_code == 404


def test_las_sesiones_viejas_se_descartan_al_pasarse_del_maximo():
    sesiones = servicios.Sesiones(maximo=2)

    ids = [sesiones.crear(objeto) for objeto in ("a", "b", "c")]

    assert sesiones.obtener(ids[0]) is None
    assert sesiones.obtener(ids[1]) == "b" and sesiones.obtener(ids[2]) == "c"


# --------------------------------------------------------------- comparacion


def test_comparar_dos_recintos_con_varias_semillas(cliente_real):
    pedido = {
        "planos": [{"recinto": "sala_con_puerta"}, {"recinto": "dos_salidas"}],
        "semillas": 3,
        "parametros": {"num_agentes": 30},
    }

    respuesta = cliente_real.post("/api/comparaciones", json=pedido)
    datos = respuesta.json()

    assert respuesta.status_code == 200
    assert datos["semillas"] == [0, 1, 2]
    etiquetas = [r["etiqueta"] for r in datos["resultados"]]
    assert etiquetas == ["sala_con_puerta", "dos_salidas"]
    for resultado in datos["resultados"]:
        assert resultado["corridas"] == resultado["terminaron"] == 3
        assert resultado["pasos_media"] > 0 and resultado["pasos_desvio"] >= 0
        assert resultado["pasos_p95"] >= resultado["pasos_media"] - resultado["pasos_desvio"] * 3
        curva = resultado["curva"]
        assert curva["pasos"][0] == 0 and curva["evacuados"][0] == 0
        assert curva["evacuados"][-1] == curva["total"] == 30  # todos terminaron
    # sin pared ni puerta de una celda, evacuar es mas rapido
    assert datos["hallazgo"]["mejor"] == "dos_salidas"
    assert 0 < datos["hallazgo"]["mejora_pct"] < 100


def test_comparar_es_reproducible(cliente_real):
    pedido = {
        "planos": [{"recinto": "sala_con_puerta"}, {"recinto": "dos_salidas"}],
        "semillas": 2,
        "parametros": {"num_agentes": 20},
    }

    assert cliente_real.post("/api/comparaciones", json=pedido).json() == \
        cliente_real.post("/api/comparaciones", json=pedido).json()


def test_comparar_incluye_un_diseno_sin_guardar(cliente):
    pedido = {
        "planos": [{"recinto": "chica"}, {"filas": ["#####", "S...S", "#####"], "etiqueta": "Con dos salidas"}],
        "semillas": 2,
        "parametros": {"num_agentes": 3},
    }

    datos = cliente.post("/api/comparaciones", json=pedido).json()

    assert [r["etiqueta"] for r in datos["resultados"]] == ["chica", "Con dos salidas"]


def test_comparar_valida_el_pedido(cliente):
    uno_solo = {"planos": [{"recinto": "chica"}]}
    repetidos = {"planos": [{"recinto": "chica"}, {"recinto": "chica"}], "semillas": 2}
    inexistente = {"planos": [{"recinto": "chica"}, {"recinto": "fantasma"}], "semillas": 2}
    pocas_semillas = {"planos": [{"recinto": "chica"}, {"filas": SALA_SIMPLE}], "semillas": 1}

    assert cliente.post("/api/comparaciones", json=uno_solo).status_code == 422
    assert cliente.post("/api/comparaciones", json=repetidos).status_code == 422
    assert cliente.post("/api/comparaciones", json=inexistente).status_code == 404
    assert cliente.post("/api/comparaciones", json=pocas_semillas).status_code == 422


# ------------------------------------------------------------------ servicios


def test_percentil_por_rango_mas_cercano():
    assert servicios.percentil([10, 20, 30, 40, 50], 50) == 30
    assert servicios.percentil([10, 20, 30, 40, 50], 95) == 50
    assert servicios.percentil([7], 95) == 7


def test_el_hallazgo_solo_compara_recintos_donde_todas_las_corridas_terminaron():
    def resumen(etiqueta, media, terminaron):
        return {"etiqueta": etiqueta, "pasos_media": media, "corridas": 5, "terminaron": terminaron}

    resumenes = [resumen("A", 100.0, 5), resumen("B", 60.0, 5), resumen("C", 10.0, 3)]

    hallazgo = servicios.hallazgo(resumenes)

    assert hallazgo == {"mejor": "B", "peor": "A", "pasos_ahorrados": 40.0, "mejora_pct": 40.0}
    assert servicios.hallazgo([resumen("A", 100.0, 5), resumen("C", 10.0, 3)]) is None


def test_la_curva_promedio_mantiene_en_el_total_a_las_corridas_que_ya_terminaron():
    rapida = servicios.Corrida(pasos=2, termino=True, evacuados_por_paso=[0, 2, 4], congestion_maxima=1)
    lenta = servicios.Corrida(pasos=4, termino=True, evacuados_por_paso=[0, 1, 2, 3, 4], congestion_maxima=2)

    curva = servicios._curva_promedio([rapida, lenta], total=4)

    assert curva["evacuados"] == [0.0, 1.5, 3.0, 3.5, 4.0]  # la rapida se queda en 4, no vuelve a 0


def test_la_pantalla_se_sirve_en_la_raiz(cliente):
    respuesta = cliente.get("/")

    assert respuesta.status_code == 200
    assert "text/html" in respuesta.headers["content-type"]
