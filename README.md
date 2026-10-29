# Aglomera

Simulación de evacuación de multitudes en eventos masivos, basada en agentes,
para el TP de la materia **Sistemas de la Industria 4.0** (UTN FRLP).

Modela una multitud dentro de un recinto (tipo estadio o recital) para
detectar puntos de aglomeración y comparar configuraciones de salidas de
emergencia, y permite explorar cómo cambian los resultados cuando la gente
se empuja, se desvía o entra en pánico.

## Pilares de Industria 4.0

| Pilar | Qué hay |
|---|---|
| Simulación (núcleo) | Autómata celular con agentes (Mesa) y visualización interactiva (Solara) |
| Big Data y análisis | Corridas Monte Carlo (`experiments/`) que generan CSV, analizados con Pandas (`notebooks/`) |
| IoT | **Prototipo** con sensores simulados: conteos por zona que llegan a la API y alimentan la simulación. Sensores físicos y MQTT son solo propuesta |

## Qué incluye hoy

- Recinto en grilla 2D con salidas y muros, y un *floor field* (mapa de
  distancia a la salida más cercana) calculado una sola vez.
- **App web propia** (FastAPI + frontend) con tres pantallas: diseñar el recinto,
  simularlo y comparar recintos con varias semillas.
- Recintos definidos por el usuario: un plano de texto o una imagen dibujada
  (negro pared, verde salida), en `recintos/`.
- Peatones que avanzan hacia la salida y se bloquean entre sí, con una métrica
  de congestión (`bloqueados`).
- Activación **sincrónica** con resolución explícita de conflictos y un
  parámetro de **fricción**.
- Comportamientos opcionales: **agresividad** (no espera su turno) y
  **pánico/manada** (a veces imita a la multitud en vez de ir a la salida).
- Vecindad configurable: 4 direcciones (`von_neumann`) u 8 con diagonales
  (`moore`).
- Visualización interactiva con sliders, y seguimiento visual de un peatón.
- Cuatro experimentos Monte Carlo reproducibles con un comando y un notebook
  que los analiza.
- Métrica de cuánta gente usó cada salida.
- 184 tests automáticos.

## Documentación

- [docs/informe_fase1.md](docs/informe_fase1.md): informe de la Fase 1
  (entrega parcial), con capturas, resultados y lo que sigue.
- [docs/marco_teorico.md](docs/marco_teorico.md): la teoría de fondo y las
  decisiones de modelado.
- [docs/arquitectura.md](docs/arquitectura.md): diagramas de los módulos, del
  paso de la simulación y de la decisión de un peatón.
- [docs/iot.md](docs/iot.md): el prototipo de IoT (qué está implementado y qué es solo propuesta).
- [docs/guion_defensa.md](docs/guion_defensa.md): borrador del guion de la
  defensa, con la demo y las preguntas probables.

## Stack

- Python (desarrollado con 3.14)
- [Mesa](https://mesa.readthedocs.io) 3.5 (simulación basada en agentes) y
  Solara (visualizador interactivo)
- FastAPI (servidor de la app web) con un frontend en HTML, CSS y JavaScript
- NumPy y Pandas (análisis), Matplotlib (dibujo de la grilla y gráficos)
- pytest (tests)

## Instalación

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` fija `ipyvue==1.12.0` e `ipyvuetify==1.11.3` a propósito:
con la versión 3.0.0 que instala `pip` por defecto, el frontend de Solara se
queda cargando para siempre. No las actualices sin probar la app.

## Cómo usarlo

**Visualizador interactivo** (abrir luego `http://localhost:8765`):

```bash
venv/bin/solara run app.py
```

Controles: `STEP` avanza un paso, el botón de play corre hasta el final y
`RESET` reinicia con los valores actuales de los sliders (cantidad de
peatones, agresividad, fricción y pánico).

**Elegir el recinto.** El plano se lee de un archivo de texto de la carpeta
`recintos/`: un caracter por celda, `#` muro, `S` salida y `.` piso, y la
primera línea del archivo es la fila de arriba. Hay dos de ejemplo
(`sala_con_puerta`, el de por defecto, y `dos_salidas`). Para usar otro, o uno
propio (por nombre o por ruta):

```bash
AGLOMERA_RECINTO=dos_salidas venv/bin/solara run app.py
AGLOMERA_RECINTO=mi_plano.txt venv/bin/solara run app.py
```

Un plano inválido (caracter desconocido, filas de distinto largo, sin salida)
falla con un mensaje que indica la línea y la columna del problema. Los
peatones solo se ubican en celdas desde las que hay camino a una salida.

**Recinto dibujado en una imagen.** También se puede dibujar el plano en
cualquier programa (Paint, Preview, una foto de un dibujo) y usarlo directo.
La convención de colores es: **negro = pared, verde = salida**, y cualquier
otro color claro es piso. No usa inteligencia artificial: es procesamiento de
imagen clásico, que achica el dibujo a una grilla y decide celda por celda.
Hay que indicar cuántas celdas de ancho debe tener el recinto (el alto sale de
las proporciones):

```bash
AGLOMERA_RECINTO=recintos/auditorio.png AGLOMERA_ANCHO_CELDAS=40 venv/bin/solara run app.py
```

Como el resultado depende del tamaño del dibujo y de cuántas celdas se pidan,
conviene **revisar cómo se interpretó** antes de simular. Este comando
imprime el plano de texto resultante, que se puede corregir a mano y guardar
en `recintos/`:

```bash
venv/bin/python -m src.recinto_imagen recintos/auditorio.png --ancho 40
venv/bin/python -m src.recinto_imagen mi_dibujo.png --ancho 50 --guardar recintos/mi_plano.txt
```

Limitaciones: una pared dibujada con un trazo grueso sale de 1 o 2 celdas de
ancho según cómo caiga sobre la grilla, y una línea más fina que el grosor
mínimo (`--grosor`, 2 píxeles por defecto) puede perderse. Distinguir puertas
y paredes en el plano escaneado de un edificio real (con escala, ruido y
símbolos) es otro problema, mucho más grande, y no está resuelto: las salidas
siempre se marcan a mano en verde.

**Editor visual.** Para dibujar el recinto con el mouse, sin escribir texto ni
usar otro programa:

```bash
venv/bin/solara run editor.py
```

Se elige una herramienta (pared, salida o borrar) y se hace clic o se arrastra
sobre la grilla; arrastrar une los puntos con una recta, así que las paredes
salen continuas aunque el mouse vaya rápido. Se puede cambiar el tamaño, poner
pared en todo el borde, abrir un recinto guardado para modificarlo y guardar el
resultado en `recintos/`. El editor avisa si el plano todavía no sirve (por
ejemplo, si falta una salida) y no pisa un archivo existente salvo que se marque
"sobrescribir". Lo guardado se simula con
`AGLOMERA_RECINTO=<nombre> venv/bin/solara run app.py`.

Una advertencia sobre las paredes en diagonal: el modelo permite moverse en
diagonal entre dos celdas de pared que solo se tocan por la esquina cuando la
vecindad es `moore`, así que una pared dibujada en diagonal deja pasar gente
con esa vecindad. Con `von_neumann` (4 direcciones) no hay filtración.

**App web propia (diseñar, simular y comparar en un solo lugar).** Es la
interfaz principal del proyecto: un servidor FastAPI que usa el mismo modelo y
los mismos recintos, y una pantalla con diseño propio. Se levanta con:

```bash
venv/bin/uvicorn web.app:app --port 8000
```

y se abre en `http://localhost:8000`. Tiene tres pestañas:

1. **Diseño**: el editor. Se pinta con clic o arrastre (herramientas pared,
   salida y borrar, con atajos W, E, X y Ctrl+Z), se valida en vivo y se guarda
   en `recintos/`. Muestra los recintos guardados con su miniatura.
2. **Simular**: reproduce la evacuación (pausa, paso a paso y velocidades desde
   0,25× hasta 10×), con
   las métricas reales (paso, evacuados, bloqueados, flujo de salida), la curva
   de evacuación en vivo y el panel de parámetros (peatones, agresividad,
   fricción, pánico, vecindad y semilla). Se puede simular el diseño que se está
   dibujando sin guardarlo.
3. **Comparar**: se eligen varios recintos y se corren con las mismas semillas.
   Muestra qué recinto evacúa más rápido y cuánto, un gráfico de barras con
   desvío, las curvas de evacuación y una tabla (pasos medios, desvío, P95,
   congestión máxima). Se exporta a CSV.

Todo lo que se ve sale de la simulación real; nada es de relleno. La
documentación interactiva de la API está en `http://localhost:8000/api/docs`.
Tailwind y las fuentes están dentro del proyecto (`web/static/vendor/`), así
que la app **funciona sin conexión**. Las dos apps de Solara de más arriba
(`app.py` y `editor.py`) siguen funcionando.

**IoT: sensores simulados que alimentan la simulación.** Prototipo del tercer
pilar. Los sensores (simulados) informan a la API cuánta gente cuentan en cada
zona del recinto, y la simulación puede arrancar con esa ocupación medida en
lugar de ubicar a la gente al azar.

Es opcional y se hace en dos pasos, desde la pestaña **Simular**, con un recinto
guardado, en el panel *Sensores de ocupación (IoT)*:

1. **Encender los sensores**: se aprieta **Iniciar sensores simulados** (se elige
   cuánta gente fingen contar, si está repartida pareja o concentrada, y si se
   quiere simular que un sensor falla). El panel muestra cada zona (personas,
   antigüedad y estado) y el plano muestra las zonas.
2. **Elegir de dónde sale la gente**: *Al azar, según el slider* (lo de siempre)
   o *Medida por los sensores*, que reinicia la simulación con esa gente en cada
   zona.

Sin sensores todo funciona como antes. Una zona que deja de reportar pasa a
**SIN SEÑAL** y no se usa.

Los mismos sensores existen también como un programa aparte, que hace de
gateway y le habla a la API por la red, igual que lo haría hardware real. Con el
servidor andando, en otra terminal:

```bash
venv/bin/python -m iot.simulador_sensores --recinto sala_con_puerta
```

Ver [docs/iot.md](docs/iot.md), que explica qué está implementado y qué sigue
siendo propuesta (sensores físicos, MQTT, base de series de tiempo).

**Tests:**

```bash
venv/bin/python -m pytest tests/ -q
```

**Corridas Monte Carlo.** Cada comparación de la sección de resultados es un
experimento con nombre. Guardan un CSV por experimento en `data/results/`
(que no se versiona) y tardan unos segundos en total:

```bash
venv/bin/python experiments/run_batch.py --listar    # ver los experimentos
venv/bin/python experiments/run_batch.py panico      # correr uno
venv/bin/python experiments/run_batch.py             # correr todos
```

Los experimentos son `salidas`, `friccion`, `vecindad` y `panico`, y se
definen en `EXPERIMENTOS` dentro de `experiments/run_batch.py`.

**Análisis:** abrir `notebooks/analisis_resultados.ipynb`. Lee el CSV más
reciente de cada experimento, así que hay que correr el batch antes.

## Estructura del repositorio

```
app.py                  Punto de entrada del visualizador (solara run app.py)
src/
  space.py              Grilla, salidas, muros y floor field
  agent.py              Peaton: reglas de decisión de movimiento
  model.py              EvacuacionModel: orquesta el paso y registra métricas
  visualization.py      Dibujo de la grilla con matplotlib para Solara
experiments/run_batch.py  Experimentos Monte Carlo con nombre, a CSV
notebooks/              Análisis de resultados con Pandas
tests/                  Tests de space, agent, model y experimentos
docs/marco_teorico.md   Marco teórico y decisiones de modelado
dashboard/              Reservado para un dashboard Streamlit (vacío)
data/results/           CSV generados (ignorado por git)
```

## Cómo funciona

Cada **paso** del modelo (`EvacuacionModel.step`) tiene tres fases:

1. **Evacuar**: quien está parado en una celda de salida se va y la libera.
2. **Decidir**: todos los peatones activos eligen a qué celda querrían ir,
   mirando la misma foto del mundo (nadie se movió todavía).
3. **Resolver**: si dos o más quieren la misma celda vacía hay un conflicto.
   Con probabilidad `probabilidad_friccion` nadie del grupo se mueve; si no,
   gana uno al azar y el resto queda bloqueado.

La regla de decisión de un peatón (`Peaton.decidir_movimiento`):

- Con probabilidad `probabilidad_panico` (se sortea en cada paso) sigue a la
  manada: se mueve hacia el centro de las personas que tiene a 3 celdas o
  menos. Si no hay nadie cerca, decide como siempre.
- Si no, elige la vecina libre con menor distancia a la salida. Si ninguna lo
  acerca se queda quieto, salvo que sea agresivo: en ese caso se desvía a
  cualquier vecina libre.

Una celda admite un solo peatón a la vez. Un peatón está **bloqueado** cuando
existía una celda mejor para él pero no pudo ocuparla (estaba ocupada o perdió
un conflicto). Si simplemente no hay adónde mejorar, no cuenta como bloqueado.

### Colores de la visualización

| Color | Significado |
|---|---|
| Blanco | Piso |
| Negro | Muro |
| Verde | Salida |
| Azul | Peatón que avanza |
| Rojo | Peatón bloqueado |
| Círculo grande con borde violeta y línea | Peatón seguido y su recorrido |

## Parámetros del modelo

`EvacuacionModel(ancho, alto, num_agentes, salidas, ...)`. Las coordenadas son
`(x, y)` con el origen abajo a la izquierda.

| Parámetro | Default | Qué hace |
|---|---|---|
| `ancho`, `alto` | — | Tamaño de la grilla en celdas |
| `num_agentes` | — | Cantidad de peatones (se ubican al azar en celdas libres) |
| `salidas` | — | Lista de coordenadas de salida |
| `muros` | `None` | Lista de coordenadas de pared |
| `rng` | `None` | Semilla, para corridas reproducibles |
| `probabilidad_friccion` | `0.0` | Probabilidad de que un conflicto por una celda deje a todos quietos |
| `probabilidad_agresivo` | `0.0` | Fracción de peatones que no esperan su turno |
| `probabilidad_panico` | `0.0` | Probabilidad, en cada decisión, de seguir a la manada |
| `tipo_vecindad` | `"von_neumann"` | `"von_neumann"` (4 direcciones) o `"moore"` (8) |
| `seguir_un_peaton` | `True` | Marca al primer peatón y guarda su recorrido |

Métricas registradas por paso (`DataCollector`): `evacuados`, `restantes`,
`bloqueados` y una columna `evacuados_salida_X_Y` por cada salida (cuánta gente
salió por esa coordenada).

## Escenario del visualizador

`app.py` arma una sala de 15x10 partida por una pared en `x=7` con una única
puerta de una celda, y la salida en `(14, 5)`. Sirve para observar el
**arqueo**: la gente se amontona contra la puerta. La constante
`TIPO_VECINDAD` se cambia a mano en `app.py` (esta versión de Mesa no trae un
selector desplegable). El slider de pánico llega solo hasta 0.9, porque con
pánico total la simulación puede no terminar nunca (ver abajo).

## Resultados obtenidos hasta ahora

Pasos promedio hasta evacuar a todos. Todo sale de los experimentos de
`experiments/run_batch.py` (el nombre de cada uno está entre paréntesis), con
semillas fijas, así que se puede regenerar tal cual.

| Experimento | Resultado |
|---|---|
| 1 salida central vs 2 en los extremos (`salidas`: sala 20x15, 10 semillas) | Con 30/60/90 agentes: 40.9/74.2/104.9 pasos con 1 salida y 28.1/45.5/62.3 con 2. La ventaja crece con la gente |
| Fricción (`friccion`: sala con puerta, 100 agentes, 15 semillas) | 0.0: 144.1, 0.3: 176.0, 0.6: 243.2 pasos. También sube la congestión máxima (86.1, 90.5 y 92.7 bloqueados a la vez) |
| Vecindad (`vecindad`: misma sala, 100 agentes, 15 semillas) | `moore` evacúa ~22% más rápido (113.0 vs 144.1), pero la congestión máxima en la puerta no baja (88.1 vs 86.1 bloqueados a la vez) |
| Pánico (`panico`: 2 salidas, 80 agentes, 20 semillas) | 0.0: 50.1, 0.4: 63.0, 0.8: 229.2 pasos. Con 1.0 ninguna de las 20 corridas termina y en promedio solo ~7 de 80 personas llegan a salir |

Dos cosas que muestran las corridas y que no eran obvias:

- El pánico **no desbalancea** el uso de las salidas: con 0.0 y con 0.8 la
  gente se reparte casi parejo entre las dos (unos 39 y 41 de 80). La
  evacuación empeora porque la gente pierde tiempo siguiendo a otros, no
  porque se amontone en una sola salida.
- Los números de la fila de salidas son distintos a los de versiones
  anteriores de este documento, porque esas se midieron antes de pasar a la
  activación sincrónica. La conclusión no cambia.

Resultados negativos que vale la pena conocer:

- Con activación asincrónica (turno por turno), la impaciencia **aceleraba** la
  evacuación en vez de empeorarla, porque nunca hay un conflicto real por una
  celda. Por eso el modelo pasó a activación sincrónica con fricción.
- La combinación agresividad por fricción no mostró un efecto limpio en las
  geometrías probadas.

## Limitaciones

- Una celda es una persona y un paso no tiene una duración calibrada: no hay
  escala en metros ni en segundos.
- El floor field es estático (solo distancia), no tiene en cuenta a la gente.
- Los recintos dibujados no tienen escala real, y el importador de imágenes no detecta puertas ni interpreta planos de edificios reales.
- Con vecindad de 8 direcciones, una pared dibujada en diagonal deja pasar gente.
- La comparación de recintos no incluye un test de significancia estadística.
- Los experimentos no incluyen la agresividad, y la combinación de agresividad
  con fricción no se estudió de forma sistemática.
- No hay tests automáticos de `src/visualization.py` ni del frontend de la app web (se verificó a mano).
- IoT es un prototipo: los sensores son simulados, sin autenticación ni persistencia de las lecturas. El dashboard de Streamlit no se implementó (lo reemplaza la app web).

## Próximos pasos

1. Un test estadístico (Welch) en la pestaña Comparar, para saber si una
   diferencia entre recintos es significativa.
2. Mapa de calor de densidad, escenarios predeterminados y exportar la
   simulación como GIF.
3. IoT: transporte MQTT, guardar las lecturas y autenticar a los sensores.

El detalle y el orden están en el tablero de Trello.

## Flujo de trabajo

Una rama por funcionalidad (`feature/...`) que se mergea a `main` cuando tiene
sus tests pasando. Commits en español y descriptivos.

## Referencias

Ver [docs/marco_teorico.md](docs/marco_teorico.md).
