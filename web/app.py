"""La API web de Aglomera (FastAPI) y el servidor de la pantalla.

    venv/bin/uvicorn web.app:app --port 8000

Las rutas solo traducen pedidos HTTP a llamadas de servicios.py (la lógica) y
de src/ (el modelo, los recintos y el editor); acá no hay reglas de negocio.
Todo lo que está bajo /api devuelve JSON; el resto es la pantalla (web/static).
"""

import random
import time
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
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
from src.zonas import ubicar_por_zona, zonas_en_grilla
from web import servicios
from web.modelos import (
    Filas,
    LecturasEntrada,
    NuevaComparacion,
    NuevaSimulacion,
    Pasos,
    Plano,
    RecintoAGuardar,
    SimuladorDeSensores,
)
from web.generador_sensores import GeneradorDeSensores
from web.sensores import ACTIVO, CADUCIDAD_POR_DEFECTO_S, SIN_DATOS, RegistroDeSensores

CARPETA_ESTATICA = Path(__file__).resolve().parent / "static"

class ArchivosDeLaPantalla(StaticFiles):
    """Sirve la pantalla pidiéndole al navegador que revalide siempre: sin esto
    puede mostrar una copia vieja del HTML o del JavaScript después de un cambio
    (con ETag, si no cambió no se vuelve a descargar)."""

    async def get_response(self, path, scope):
        respuesta = await super().get_response(path, scope)
        respuesta.headers["Cache-Control"] = "no-cache"
        return respuesta


# el nombre de un recinto se usa como nombre de archivo: solo caracteres seguros
NombreDeRecinto = Annotated[str, RutaParam(pattern=r"^[A-Za-z0-9_-]+$", max_length=60)]


def crear_app(
    carpeta_recintos=CARPETA_RECINTOS,
    reloj=time.time,
    caducidad_s=CADUCIDAD_POR_DEFECTO_S,
    sensores_en_segundo_plano=True,
):
    carpeta = Path(carpeta_recintos)
    app = FastAPI(title="Aglomera", docs_url="/api/docs", openapi_url="/api/openapi.json")
    sesiones = servicios.Sesiones()
    registro = RegistroDeSensores(caducidad_s, reloj)  # `reloj` se inyecta para poder probar la caducidad
    generador = GeneradorDeSensores(registro, sensores_en_segundo_plano)

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

    # ------------------------------------------------------------- sensores
    # Prototipo de la capa de IoT (docs/iot.md): los sensores informan cuanta
    # gente hay en cada zona y la simulacion puede arrancar con esa ocupacion.

    def zonas_de(recinto, columnas, filas):
        try:
            return zonas_en_grilla(recinto, columnas, filas)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    def describir(zona):
        return {
            "id": zona.id,
            "columna": zona.columna,
            "fila": zona.fila,
            "ancho": zona.ancho,
            "alto": zona.alto,
            "capacidad": zona.capacidad,
        }

    def ubicar_con_sensores(datos, recinto):
        if datos.plano.recinto is None:
            raise HTTPException(422, "La ocupación medida solo está disponible para recintos guardados.")
        vigente = registro.ocupacion_vigente(datos.plano.recinto)
        if vigente is None:
            raise HTTPException(409, "No hay lecturas vigentes de sensores para este recinto.")
        columnas, filas, conteos = vigente
        zonas = zonas_de(recinto, columnas, filas)
        permitidas = servicios.celdas_alcanzables(recinto, datos.parametros.tipo_vecindad)
        posiciones, avisos = ubicar_por_zona(
            zonas, conteos, permitidas, random.Random(datos.parametros.semilla)
        )
        if not posiciones:
            raise HTTPException(
                422, "Las lecturas vigentes no registran a nadie en el recinto: no hay a quién simular."
            )
        return posiciones, conteos, avisos

    @app.get("/api/recintos/{nombre}/zonas")
    def zonas_del_recinto(
        nombre: NombreDeRecinto,
        columnas: int = Query(3, ge=1, le=26),
        filas: int = Query(2, ge=1, le=40),
    ):
        return [describir(zona) for zona in zonas_de(cargar(nombre), columnas, filas)]

    @app.post("/api/sensores/{nombre}")
    def recibir_lecturas(nombre: NombreDeRecinto, datos: LecturasEntrada):
        zonas = zonas_de(cargar(nombre), datos.columnas, datos.filas)
        desconocidas = sorted({l.zona for l in datos.lecturas} - {z.id for z in zonas})
        if desconocidas:
            raise HTTPException(
                422,
                f"Con {datos.columnas}x{datos.filas} zonas no existen: {', '.join(desconocidas)}.",
            )
        registro.registrar(
            nombre, datos.columnas, datos.filas, [l.model_dump(mode="json") for l in datos.lecturas]
        )
        return {"recibidas": len(datos.lecturas)}

    @app.get("/api/sensores/{nombre}")
    def estado_de_los_sensores(nombre: NombreDeRecinto):
        recinto = cargar(nombre)
        estado = registro.estado(nombre)
        simulador = generador.estado(nombre)
        if estado is None:
            return {"hay_datos": False, "caducidad_s": registro.caducidad_s, "zonas": [], "simulador": simulador}
        columnas, filas, lecturas = estado
        zonas = []
        for zona in zonas_de(recinto, columnas, filas):
            fila = describir(zona)
            if zona.id in lecturas:
                lectura, edad, situacion = lecturas[zona.id]
                fila.update(personas=lectura.personas, sensor=lectura.sensor, momento=lectura.momento,
                            edad_s=round(edad, 1), estado=situacion)
            else:
                fila.update(personas=None, sensor=None, momento=None, edad_s=None, estado=SIN_DATOS)
            zonas.append(fila)
        vigentes = [z for z in zonas if z["estado"] == ACTIVO]
        return {
            "hay_datos": True,
            "columnas": columnas,
            "filas": filas,
            "caducidad_s": registro.caducidad_s,
            "zonas": zonas,
            "zonas_vigentes": len(vigentes),
            "total_vigente": sum(z["personas"] for z in vigentes),
            "simulador": simulador,
        }

    @app.post("/api/sensores/{nombre}/simulador", status_code=201)
    def encender_sensores_simulados(nombre: NombreDeRecinto, datos: SimuladorDeSensores):
        zonas = zonas_de(cargar(nombre), datos.columnas, datos.filas)
        if datos.zona_llena is not None and datos.zona_llena not in {z.id for z in zonas}:
            raise HTTPException(422, f"La zona {datos.zona_llena} no existe con {datos.columnas}x{datos.filas} zonas.")
        return generador.iniciar(
            nombre, zonas, datos.columnas, datos.filas, datos.total, datos.escenario,
            datos.zona_llena, datos.intervalo_s, datos.falla,
        )

    @app.delete("/api/sensores/{nombre}/simulador", status_code=204)
    def apagar_sensores_simulados(nombre: NombreDeRecinto):
        generador.detener(nombre)

    # ---------------------------------------------------------- simulaciones

    def modelo_de(sesion_id):
        modelo = sesiones.obtener(sesion_id)
        if modelo is None:
            raise HTTPException(404, "La simulación no existe o ya venció. Iniciá una nueva.")
        return modelo

    @app.post("/api/simulaciones", status_code=201)
    def crear_simulacion(datos: NuevaSimulacion):
        etiqueta, recinto = resolver(datos.plano)
        posiciones, conteos, avisos = None, None, []
        if datos.ocupacion == "sensores":
            posiciones, conteos, avisos = ubicar_con_sensores(datos, recinto)
        try:
            modelo = servicios.crear_modelo(
                recinto, datos.parametros, datos.parametros.semilla, True, posiciones
            )
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        sesion_id = sesiones.crear(modelo)
        return {
            "id": sesion_id,
            "plano": {"etiqueta": etiqueta, "ancho": recinto.ancho, "alto": recinto.alto,
                      "filas": filas_de(recinto)},
            "ocupacion": {
                "fuente": datos.ocupacion,
                "total": len(modelo.agents),
                "conteos": conteos,
                "avisos": avisos,
            },
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
    app.mount("/", ArchivosDeLaPantalla(directory=CARPETA_ESTATICA, html=True), name="pantalla")
    return app


app = crear_app()
