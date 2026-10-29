import time

import pytest
from fastapi.testclient import TestClient

from src.recinto import leer_recinto_texto
from src.zonas import zonas_en_grilla
from web.app import crear_app
from web.generador_sensores import ENVIOS_ANTES_DE_LA_FALLA, GeneradorDeSensores
from web.sensores import RegistroDeSensores

SALA = [
    "##########",
    "#........#",
    "#........#",
    "#........S",
    "#........#",
    "#........#",
    "##########",
]  # el interior tiene 8 x 5 = 40 celdas


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
def registro(reloj):
    return RegistroDeSensores(caducidad_s=30, reloj=reloj)


@pytest.fixture
def zonas():
    return zonas_en_grilla(leer_recinto_texto("\n".join(SALA) + "\n"), 2, 1)


def personas_por_zona(registro):
    _, _, estado = registro.estado("sala")
    return {zona: lectura.personas for zona, (lectura, _, _) in estado.items()}


# ------------------------------------------------------------ el generador


def test_al_iniciar_ya_hay_datos_sin_esperar_al_primer_intervalo(registro, zonas):
    generador = GeneradorDeSensores(registro, en_segundo_plano=False)

    estado = generador.iniciar("sala", zonas, 2, 1, total=20)

    assert estado["activo"] and estado["envios"] == 1
    assert sum(personas_por_zona(registro).values()) == 20


def test_cada_envio_mantiene_el_total_aunque_varien_las_zonas(registro, zonas):
    generador = GeneradorDeSensores(registro, en_segundo_plano=False)
    generador.iniciar("sala", zonas, 2, 1, total=20, semilla=1)

    distribuciones = set()
    for _ in range(15):
        generador.enviar_ahora("sala")
        conteos = personas_por_zona(registro)
        assert sum(conteos.values()) == 20
        distribuciones.add(tuple(sorted(conteos.items())))

    assert len(distribuciones) > 1  # los sensores no informan siempre lo mismo


def test_el_escenario_concentrado_llena_mas_la_zona_elegida(registro, zonas):
    generador = GeneradorDeSensores(registro, en_segundo_plano=False)

    generador.iniciar("sala", zonas, 2, 1, total=20, escenario="concentrado", zona_llena="B1", semilla=1)
    conteos = personas_por_zona(registro)

    assert conteos["B1"] > conteos["A1"]


def test_una_falla_apaga_al_ultimo_sensor_y_su_zona_pasa_a_sin_senal(registro, reloj, zonas):
    generador = GeneradorDeSensores(registro, en_segundo_plano=False)
    generador.iniciar("sala", zonas, 2, 1, total=20, falla=True)
    for _ in range(ENVIOS_ANTES_DE_LA_FALLA - 1):  # ya hubo uno al iniciar
        generador.enviar_ahora("sala")
    assert generador.estado("sala")["zona_con_falla"] == "B1"

    reloj.avanzar(25)
    generador.enviar_ahora("sala")  # A1 reporta; B1 ya fallo
    reloj.avanzar(10)
    _, _, estado = registro.estado("sala")

    assert estado["A1"][2] == "ACTIVO"
    assert estado["B1"][2] == "SIN SEÑAL"


def test_apagarlo_deja_de_enviar_y_las_lecturas_caducan_solas(registro, reloj, zonas):
    generador = GeneradorDeSensores(registro, en_segundo_plano=False)
    generador.iniciar("sala", zonas, 2, 1, total=20)

    assert generador.detener("sala") is True
    assert generador.estado("sala") is None
    assert generador.enviar_ahora("sala") is False
    assert generador.detener("sala") is False  # ya estaba apagado

    assert registro.ocupacion_vigente("sala") is not None  # todavia vigentes...
    reloj.avanzar(31)
    assert registro.ocupacion_vigente("sala") is None  # ...hasta que caducan


def test_iniciar_de_nuevo_reemplaza_a_los_sensores_anteriores(registro, zonas):
    generador = GeneradorDeSensores(registro, en_segundo_plano=False)
    generador.iniciar("sala", zonas, 2, 1, total=10)

    generador.iniciar("sala", zonas, 2, 1, total=30)

    assert generador.estado("sala")["total"] == 30
    assert generador.estado("sala")["envios"] == 1
    assert sum(personas_por_zona(registro).values()) == 30


def test_el_hilo_envia_cada_intervalo_y_se_apaga_de_verdad(registro, zonas):
    llamadas = []
    registrar = registro.registrar
    registro.registrar = lambda *args, **kwargs: (llamadas.append(1), registrar(*args, **kwargs))[1]
    generador = GeneradorDeSensores(registro, en_segundo_plano=True)
    generador.iniciar("sala", zonas, 2, 1, total=20, intervalo_s=0.05)

    limite = time.time() + 3
    while len(llamadas) < 4 and time.time() < limite:
        time.sleep(0.02)
    assert len(llamadas) >= 4  # siguio enviando solo, sin que nadie lo pida

    generador.detener("sala")
    time.sleep(0.2)  # por si un envio estaba en curso justo al apagarlo
    enviadas = len(llamadas)
    time.sleep(0.3)  # varios intervalos: si el hilo siguiera vivo, llegarian mas

    assert len(llamadas) == enviadas


# --------------------------------------------------------------- las rutas


@pytest.fixture
def cliente(tmp_path, reloj):
    (tmp_path / "sala.txt").write_text("\n".join(SALA) + "\n", encoding="utf-8")
    return TestClient(crear_app(tmp_path, reloj=reloj, sensores_en_segundo_plano=False))


def test_encender_los_sensores_desde_la_api_deja_datos_a_la_vista(cliente):
    respuesta = cliente.post("/api/sensores/sala/simulador", json={"columnas": 2, "filas": 1, "total": 20})
    estado = cliente.get("/api/sensores/sala").json()

    assert respuesta.status_code == 201 and respuesta.json()["activo"] is True
    assert estado["hay_datos"] and estado["total_vigente"] == 20
    assert estado["simulador"]["activo"] and estado["simulador"]["total"] == 20


def test_sin_sensores_simulados_el_estado_lo_indica(cliente):
    estado = cliente.get("/api/sensores/sala").json()

    assert estado["hay_datos"] is False and estado["simulador"] is None


def test_apagar_los_sensores_desde_la_api(cliente):
    cliente.post("/api/sensores/sala/simulador", json={"columnas": 2, "filas": 1})

    assert cliente.delete("/api/sensores/sala/simulador").status_code == 204
    assert cliente.get("/api/sensores/sala").json()["simulador"] is None
    assert cliente.delete("/api/sensores/sala/simulador").status_code == 204  # apagar dos veces no falla


def test_los_sensores_simulados_se_pueden_usar_para_simular(cliente):
    cliente.post("/api/sensores/sala/simulador", json={"columnas": 2, "filas": 1, "total": 12})

    respuesta = cliente.post(
        "/api/simulaciones",
        json={"plano": {"recinto": "sala"}, "parametros": {"semilla": 2}, "ocupacion": "sensores"},
    ).json()

    assert respuesta["ocupacion"]["fuente"] == "sensores" and respuesta["ocupacion"]["total"] == 12


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"columnas": 99},  # division imposible
        {"columnas": 2, "filas": 1, "zona_llena": "Z9"},  # esa zona no existe
        {"total": 0},
        {"escenario": "caotico"},
        {"intervalo_s": 0},
    ],
)
def test_rechaza_pedidos_invalidos(cliente, cuerpo):
    assert cliente.post("/api/sensores/sala/simulador", json=cuerpo).status_code == 422


def test_encender_sensores_de_un_recinto_inexistente_da_404(cliente):
    assert cliente.post("/api/sensores/fantasma/simulador", json={}).status_code == 404
