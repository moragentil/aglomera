"""La API web de Aglomera (FastAPI) y el servidor de la pantalla.

    venv/bin/uvicorn web.app:app --port 8000

Las rutas solo traducen pedidos HTTP a llamadas de servicios.py (la lógica) y
de src/ (el modelo, los recintos y el editor); acá no hay reglas de negocio.
Todo lo que está bajo /api devuelve JSON; el resto es la pantalla (web/static).
"""

from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException
from fastapi import Path as RutaParam
from fastapi.staticfiles import StaticFiles

from src import editor_recinto as editor
from src.recinto import (
    CARPETA_RECINTOS,
    RecintoInvalido,
    cargar_recinto,
    leer_recinto_texto,
    recinto_a_texto,
)
from web import servicios
from web.modelos import (
    Filas,
    NuevaComparacion,
    NuevaSimulacion,
    Pasos,
    Plano,
    RecintoAGuardar,
)

CARPETA_ESTATICA = Path(__file__).resolve().parent / "static"

# el nombre de un recinto se usa como nombre de archivo: solo caracteres seguros
NombreDeRecinto = Annotated[str, RutaParam(pattern=r"^[A-Za-z0-9_-]+$", max_length=60)]


def crear_app(carpeta_recintos=CARPETA_RECINTOS):
    carpeta = Path(carpeta_recintos)
    app = FastAPI(title="Aglomera", docs_url="/api/docs", openapi_url="/api/openapi.json")
    sesiones = servicios.Sesiones()

    # --------------------------------------------------------------- ayudas

    def cargar(nombre):
        ruta = carpeta / f"{nombre}.txt"
        if not editor.NOMBRE_VALIDO.match(nombre) or not ruta.exists():
            raise HTTPException(404, f"No existe el recinto '{nombre}'.")
        try:
            return cargar_recinto(ruta)
        except RecintoInvalido as error:
            raise HTTPException(422, f"El recinto '{nombre}' no es válido: {error}") from error

    def resolver(plano: Plano):
        """(etiqueta, Recinto) de un plano guardado o enviado en el pedido."""
        if plano.recinto is not None:
            return plano.etiqueta or plano.recinto, cargar(plano.recinto)
        try:
            return plano.etiqueta or "Diseño actual", leer_recinto_texto(editor.a_texto(plano.filas))
        except RecintoInvalido as error:
            raise HTTPException(422, str(error)) from error

    def filas_de(recinto):
        return recinto_a_texto(recinto).splitlines()

    def resumen(nombre, recinto):
        return {
            "nombre": nombre,
            "ancho": recinto.ancho,
            "alto": recinto.alto,
            "salidas": len(recinto.salidas),
            "paredes": len(recinto.muros),
            "filas": filas_de(recinto),
        }

    # ------------------------------------------------------------- recintos

    @app.get("/api/recintos")
    def listar_recintos():
        recintos = []
        for nombre in editor.listar_recintos(carpeta):
            try:
                recintos.append(resumen(nombre, cargar_recinto(carpeta / f"{nombre}.txt")))
            except RecintoInvalido:
                continue  # un archivo roto no tira abajo la lista
        return recintos

    @app.get("/api/recintos/{nombre}")
    def obtener_recinto(nombre: NombreDeRecinto):
        return resumen(nombre, cargar(nombre))

    @app.post("/api/validar")
    def validar(datos: Filas):
        try:
            recinto = leer_recinto_texto(editor.a_texto(datos.filas))
        except RecintoInvalido as error:
            return {"valido": False, "mensaje": str(error), "salidas": 0, "paredes": 0}
        return {
            "valido": True,
            "mensaje": None,
            "ancho": recinto.ancho,
            "alto": recinto.alto,
            "salidas": len(recinto.salidas),
            "paredes": len(recinto.muros),
        }

    @app.post("/api/recintos", status_code=201)
    def guardar_recinto(datos: RecintoAGuardar):
        try:
            editor.guardar(datos.nombre, datos.filas, carpeta=carpeta, sobrescribir=datos.sobrescribir)
        except FileExistsError as error:
            raise HTTPException(409, str(error)) from error
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        return {"nombre": datos.nombre}

    # ---------------------------------------------------------- simulaciones

    def modelo_de(sesion_id):
        modelo = sesiones.obtener(sesion_id)
        if modelo is None:
            raise HTTPException(404, "La simulación no existe o ya venció. Iniciá una nueva.")
        return modelo

    @app.post("/api/simulaciones", status_code=201)
    def crear_simulacion(datos: NuevaSimulacion):
        etiqueta, recinto = resolver(datos.plano)
        try:
            modelo = servicios.crear_modelo(recinto, datos.parametros, datos.parametros.semilla, True)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        sesion_id = sesiones.crear(modelo)
        return {
            "id": sesion_id,
            "plano": {"etiqueta": etiqueta, "ancho": recinto.ancho, "alto": recinto.alto,
                      "filas": filas_de(recinto)},
            "estado": servicios.estado_de_simulacion(modelo),
        }

    @app.get("/api/simulaciones/{sesion_id}")
    def estado_de_la_simulacion(sesion_id: str):
        return servicios.estado_de_simulacion(modelo_de(sesion_id))

    @app.post("/api/simulaciones/{sesion_id}/pasos")
    def avanzar_simulacion(sesion_id: str, datos: Pasos = Pasos()):
        modelo = modelo_de(sesion_id)
        servicios.avanzar(modelo, datos.cantidad)
        return servicios.estado_de_simulacion(modelo)

    @app.delete("/api/simulaciones/{sesion_id}", status_code=204)
    def borrar_simulacion(sesion_id: str):
        sesiones.eliminar(sesion_id)

    # ---------------------------------------------------------- comparación

    @app.post("/api/comparaciones")
    def comparar(datos: NuevaComparacion):
        planos = [resolver(plano) for plano in datos.planos]
        etiquetas = [etiqueta for etiqueta, _ in planos]
        if len(set(etiquetas)) != len(etiquetas):
            raise HTTPException(422, "Dos de los recintos a comparar tienen el mismo nombre.")
        try:
            return servicios.comparar(planos, datos.semillas, datos.parametros, datos.pasos_maximos)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    # ------------------------------------------------------------- pantalla
    # al final: las rutas de /api tienen prioridad sobre los archivos estaticos
    app.mount("/", StaticFiles(directory=CARPETA_ESTATICA, html=True), name="pantalla")
    return app


app = crear_app()
