# Marco teórico

Este documento explica la teoría que hay detrás de la simulación y cómo cada
idea se traduce (o no) en el código. Para instalar y correr el proyecto, ver el
[README](../README.md).

## 1. Por qué un modelo basado en agentes

Hay dos formas clásicas de modelar una multitud:

- **Macroscópica**: trata a la multitud como un fluido, con ecuaciones de
  densidad y velocidad. Es elegante, pero no ve a las personas individuales:
  no puede mostrar que alguien quedó bloqueado en una puerta.
- **Microscópica (basada en agentes)**: cada persona es un agente con posición
  y reglas propias. Cuesta más de calcular, pero permite ver **emergencia**:
  patrones colectivos (colas, amontonamientos, pánico) que nadie programó
  explícitamente y que surgen de la interacción de reglas simples.

Como el objetivo del TP es detectar puntos de aglomeración y comparar
configuraciones de salidas, se eligió el enfoque microscópico.

## 2. Modelo de Fuerzas Sociales (Helbing & Molnár, 1995)

Es el marco de referencia de la dinámica de peatones. Cada peatón es una
partícula que obedece una ecuación de movimiento de tipo Newton, con tres
tipos de fuerza:

1. **Fuerza motriz**: lo empuja a acelerar hacia su destino a la velocidad
   que desea. Es una "relajación": cuanto más se aparta de su velocidad
   deseada, más fuerte es.
2. **Repulsión entre peatones**: nadie quiere estar pegado a otro. Suele
   modelarse como una función que decae exponencialmente con la distancia.
3. **Repulsión de paredes y obstáculos**: igual que la anterior, pero contra
   el entorno.

La suma de las tres da la aceleración de cada persona. El espacio y la
velocidad son continuos.

**En este proyecto no se implementa.** Se usa un autómata celular (sección 4),
que es discreto y más simple. Del modelo de fuerzas se toma la *idea*
(destino que atrae, otros que estorban), no las ecuaciones.

## 3. Dinámica del pánico (Helbing, Farkas & Vicsek, 2000)

Extiende el modelo anterior a evacuaciones de emergencia y describe tres
fenómenos que motivan este TP:

- **Faster is slower** (más rápido es más lento): si todos intentan ir más
  rápido, el tiempo total de evacuación puede empeorar, porque aumentan las
  fricciones y los bloqueos en los cuellos de botella.
- **Arqueo y obstrucción**: en una puerta angosta no se forma una fila
  ordenada; la gente se bloquea mutuamente y el flujo se vuelve intermitente.
- **Herding (comportamiento de manada)**: bajo estrés, las personas tienden a
  imitar a los demás en lugar de decidir por sí mismas, y pueden ignorar
  salidas alternativas.

## 4. Autómatas celulares para peatones (Blue & Adler, 2001)

Alternativa **discreta** al modelo de fuerzas:

- El espacio es una grilla; cada celda está vacía u ocupada por una persona.
- En cada paso, cada persona evalúa sus celdas vecinas y se mueve a una según
  una regla. Los choques se resuelven con reglas de prioridad o probabilidades.
- Es mucho más liviano de calcular que resolver fuerzas continuas.

### Floor field

Para no calcular un camino por persona en cada paso, se usa un *floor field*
(campo de piso): un mapa estático donde cada celda guarda su distancia mínima
a la salida más cercana. Es como cachear un resultado caro: se calcula una
vez y después cada peatón solo consulta el valor de sus vecinas.

En `src/space.py` se calcula con un **BFS multi-fuente**: se arranca desde
todas las salidas con distancia 0 y se expande de a un anillo por vez (como
una onda), sin atravesar muros. Las celdas que quedan aisladas detrás de una
pared completa quedan con distancia infinita.

Una consecuencia importante: el floor field dice qué tan lejos está cada
celda de la salida *si nadie más existiera*. No sabe nada de congestión. Los
cuellos de botella aparecen recién cuando varios peatones compiten por la
misma celda, y eso lo resuelve la dinámica de `agent.py` y `model.py`, no el
mapa.

## 5. Decisiones de modelado

### 5.1 Vecindad: Von Neumann vs Moore

- **Von Neumann** (default): 4 vecinas (arriba, abajo, izquierda, derecha). La
  distancia del floor field es de tipo Manhattan, y un muro de una celda
  obliga a dar un desvío real.
- **Moore**: suma las 4 diagonales. La distancia se parece a la de Chebyshev y
  un obstáculo chico casi no cuesta, porque se esquiva en diagonal.

Se dejó configurable (`tipo_vecindad`). En el escenario de la puerta, Moore
evacúa más rápido en total, pero no reduce la congestión máxima: la puerta
sigue siendo un cuello de botella de una celda, así que la gente solo llega
antes a formar la cola.

### 5.2 Activación asincrónica vs sincrónica

- **Asincrónica**: los agentes se mueven de a uno, en orden aleatorio, y cada
  uno ya ve lo que hicieron los anteriores. Dos personas nunca compiten por la
  misma celda a la vez, porque el orden de turnos ya lo resolvió.
- **Sincrónica** (la que se usa): todos deciden mirando la misma foto del
  mundo y recién después se resuelven los conflictos.

Se pasó de la primera a la segunda al probar la idea de "impaciencia". Con
turnos secuenciales, una población impaciente evacuaba **más rápido**, no más
lento, en todas las geometrías probadas: sin conflictos reales no hay fricción
posible. Con activación sincrónica sí puede haber dos agentes queriendo la
misma celda vacía en el mismo paso.

### 5.3 Fricción (Kirchner y Schadschneider)

En los autómatas celulares con actualización paralela, cuando dos o más
peatones eligen la misma celda se agrega un parámetro de **fricción** `μ`: con
probabilidad `μ` ninguno se mueve, aunque la celda estuviera libre. Representa
el roce, los empujones y la descoordinación. Aquí es `probabilidad_friccion` y
solo se aplica cuando hay un conflicto real (dos o más pretendientes); un
peatón que quiere una celda que nadie más quiere siempre se mueve.

### 5.4 Agresividad

Un peatón agresivo no tolera esperar: si su mejor opción está ocupada, en vez
de quedarse quieto elige cualquier celda vecina libre, aunque no lo acerque a
la salida. Es un intento de representar impaciencia. Combinada con fricción no
mostró un efecto limpio de "más agresivo, más lento": los conflictos que
genera ocurren mayormente lejos del cuello de botella que limita el flujo.

### 5.5 Pánico y manada

Con probabilidad `probabilidad_panico`, en un paso dado un peatón no sigue el
floor field: mira a quién tiene a 3 celdas o menos y se mueve hacia el centro
de esa multitud. Si no hay nadie cerca, decide con normalidad.

El pánico se **sortea de nuevo en cada paso** y no es una etiqueta fija por
peatón. La primera versión era una etiqueta fija, y dos peatones en pánico
cerca de una salida se perseguían mutuamente en círculo sin cruzar nunca. Con
pánico sorteado paso a paso siempre hay una chance de recuperar la cabeza fría
y salir. En el extremo de pánico total (probabilidad 1.0, sin ningún momento de
lucidez) la simulación no termina; se documenta como un hallazgo y no como un
error, y por eso el slider del visualizador se limita a 0.9.

### 5.6 Capacidad de una celda

Cada celda admite un solo peatón (`capacity=1`), que es la convención habitual
en autómatas celulares de peatones y es lo que genera las colas.

### 5.7 Peatón bloqueado

Se distingue por qué un peatón no se mueve:

- no hay ninguna vecina que lo acerque a la salida (óptimo local, nadie tiene
  la culpa); o
- sí había una celda mejor pero estaba ocupada o perdió un conflicto
  (congestión real).

Solo el segundo caso cuenta como `bloqueado`, que es la métrica que mide el
arqueo.

### 5.8 El recinto lo define el usuario

El recinto no está escrito en el código: es un dato. Se puede definir de tres
formas que terminan en el mismo objeto (ancho, alto, salidas y muros), así que
el modelo no sabe de dónde vino:

- **Plano de texto**: un carácter por celda (`#` pared, `S` salida, `.` piso),
  con la primera línea del archivo como la fila de arriba, tal como se ve en
  pantalla.
- **Dibujo** (negro pared, verde salida): procesamiento de imagen clásico, **sin
  inteligencia artificial**. Se achica el dibujo a una grilla y cada celda decide
  si es pared, salida o piso según el color de los píxeles que le tocan. Hay una
  decisión de diseño importante: al achicar, una pared fina puede quedar partida
  entre dos celdas y desaparecer, abriendo un hueco por donde no debería pasar
  nadie, y eso falla en silencio. Por eso una celda cuenta como pared si tiene al
  menos medio "grosor mínimo" de píxeles oscuros cruzándola; a cambio, una línea
  puede salir de dos celdas de ancho.
- **Editor visual** (en la app web): se pinta con el mouse y arrastrar une los
  puntos con una recta (algoritmo de Bresenham), de modo que una pared dibujada
  rápido no deja huecos.

Se valida que haya al menos una salida y que todas las filas midan lo mismo.
Además, el modelo solo ubica peatones en celdas desde las que hay un camino a
alguna salida (distancia finita en el *floor field*): un cuarto encerrado en un
plano dibujado dejaría peatones que nunca pueden evacuar.

**Una consecuencia de la vecindad.** Con 8 direcciones (Moore) un peatón puede
cruzar en diagonal entre dos paredes que se tocan solo por la esquina, así que
una pared dibujada "en escalera" deja pasar gente. Con 4 direcciones (Von
Neumann) no hay filtración. Es una limitación conocida y está cubierta por un
test; para recintos dibujados a mano, Von Neumann es la opción más segura.

### 5.9 Comparar recintos con varias semillas

Para comparar dos recintos no alcanza una corrida: el resultado depende del
azar (posiciones iniciales, desempates, fricción). El método es el mismo del
análisis Monte Carlo: cada recinto se corre con las **mismas semillas** (0 a
N−1), de modo que la única diferencia entre las corridas de dos recintos es el
recinto. Se informa:

- la **media y el desvío estándar muestral** de los pasos hasta evacuar a todos;
- el **percentil 95** (por el método del rango más cercano), que dice cuánto
  puede tardar en un mal caso;
- la **congestión máxima**: el mayor número de peatones bloqueados a la vez,
  promediado entre semillas.

Solo cuentan las corridas que terminaron dentro del máximo de pasos, y el
"hallazgo" (cuánto más rápido es un recinto) solo compara recintos en los que
todas las corridas terminaron: si algunas no terminaron, el promedio de pasos no
es comparable. Una diferencia grande frente al desvío (por ejemplo 28 contra
53,8 pasos con desvíos de unos 3) es evidente; una diferencia chica no lo es, y
para eso haría falta un test de significancia, que está pendiente.

## 6. De la teoría al código

| Concepto | Dónde está |
|---|---|
| Entorno discreto, salidas y muros | `src/space.py` (`crear_espacio`) |
| Floor field (BFS multi-fuente) | `src/space.py` (`_calcular_floor_field`) |
| Regla de movimiento y herding | `src/agent.py` (`decidir_movimiento`) |
| Activación sincrónica y conflictos | `src/model.py` (`step`) |
| Fricción | `src/model.py` (`probabilidad_friccion`) |
| Métricas (evacuados, bloqueados) | `src/model.py` (`DataCollector`) |
| Monte Carlo | `experiments/run_batch.py` |
| Recinto definido por el usuario (texto) | `src/recinto.py` |
| Recinto desde un dibujo (sin IA) | `src/recinto_imagen.py` |
| Editor visual | `web/static/js/diseno.js` (app web), `src/editor_recinto.py` |
| Comparación de recintos | `web/servicios.py` (`comparar`) |
| Ocupación medida por zona (IoT) | `src/zonas.py`, `web/sensores.py`, `iot/simulador_sensores.py` |

## 7. Limitaciones respecto de la teoría

- No hay física continua: no existen fuerzas de contacto, empujones ni
  aplastamiento, solo una fricción probabilística.
- El floor field es estático; no hay un campo dinámico que reaccione a la
  presencia de otros peatones.
- No hay escala real: una celda es una persona y un paso no equivale a un
  tiempo calibrado.
- La percepción de la manada es local (radio fijo de 3 celdas) y no modela
  comunicación, visibilidad ni familiaridad con las salidas.
- No se calibró contra datos reales de evacuaciones.
- Los recintos dibujados no tienen escala real y el importador no detecta
  puertas ni interpreta planos de edificios reales.
- Con vecindad de 8 direcciones, una pared diagonal deja pasar gente (ver 5.8).
- La comparación de recintos informa media, desvío y percentil 95, pero no
  incluye un test de significancia estadística.
- La ocupación medida por zona solo fija dónde empieza la gente: dentro de una
  zona las posiciones se sortean, porque un contador no informa dónde está cada
  persona. Los sensores del prototipo son simulados.

## 8. Referencias

Las tres primeras son las del enunciado del proyecto. Las otras dos son de las
ideas de fricción y floor field; **conviene verificar los datos
bibliográficos antes de la entrega**.

- Helbing, D. & Molnár, P. (1995). Social force model for pedestrian
  dynamics. *Physical Review E*.
- Helbing, D., Farkas, I. & Vicsek, T. (2000). Simulating dynamical features
  of escape panic. *Nature*.
- Blue, V. J. & Adler, J. L. (2001). Cellular automata microsimulation for
  modeling bi-directional pedestrian walkways. *Transportation Research
  Part B*.
- Kirchner, A., Nishinari, K. & Schadschneider, A. (2003). Friction effects and
  clogging in a cellular automaton model for pedestrian dynamics. *Physical
  Review E*.
- Burstedde, C., Klauck, K., Schadschneider, A. & Zittartz, J. (2001).
  Simulation of pedestrian dynamics using a two-dimensional cellular
  automaton. *Physica A*.
