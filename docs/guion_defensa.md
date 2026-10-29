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
| 4 | Demo en vivo (app web) | 4 min |
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
  - **Simulación**: el modelo y la app web, donde se diseña el recinto, se
    simula y se compara.
  - **Big Data y análisis**: corridas Monte Carlo a CSV analizadas con Pandas, y
    la pestaña *Comparar* de la app, que repite cada recinto con varias semillas.
  - **IoT**: propuesta de arquitectura (ver [iot.md](iot.md)); aclarar que **no
    está implementada**.

## 3. Cómo funciona el modelo

Apoyarse en [arquitectura.md](arquitectura.md).

- Una grilla donde cada celda admite una persona, con salidas y muros.
- **El recinto lo define el usuario**: se dibuja con el mouse, se importa de una
  imagen dibujada (negro pared, verde salida, sin inteligencia artificial) o se
  escribe como texto.
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
venv/bin/uvicorn web.app:app --port 8000
```

Abrir `http://localhost:8000`. La app **funciona sin conexión** (las librerías y
las fuentes están dentro del proyecto). Los números siguientes son los de la
sala con puerta (15x10, con una pared y una puerta de una celda), con 40
peatones y la semilla 1, así que se repiten idénticos:

| Vecindad | Sin nada | Fricción 60% | Pánico 60% |
|---|---|---|---|
| 4 direcciones (`von_neumann`, el valor por defecto de la app) | 55 pasos | 86 pasos | 187 pasos |
| 8 direcciones (`moore`, se elige en el panel) | 49 pasos | 88 pasos | 108 pasos |

Guion de la demo (unos 4 minutos):

1. **Diseño (1 min).** Abrir `sala_con_puerta` desde "Recintos guardados" o
   dibujar un recinto simple (pared con `W`, salida con `E`). Mostrar que el
   estado de validación avisa en vivo y que **sin una salida no deja guardar ni
   simular**. Decir que el plano también se puede importar de un dibujo o
   escribir como texto.
2. **Simular (2 min).** Apretar "Simular este diseño" (o elegir la sala con
   puerta) y reproducir. Señalar los peatones **bloqueados en rojo**
   amontonados en la puerta y la tarjeta "Bloqueados ahora": con esta semilla
   llegan a **26 de 40 a la vez**. Al terminar: **55 pasos**.
   - Subir la **fricción a 60%** y "Aplicar y reiniciar": termina en **86**.
     Explicar que es el roce y los empujones en la puerta.
   - Volver la fricción a 0, subir el **pánico a 60%** y reiniciar: la gente deja
     de ir directo a la salida y sigue a los demás; termina en **187**.
   - Mostrar el **peatón seguido** (anillo violeta con su recorrido) para ver
     cuánto tiempo pasa quieto en la cola.
3. **Comparar (1 min).** Elegir `sala_con_puerta` y `dos_salidas`, 40 peatones y
   10 semillas, y ejecutar. Resultado: **`dos_salidas` evacúa 48% más rápido**
   (28,0 contra 53,8 pasos medios, con desvíos de ±3,1 y ±2,8). El P95 es 33
   contra 58 pasos y la congestión máxima, 41% contra 65% de la gente. Aclarar que
   todos los recintos corren con las **mismas semillas**: la única diferencia es
   el recinto.

Las apps de Solara (`app.py` y `editor.py`) siguen funcionando, pero la demo se
hace con la app web.

Plan B si la demo falla: tener una grabación de pantalla o un GIF de la
simulación ya hechos (ver el pendiente en el tablero) y, aparte, las imágenes
de los gráficos del notebook y las capturas del informe de la Fase 1.

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

Mostrar los dos gráficos del notebook (barras y curva de evacuación). La
pestaña *Comparar* de la app aplica el mismo método a recintos dibujados por el
usuario.

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
- Una pared **dibujada en diagonal deja pasar gente** con vecindad de 8
  direcciones (dos paredes que se tocan solo por la esquina). Lo encontramos al
  hacer el editor; con 4 direcciones no ocurre. Está documentado y cubierto por
  un test.

## 7. Limitaciones y trabajo futuro

- Una celda es una persona y un paso no tiene duración calibrada: sirve para
  **comparar configuraciones**, no para predecir tiempos reales.
- No está validado contra datos de evacuaciones reales.
- El recinto lo define el usuario, pero **sin escala real**. El importador de
  dibujos no detecta puertas ni interpreta planos reales de un edificio (con
  escala, ruido y símbolos): las salidas se marcan a mano en verde.
- La pestaña *Comparar* muestra media, desvío y P95, pero **todavía no hay un
  test estadístico formal** que diga si una diferencia es significativa. Es el
  siguiente paso para el análisis.
- IoT queda como propuesta de arquitectura. Siguiente paso: un prototipo con
  sensores simulados que alimenten la simulación a través de la API.
- Otras mejoras ya anotadas: mapa de calor de densidad, escenarios
  predeterminados y exportar la simulación como GIF.

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
reproducible. Todavía no calculamos un test de significancia formal, y lo
decimos como limitación.

**¿Por qué con pánico 1.0 no termina?**
Porque ningún peatón tiene un momento de lucidez: grupos chicos se siguen
entre sí sin cruzar la salida. Con probabilidades menores a 1 siempre hay una
chance de actuar racionalmente y salir.

**¿Dónde está el IoT?**
Es una propuesta de arquitectura, no está implementada. Está descripta en
[iot.md](iot.md): qué sensores aportarían datos, cómo alimentarían al
simulador y qué le faltaría al código para soportarlo. Ahora que existe la API
web, el siguiente paso es un prototipo con sensores simulados.

**¿Por qué el default es Von Neumann y no Moore?**
Con 4 direcciones un muro de una celda obliga a dar un desvío real y los
cuellos de botella se notan; con diagonales se esquivan casi gratis. Además, con
diagonales una pared dibujada en diagonal deja pasar gente. Las dos están
disponibles en la app y comparadas.

**¿El dibujo del plano usa inteligencia artificial?**
No. Es procesamiento de imagen clásico: se achica el dibujo a una grilla y cada
celda decide si es pared, salida o piso según el color de sus píxeles. Una
regla de grosor mínimo evita que una pared fina se pierda entre dos celdas.
Detectar puertas o la escala en planos reales sí sería un problema abierto.

**¿Qué pasa si el recinto dibujado no tiene salida o tiene una zona cerrada?**
La validación no deja guardar ni simular un plano sin salida, y el modelo no
ubica peatones en celdas que no tienen camino a una salida.

**¿Qué tecnología usa la app web?**
Un servidor FastAPI que usa el mismo modelo, y una pantalla en HTML, CSS y
JavaScript sin frameworks. Todo está dentro del proyecto, así que funciona sin
conexión. El diseño visual se hizo con Google Stitch y se adaptó para mostrar
solo datos que el modelo realmente calcula.

## Lista de chequeo antes de presentar

- [ ] `venv/bin/python -m pytest tests/ -q` pasa.
- [ ] La app web abre en `http://localhost:8000`, se puede dibujar, guardar,
      simular y comparar.
- [ ] Probar la app **sin conexión** (desconectar el wifi) en la computadora y
      la pantalla donde se va a presentar.
- [ ] Verificar que los números de la demo (55, 86 y 187 pasos; 53,8 contra 28,0
      en Comparar) dan igual en esa máquina.
- [ ] Tener el plan B (grabación o GIF) y las imágenes de los gráficos listas.
- [ ] Probar la instalación desde cero (venv nuevo e `pip install -r
      requirements.txt`).
