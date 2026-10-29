import pytest
from PIL import Image

from src.model import EvacuacionModel
from src.recinto import (
    RecintoInvalido,
    cargar_recinto,
    leer_recinto_texto,
    recinto_a_texto,
)
from src.recinto_imagen import leer_recinto_imagen

NEGRO, BLANCO, VERDE = (0, 0, 0), (255, 255, 255), (0, 200, 0)


def guardar_imagen(tmp_path, ancho, alto, pintar, modo="RGB", fondo=BLANCO):
    """Crea una imagen con fondo blanco y deja que `pintar(imagen)` dibuje encima."""
    imagen = Image.new(modo, (ancho, alto), fondo)
    pintar(imagen)
    ruta = tmp_path / "plano.png"
    imagen.save(ruta)
    return ruta


def rectangulo(imagen, x0, y0, x1, y1, color):
    """Pinta los pixeles con x0 <= x < x1 y y0 <= y < y1."""
    for x in range(x0, x1):
        for y in range(y0, y1):
            imagen.putpixel((x, y), color)


def test_un_pixel_por_celda_con_la_convencion_de_colores(tmp_path):
    def pintar(imagen):
        imagen.putpixel((0, 0), NEGRO)  # arriba a la izquierda: pared
        imagen.putpixel((3, 2), VERDE)  # abajo a la derecha: salida
        imagen.putpixel((1, 1), (200, 200, 200))  # gris claro: piso
        imagen.putpixel((2, 0), (30, 30, 30))  # gris muy oscuro: pared

    recinto = leer_recinto_imagen(guardar_imagen(tmp_path, 4, 3, pintar))

    assert recinto_a_texto(recinto) == "#.#.\n....\n...S\n"


def test_la_fila_de_arriba_de_la_imagen_es_la_y_mas_alta(tmp_path):
    ruta = guardar_imagen(tmp_path, 3, 2, lambda im: im.putpixel((0, 0), VERDE))

    recinto = leer_recinto_imagen(ruta)

    assert recinto.salidas == [(0, 1)]


def test_una_salida_dibujada_sobre_una_pared_sigue_siendo_salida(tmp_path):
    def pintar(imagen):
        imagen.putpixel((1, 0), (0, 128, 0))  # verde oscuro: la luminancia lo haria pared

    recinto = leer_recinto_imagen(guardar_imagen(tmp_path, 3, 1, pintar))

    assert recinto.salidas == [(1, 0)]
    assert recinto.muros == []


def test_lo_transparente_cuenta_como_piso_no_como_pared(tmp_path):
    def pintar(imagen):
        imagen.putpixel((0, 0), (0, 0, 0, 0))  # negro, pero totalmente transparente
        imagen.putpixel((1, 0), VERDE + (255,))

    ruta = guardar_imagen(tmp_path, 3, 1, pintar, modo="RGBA", fondo=(0, 0, 0, 0))
    recinto = leer_recinto_imagen(ruta)

    assert recinto.muros == []
    assert recinto.salidas == [(1, 0)]


def test_achica_el_dibujo_a_la_cantidad_de_celdas_pedida(tmp_path):
    def pintar(imagen):
        rectangulo(imagen, 0, 0, 10, 10, VERDE)  # una celda de 10x10 px

    ruta = guardar_imagen(tmp_path, 100, 50, pintar)
    recinto = leer_recinto_imagen(ruta, ancho_en_celdas=10)

    assert (recinto.ancho, recinto.alto) == (10, 5)  # el alto sale de las proporciones
    assert recinto.salidas == [(0, 4)]


@pytest.mark.parametrize("x_desde", [40, 44, 49])  # centrada, contra un borde, justo en el borde
def test_una_linea_de_2_pixeles_no_se_pierde_aunque_caiga_entre_dos_celdas(tmp_path, x_desde):
    def pintar(imagen):
        rectangulo(imagen, x_desde, 0, x_desde + 2, 50, NEGRO)  # pared vertical fina
        rectangulo(imagen, 0, 0, 10, 10, VERDE)

    recinto = leer_recinto_imagen(guardar_imagen(tmp_path, 100, 50, pintar), ancho_en_celdas=10)

    # la pared cruza las 5 filas (en la columna 4 o en la 5): sin ningun hueco por donde pasar
    for y in range(5):
        assert any(muro_y == y and muro_x in (4, 5) for (muro_x, muro_y) in recinto.muros)


def test_grosor_minimo_permite_ignorar_trazos_demasiado_finos(tmp_path):
    def pintar(imagen):
        rectangulo(imagen, 44, 0, 45, 50, NEGRO)  # una linea de 1 pixel
        rectangulo(imagen, 0, 0, 10, 10, VERDE)

    ruta = guardar_imagen(tmp_path, 100, 50, pintar)

    con_el_default = leer_recinto_imagen(ruta, ancho_en_celdas=10)
    exigiendo_trazos_gruesos = leer_recinto_imagen(ruta, ancho_en_celdas=10, grosor_minimo=4)

    assert len(con_el_default.muros) > 0
    assert exigiendo_trazos_gruesos.muros == []


def test_sin_verde_no_hay_salida_y_el_mensaje_explica_como_marcarla(tmp_path):
    ruta = guardar_imagen(tmp_path, 4, 4, lambda im: None)

    with pytest.raises(RecintoInvalido, match="verde"):
        leer_recinto_imagen(ruta)


@pytest.mark.parametrize("ancho_en_celdas", [0, -3, 101])
def test_rechaza_una_cantidad_de_celdas_imposible(tmp_path, ancho_en_celdas):
    ruta = guardar_imagen(tmp_path, 100, 50, lambda im: im.putpixel((0, 0), VERDE))

    with pytest.raises(RecintoInvalido, match="ancho_en_celdas"):
        leer_recinto_imagen(ruta, ancho_en_celdas=ancho_en_celdas)


def test_un_plano_de_texto_dibujado_como_imagen_se_lee_igual(tmp_path):
    texto = "#####\n#..S#\n#.#.#\nS...#\n#####\n"
    plano = leer_recinto_texto(texto)

    def pintar(imagen):
        for fila, linea in enumerate(texto.splitlines()):
            for x, caracter in enumerate(linea):
                color = {"#": NEGRO, "S": VERDE}.get(caracter)
                if color:
                    rectangulo(imagen, x * 6, fila * 6, x * 6 + 6, fila * 6 + 6, color)

    ruta = guardar_imagen(tmp_path, 30, 30, pintar)

    assert leer_recinto_imagen(ruta, ancho_en_celdas=5) == plano
    assert recinto_a_texto(plano) == texto


def test_cargar_recinto_acepta_imagenes_por_nombre_y_por_ruta():
    por_nombre = cargar_recinto("auditorio", ancho_en_celdas=40)
    por_ruta = cargar_recinto("recintos/auditorio.png", ancho_en_celdas=40)

    assert por_nombre == por_ruta
    assert (por_nombre.ancho, por_nombre.alto) == (40, 25)
    assert len(por_nombre.salidas) == 6  # dos salidas de 3 celdas


def test_el_auditorio_dibujado_se_puede_evacuar_completo():
    recinto = cargar_recinto("auditorio", ancho_en_celdas=40)

    model = EvacuacionModel(**recinto.como_parametros(), num_agentes=40, rng=1)
    while model.running and model.pasos_transcurridos < 1000:
        model.step()

    assert model.todos_evacuaron()
