"""Sensores simulados que corren dentro del propio servidor.

Es la misma idea que iot/simulador_sensores.py (un gateway de juguete que
informa cuánta gente cuenta cada zona), pero sin necesidad de abrir otra
terminal: se enciende y se apaga con un botón de la pantalla. Es una comodidad
para la demo. Para mostrar cómo sería con un gateway real, que es un programa
aparte que habla con la API por la red, está el script de iot/.

Genera los conteos con las mismas funciones que el script, y los entrega
directamente al registro de lecturas (web/sensores.py), sin pasar por HTTP.
"""

import random
import threading
from datetime import datetime, timezone

from iot.simulador_sensores import (
    conteos_en_un_instante,
    construir_mensaje,
    pesos_del_escenario,
)

ENVIOS_ANTES_DE_LA_FALLA = 5  # "simular una falla": el ultimo sensor se apaga tras estos envios
RUIDO_POR_DEFECTO = 0.15


class _Corrida:
    """Una tanda de sensores simulados de un recinto."""

    def __init__(self, recinto, columnas, filas, ids, capacidades, total, escenario, pesos,
                 intervalo_s, ruido, zona_con_falla, azar):
        self.recinto = recinto
        self.columnas, self.filas = columnas, filas
        self.ids, self.capacidades = ids, capacidades
        self.total, self.escenario, self.pesos = total, escenario, pesos
        self.intervalo_s, self.ruido = intervalo_s, ruido
        self.zona_con_falla = zona_con_falla
        self.azar = azar
        self.envios = 0
        self.parar = threading.Event()
        self.candado = threading.Lock()


class GeneradorDeSensores:
    def __init__(self, registro, en_segundo_plano=True):
        """`en_segundo_plano=False` no lanza el hilo: los envíos se hacen a mano
        con `enviar_ahora` (para probar sin esperar)."""
        self._registro = registro
        self._en_segundo_plano = en_segundo_plano
        self._corridas = {}
        self._candado = threading.Lock()

    def iniciar(self, recinto, zonas, columnas, filas, total, escenario="parejo", zona_llena=None,
                intervalo_s=2.0, falla=False, ruido=RUIDO_POR_DEFECTO, semilla=None):
        """Empieza a informar. Si ya había sensores simulados para ese recinto, los reemplaza.
        El primer envío se hace ya, así que al volver de esta llamada hay datos."""
        self.detener(recinto)
        ids = [zona.id for zona in zonas]
        capacidades = [zona.capacidad for zona in zonas]
        corrida = _Corrida(
            recinto, columnas, filas, ids, capacidades, total, escenario,
            pesos_del_escenario(escenario, capacidades, ids, zona_llena),
            intervalo_s, ruido, ids[-1] if falla else None, random.Random(semilla),
        )
        with self._candado:
            self._corridas[recinto] = corrida
        self._enviar(corrida)
        if self._en_segundo_plano:
            threading.Thread(target=self._bucle, args=(corrida,), daemon=True).start()
        return self.estado(recinto)

    def detener(self, recinto):
        """Apaga los sensores simulados. Las últimas lecturas quedan en el
        registro y caducan solas: las zonas pasan a SIN SEÑAL, como pasaría si
        los sensores reales se apagaran."""
        with self._candado:
            corrida = self._corridas.pop(recinto, None)
        if corrida is None:
            return False
        corrida.parar.set()
        return True

    def enviar_ahora(self, recinto):
        """Un envío más, sin esperar el intervalo. False si no hay sensores simulados."""
        with self._candado:
            corrida = self._corridas.get(recinto)
        if corrida is None:
            return False
        self._enviar(corrida)
        return True

    def estado(self, recinto):
        with self._candado:
            corrida = self._corridas.get(recinto)
        if corrida is None:
            return None
        return {
            "activo": True,
            "total": corrida.total,
            "escenario": corrida.escenario,
            "intervalo_s": corrida.intervalo_s,
            "envios": corrida.envios,
            "zona_con_falla": corrida.zona_con_falla,
            "envios_antes_de_la_falla": ENVIOS_ANTES_DE_LA_FALLA if corrida.zona_con_falla else None,
        }

    # ------------------------------------------------------------ internos

    def _enviar(self, corrida):
        if corrida.parar.is_set():
            return  # ya lo apagaron: no mandar una lectura de mas
        with corrida.candado:
            corrida.envios += 1
            conteos = conteos_en_un_instante(
                corrida.total, corrida.pesos, corrida.capacidades, corrida.ruido, corrida.azar
            )
            silenciadas = (
                {corrida.zona_con_falla}
                if corrida.zona_con_falla and corrida.envios > ENVIOS_ANTES_DE_LA_FALLA
                else set()
            )
            mensaje = construir_mensaje(
                corrida.columnas, corrida.filas, corrida.ids, conteos,
                datetime.now(timezone.utc), silenciadas,
            )
        self._registro.registrar(corrida.recinto, corrida.columnas, corrida.filas, mensaje["lecturas"])

    def _bucle(self, corrida):
        # wait() devuelve True si pidieron parar: ahi se termina el hilo
        while not corrida.parar.wait(corrida.intervalo_s):
            self._enviar(corrida)
