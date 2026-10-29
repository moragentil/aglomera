import pytest
from fastapi.testclient import TestClient

from web.app import crear_app
from web.sensores import RegistroDeSensores

SALA = [
    "##########",
    "#........#",
    "#........#",
    "#........S",
    "#........#",
    "#........#",
    "##########",
]  # 10 de ancho x 7 de alto, una salida a la derecha


class RelojFalso:
    def __init__(self):
        self.ahora = 1000.0

    def __call__(self):
        return self.ahora

    def avanzar(self, segundos):
        self.ahora += segundos


@pytest.fixture
def reloj():
    return RelojFalso()


@pytest.fixture
def cliente(tmp_path, reloj):
    (tmp_path / "sala.txt").write_text("\n".join(SALA) + "\n", encoding="utf-8")
    return TestClient(crear_app(tmp_path, reloj=reloj, caducidad_s=30))


def enviar(cliente, lecturas, columnas=2, filas=1, recinto="sala"):
    return cliente.post(
        f"/api/sensores/{recinto}",
        json={"columnas": columnas, "filas": filas, "lecturas": lecturas},
    )


def lectura(zona, personas, sensor="S1"):
    return {"sensor": sensor, "zona": zona, "personas": personas}


# --------------------------------------------------------------- zonas


def test_lista_las_zonas_con_su_capacidad(cliente):
    zonas = cliente.get("/api/recintos/sala/zonas", params={"columnas": 2, "filas": 1}).json()

    assert [z["id"] for z in zonas] == ["A1", "B1"]
    assert sum(z["ancho"] for z in zonas) == 10
    assert sum(z["capacidad"] for z in zonas) == 8 * 5  # el interior, sin paredes ni salida


def test_una_division_imposible_en_zonas_se_rechaza(cliente):
    assert cliente.get("/api/recintos/sala/zonas", params={"columnas": 11}).status_code == 422
    assert cliente.get("/api/recintos/inexistente/zonas").status_code == 404


# ------------------------------------------------------- ingesta de lecturas


def test_sin_lecturas_no_hay_datos(cliente):
    respuesta = cliente.get("/api/sensores/sala").json()

    assert respuesta["hay_datos"] is False and respuesta["zonas"] == []


def test_recibe_lecturas_y_las_muestra_activas(cliente):
    respuesta = enviar(cliente, [lectura("A1", 12, "puerta-izq"), lectura("B1", 7, "puerta-der")])
    estado = cliente.get("/api/sensores/sala").json()

    assert respuesta.status_code == 200 and respuesta.json() == {"recibidas": 2}
    assert estado["hay_datos"] and (estado["columnas"], estado["filas"]) == (2, 1)
    assert [(z["id"], z["personas"], z["estado"], z["sensor"]) for z in estado["zonas"]] == [
        ("A1", 12, "ACTIVO", "puerta-izq"),
        ("B1", 7, "ACTIVO", "puerta-der"),
    ]
    assert estado["total_vigente"] == 19 and estado["zonas_vigentes"] == 2


def test_una_lectura_nueva_reemplaza_a_la_anterior_de_esa_zona(cliente):
    enviar(cliente, [lectura("A1", 12)])
    enviar(cliente, [lectura("A1", 3)])

    zonas = cliente.get("/api/sensores/sala").json()["zonas"]

    assert next(z for z in zonas if z["id"] == "A1")["personas"] == 3


def test_una_zona_que_nunca_reporto_figura_sin_datos(cliente):
    enviar(cliente, [lectura("A1", 5)])

    zonas = {z["id"]: z for z in cliente.get("/api/sensores/sala").json()["zonas"]}

    assert zonas["B1"]["estado"] == "SIN DATOS" and zonas["B1"]["personas"] is None


def test_una_zona_que_deja_de_reportar_pasa_a_sin_senal_y_ya_no_cuenta(cliente, reloj):
    enviar(cliente, [lectura("A1", 12), lectura("B1", 7)])
    reloj.avanzar(20)
    enviar(cliente, [lectura("B1", 8)])  # solo B1 sigue reportando
    reloj.avanzar(15)  # A1 lleva 35 s sin reportar; B1, 15 s

    estado = cliente.get("/api/sensores/sala").json()
    zonas = {z["id"]: z for z in estado["zonas"]}

    assert zonas["A1"]["estado"] == "SIN SEÑAL" and zonas["A1"]["edad_s"] == 35.0
    assert zonas["B1"]["estado"] == "ACTIVO"
    assert estado["total_vigente"] == 8 and estado["zonas_vigentes"] == 1


def test_cambiar_la_division_en_zonas_descarta_las_lecturas_anteriores(cliente):
    enviar(cliente, [lectura("A1", 12)], columnas=2, filas=1)
    enviar(cliente, [lectura("A1", 4)], columnas=1, filas=2)

    estado = cliente.get("/api/sensores/sala").json()

    assert (estado["columnas"], estado["filas"]) == (1, 2)
    assert {z["id"]: z["personas"] for z in estado["zonas"]} == {"A1": 4, "A2": None}


@pytest.mark.parametrize(
    "lecturas, columnas",
    [
        ([lectura("C1", 1)], 2),  # esa zona no existe con 2 columnas
        ([lectura("zona", 1)], 2),  # formato invalido
        ([lectura("A1", -5)], 2),  # un conteo no puede ser negativo
        ([], 2),  # un mensaje sin lecturas
        ([lectura("A1", 1)], 99),  # division imposible
    ],
)
def test_rechaza_mensajes_invalidos(cliente, lecturas, columnas):
    assert enviar(cliente, lecturas, columnas=columnas).status_code == 422


def test_rechaza_lecturas_de_un_recinto_que_no_existe(cliente):
    assert enviar(cliente, [lectura("A1", 1)], recinto="fantasma").status_code == 404


# -------------------------------------------- simulacion con ocupacion medida


def crear_con_sensores(cliente, **extra):
    pedido = {
        "plano": {"recinto": "sala"},
        "parametros": {"num_agentes": 5, "semilla": 3, "tipo_vecindad": "von_neumann"},
        "ocupacion": "sensores",
        **extra,
    }
    return cliente.post("/api/simulaciones", json=pedido)


def personas_por_zona(respuesta, zonas):
    """Cuenta los peatones del estado inicial dentro del rectangulo de cada zona."""
    estado = respuesta["estado"]
    puntos = [(c, f) for c, f, _ in estado["agentes"]]
    puntos.append(tuple(estado["seguido"]["historial"][-1]))  # el seguido va aparte
    return {
        z["id"]: sum(
            1
            for c, f in puntos
            if z["columna"] <= c < z["columna"] + z["ancho"] and z["fila"] <= f < z["fila"] + z["alto"]
        )
        for z in zonas
    }


def test_la_simulacion_arranca_con_la_ocupacion_medida_en_cada_zona(cliente):
    enviar(cliente, [lectura("A1", 9), lectura("B1", 4)])
    zonas = cliente.get("/api/recintos/sala/zonas", params={"columnas": 2, "filas": 1}).json()

    respuesta = crear_con_sensores(cliente).json()

    assert respuesta["ocupacion"]["fuente"] == "sensores"
    assert respuesta["ocupacion"]["total"] == 13 and respuesta["estado"]["total"] == 13
    assert respuesta["ocupacion"]["conteos"] == {"A1": 9, "B1": 4}
    assert personas_por_zona(respuesta, zonas) == {"A1": 9, "B1": 4}  # num_agentes (5) no se usa


def test_la_misma_semilla_ubica_a_la_gente_en_los_mismos_lugares(cliente):
    enviar(cliente, [lectura("A1", 6), lectura("B1", 6)])

    primera = crear_con_sensores(cliente).json()["estado"]["agentes"]
    segunda = crear_con_sensores(cliente).json()["estado"]["agentes"]

    assert primera == segunda


def test_una_simulacion_con_ocupacion_medida_se_puede_correr_hasta_el_final(cliente):
    enviar(cliente, [lectura("A1", 8), lectura("B1", 8)])
    sesion = crear_con_sensores(cliente).json()["id"]

    estado = None
    for _ in range(60):
        estado = cliente.post(f"/api/simulaciones/{sesion}/pasos", json={"cantidad": 10}).json()
        if estado["terminada"]:
            break

    assert estado["terminada"] and estado["evacuados"] == 16


def test_avisa_si_se_midieron_mas_personas_que_lugares(cliente):
    enviar(cliente, [lectura("A1", 500), lectura("B1", 2)])

    respuesta = crear_con_sensores(cliente).json()

    assert any("A1" in aviso for aviso in respuesta["ocupacion"]["avisos"])
    assert respuesta["ocupacion"]["total"] < 500


def test_no_simula_con_ocupacion_medida_sin_lecturas_vigentes(cliente, reloj):
    assert crear_con_sensores(cliente).status_code == 409  # nunca llego nada

    enviar(cliente, [lectura("A1", 5)])
    reloj.avanzar(31)  # ya vencieron

    assert crear_con_sensores(cliente).status_code == 409


def test_no_simula_si_las_lecturas_vigentes_no_tienen_a_nadie(cliente):
    enviar(cliente, [lectura("A1", 0), lectura("B1", 0)])

    respuesta = crear_con_sensores(cliente)

    assert respuesta.status_code == 422 and "a nadie" in respuesta.json()["detail"]


def test_la_ocupacion_medida_solo_vale_para_recintos_guardados(cliente):
    pedido = {"plano": {"filas": SALA}, "ocupacion": "sensores"}

    assert cliente.post("/api/simulaciones", json=pedido).status_code == 422


def test_sin_pedir_ocupacion_medida_todo_sigue_igual(cliente):
    enviar(cliente, [lectura("A1", 9)])

    respuesta = cliente.post(
        "/api/simulaciones", json={"plano": {"recinto": "sala"}, "parametros": {"num_agentes": 5}}
    ).json()

    assert respuesta["ocupacion"]["fuente"] == "azar" and respuesta["estado"]["total"] == 5


# ---------------------------------------------------------------- registro


def test_el_registro_solo_ofrece_para_simular_las_zonas_activas():
    reloj = RelojFalso()
    registro = RegistroDeSensores(caducidad_s=10, reloj=reloj)
    registro.registrar("sala", 2, 1, [{"sensor": "a", "zona": "A1", "personas": 3}])
    reloj.avanzar(6)
    registro.registrar("sala", 2, 1, [{"sensor": "b", "zona": "B1", "personas": 4}])
    reloj.avanzar(6)  # A1 lleva 12 s (vencida), B1 lleva 6 s

    assert registro.ocupacion_vigente("sala") == (2, 1, {"B1": 4})
    reloj.avanzar(6)
    assert registro.ocupacion_vigente("sala") is None
    assert registro.ocupacion_vigente("otra") is None
