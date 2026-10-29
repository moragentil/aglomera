"""Interfaz del editor visual de recintos (Solara). La lógica está en
editor_recinto.py; acá solo se arma la pantalla y se conecta con esa lógica."""

from typing import Callable

import solara

from src import editor_recinto as editor
from src.recinto import RecintoInvalido, leer_recinto_texto

LADO_DE_CELDA_PX = 18
HERRAMIENTAS = ["pared", "salida", "borrar"]


@solara.component_vue("grilla_editable.vue")
def GrillaEditable(
    ancho: int,
    celdas: list,
    herramienta: str,
    lado: int,
    event_pintar: Callable,
):
    pass


@solara.component
def Page():
    filas, set_filas = solara.use_state(editor.grilla_inicial())
    herramienta, set_herramienta = solara.use_state("pared")
    nombre, set_nombre = solara.use_state("mi_plano")
    sobrescribir, set_sobrescribir = solara.use_state(False)
    resultado, set_resultado = solara.use_state(None)  # (tipo, mensaje) o None
    abierto, set_abierto = solara.use_state(None)

    ancho, alto = len(filas[0]), len(filas)

    def pintar(dato):
        # la grilla avisa con el nombre de la clase de celda ("pared", "salida" o "piso")
        caracter = editor.CARACTER_POR_CLASE[dato["herramienta"]]
        # forma funcional: varios eventos seguidos (un arrastre) no se pisan entre si
        set_filas(lambda actuales: editor.pintar(actuales, dato["x"], dato["y"], caracter))
        set_resultado(None)

    def cambiar_tamano(nuevo_ancho, nuevo_alto):
        set_filas(editor.redimensionar(filas, nuevo_ancho, nuevo_alto))
        set_resultado(None)

    def abrir(nombre_del_plano):
        if nombre_del_plano is None:
            return
        ruta = editor.CARPETA_RECINTOS / f"{nombre_del_plano}.txt"
        try:
            set_filas(editor.desde_texto(ruta.read_text(encoding="utf-8")))
        except (OSError, RecintoInvalido) as error:
            set_resultado(("error", f"No pude abrir {nombre_del_plano}: {error}"))
            return
        set_abierto(nombre_del_plano)
        set_nombre(nombre_del_plano)
        set_sobrescribir(False)
        set_resultado(None)

    def guardar():
        try:
            ruta = editor.guardar(nombre, filas, sobrescribir=sobrescribir)
        except (ValueError, FileExistsError) as error:
            set_resultado(("error", str(error)))
            return
        set_resultado(("exito", f"Guardado en recintos/{ruta.name}"))

    problema = editor.validar(filas)
    celdas = [editor.CLASE_POR_CARACTER[c] for fila in filas for c in fila]
    clase_de_herramienta = {"pared": "pared", "salida": "salida", "borrar": "piso"}[herramienta]

    with solara.Column(style={"padding": "16px", "max-width": "1500px"}):
        solara.Markdown("## Editor de recintos")
        solara.Markdown(
            "Elegí una herramienta y **hacé clic o arrastrá** sobre la grilla. "
            "La fila de arriba del dibujo es la de arriba del recinto."
        )

        with solara.Row(style={"align-items": "center", "gap": "24px", "flex-wrap": "wrap"}):
            solara.ToggleButtonsSingle(
                value=herramienta,
                values=HERRAMIENTAS,
                on_value=set_herramienta,
            )
            solara.Button("Borde de pared", on_click=lambda: set_filas(editor.con_borde(filas)), outlined=True)
            solara.Button(
                "Limpiar",
                on_click=lambda: set_filas(editor.grilla_inicial(ancho, alto)),
                outlined=True,
            )
            solara.Select(
                "Abrir un recinto",
                values=editor.listar_recintos(),
                value=abierto,
                on_value=abrir,
            )

        with solara.Row(style={"gap": "24px", "flex-wrap": "wrap"}):
            with solara.Column(style={"min-width": "220px"}):
                solara.SliderInt(
                    f"Ancho: {ancho} celdas",
                    value=ancho,
                    min=5,
                    max=60,
                    on_value=lambda v: cambiar_tamano(v, alto),
                )
            with solara.Column(style={"min-width": "220px"}):
                solara.SliderInt(
                    f"Alto: {alto} celdas",
                    value=alto,
                    min=5,
                    max=40,
                    on_value=lambda v: cambiar_tamano(ancho, v),
                )

        GrillaEditable(
            ancho=ancho,
            celdas=celdas,
            herramienta=clase_de_herramienta,
            lado=LADO_DE_CELDA_PX,
            event_pintar=pintar,
        )

        if problema:
            solara.Warning(f"Todavía no sirve para simular: {problema}", icon=True)
        else:
            salidas = leer_recinto_texto(editor.a_texto(filas)).salidas
            solara.Success(f"Plano válido: {ancho}x{alto} celdas y {len(salidas)} de salida.", icon=True)

        with solara.Row(style={"align-items": "center", "gap": "16px", "flex-wrap": "wrap"}):
            solara.InputText("Nombre del archivo", value=nombre, on_value=set_nombre)
            solara.Checkbox(label="Sobrescribir si ya existe", value=sobrescribir, on_value=set_sobrescribir)
            solara.Button("Guardar", on_click=guardar, color="primary", disabled=problema is not None)

        if resultado is not None:
            tipo, mensaje = resultado
            if tipo == "exito":
                solara.Success(mensaje, icon=True)
                solara.Markdown(
                    "Para simularlo:\n\n"
                    f"```bash\nAGLOMERA_RECINTO={nombre} venv/bin/solara run app.py\n```"
                )
            else:
                solara.Error(mensaje, icon=True)
