"""Los datos que acepta la API web (esquemas de pydantic).

Pydantic valida cada pedido antes de que llegue a la lógica: un valor fuera
de rango o un campo que falta se rechaza con un mensaje claro (HTTP 422) en
vez de explotar adentro del modelo.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Parametros(BaseModel):
    """Lo que se puede cambiar de la simulación (los sliders de la pantalla)."""

    num_agentes: int = Field(40, ge=1, le=1000)
    probabilidad_agresivo: float = Field(0.0, ge=0, le=1)
    probabilidad_friccion: float = Field(0.0, ge=0, le=1)
    probabilidad_panico: float = Field(0.0, ge=0, le=1)
    # von_neumann por defecto: con diagonales (moore) una pared dibujada en
    # diagonal deja pasar gente (ver README)
    tipo_vecindad: Literal["von_neumann", "moore"] = "von_neumann"


class ParametrosSimulacion(Parametros):
    semilla: int = Field(1, ge=0)


class Plano(BaseModel):
    """Un recinto: o el nombre de uno guardado, o las filas de un plano que
    todavía no se guardó (por ejemplo el que se está dibujando)."""

    recinto: str | None = None
    filas: list[str] | None = None
    etiqueta: str | None = Field(None, max_length=60)

    @model_validator(mode="after")
    def _uno_solo(self):
        if (self.recinto is None) == (self.filas is None):
            raise ValueError("Indicá el plano con 'recinto' (nombre) o con 'filas', pero no con los dos.")
        return self


class Filas(BaseModel):
    filas: list[str]


class RecintoAGuardar(BaseModel):
    nombre: str = Field(max_length=60)
    filas: list[str]
    sobrescribir: bool = False


class NuevaSimulacion(BaseModel):
    plano: Plano
    parametros: ParametrosSimulacion = ParametrosSimulacion()
    # "sensores": ubicar a los peatones segun la ocupacion medida por zona (solo
    # para un recinto guardado) en vez de al azar; num_agentes no se usa
    ocupacion: Literal["azar", "sensores"] = "azar"


class Pasos(BaseModel):
    cantidad: int = Field(1, ge=1, le=50)


class NuevaComparacion(BaseModel):
    planos: list[Plano] = Field(min_length=2, max_length=8)
    semillas: int = Field(10, ge=2, le=30)
    parametros: Parametros = Parametros()
    pasos_maximos: int = Field(1000, ge=10, le=5000)


class LecturaEntrada(BaseModel):
    """Lo que informa un sensor: cuanta gente cuenta en una zona."""

    sensor: str = Field("sensor", min_length=1, max_length=40)
    zona: str = Field(pattern=r"^[A-Z][0-9]{1,2}$")
    personas: int = Field(ge=0, le=100_000)
    momento: datetime | None = None  # marca de tiempo del sensor (informativa)


class LecturasEntrada(BaseModel):
    """Un mensaje de un gateway: la division en zonas que usa y sus lecturas."""

    columnas: int = Field(ge=1, le=26)
    filas: int = Field(ge=1, le=40)
    lecturas: list[LecturaEntrada] = Field(min_length=1, max_length=200)


class SimuladorDeSensores(BaseModel):
    """Para encender los sensores simulados desde la pantalla."""

    columnas: int = Field(3, ge=1, le=26)
    filas: int = Field(2, ge=1, le=40)
    total: int = Field(40, ge=1, le=2000)  # personas que hay en el recinto
    escenario: Literal["parejo", "concentrado"] = "parejo"
    zona_llena: str | None = Field(None, pattern=r"^[A-Z][0-9]{1,2}$")
    intervalo_s: float = Field(2.0, ge=0.1, le=30)
    falla: bool = False  # el sensor de la ultima zona deja de reportar tras unos envios
