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
| IoT | Solo como extensión de arquitectura, **no implementada** |

## Qué incluye hoy

- Recinto en grilla 2D con salidas y muros, y un *floor field* (mapa de
  distancia a la salida más cercana) calculado una sola vez.
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
- 32 tests automáticos.

## Documentación

- [docs/marco_teorico.md](docs/marco_teorico.md): la teoría de fondo y las
  decisiones de modelado.
- [docs/arquitectura.md](docs/arquitectura.md): diagramas de los módulos, del
  paso de la simulación y de la decisión de un peatón.
- [docs/iot.md](docs/iot.md): propuesta de extensión con IoT (no implementada).
- [docs/guion_defensa.md](docs/guion_defensa.md): borrador del guion de la
  defensa, con la demo y las preguntas probables.

## Stack

- Python (desarrollado con 3.14)
- [Mesa](https://mesa.readthedocs.io) 3.5 (simulación basada en agentes) y
  Solara (visualizador interactivo)
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
- El recinto está fijo en `app.py`; todavía no se puede cargar un plano.
- Los experimentos no incluyen la agresividad, y la combinación de agresividad
  con fricción no se estudió de forma sistemática.
- No hay tests de `src/visualization.py`.
- IoT y el dashboard de Streamlit no están implementados.

## Próximos pasos

1. Definir el recinto desde un archivo (formato de texto o JSON), con editor
   visual y, como opcional, importar un plano como imagen.
2. Escenario de dos salidas en el visualizador para mostrar el pánico en vivo.

## Flujo de trabajo

Una rama por funcionalidad (`feature/...`) que se mergea a `main` cuando tiene
sus tests pasando. Commits en español y descriptivos.

## Referencias

Ver [docs/marco_teorico.md](docs/marco_teorico.md).
