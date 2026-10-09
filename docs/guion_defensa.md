# Guion de la defensa

Borrador para armar la presentación. Está pensado para unos **15 minutos**
(ajustar los tiempos a lo que den en la cátedra). Todos los números salen de
corridas reales del proyecto; conviene volver a verificarlos en la máquina
donde se va a presentar.

## Estructura

| # | Bloque | Tiempo sugerido |
|---|---|---|
| 1 | El problema y el objetivo | 1 min |
| 2 | Enfoque y pilares de Industria 4.0 | 2 min |
| 3 | Cómo funciona el modelo | 3 min |
| 4 | Demo en vivo | 4 min |
| 5 | Resultados (Monte Carlo) | 3 min |
| 6 | Qué no salió como esperábamos | 1 min |
| 7 | Limitaciones y trabajo futuro | 1 min |

## 1. El problema y el objetivo

- En eventos masivos, la forma del recinto y la cantidad de salidas cambian
  mucho cuánto tarda una evacuación y dónde se amontona la gente.
- Objetivo: simular la evacuación para **detectar puntos de aglomeración** y
  **comparar configuraciones de salidas** sin necesitar un recinto real.

## 2. Enfoque y pilares

- Simulación basada en agentes: cada persona es un agente; los colectivos
  (colas, arqueo, pánico) **emergen**, no están programados.
- Los tres pilares de la materia:
  - **Simulación**: el modelo y el visualizador interactivo.
  - **Big Data y análisis**: corridas Monte Carlo a CSV, analizadas con Pandas.
  - **IoT**: propuesta de arquitectura (ver [iot.md](iot.md)); aclarar que no
    está implementada.

## 3. Cómo funciona el modelo

Apoyarse en [arquitectura.md](arquitectura.md).

- Una grilla donde cada celda admite una persona, con salidas y muros.
- El *floor field*: un mapa con la distancia de cada celda a la salida más
  cercana, calculado una sola vez.
- Cada paso tiene tres fases: **evacuar, decidir, resolver conflictos**. Dos
  personas pueden querer la misma celda al mismo tiempo, y ahí entra la
  **fricción**.
- Comportamientos opcionales: agresividad y pánico/manada.

## 4. Demo en vivo

Preparación (hacerla **antes** de que empiece la defensa):

```bash
cd "<carpeta del proyecto>"
venv/bin/solara run app.py
```

Abrir `http://localhost:8765`. La app arranca con 40 peatones y semilla fija,
así que los resultados se repiten. Los números siguientes son los de esa
configuración (sala de 15x10 con una pared y una puerta de una celda):

| Vecindad (`TIPO_VECINDAD` en `app.py`) | Fricción 0 | Fricción 0.6 | Pánico 0.6 |
|---|---|---|---|
| `von_neumann` | 55 pasos | 86 pasos | 187 pasos |
| `moore` | 49 pasos | 88 pasos | 108 pasos |

Guion de la demo:

1. **Sin nada activado**, apretar `STEP` unas 6 u 8 veces: los peatones
   bloqueados se pintan de **rojo** y se amontonan contra la puerta. Es el
   *arqueo*. Señalar el contador de bloqueados en el título.
2. Apretar play hasta el final y anotar el paso en que termina.
3. Subir **fricción a 0.6**, `RESET` y play: termina bastante más tarde.
   Explicar que es el roce y los empujones en la puerta.
4. Volver la fricción a 0, subir **pánico a 0.6**, `RESET` y play: la gente
   deja de ir directo a la salida y sigue a los demás; termina mucho más tarde.
5. Mostrar el **peatón seguido** (círculo violeta con su recorrido) para ver
   cuánto tiempo pasa quieto en la cola.

Plan B si la demo falla: tener una grabación de pantalla o un GIF de la
simulación ya hechos (ver el pendiente en el tablero) y, aparte, las
imágenes de los gráficos del notebook.

## 5. Resultados (Monte Carlo)

Repetir cada escenario con 10 o más semillas distintas muestra qué tan estable
es el resultado (el desvío), no una corrida con suerte. Todo se regenera con
`venv/bin/python experiments/run_batch.py` (unos segundos) y se analiza en
`notebooks/analisis_resultados.ipynb`.

- **Dos salidas evacúan mucho más rápido que una**, y la ventaja crece con la
  cantidad de gente. Con 90 agentes: 104.9 pasos con una salida contra 62.3
  con dos. El desvío fue de 1 a 4 pasos, así que la diferencia es real.
- **La fricción empeora todo, de forma sostenida.** Con 100 agentes: 144 pasos
  sin fricción, 176 con 0.3 y 243 con 0.6.
- **El pánico empeora la evacuación de forma pronunciada.** Con dos salidas y
  80 agentes: 50 pasos sin pánico, 63 con 0.4 y 229 con 0.8. Con pánico total
  (1.0) ninguna corrida termina y solo ~7 de 80 personas logran salir.
- **El pánico no desbalancea las salidas.** La gente se reparte casi parejo
  entre las dos (unos 39 y 41 de 80) con cualquier nivel de pánico: la
  evacuación se enlentece porque se pierde tiempo siguiendo a otros, no
  porque todos se amontonen en una sola salida.
- **Las diagonales aceleran el tránsito pero no la puerta.** Con Moore la
  evacuación fue ~22% más rápida (113.0 contra 144.1 pasos), pero la
  congestión máxima en la puerta no bajó (88 contra 86 bloqueados a la vez).

Mostrar los dos gráficos del notebook (barras y curva de evacuación).

## 6. Qué no salió como esperábamos

Vale la pena contarlo: muestra que se entienden las hipótesis del modelo.

- La primera versión del "faster is slower" **no funcionó**: con turnos
  secuenciales, la impaciencia hacía evacuar *más rápido*, porque nunca hay un
  conflicto real por una celda. Eso nos llevó a pasar a activación
  sincrónica con fricción, que es el mecanismo que la literatura señala.
- El pánico tuvo un bug real: si era una etiqueta fija, dos peatones en pánico
  cerca de una salida se perseguían en círculo y nunca salían. Se corrigió
  sorteándolo en cada paso.
- Con **pánico total (1.0) la simulación no termina nunca**. Lo tomamos como un
  hallazgo (el pánico absoluto puede impedir escapar), no como un error.

## 7. Limitaciones y trabajo futuro

- Una celda es una persona y un paso no tiene duración calibrada: sirve para
  **comparar configuraciones**, no para predecir tiempos reales.
- No está validado contra datos de evacuaciones reales.
- El recinto está fijo en el código; el siguiente paso es definirlo desde un
  archivo o un editor, e incluso importar un plano.
- IoT queda como propuesta de arquitectura.

## Preguntas que pueden hacer

**¿Por qué un autómata celular y no el modelo de fuerzas sociales?**
Es mucho más liviano y más fácil de razonar y de verificar. Del modelo de
fuerzas tomamos las ideas (destino que atrae, otros que estorban) pero no las
ecuaciones continuas.

**¿Está validado con datos reales?**
No. Los resultados sirven para comparar configuraciones entre sí, no como
pronóstico de tiempos. Calibrarlo sería un trabajo aparte.

**¿Qué significa un "paso"?**
No tiene una equivalencia calibrada en segundos; es una unidad del modelo.

**¿Cómo se asegura que los resultados no son casualidad?**
Con corridas Monte Carlo: cada escenario se repite con varias semillas y se
mira el promedio y el desvío. Las semillas fijas hacen que todo sea
reproducible.

**¿Por qué con pánico 1.0 no termina?**
Porque ningún peatón tiene un momento de lucidez: grupos chicos se siguen
entre sí sin cruzar la salida. Con probabilidades menores a 1 siempre hay una
chance de actuar racionalmente y salir.

**¿Dónde está el IoT?**
Es una propuesta de arquitectura, no está implementada. Está descripta en
[iot.md](iot.md): qué sensores aportarían datos, cómo alimentarían al
simulador y qué le faltaría al código para soportarlo.

**¿Por qué el default es Von Neumann y no Moore?**
Con 4 direcciones un muro de una celda obliga a dar un desvío real y los
cuellos de botella se notan; con diagonales se esquivan casi gratis. Las dos
están disponibles y comparadas.

## Lista de chequeo antes de presentar

- [ ] `venv/bin/python -m pytest tests/ -q` pasa.
- [ ] La app abre en `http://localhost:8765` y los sliders responden.
- [ ] Decidir y dejar fijado `TIPO_VECINDAD` en `app.py` antes de la demo.
- [ ] Anotar los pasos finales de cada escenario de la demo en esta máquina.
- [ ] Tener el plan B (grabación o GIF) y las imágenes de los gráficos listas.
- [ ] Probar en el equipo y la pantalla donde se va a presentar.
