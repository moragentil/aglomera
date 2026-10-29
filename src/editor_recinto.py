"""Lógica del editor visual de recintos, sin nada de interfaz.

El editor (editor.py) dibuja una grilla donde se pinta con el mouse, pero todo
lo que *decide algo* vive acá, para poder probarlo sin abrir un navegador. El
plano se guarda como una lista de filas de texto, la de arriba primero, con los
mismos caracteres que el formato de recinto.py (# pared, S salida, . piso): así
lo que se edita es lo mismo que se guarda y lo que lee `cargar_recinto`.
"""

import re
from pathlib import Path

from src.recinto import (
    CARPETA_RECINTOS,
    MURO,
    PISO,
    SALIDA,
    RecintoInvalido,
    leer_recinto_texto,
    recinto_a_texto,
)

ANCHO_POR_DEFECTO, ALTO_POR_DEFECTO = 30, 16

# lo que cada herramienta del editor pinta
CARACTER_POR_HERRAMIENTA = {"pared": MURO, "salida": SALIDA, "borrar": PISO}
CLASE_POR_CARACTER = {MURO: "pared", SALIDA: "salida", PISO: "piso"}
CARACTER_POR_CLASE = {clase: caracter for caracter, clase in CLASE_POR_CARACTER.items()}

# solo letras, numeros, guion y guion bajo: el nombre se usa como nombre de archivo
NOMBRE_VALIDO = re.compile(r"^[A-Za-z0-9_-]+$")


def grilla_inicial(ancho=ANCHO_POR_DEFECTO, alto=ALTO_POR_DEFECTO):
    """Un recinto vacío rodeado de pared, sin salidas todavía."""
    return con_borde(redimensionar([], ancho, alto))


def redimensionar(filas, ancho, alto):
    """Cambia el tamaño conservando lo ya dibujado: recorta lo que sobra y
    rellena con piso lo nuevo. Se ancla arriba a la izquierda."""
    filas = [fila.ljust(ancho, PISO)[:ancho] for fila in filas[:alto]]
    filas += [PISO * ancho] * (alto - len(filas))
    return filas


def con_borde(filas):
    """Pone pared en todo el borde (las salidas que ya había se conservan)."""
    if not filas:
        return filas
    ultima_fila, ultima_columna = len(filas) - 1, len(filas[0]) - 1
    resultado = []
    for y, fila in enumerate(filas):
        celdas = list(fila)
        for x in range(len(celdas)):
            en_el_borde = y in (0, ultima_fila) or x in (0, ultima_columna)
            if en_el_borde and celdas[x] != SALIDA:
                celdas[x] = MURO
        resultado.append("".join(celdas))
    return resultado


def pintar(filas, x, y, caracter):
    """Devuelve el plano con la celda (columna x, fila y desde arriba) cambiada.
    Una celda fuera del plano se ignora: un arrastre puede salirse del borde."""
    if not (0 <= y < len(filas) and 0 <= x < len(filas[y])):
        return filas
    if filas[y][x] == caracter:
        return filas
    nuevas = list(filas)
    nuevas[y] = filas[y][:x] + caracter + filas[y][x + 1 :]
    return nuevas


def a_texto(filas):
    return "\n".join(filas) + "\n"


def desde_texto(texto):
    """Las filas de un plano de texto. Falla con RecintoInvalido si no es un plano válido."""
    return recinto_a_texto(leer_recinto_texto(texto)).splitlines()


def validar(filas):
    """None si el plano sirve para simular; si no, un mensaje que explica por qué."""
    try:
        leer_recinto_texto(a_texto(filas))
    except RecintoInvalido as error:
        return str(error)
    return None


def listar_recintos(carpeta=CARPETA_RECINTOS):
    """Nombres de los planos de texto guardados (los que el editor puede abrir)."""
    return sorted(ruta.stem for ruta in Path(carpeta).glob("*.txt"))


def guardar(nombre, filas, carpeta=CARPETA_RECINTOS, sobrescribir=False):
    """Guarda el plano como <carpeta>/<nombre>.txt y devuelve la ruta.

    No pisa un archivo que ya existe salvo que se pida (los planos de ejemplo
    son los que usan los experimentos). Falla con ValueError si el nombre no es
    válido o el plano no sirve para simular.
    """
    if not NOMBRE_VALIDO.match(nombre):
        raise ValueError("El nombre solo puede tener letras, números, guion y guion bajo.")
    problema = validar(filas)
    if problema:
        raise ValueError(f"El plano no se puede guardar: {problema}")

    ruta = Path(carpeta) / f"{nombre}.txt"
    if ruta.exists() and not sobrescribir:
        raise FileExistsError(f"Ya existe {ruta.name}. Elegí otro nombre o marcá sobrescribir.")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(a_texto(filas), encoding="utf-8")
    return ruta
