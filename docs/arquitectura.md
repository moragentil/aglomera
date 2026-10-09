# Arquitectura

Cómo se relacionan las piezas del proyecto y qué hace el código en cada paso
de la simulación. Los diagramas están en [Mermaid](https://mermaid.js.org):
se ven renderizados en GitHub y en la mayoría de los visores de Markdown.

## 1. Módulos y dependencias

```mermaid
flowchart LR
    app["app.py"] --> viz["src/visualization.py"]
    app --> model["src/model.py"]
    model --> agent["src/agent.py"]
    model --> space["src/space.py"]
    agent --> space
    viz --> space
    batch["experiments/run_batch.py"] --> model
    batch --> csv[("data/results/*.csv")]
    csv --> nb["notebooks/analisis_resultados.ipynb"]
```

| Módulo | Responsabilidad |
|---|---|
| `space.py` | El mapa: grilla, salidas, muros y floor field. No sabe nada de peatones. |
| `agent.py` | Un peatón: decide a qué celda querría moverse. No mueve a nadie. |
| `model.py` | Crea todo, ejecuta cada paso, resuelve conflictos y registra métricas. |
| `visualization.py` | Dibuja el estado actual del modelo. Solo lo lee. |
| `app.py` | Arma el escenario y el visualizador interactivo. |
| `run_batch.py` | Corre muchas simulaciones y guarda el resultado en CSV. |

Una regla que se mantiene en todo el proyecto: cada módulo solo conoce a los
que están "debajo" en el diagrama. `space.py` no importa a nadie del proyecto,
por eso se pudo cambiar el tipo de vecindad con una sola línea.

## 2. Un paso de la simulación

Es lo que hace `EvacuacionModel.step()`.

```mermaid
flowchart TD
    A["Inicio del paso"] --> B["Fase 1: evacuar<br/>quien está en una salida se va y la libera"]
    B --> C["Fase 2: decidir<br/>cada peatón activo elige una celda deseada<br/>mirando la misma foto del mundo"]
    C --> D["Agrupar los deseos por celda destino"]
    D --> E{"¿Más de un<br/>pretendiente?"}
    E -- No --> F["Se mueve a la celda"]
    E -- Sí --> G{"¿Sale la fricción?<br/>probabilidad_friccion"}
    G -- Sí --> H["Nadie se mueve<br/>todos quedan bloqueados"]
    G -- No --> I["Gana uno al azar<br/>el resto queda bloqueado"]
    F --> J["Registrar métricas<br/>y cortar si todos evacuaron"]
    H --> J
    I --> J
```

La fase 3 (resolver) es la razón de que la decisión y el movimiento estén
separados: si cada peatón se moviera apenas decide, el que va segundo ya vería
la celda ocupada y nunca habría un conflicto real que resolver.

## 3. Cómo decide un peatón

Es lo que hace `Peaton.decidir_movimiento()`. Devuelve la celda que querría
ocupar (o ninguna) y si existía alguna celda que lo acercara a la salida.

```mermaid
flowchart TD
    A["decidir_movimiento"] --> B{"¿Ya evacuó?"}
    B -- Sí --> Z["Sin celda deseada"]
    B -- No --> C{"¿Tiene alguna<br/>vecina libre?"}
    C -- No --> Z
    C -- Sí --> D{"¿Sale el pánico y hay gente<br/>a 3 celdas o menos?"}
    D -- Sí --> E["Desea la vecina libre más cercana<br/>al centro de esa multitud"]
    D -- No --> F{"¿Alguna vecina libre mejora<br/>la distancia a la salida?"}
    F -- Sí --> G["Desea la mejor<br/>desempate al azar"]
    F -- No --> H{"¿Es agresivo?"}
    H -- Sí --> I["Desea cualquier vecina libre<br/>elegida al azar"]
    H -- No --> Z
```

## 4. Qué información guarda cada pieza

**En cada celda del espacio** (`celda.properties`):

| Clave | Valor |
|---|---|
| `es_salida` | `True` si la celda es una salida |
| `es_muro` | `True` si la celda es una pared |
| `distancia_a_salida` | Pasos hasta la salida más cercana (infinito si es inalcanzable) |

**En cada peatón:**

| Atributo | Para qué sirve |
|---|---|
| `cell` | Celda donde está parado (`None` una vez evacuado) |
| `evacuado` | Si ya salió |
| `bloqueado` | Si quería avanzar y no pudo (lo fija el modelo) |
| `agresivo` | Si se desvía en vez de esperar |
| `seguido` e `historial` | Si se le dibuja el recorrido, y las celdas por las que pasó |

**En el modelo:** `espacio`, `probabilidad_friccion`, `probabilidad_panico`,
`pasos_transcurridos` y `peaton_seguido`. El `DataCollector` registra
`evacuados`, `restantes` y `bloqueados` en cada paso.

## 5. Flujo de datos del análisis (Big Data)

```mermaid
flowchart LR
    P["PARAMETROS<br/>combinaciones y semillas"] --> BR["mesa.batch_run"]
    BR --> S["Una simulación por<br/>combinación y semilla"]
    S --> DC["DataCollector<br/>una fila por paso"]
    DC --> CSV[("batch_FECHA.csv")]
    CSV --> NB["Notebook con Pandas<br/>resumen, tablas y gráficos"]
```

Cada fila del CSV es un paso de una corrida. El notebook primero resume (una
fila por corrida, con el paso final) y recién después compara
configuraciones.

## 6. Dónde tocar para agregar algo

| Quiero... | Toco... |
|---|---|
| Un nuevo tipo de celda (por ejemplo una zona lenta) | `space.py` |
| Una nueva regla de movimiento o comportamiento | `agent.py` (`decidir_movimiento`) |
| Cambiar cómo se resuelven los conflictos o agregar una métrica | `model.py` |
| Cambiar cómo se ve | `visualization.py` |
| Probar otro escenario en vivo | `app.py` |
| Comparar parámetros en masa | `experiments/run_batch.py` |
