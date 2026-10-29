// Pantalla 3: COMPARAR. Se eligen varios recintos y el servidor corre cada uno
// con las mismas semillas; esta pantalla muestra que tan distintos salen.

import { api } from "./api.js";
import { dibujarMiniatura } from "./dibujo.js";
import { PALETA, escapar, graficoBarras, graficoLineas } from "./graficos.js";
import { icono } from "./iconos.js";

const DISENO = "__diseno__";

const PARAMETROS_POR_DEFECTO = {
  semillas: 10,
  num_agentes: 40,
  probabilidad_friccion: 0,
  probabilidad_panico: 0,
  tipo_vecindad: "von_neumann",
};

const PLANTILLA = `
<div class="flex flex-col gap-4 p-4">
  <div class="grid gap-4 lg:grid-cols-[1fr_22rem]">
    <div class="tarjeta p-4">
      <div class="mb-3 flex items-center justify-between">
        <span class="etiqueta">Recintos a comparar</span>
        <span id="contador-seleccion" class="font-mono text-[11px] text-primary"></span>
      </div>
      <div id="opciones" class="grid gap-3 sm:grid-cols-2"></div>
    </div>

    <div class="tarjeta flex flex-col gap-4 p-4">
      <span class="etiqueta">Parámetros del experimento</span>
      <div class="flex flex-col">
        <div class="flex items-baseline justify-between"><span class="text-xs">Semillas (repeticiones)</span><span id="valor-semillas" class="valor text-xs font-semibold text-primary"></span></div>
        <input type="range" class="deslizador" id="parametro-semillas" min="2" max="30" step="1" />
      </div>
      <div class="flex flex-col">
        <div class="flex items-baseline justify-between"><span class="text-xs">Cantidad de peatones</span><span id="valor-num_agentes" class="valor text-xs font-semibold text-primary"></span></div>
        <input type="range" class="deslizador" id="parametro-num_agentes" min="5" max="300" step="5" />
      </div>
      <div class="flex flex-col">
        <div class="flex items-baseline justify-between"><span class="text-xs">Fricción en conflictos</span><span id="valor-probabilidad_friccion" class="valor text-xs font-semibold text-primary"></span></div>
        <input type="range" class="deslizador" id="parametro-probabilidad_friccion" min="0" max="100" step="5" />
      </div>
      <div class="flex flex-col">
        <div class="flex items-baseline justify-between"><span class="text-xs">Pánico / efecto manada</span><span id="valor-probabilidad_panico" class="valor text-xs font-semibold text-primary"></span></div>
        <input type="range" class="deslizador" id="parametro-probabilidad_panico" min="0" max="90" step="5" />
      </div>
      <div class="grid grid-cols-2 gap-1" id="vecindad">
        <button type="button" class="btn" data-vecindad="von_neumann">4 direcciones</button>
        <button type="button" class="btn" data-vecindad="moore">8 direcciones</button>
      </div>
      <p class="text-[11px] leading-snug text-on-surface-variant">Todos los recintos corren con las mismas semillas (0 a N−1): la única diferencia entre ellos es el recinto.</p>
      <button type="button" id="btn-ejecutar" class="btn-primario">${icono("rayo", 14)} Ejecutar experimento</button>
      <div id="estado-ejecucion" class="min-h-[1.25rem] font-mono text-[11px] text-on-surface-variant"></div>
    </div>
  </div>

  <div id="resultados" class="flex flex-col gap-4"></div>
</div>`;

let alMostrarPantalla = () => {};

export function alMostrar() {
  alMostrarPantalla();
}

export function montar(raiz, app) {
  raiz.innerHTML = PLANTILLA;
  const $ = (selector) => raiz.querySelector(selector);

  const parametros = { ...PARAMETROS_POR_DEFECTO };
  const seleccion = new Set();
  let ultimoResultado = null;
  let seleccionInicializada = false;

  // ------------------------------------------------------- seleccion

  function opcionesDisponibles() {
    const opciones = app.recintos.map((r) => ({ id: r.nombre, etiqueta: r.nombre, filas: r.filas, detalle: `${r.ancho}×${r.alto} · ${r.salidas} salida${r.salidas === 1 ? "" : "s"}` }));
    opciones.push({
      id: DISENO,
      etiqueta: `${app.nombre || "Diseño actual"} (sin guardar)`,
      filas: app.filas,
      detalle: `${app.filas[0].length}×${app.filas.length} · el que estás dibujando`,
    });
    return opciones;
  }

  function renderOpciones() {
    const opciones = opcionesDisponibles();
    $("#opciones").innerHTML = opciones
      .map(
        (o, i) => `
      <label class="tarjeta flex cursor-pointer items-center gap-3 p-2 transition-colors hover:border-primary-container ${seleccion.has(o.id) ? "!border-primary-container bg-surface-container-highest" : ""}">
        <input type="checkbox" class="accent-[#0ea5e9]" data-opcion="${escapar(o.id)}" ${seleccion.has(o.id) ? "checked" : ""} />
        <canvas width="96" height="60" data-miniatura="${i}" class="shrink-0 rounded border border-outline-variant/40"></canvas>
        <div class="min-w-0">
          <div class="truncate font-mono text-xs text-on-surface">${escapar(o.etiqueta)}</div>
          <div class="font-mono text-[10px] text-on-surface-variant">${escapar(o.detalle)}</div>
        </div>
      </label>`,
      )
      .join("");
    $("#opciones").querySelectorAll("[data-miniatura]").forEach((canvas) => {
      dibujarMiniatura(canvas, opciones[Number(canvas.dataset.miniatura)].filas);
    });
    $("#opciones").querySelectorAll("[data-opcion]").forEach((caja) => {
      caja.addEventListener("change", () => {
        caja.checked ? seleccion.add(caja.dataset.opcion) : seleccion.delete(caja.dataset.opcion);
        renderOpciones();
        actualizarBoton();
      });
    });
    actualizarBoton();
  }

  function actualizarBoton() {
    const n = seleccion.size;
    $("#contador-seleccion").textContent = `${n} seleccionado${n === 1 ? "" : "s"}`;
    $("#btn-ejecutar").disabled = n < 2 || n > 8;
    $("#estado-ejecucion").textContent = n < 2 ? "Elegí al menos dos recintos." : n > 8 ? "Se pueden comparar hasta 8 recintos." : "";
  }

  // ------------------------------------------------------- parametros

  function sincronizarPanel() {
    const mostrar = (clave, valor, sufijo = "") => {
      $(`#parametro-${clave}`).value = valor;
      $(`#valor-${clave}`).textContent = `${valor}${sufijo}`;
    };
    mostrar("semillas", parametros.semillas);
    mostrar("num_agentes", parametros.num_agentes);
    mostrar("probabilidad_friccion", Math.round(parametros.probabilidad_friccion * 100), "%");
    mostrar("probabilidad_panico", Math.round(parametros.probabilidad_panico * 100), "%");
    raiz.querySelectorAll("[data-vecindad]").forEach((boton) => {
      boton.classList.toggle("btn-activo", boton.dataset.vecindad === parametros.tipo_vecindad);
    });
  }

  for (const clave of ["semillas", "num_agentes"]) {
    $(`#parametro-${clave}`).addEventListener("input", (e) => {
      parametros[clave] = Number(e.target.value);
      sincronizarPanel();
    });
  }
  for (const clave of ["probabilidad_friccion", "probabilidad_panico"]) {
    $(`#parametro-${clave}`).addEventListener("input", (e) => {
      parametros[clave] = Number(e.target.value) / 100;
      sincronizarPanel();
    });
  }
  raiz.querySelectorAll("[data-vecindad]").forEach((boton) => {
    boton.addEventListener("click", () => {
      parametros.tipo_vecindad = boton.dataset.vecindad;
      sincronizarPanel();
    });
  });

  // --------------------------------------------------------- ejecucion

  $("#btn-ejecutar").addEventListener("click", async () => {
    const opciones = opcionesDisponibles().filter((o) => seleccion.has(o.id));
    const planos = opciones.map((o) =>
      o.id === DISENO ? { filas: app.filas, etiqueta: o.etiqueta } : { recinto: o.id },
    );
    const { semillas, ...resto } = parametros;
    const corridas = opciones.length * semillas;
    const inicio = performance.now();
    $("#btn-ejecutar").disabled = true;
    $("#btn-ejecutar").innerHTML = `<span class="girando inline-block">${icono("reiniciar", 14)}</span> Ejecutando…`;
    $("#estado-ejecucion").textContent = `${opciones.length} recintos × ${semillas} semillas = ${corridas} simulaciones`;
    try {
      ultimoResultado = await api.comparar(planos, semillas, resto);
      const segundos = ((performance.now() - inicio) / 1000).toFixed(1);
      $("#estado-ejecucion").textContent = `${corridas} simulaciones completadas en ${segundos} s`;
      renderResultados();
    } catch (error) {
      $("#estado-ejecucion").innerHTML = `<span class="text-tertiary">${escapar(error.message)}</span>`;
    }
    $("#btn-ejecutar").innerHTML = `${icono("rayo", 14)} Ejecutar experimento`;
    actualizarBoton();
  });

  // -------------------------------------------------------- resultados

  function renderResultados() {
    const { resultados, hallazgo } = ultimoResultado;
    const semillas = ultimoResultado.semillas.length; // cuantas, no cuales
    const colorDe = (i) => PALETA[i % PALETA.length];
    const mejor = hallazgo?.mejor;

    const tarjetaHallazgo = hallazgo
      ? `<div class="tarjeta flex flex-wrap items-center justify-between gap-4 border-secondary-container/50 p-5">
           <div class="min-w-0 flex-1">
             <span class="rounded bg-secondary-container/20 px-2 py-0.5 font-mono text-[10px] font-semibold tracking-wider text-secondary">HALLAZGO CLAVE</span>
             <h2 class="mt-2 text-2xl font-semibold tracking-tight">
               <span class="text-secondary">${escapar(hallazgo.mejor)}</span> evacúa
               <span class="text-secondary">${hallazgo.mejora_pct}% más rápido</span> que ${escapar(hallazgo.peor)}
             </h2>
             <p class="mt-1 font-mono text-xs text-on-surface-variant">Promedio de ${semillas} semillas. La comparación incluye solo los recintos en los que todas las corridas terminaron.</p>
           </div>
           <div class="rounded border border-outline-variant/40 bg-surface-container-lowest px-5 py-3 text-right">
             <div class="etiqueta">Pasos ahorrados</div>
             <div class="valor text-3xl font-medium text-secondary">−${hallazgo.pasos_ahorrados}</div>
           </div>
         </div>`
      : `<div class="tarjeta flex items-start gap-3 p-4 text-xs text-tertiary">${icono("alerta", 16)}
           <span>No hay un hallazgo para mostrar: en algunos recintos no todas las corridas terminaron dentro del máximo de ${ultimoResultado.pasos_maximos} pasos, y así el promedio de pasos no es comparable.</span></div>`;

    const barras = resultados.map((r, i) => ({
      etiqueta: r.etiqueta,
      valor: r.pasos_media,
      error: r.pasos_desvio,
      color: r.etiqueta === mejor ? "#10b981" : colorDe(i),
    }));
    const series = resultados.map((r, i) => ({ etiqueta: r.etiqueta, color: colorDe(i), x: r.curva.pasos, y: r.curva.evacuados }));
    const leyenda = resultados
      .map((r, i) => `<span class="flex items-center gap-1.5"><i class="inline-block h-0.5 w-4" style="background:${colorDe(i)}"></i>${escapar(r.etiqueta)}</span>`)
      .join("");

    const maxCongestion = Math.max(...resultados.map((r) => r.congestion_maxima_pct), 1);
    const filas = resultados
      .map((r, i) => {
        const esMejor = r.etiqueta === mejor;
        return `<tr class="border-t border-outline-variant/30 ${esMejor ? "bg-secondary-container/10" : ""}">
          <td class="px-3 py-2"><span class="mr-2 inline-block h-2 w-2 rounded-sm" style="background:${esMejor ? "#10b981" : colorDe(i)}"></span>
            <span class="${esMejor ? "text-secondary" : ""}">${escapar(r.etiqueta)}</span>${esMejor ? ' <span class="rounded bg-secondary-container/20 px-1 text-[9px] text-secondary">MÁS RÁPIDO</span>' : ""}</td>
          <td class="valor px-3 py-2 text-right">${r.salidas}</td>
          <td class="valor px-3 py-2 text-right font-semibold">${r.pasos_media ?? "—"}</td>
          <td class="valor px-3 py-2 text-right text-on-surface-variant">${r.pasos_desvio != null ? `±${r.pasos_desvio}` : "—"}</td>
          <td class="px-3 py-2"><div class="flex items-center justify-end gap-2"><span class="valor">${r.congestion_maxima_media}</span>
            <span class="valor text-on-surface-variant">(${r.congestion_maxima_pct}%)</span>
            <span class="h-1 w-16 rounded bg-outline-variant/40"><span class="block h-1 rounded bg-bloqueo" style="width:${(100 * r.congestion_maxima_pct) / maxCongestion}%"></span></span></div></td>
          <td class="valor px-3 py-2 text-right">${r.pasos_p95 ?? "—"}</td>
          <td class="valor px-3 py-2 text-right ${r.terminaron < r.corridas ? "text-tertiary" : "text-on-surface-variant"}">${r.terminaron}/${r.corridas}</td>
        </tr>`;
      })
      .join("");

    $("#resultados").innerHTML = `
      ${tarjetaHallazgo}
      <div class="grid gap-4 xl:grid-cols-2">
        <div class="tarjeta p-4">
          <div class="mb-1 flex items-center justify-between"><span class="etiqueta">Pasos promedio para evacuar</span><span class="font-mono text-[10px] text-secondary">MENOR ES MEJOR</span></div>
          <p class="mb-2 font-mono text-[11px] text-on-surface-variant">Media de ${semillas} semillas ± 1 desvío estándar (σ)</p>
          ${graficoBarras({ barras })}
        </div>
        <div class="tarjeta p-4">
          <div class="mb-1 flex items-center justify-between"><span class="etiqueta">Evacuación en el tiempo</span></div>
          <p class="mb-2 font-mono text-[11px] text-on-surface-variant">Personas evacuadas (promedio) según el paso de la simulación</p>
          ${graficoLineas({ series, tope: resultados[0].curva.total })}
          <div class="mt-2 flex flex-wrap gap-x-4 gap-y-1 font-mono text-[11px] text-on-surface-variant">${leyenda}</div>
        </div>
      </div>
      <div class="tarjeta overflow-hidden">
        <div class="flex flex-wrap items-center justify-between gap-2 p-4">
          <div><div class="text-base font-semibold">Matriz comparativa</div>
            <div class="font-mono text-[11px] text-on-surface-variant">Semillas 0 a ${semillas - 1} · ${resultados[0].curva.total} peatones</div></div>
          <button type="button" id="btn-csv" class="btn">${icono("descargar", 14)} Exportar CSV</button>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full font-mono text-xs">
            <thead><tr class="bg-surface-container-lowest text-left">
              <th class="etiqueta px-3 py-2">Recinto</th><th class="etiqueta px-3 py-2 text-right">Salidas</th>
              <th class="etiqueta px-3 py-2 text-right">Pasos medios</th><th class="etiqueta px-3 py-2 text-right">Desv. est. (σ)</th>
              <th class="etiqueta px-3 py-2 text-right">Congestión máx.</th><th class="etiqueta px-3 py-2 text-right">P95 (pasos)</th>
              <th class="etiqueta px-3 py-2 text-right">Terminaron</th></tr></thead>
            <tbody>${filas}</tbody>
          </table>
        </div>
        <p class="border-t border-outline-variant/30 p-4 font-mono text-[11px] leading-relaxed text-on-surface-variant">
          Un “paso” es una unidad del modelo, sin equivalencia calibrada en segundos. <b>P95</b>: percentil 95 de los pasos entre las semillas.
          <b>Congestión máx.</b>: mayor cantidad de personas bloqueadas a la vez, promedio entre semillas (entre paréntesis, como % del total).
          <b>Terminaron</b>: corridas que evacuaron a todos dentro del máximo de ${ultimoResultado.pasos_maximos} pasos; solo ellas entran en los pasos medios.
        </p>
      </div>`;
    $("#btn-csv").addEventListener("click", exportarCsv);
    $("#resultados").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function exportarCsv() {
    const columnas = ["recinto", "ancho", "alto", "salidas", "corridas", "terminaron", "pasos_media", "pasos_desvio", "pasos_p95", "congestion_maxima_media", "congestion_maxima_pct"];
    const campo = (valor) => {
      const texto = valor == null ? "" : String(valor);
      return /[",\n]/.test(texto) ? `"${texto.replace(/"/g, '""')}"` : texto;
    };
    const lineas = [columnas.join(",")].concat(
      ultimoResultado.resultados.map((r) =>
        [r.etiqueta, r.ancho, r.alto, r.salidas, r.corridas, r.terminaron, r.pasos_media, r.pasos_desvio, r.pasos_p95, r.congestion_maxima_media, r.congestion_maxima_pct]
          .map(campo)
          .join(","),
      ),
    );
    const enlace = document.createElement("a");
    enlace.href = URL.createObjectURL(new Blob([lineas.join("\n") + "\n"], { type: "text/csv;charset=utf-8" }));
    enlace.download = "aglomera_comparacion.csv";
    enlace.click();
    URL.revokeObjectURL(enlace.href);
  }

  // ------------------------------------------------------------- inicio

  alMostrarPantalla = () => {
    if (!seleccionInicializada && app.recintos.length >= 2) {
      // por defecto, los dos primeros guardados (o los de ejemplo si estan)
      const preferidos = ["sala_con_puerta", "dos_salidas"].filter((n) => app.recintos.some((r) => r.nombre === n));
      (preferidos.length === 2 ? preferidos : app.recintos.slice(0, 2).map((r) => r.nombre)).forEach((n) => seleccion.add(n));
      seleccionInicializada = true;
    }
    // un recinto que ya no existe no puede seguir seleccionado
    const existentes = new Set(opcionesDisponibles().map((o) => o.id));
    [...seleccion].filter((id) => !existentes.has(id)).forEach((id) => seleccion.delete(id));
    sincronizarPanel();
    renderOpciones();
  };

  sincronizarPanel();
}
