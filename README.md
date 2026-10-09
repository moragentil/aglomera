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
- Corridas batch tipo Monte Carlo y un notebook de análisis.
- 28 tests automáticos.

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

**Corridas Monte Carlo** (guarda un CSV en `data/results/`, que no se versiona):

```bash
venv/bin/python experiments/run_batch.py
```

**Análisis:** abrir `notebooks/analisis_resultados.ipynb`. Lee el CSV más
reciente de `data/results/`.

## Estructura del repositorio

```
app.py                  Punto de entrada del visualizador (solara run app.py)
src/
  space.py              Grilla, salidas, muros y floor field
  agent.py              Peaton: reglas de decisión de movimiento
  model.py              EvacuacionModel: orquesta el paso y registra métricas
  visualization.py      Dibujo de la grilla con matplotlib para Solara
experiments/run_batch.py  Corridas batch (Monte Carlo) a CSV
notebooks/              Análisis de resultados con Pandas
tests/                  Tests de space, agent y model
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

Métricas registradas por paso (`DataCollector`): `evacuados`, `restantes` y
`bloqueados`.

## Escenario del visualizador

`app.py` arma una sala de 15x10 partida por una pared en `x=7` con una única
puerta de una celda, y la salida en `(14, 5)`. Sirve para observar el
**arqueo**: la gente se amontona contra la puerta. La constante
`TIPO_VECINDAD` se cambia a mano en `app.py` (esta versión de Mesa no trae un
selector desplegable). El slider de pánico llega solo hasta 0.9, porque con
pánico total la simulación puede no terminar nunca (ver abajo).

## Resultados obtenidos hasta ahora

Pasos promedio hasta evacuar a todos. Son corridas con semillas fijas; los
números exactos dependen de la configuración indicada.

| Experimento | Resultado |
|---|---|
| 1 salida central vs 2 en los extremos (sala 20x15, 10 semillas) | Con 30/60/90 agentes: 48.9/87.8/128.3 pasos con 1 salida y 32.4/54.9/76.4 con 2 |
| Fricción (sala con puerta, 100 agentes, 15 semillas) | 0.0: 145.0, 0.3: 174.1, 0.6: 237.5 pasos |
| Vecindad (misma sala, 100 agentes, 15 semillas) | `moore` evacúa ~24% más rápido (110.5 vs 145.0), pero la congestión máxima en la puerta no baja (88.7 vs 86.1 bloqueados a la vez) |
| Pánico (2 salidas, 80 agentes, 20 semillas) | 0.0: 50.1, 0.4: 63.0, 0.8: 229.2 pasos. Con 1.0 la simulación no termina en 20 de 20 corridas |

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
- `experiments/run_batch.py` solo compara salidas y cantidad de agentes; las
  comparaciones de fricción, pánico y vecindad se hicieron con scripts sueltos
  que no están en el repo.
- No hay tests de `src/visualization.py` ni de `experiments/run_batch.py`.
- IoT y el dashboard de Streamlit no están implementados.

## Próximos pasos

1. Definir el recinto desde un archivo (formato de texto o JSON), con editor
   visual y, como opcional, importar un plano como imagen.
2. Registrar qué salida usó cada peatón y ampliar `run_batch.py` y el notebook.
3. Escenario de dos salidas en el visualizador para mostrar el pánico en vivo.

## Flujo de trabajo

Una rama por funcionalidad (`feature/...`) que se mergea a `main` cuando tiene
sus tests pasando. Commits en español y descriptivos.

## Referencias

Ver [docs/marco_teorico.md](docs/marco_teorico.md).
