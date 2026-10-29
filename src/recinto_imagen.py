"""Recinto a partir de una imagen dibujada: procesamiento de imagen clásico,
sin IA. El plano se dibuja en cualquier programa (Paint, Preview, una foto de
un dibujo en papel) con una convención de colores:

    negro (oscuro)   pared
    verde            salida
    cualquier otro   piso (el blanco, un gris claro, el fondo)

Después se achica el dibujo a una grilla: cada celda mira el bloque de píxeles
que le corresponde y decide si es pared, salida o piso. El resultado es el
mismo `Recinto` que sale de un plano de texto (ver recinto.py), así que el
resto del proyecto no se entera de dónde vino.

Un detalle que importa: al achicar, una pared fina puede quedar partida entre
dos celdas y perderse, abriendo un hueco donde no lo hay. Para evitarlo, una
celda cuenta como pared (o salida) si tiene al menos `grosor_minimo / 2`
"líneas" de píxeles de ese color cruzándola. Así cualquier línea de
`grosor_minimo` píxeles o más sobrevive aunque caiga justo en el borde entre
dos celdas; a cambio, esa línea puede salir de 2 celdas de ancho. Las líneas
más finas que `grosor_minimo` pueden perderse.

Como el resultado depende del tamaño del dibujo y de cuántas celdas se pidan,
conviene revisarlo antes de simular. Desde la línea de comandos:

    venv/bin/python -m src.recinto_imagen plano.png --ancho 40
    venv/bin/python -m src.recinto_imagen plano.png --ancho 40 --guardar recintos/mi_plano.txt

imprime el plano de texto resultante (se puede corregir a mano) y, si se pide,
lo guarda.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from src.recinto import Recinto, RecintoInvalido, recinto_a_texto

GROSOR_MINIMO_POR_DEFECTO = 2  # en pixeles

# luminancia por debajo de la cual un pixel se considera "oscuro" (0 a 255)
UMBRAL_OSCURO = 100


def _pixeles_de_salida_y_de_muro(ruta):
    """Devuelve dos matrices de booleanos (una posición por píxel): cuáles son
    verdes (salida) y cuáles son oscuros (pared)."""
    with Image.open(ruta) as original:
        con_alfa = original.convert("RGBA")
    # lo transparente cuenta como blanco (piso), no como negro
    fondo = Image.new("RGBA", con_alfa.size, (255, 255, 255, 255))
    rgb = np.asarray(Image.alpha_composite(fondo, con_alfa).convert("RGB")).astype(int)

    rojo, verde, azul = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    es_verde = (verde >= 100) & (verde >= rojo + 40) & (verde >= azul + 40)
    luminancia = 0.299 * rojo + 0.587 * verde + 0.114 * azul
    # una salida se dibuja encima de la pared, asi que si es verde no es pared
    es_oscuro = (luminancia < UMBRAL_OSCURO) & ~es_verde
    return es_verde, es_oscuro


def _bordes(largo_en_pixeles, cantidad_de_celdas):
    """Dónde empieza cada celda dentro de la imagen (cantidad_de_celdas + 1
    números). Cada bloque mide al menos un píxel."""
    bordes = np.linspace(0, largo_en_pixeles, cantidad_de_celdas + 1).round().astype(int)
    for i in range(1, len(bordes)):
        bordes[i] = max(bordes[i], bordes[i - 1] + 1)
    return np.minimum(bordes, largo_en_pixeles)


def leer_recinto_imagen(ruta, ancho_en_celdas=None, grosor_minimo=GROSOR_MINIMO_POR_DEFECTO):
    """Interpreta una imagen dibujada como plano. Ver la convención en el
    docstring del módulo.

    `ancho_en_celdas` es cuántas celdas de ancho tendrá el recinto (el alto
    sale de las proporciones de la imagen). Sin él, cada píxel es una celda.
    """
    es_salida, es_muro = _pixeles_de_salida_y_de_muro(ruta)
    alto_px, ancho_px = es_salida.shape

    if ancho_en_celdas is None:
        ancho_en_celdas = ancho_px
    if not 1 <= ancho_en_celdas <= ancho_px:
        raise RecintoInvalido(
            f"ancho_en_celdas debe estar entre 1 y {ancho_px} (el ancho de la imagen "
            f"en píxeles); pediste {ancho_en_celdas}."
        )

    lado_de_celda_px = ancho_px / ancho_en_celdas
    alto_en_celdas = max(1, round(alto_px / lado_de_celda_px))
    columnas = _bordes(ancho_px, ancho_en_celdas)
    filas = _bordes(alto_px, alto_en_celdas)

    # ver "grosor_minimo" en el docstring del módulo
    pixeles_necesarios = grosor_minimo / 2 * lado_de_celda_px

    salidas, muros = [], []
    for fila in range(alto_en_celdas):
        y = alto_en_celdas - 1 - fila  # la fila de arriba de la imagen es la y mas alta
        for columna in range(ancho_en_celdas):
            bloque = (
                slice(filas[fila], filas[fila + 1]),
                slice(columnas[columna], columnas[columna + 1]),
            )
            if es_salida[bloque].sum() >= pixeles_necesarios:
                salidas.append((columna, y))
            elif es_muro[bloque].sum() >= pixeles_necesarios:
                muros.append((columna, y))

    if not salidas:
        raise RecintoInvalido(
            "No encontré ninguna salida en la imagen. Las salidas se marcan en "
            "verde; si ya lo están, probá con más celdas de ancho o con un trazo "
            "verde más grueso."
        )

    return Recinto(ancho_en_celdas, alto_en_celdas, sorted(salidas), sorted(muros))


def main():
    parser = argparse.ArgumentParser(
        description="Convierte una imagen dibujada en un plano de texto para revisarlo."
    )
    parser.add_argument("imagen", help="ruta a la imagen (png, jpg, bmp, gif)")
    parser.add_argument("--ancho", type=int, help="celdas de ancho (por defecto, un píxel por celda)")
    parser.add_argument(
        "--grosor",
        type=int,
        default=GROSOR_MINIMO_POR_DEFECTO,
        help="grosor mínimo en píxeles de una línea para que cuente (por defecto %(default)s)",
    )
    parser.add_argument("--guardar", help="guarda el plano de texto en este archivo")
    args = parser.parse_args()

    try:
        recinto = leer_recinto_imagen(args.imagen, args.ancho, args.grosor)
    except RecintoInvalido as error:
        sys.exit(f"Error: {error}")

    texto = recinto_a_texto(recinto)
    print(texto, end="")
    print(
        f"{recinto.ancho}x{recinto.alto} celdas, {len(recinto.muros)} de pared, "
        f"{len(recinto.salidas)} de salida",
        file=sys.stderr,
    )
    if args.guardar:
        Path(args.guardar).write_text(texto, encoding="utf-8")
        print(f"Guardado en {args.guardar}", file=sys.stderr)


if __name__ == "__main__":
    main()
