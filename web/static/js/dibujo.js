// Dibujo de la grilla en un <canvas>: lo comparten el editor, el simulador y
// las miniaturas de la libreria. Un plano es una lista de filas de texto
// (# pared, S salida, . piso); la fila 0 es la de arriba.

export const COLORES = {
  fondo: "#0a0e16",
  piso: "#121826",
  linea: "#1c2433",
  pared: "#3d4b66",
  paredBorde: "#566684",
  salida: "#10b981",
  libre: "#3b82f6",
  bloqueado: "#ef4444",
  seguido: "#a855f7",
};

export const PARED = "#";
export const SALIDA = "S";
export const PISO = ".";

/** Ajusta el canvas para que el plano entre en `contenedor` con celdas cuadradas
 *  y nitido en pantallas de alta densidad. Devuelve el lado de la celda en px. */
export function ajustarCanvas(canvas, contenedor, ancho, alto, maximo = 40) {
  const disponibleX = Math.max(contenedor.clientWidth, 1);
  const disponibleY = Math.max(contenedor.clientHeight, 1);
  const celda = Math.max(3, Math.min(maximo, Math.floor(Math.min(disponibleX / ancho, disponibleY / alto))));
  const densidad = window.devicePixelRatio || 1;
  canvas.style.width = `${ancho * celda}px`;
  canvas.style.height = `${alto * celda}px`;
  canvas.width = Math.round(ancho * celda * densidad);
  canvas.height = Math.round(alto * celda * densidad);
  canvas.getContext("2d").setTransform(densidad, 0, 0, densidad, 0, 0);
  return celda;
}

/** Dibuja paredes, salidas y piso. */
export function dibujarPlano(ctx, filas, celda) {
  const alto = filas.length;
  const ancho = filas[0].length;
  ctx.fillStyle = COLORES.fondo;
  ctx.fillRect(0, 0, ancho * celda, alto * celda);

  for (let fila = 0; fila < alto; fila++) {
    for (let columna = 0; columna < ancho; columna++) {
      const x = columna * celda;
      const y = fila * celda;
      const tipo = filas[fila][columna];
      if (tipo === PARED) {
        ctx.fillStyle = COLORES.pared;
        ctx.fillRect(x, y, celda, celda);
        if (celda >= 8) {
          ctx.strokeStyle = COLORES.paredBorde;
          ctx.lineWidth = 1;
          ctx.strokeRect(x + 0.5, y + 0.5, celda - 1, celda - 1);
        }
      } else if (tipo === SALIDA) {
        ctx.fillStyle = COLORES.salida;
        ctx.fillRect(x, y, celda, celda);
      } else {
        ctx.fillStyle = COLORES.piso;
        ctx.fillRect(x, y, celda, celda);
        if (celda >= 10) {
          ctx.strokeStyle = COLORES.linea;
          ctx.lineWidth = 1;
          ctx.strokeRect(x + 0.5, y + 0.5, celda - 1, celda - 1);
        }
      }
    }
  }
}

/** Plano + peatones. `estado` viene de la API (agentes: [columna, fila, bloqueado]). */
export function dibujarSimulacion(ctx, filas, estado, celda) {
  dibujarPlano(ctx, filas, celda);
  const centro = (n) => n * celda + celda / 2;

  const seguido = estado.seguido;
  if (seguido && seguido.historial.length > 1) {
    ctx.strokeStyle = COLORES.seguido;
    ctx.lineWidth = Math.max(1.5, celda / 8);
    ctx.lineJoin = "round";
    ctx.beginPath();
    seguido.historial.forEach(([columna, fila], i) => {
      i === 0 ? ctx.moveTo(centro(columna), centro(fila)) : ctx.lineTo(centro(columna), centro(fila));
    });
    ctx.stroke();
  }

  const radio = celda * 0.36;
  for (const [columna, fila, bloqueado] of estado.agentes) {
    ctx.fillStyle = bloqueado ? COLORES.bloqueado : COLORES.libre;
    ctx.beginPath();
    ctx.arc(centro(columna), centro(fila), radio, 0, Math.PI * 2);
    ctx.fill();
  }

  if (seguido && !seguido.evacuado) {
    const [columna, fila] = seguido.historial[seguido.historial.length - 1];
    ctx.fillStyle = seguido.bloqueado ? COLORES.bloqueado : COLORES.libre;
    ctx.strokeStyle = COLORES.seguido;
    ctx.lineWidth = Math.max(2, celda / 8);
    ctx.beginPath();
    ctx.arc(centro(columna), centro(fila), radio * 1.35, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
  }
}

/** Una miniatura de un plano dentro de un canvas chico. */
export function dibujarMiniatura(canvas, filas) {
  const ancho = filas[0].length;
  const alto = filas.length;
  const celda = Math.max(1, Math.floor(Math.min(canvas.width / ancho, canvas.height / alto)));
  const ctx = canvas.getContext("2d");
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.save();
  ctx.translate(Math.floor((canvas.width - ancho * celda) / 2), Math.floor((canvas.height - alto * celda) / 2));
  dibujarPlano(ctx, filas, celda);
  ctx.restore();
}

// ---- operaciones sobre un plano (las mismas reglas que src/editor_recinto.py)

export function planoInicial(ancho = 30, alto = 16) {
  return conBorde(redimensionar([], ancho, alto));
}

export function redimensionar(filas, ancho, alto) {
  const nuevas = filas.slice(0, alto).map((fila) => fila.padEnd(ancho, PISO).slice(0, ancho));
  while (nuevas.length < alto) nuevas.push(PISO.repeat(ancho));
  return nuevas;
}

export function conBorde(filas) {
  const ultimaFila = filas.length - 1;
  const ultimaColumna = filas[0].length - 1;
  return filas.map((fila, y) =>
    [...fila]
      .map((c, x) => ((y === 0 || y === ultimaFila || x === 0 || x === ultimaColumna) && c !== SALIDA ? PARED : c))
      .join(""),
  );
}

export function pintar(filas, columna, fila, caracter) {
  if (fila < 0 || fila >= filas.length || columna < 0 || columna >= filas[fila].length) return filas;
  if (filas[fila][columna] === caracter) return filas;
  const nuevas = filas.slice();
  nuevas[fila] = filas[fila].slice(0, columna) + caracter + filas[fila].slice(columna + 1);
  return nuevas;
}

export function contar(filas) {
  const total = { paredes: 0, salidas: 0, transitables: 0 };
  for (const fila of filas) {
    for (const c of fila) {
      if (c === PARED) total.paredes++;
      else if (c === SALIDA) total.salidas++;
      else total.transitables++;
    }
  }
  return total;
}

/** Celdas (columna, fila) de la recta entre dos celdas: Bresenham. Asi una
 *  linea dibujada rapido con el mouse no deja huecos. */
export function recta(desde, hasta) {
  let [x, y] = desde;
  const [xFinal, yFinal] = hasta;
  const dx = Math.abs(xFinal - x);
  const dy = Math.abs(yFinal - y);
  const pasoX = x < xFinal ? 1 : -1;
  const pasoY = y < yFinal ? 1 : -1;
  let error = dx - dy;
  const celdas = [];
  for (;;) {
    celdas.push([x, y]);
    if (x === xFinal && y === yFinal) return celdas;
    const doble = 2 * error;
    if (doble > -dy) {
      error -= dy;
      x += pasoX;
    }
    if (doble < dx) {
      error += dx;
      y += pasoY;
    }
  }
}
