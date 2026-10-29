import pytest

from src.editor_recinto import (
    a_texto,
    con_borde,
    desde_texto,
    grilla_inicial,
    guardar,
    listar_recintos,
    pintar,
    redimensionar,
    validar,
)
from src.recinto import cargar_recinto, recinto_a_texto


def test_la_grilla_inicial_tiene_pared_en_el_borde_y_el_resto_vacio():
    filas = grilla_inicial(5, 4)

    assert filas == ["#####", "#...#", "#...#", "#####"]


def test_pintar_cambia_solo_la_celda_pedida_y_no_modifica_el_original():
    original = ["...", "...", "..."]

    nuevas = pintar(original, x=2, y=1, caracter="#")

    assert nuevas == ["...", "..#", "..."]
    assert original == ["...", "...", "..."]


@pytest.mark.parametrize("x, y", [(-1, 0), (3, 0), (0, -1), (0, 2)])
def test_pintar_fuera_del_plano_no_hace_nada(x, y):
    filas = ["...", "..."]

    assert pintar(filas, x, y, "#") == filas


def test_redimensionar_conserva_lo_dibujado_y_rellena_con_piso():
    filas = ["#S", "#."]

    assert redimensionar(filas, 3, 3) == ["#S.", "#..", "..."]


def test_redimensionar_recorta_lo_que_sobra():
    filas = ["#S.", "#..", "..#"]

    assert redimensionar(filas, 2, 2) == ["#S", "#."]


def test_con_borde_no_tapa_las_salidas_que_ya_estaban():
    filas = ["S..", "...", "..."]

    assert con_borde(filas) == ["S##", "#.#", "###"]


def test_sin_salida_no_es_valido_y_con_salida_si():
    sin_salida = grilla_inicial(5, 4)
    con_salida = pintar(sin_salida, 4, 1, "S")

    assert "ninguna salida" in validar(sin_salida)
    assert validar(con_salida) is None


def test_lo_que_se_edita_es_lo_que_lee_el_modelo(tmp_path):
    filas = pintar(pintar(grilla_inicial(6, 4), 5, 2, "S"), 3, 1, "#")

    ruta = guardar("mi_sala", filas, carpeta=tmp_path)
    recinto = cargar_recinto(ruta)

    assert recinto_a_texto(recinto) == a_texto(filas)
    assert recinto.salidas == [(5, 1)]  # la fila 2 desde arriba, en un plano de alto 4


def test_guardar_no_pisa_un_archivo_existente_salvo_que_se_pida(tmp_path):
    filas = pintar(grilla_inicial(5, 4), 4, 1, "S")
    guardar("sala", filas, carpeta=tmp_path)

    with pytest.raises(FileExistsError, match="sobrescribir"):
        guardar("sala", filas, carpeta=tmp_path)
    guardar("sala", filas, carpeta=tmp_path, sobrescribir=True)  # no falla


@pytest.mark.parametrize("nombre", ["", "../afuera", "con espacio", "sala.txt", "a/b"])
def test_guardar_rechaza_nombres_que_no_son_un_nombre_de_archivo_simple(tmp_path, nombre):
    filas = pintar(grilla_inicial(5, 4), 4, 1, "S")

    with pytest.raises(ValueError, match="nombre"):
        guardar(nombre, filas, carpeta=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_guardar_rechaza_un_plano_sin_salida(tmp_path):
    with pytest.raises(ValueError, match="ninguna salida"):
        guardar("sala", grilla_inicial(5, 4), carpeta=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_se_pueden_listar_y_reabrir_los_recintos_guardados(tmp_path):
    guardar("uno", pintar(grilla_inicial(5, 4), 4, 1, "S"), carpeta=tmp_path)
    guardar("dos", pintar(grilla_inicial(6, 4), 5, 1, "S"), carpeta=tmp_path)

    assert listar_recintos(tmp_path) == ["dos", "uno"]
    assert desde_texto((tmp_path / "uno.txt").read_text()) == pintar(grilla_inicial(5, 4), 4, 1, "S")


def test_los_recintos_de_ejemplo_se_pueden_abrir_en_el_editor():
    nombres = listar_recintos()

    assert {"sala_con_puerta", "dos_salidas"} <= set(nombres)
    for nombre in nombres:
        filas = desde_texto(recinto_a_texto(cargar_recinto(nombre)))
        assert validar(filas) is None
