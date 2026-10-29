// Graficos en SVG sin librerias (la app tiene que funcionar sin conexion).
// Cada funcion devuelve el texto del <svg>, listo para ponerlo en innerHTML.

// sin verde: el verde (#10b981) se reserva para marcar al recinto mas rapido
export const PALETA = ["#0ea5e9", "#f59e0b", "#ec4899", "#8b5cf6", "#f97316", "#22d3ee", "#e879f9", "#94a3b8"];

const ANCHO = 640;
const MARGEN = { izq: 46, der: 16, arriba: 14, abajo: 34 };
const COLOR_EJE = "#3e4850";
const COLOR_TEXTO = "#94a3b8";

const escapar = (texto) =>
  String(texto).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

/** Un maximo "redondo" para el eje y marcas parejas (por ejemplo 0, 25, 50, 75, 100). */
export function escalaNice(maximo, marcas = 4) {
  if (!(maximo > 0)) return { tope: 1, paso: 0.25 };
  const crudo = maximo / marcas;
  const potencia = Math.pow(10, Math.floor(Math.log10(crudo)));
  const paso = [1, 2, 2.5, 5, 10].map((m) => m * potencia).find((p) => p >= crudo);
  return { tope: Math.ceil(maximo / paso) * paso, paso };
}

const formatear = (n) => (Number.isInteger(n) ? String(n) : n.toFixed(1));

function ejes({ alto, tope, paso, anchoUtil, altoUtil, etiquetaX }) {
  let svg = "";
  for (let v = 0; v <= tope + 1e-9; v += paso) {
    const y = MARGEN.arriba + altoUtil - (v / tope) * altoUtil;
    svg += `<line x1="${MARGEN.izq}" x2="${MARGEN.izq + anchoUtil}" y1="${y}" y2="${y}" stroke="${COLOR_EJE}" stroke-opacity=".5" stroke-dasharray="3 4"/>`;
    svg += `<text x="${MARGEN.izq - 8}" y="${y + 4}" text-anchor="end" fill="${COLOR_TEXTO}" font-size="11">${formatear(v)}</text>`;
  }
  svg += `<line x1="${MARGEN.izq}" x2="${MARGEN.izq + anchoUtil}" y1="${MARGEN.arriba + altoUtil}" y2="${MARGEN.arriba + altoUtil}" stroke="${COLOR_EJE}"/>`;
  if (etiquetaX) {
    svg += `<text x="${MARGEN.izq + anchoUtil / 2}" y="${alto - 4}" text-anchor="middle" fill="${COLOR_TEXTO}" font-size="11">${escapar(etiquetaX)}</text>`;
  }
  return svg;
}

/** Lineas: series = [{ etiqueta, color, x: [...], y: [...] }]. */
export function graficoLineas({ series, alto = 260, tope, etiquetaX = "Paso de la simulación" }) {
  const anchoUtil = ANCHO - MARGEN.izq - MARGEN.der;
  const altoUtil = alto - MARGEN.arriba - MARGEN.abajo;
  const maxX = Math.max(1, ...series.map((s) => s.x[s.x.length - 1] ?? 0));
  const maxY = tope ?? Math.max(1, ...series.map((s) => Math.max(0, ...s.y)));
  const { tope: topeY, paso } = escalaNice(maxY);
  const px = (x) => MARGEN.izq + (x / maxX) * anchoUtil;
  const py = (y) => MARGEN.arriba + altoUtil - (y / topeY) * altoUtil;

  let svg = ejes({ alto, tope: topeY, paso, anchoUtil, altoUtil, etiquetaX });
  const marcasX = escalaNice(maxX, 5);
  for (let v = 0; v <= maxX + 1e-9; v += marcasX.paso) {
    svg += `<text x="${px(v)}" y="${MARGEN.arriba + altoUtil + 16}" text-anchor="middle" fill="${COLOR_TEXTO}" font-size="11">${formatear(v)}</text>`;
  }
  for (const serie of series) {
    if (serie.x.length < 2) continue;
    const puntos = serie.x.map((x, i) => `${px(x).toFixed(1)},${py(serie.y[i]).toFixed(1)}`).join(" ");
    svg += `<polyline points="${puntos}" fill="none" stroke="${serie.color}" stroke-width="2" stroke-linejoin="round"/>`;
  }
  return `<svg viewBox="0 0 ${ANCHO} ${alto}" class="w-full h-auto" font-family="JetBrains Mono, monospace" role="img">${svg}</svg>`;
}

/** Barras con barra de error: barras = [{ etiqueta, valor, error, color }]. */
export function graficoBarras({ barras, alto = 280 }) {
  const anchoUtil = ANCHO - MARGEN.izq - MARGEN.der;
  const altoUtil = alto - MARGEN.arriba - MARGEN.abajo;
  const maxY = Math.max(1, ...barras.map((b) => (b.valor ?? 0) + (b.error ?? 0)));
  const { tope, paso } = escalaNice(maxY);
  const hueco = anchoUtil / barras.length;
  const ancho = Math.min(80, hueco * 0.55);
  const py = (y) => MARGEN.arriba + altoUtil - (y / tope) * altoUtil;

  let svg = ejes({ alto, tope, paso, anchoUtil, altoUtil });
  barras.forEach((barra, i) => {
    const centro = MARGEN.izq + hueco * (i + 0.5);
    const etiqueta = escapar(barra.etiqueta.length > 16 ? `${barra.etiqueta.slice(0, 15)}…` : barra.etiqueta);
    if (barra.valor != null) {
      svg += `<rect x="${centro - ancho / 2}" y="${py(barra.valor)}" width="${ancho}" height="${py(0) - py(barra.valor)}" fill="${barra.color}" rx="2"/>`;
      if (barra.error) {
        const arriba = py(barra.valor + barra.error);
        const abajo = py(Math.max(0, barra.valor - barra.error));
        svg += `<g stroke="#f8fafc" stroke-width="1.5"><line x1="${centro}" x2="${centro}" y1="${arriba}" y2="${abajo}"/>` +
          `<line x1="${centro - 6}" x2="${centro + 6}" y1="${arriba}" y2="${arriba}"/>` +
          `<line x1="${centro - 6}" x2="${centro + 6}" y1="${abajo}" y2="${abajo}"/></g>`;
      }
      svg += `<text x="${centro}" y="${py((barra.valor ?? 0) + (barra.error ?? 0)) - 6}" text-anchor="middle" fill="#f8fafc" font-size="12" font-weight="600">${formatear(barra.valor)}</text>`;
    } else {
      svg += `<text x="${centro}" y="${py(0) - 8}" text-anchor="middle" fill="#f87171" font-size="11">no terminó</text>`;
    }
    svg += `<text x="${centro}" y="${MARGEN.arriba + altoUtil + 18}" text-anchor="middle" fill="${COLOR_TEXTO}" font-size="11">${etiqueta}</text>`;
  });
  return `<svg viewBox="0 0 ${ANCHO} ${alto}" class="w-full h-auto" font-family="JetBrains Mono, monospace" role="img">${svg}</svg>`;
}

export { escapar };
