"""Recinto definido por el usuario: lee un plano y lo convierte en los datos
que ya recibe el modelo (ancho, alto, salidas y muros).

El formato es un archivo de texto con una grilla de caracteres, uno por celda:

    #  muro
    S  salida
    .  piso

La primera línea del archivo es la fila de ARRIBA del recinto, igual que como
se ve dibujado en la app (el eje y de la grilla crece hacia arriba), así que
el plano se lee tal cual se ve en pantalla. Por ejemplo, una sala con una
pared a la mitad y una única puerta:

    .......#.......
    .......#......S
    ...............
    .......#.......

Este módulo no sabe nada de peatones ni del modelo: solo traduce un plano a
datos. Por eso mismo se pueden sumar otras formas de definir el recinto
(una imagen, un editor) sin tocar el resto: todas terminan en un `Recinto`.
"""

from dataclasses import dataclass
from pathlib import Path

CARPETA_RECINTOS = Path(__file__).resolve().parent.parent / "recintos"

MURO, SALIDA, PISO = "#", "S", "."
EXTENSIONES_DE_IMAGEN = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}


class RecintoInvalido(ValueError):
    """El plano no se puede interpretar (caracter desconocido, filas desparejas, sin salida...)."""


@dataclass(frozen=True)
class Recinto:
    ancho: int
    alto: int
    salidas: list
    muros: list

    def como_parametros(self):
        """Los argumentos de EvacuacionModel que describen el recinto."""
        return {
            "ancho": self.ancho,
            "alto": self.alto,
            "salidas": list(self.salidas),
            "muros": list(self.muros),
        }


def leer_recinto_texto(texto):
    """Interpreta un plano escrito como texto. Ver el formato en el docstring del módulo."""
    filas = [linea.rstrip() for linea in texto.splitlines()]
    # las lineas vacias de los bordes (un salto de linea de mas al final, por
    # ejemplo) no son parte del plano; una vacia en el medio si es un error
    while filas and not filas[0]:
        filas.pop(0)
    while filas and not filas[-1]:
        filas.pop()

    if not filas:
        raise RecintoInvalido("El plano está vacío.")

    ancho = len(filas[0])
    alto = len(filas)
    salidas, muros = [], []

    for indice, fila in enumerate(filas):
        numero_de_linea = indice + 1
        if len(fila) != ancho:
            raise RecintoInvalido(
                f"Línea {numero_de_linea}: tiene {len(fila)} caracteres y la primera "
                f"tiene {ancho}. Todas las filas deben medir lo mismo."
            )
        y = alto - 1 - indice  # la primera linea del archivo es la fila de arriba
        for x, caracter in enumerate(fila):
            if caracter == MURO:
                muros.append((x, y))
            elif caracter == SALIDA:
                salidas.append((x, y))
            elif caracter != PISO:
                raise RecintoInvalido(
                    f"Línea {numero_de_linea}, columna {x + 1}: el caracter {caracter!r} "
                    f"no es válido (usá {MURO!r} muro, {SALIDA!r} salida o {PISO!r} piso)."
                )

    if not salidas:
        raise RecintoInvalido(f"El plano no tiene ninguna salida ({SALIDA!r}).")

    # ordenados por (x, y) para que el resultado no dependa de como se recorrio
    return Recinto(ancho, alto, sorted(salidas), sorted(muros))


def recinto_a_texto(recinto):
    """Lo inverso de `leer_recinto_texto`: el plano como texto, listo para guardar o revisar."""
    muros, salidas = set(recinto.muros), set(recinto.salidas)
    filas = []
    for y in range(recinto.alto - 1, -1, -1):  # arriba primero
        filas.append(
            "".join(
                MURO if (x, y) in muros else SALIDA if (x, y) in salidas else PISO
                for x in range(recinto.ancho)
            )
        )
    return "\n".join(filas) + "\n"


def cargar_recinto(nombre_o_ruta, ancho_en_celdas=None):
    """Carga un recinto por nombre o por ruta a un archivo.

    Por nombre (`sala_con_puerta`) busca recintos/sala_con_puerta.txt y, si no
    está, recintos/sala_con_puerta.png. Un archivo de texto es un plano de
    caracteres; una imagen (png, jpg, bmp, gif) es un dibujo, y para ella
    `ancho_en_celdas` dice cuántas celdas de ancho tiene el recinto (ver
    recinto_imagen.py). Para un archivo de texto `ancho_en_celdas` no se usa.
    """
    ruta = Path(nombre_o_ruta)
    if ruta.suffix == "" and not ruta.exists():
        candidatas = [CARPETA_RECINTOS / f"{nombre_o_ruta}{extension}" for extension in (".txt", ".png")]
        ruta = next((c for c in candidatas if c.exists()), candidatas[0])
    if not ruta.exists():
        raise FileNotFoundError(f"No encuentro el recinto {nombre_o_ruta!r} (busqué {ruta}).")

    if ruta.suffix.lower() in EXTENSIONES_DE_IMAGEN:
        # import aca adentro porque recinto_imagen importa este modulo
        from src.recinto_imagen import leer_recinto_imagen

        return leer_recinto_imagen(ruta, ancho_en_celdas)
    return leer_recinto_texto(ruta.read_text(encoding="utf-8"))
