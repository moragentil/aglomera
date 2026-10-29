"""Registro de las lecturas de los sensores de ocupación.

Es la capa de "ingesta" de la propuesta de IoT (docs/iot.md): recibe lo que
mide cada sensor y guarda la última lectura de cada zona. Vive en memoria: un
prototipo no necesita una base de datos, y al reiniciar el servidor los
sensores vuelven a reportar solos.

Un dato de sensor no dura para siempre: si una zona hace mucho que no
reporta, no se sabe cuánta gente hay (el sensor puede estar roto, sin red o
descalibrado). Por eso cada lectura "caduca": pasado ese tiempo la zona
figura SIN SEÑAL y su último valor ya no se usa para simular. La antigüedad se
mide con el reloj del servidor, no con el del sensor, que puede estar
desfasado.
"""

import threading
import time
from dataclasses import dataclass

CADUCIDAD_POR_DEFECTO_S = 30

ACTIVO, SIN_SENAL, SIN_DATOS = "ACTIVO", "SIN SEÑAL", "SIN DATOS"


@dataclass(frozen=True)
class Lectura:
    sensor: str
    zona: str
    personas: int
    momento: str | None  # la marca de tiempo que mandó el sensor, tal cual
    recibida: float  # cuando llegó al servidor (segundos del reloj del servidor)


class RegistroDeSensores:
    def __init__(self, caducidad_s=CADUCIDAD_POR_DEFECTO_S, reloj=time.time):
        self.caducidad_s = caducidad_s
        self._reloj = reloj
        self._por_recinto = {}  # nombre -> {"columnas", "filas", "zonas": {id: Lectura}}
        self._candado = threading.Lock()

    def registrar(self, recinto, columnas, filas, lecturas):
        """Guarda las lecturas. Si cambió la división en zonas, las lecturas
        anteriores ya no se corresponden con las zonas nuevas y se descartan."""
        ahora = self._reloj()
        with self._candado:
            actual = self._por_recinto.get(recinto)
            if actual is None or (actual["columnas"], actual["filas"]) != (columnas, filas):
                actual = {"columnas": columnas, "filas": filas, "zonas": {}}
                self._por_recinto[recinto] = actual
            for lectura in lecturas:
                actual["zonas"][lectura["zona"]] = Lectura(
                    sensor=lectura["sensor"],
                    zona=lectura["zona"],
                    personas=lectura["personas"],
                    momento=lectura.get("momento"),
                    recibida=ahora,
                )

    def estado(self, recinto):
        """None si nunca llegó nada; si no, (columnas, filas, {zona: (Lectura, edad_s, estado)})."""
        ahora = self._reloj()
        with self._candado:
            actual = self._por_recinto.get(recinto)
            if actual is None:
                return None
            zonas = {}
            for zona, lectura in actual["zonas"].items():
                edad = max(0.0, ahora - lectura.recibida)
                zonas[zona] = (lectura, edad, ACTIVO if edad <= self.caducidad_s else SIN_SENAL)
            return actual["columnas"], actual["filas"], zonas

    def ocupacion_vigente(self, recinto):
        """Lo que se puede usar para simular: (columnas, filas, {zona: personas})
        solo con las zonas ACTIVAS, o None si no hay ninguna."""
        estado = self.estado(recinto)
        if estado is None:
            return None
        columnas, filas, zonas = estado
        conteos = {zona: lectura.personas for zona, (lectura, _, situacion) in zonas.items() if situacion == ACTIVO}
        return (columnas, filas, conteos) if conteos else None
