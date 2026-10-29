// Pantalla 2: SIMULAR. El servidor guarda la simulacion y calcula cada paso;
// esta pantalla pide pasos, dibuja lo que vuelve y muestra las metricas.

import { api } from "./api.js";
import { COLORES, ajustarCanvas, dibujarSimulacion } from "./dibujo.js";
import { graficoLineas } from "./graficos.js";
import { icono } from "./iconos.js";

const DISENO_ACTUAL = "__diseno__";
const VELOCIDADES = [
  { etiqueta: "1×", pasosPorTick: 1 },
  { etiqueta: "2×", pasosPorTick: 2 },
  { etiqueta: "5×", pasosPorTick: 5 },
  { etiqueta: "10×", pasosPorTick: 10 },
];
const MS_POR_TICK = 100;
const PASOS_PARA_EL_FLUJO = 10;

const PARAMETROS_POR_DEFECTO = {
  num_agentes: 40,
  probabilidad_agresivo: 0,
  probabilidad_friccion: 0,
  probabilidad_panico: 0,
  tipo_vecindad: "von_neumann",
  semilla: 1,
};

// [clave, titulo, minimo, maximo, paso, es porcentaje, ayuda]
const DESLIZADORES = [
  ["num_agentes", "Cantidad de peatones", 5, 300, 5, false, "Cuántas personas hay en el recinto al empezar."],
  ["probabilidad_agresivo", "Conducta agresiva", 0, 100, 5, true, "Probabilidad de desviarse a cualquier celda libre en vez de esperar."],
  ["probabilidad_friccion", "Fricción en conflictos", 0, 100, 5, true, "Probabilidad de que, si dos quieren la misma celda, nadie avance. Simula empujones y arcos en puertas."],
  ["probabilidad_panico", "Pánico / efecto manada", 0, 90, 5, true, "Probabilidad de imitar a la multitud en vez de ir a la salida. Tope 90%: con pánico total puede no terminar nunca."],
];

const PLANTILLA = `
<div class="flex flex-col gap-4 p-4 lg:flex-row">
  <div class="flex min-w-0 flex-1 flex-col gap-4">
    <div class="tarjeta flex flex-wrap items-center gap-4 px-3 py-2">
      <label class="flex items-center gap-2">
        <span class="etiqueta">Recinto</span>
        <select id="origen" class="entrada !w-auto"></select>
      </label>
      <div class="flex gap-1">
        <button type="button" id="btn-play" class="btn-primario">${icono("play", 14)}<span>Reproducir</span></button>
        <button type="button" id="btn-paso" class="btn">${icono("paso", 14)}<span>Paso</span></button>
        <button type="button" id="btn-reiniciar" class="btn">${icono("reiniciar", 14)}<span>Reiniciar</span></button>
      </div>
      <div class="flex items-center gap-2">
        <span class="etiqueta">Velocidad</span>
        <div class="flex gap-1" id="velocidades">
          ${VELOCIDADES.map((v, i) => `<button type="button" class="btn !px-2 !py-1 font-mono" data-velocidad="${i}">${v.etiqueta}</button>`).join("")}
        </div>
      </div>
      <span id="estado-texto" class="ml-auto rounded-full border border-outline-variant/60 px-3 py-1 font-mono text-[10px] font-semibold tracking-wider"></span>
    </div>

    <div id="aviso" class="hidden rounded border border-tertiary/50 bg-error-container/20 px-3 py-2 text-xs text-tertiary"></div>

    <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <div class="tarjeta p-4"><div class="etiqueta">Paso actual</div><div id="tarjeta-paso" class="valor mt-2 text-2xl font-medium xl:text-3xl"></div></div>
      <div class="tarjeta p-4"><div class="etiqueta">Evacuados / total</div>
        <div class="mt-2 flex items-baseline gap-2"><span id="tarjeta-evacuados" class="valor text-2xl font-medium text-secondary xl:text-3xl"></span><span id="tarjeta-total" class="valor text-sm text-on-surface-variant"></span></div>
        <div class="mt-2 h-1 rounded bg-outline-variant/50"><div id="barra-evacuados" class="h-1 rounded bg-secondary" style="width:0%"></div></div>
        <div id="tarjeta-porcentaje" class="valor mt-1 text-[11px] text-on-surface-variant"></div></div>
      <div id="caja-bloqueados" class="tarjeta p-4"><div class="etiqueta">Bloqueados ahora</div><div id="tarjeta-bloqueados" class="valor mt-2 text-2xl font-medium xl:text-3xl"></div>
        <div id="tarjeta-bloqueados-detalle" class="valor mt-1 text-[11px] text-on-surface-variant"></div></div>
      <div class="tarjeta p-4"><div class="etiqueta">Flujo de salida</div>
        <div class="mt-2 flex items-baseline gap-2"><span id="tarjeta-flujo" class="valor text-2xl font-medium text-primary xl:text-3xl"></span><span class="valor text-xs text-on-surface-variant">pers/paso</span></div>
        <div class="valor mt-1 text-[11px] text-on-surface-variant">promedio de los últimos ${PASOS_PARA_EL_FLUJO} pasos</div></div>
    </div>

    <div class="tarjeta flex flex-col p-3">
      <div class="mb-2 flex flex-wrap items-center justify-between gap-2 font-mono text-[11px] text-on-surface-variant">
        <span id="titulo-plano" class="text-on-surface"></span>
        <div class="flex gap-4">
          <span class="flex items-center gap-1.5"><i class="inline-block h-2.5 w-2.5 rounded-full" style="background:${COLORES.libre}"></i>En movimiento</span>
          <span class="flex items-center gap-1.5"><i class="inline-block h-2.5 w-2.5 rounded-full" style="background:${COLORES.bloqueado}"></i>Bloqueado</span>
          <span class="flex items-center gap-1.5"><i class="inline-block h-2.5 w-2.5 rounded-full border-2" style="border-color:${COLORES.seguido}"></i>Peatón seguido</span>
          <span class="flex items-center gap-1.5"><i class="inline-block h-2.5 w-2.5 rounded-sm" style="background:${COLORES.salida}"></i>Salida</span>
        </div>
      </div>
      <div id="contenedor-lienzo" class="flex h-[52vh] min-h-[300px] items-center justify-center">
        <canvas id="lienzo" class="lienzo rounded border border-outline-variant/60"></canvas>
      </div>
    </div>

    <div class="tarjeta p-4">
      <div class="mb-2 flex items-center justify-between">
        <span class="etiqueta">Curva de evacuación</span>
        <span class="font-mono text-[11px] text-on-surface-variant">personas evacuadas acumuladas</span>
      </div>
      <div id="curva"></div>
    </div>
  </div>

  <aside class="tarjeta flex w-full shrink-0 flex-col gap-5 self-start p-4 lg:w-80">
    <span class="etiqueta">Parámetros del motor</span>
    ${DESLIZADORES.map(
      ([clave, titulo, min, max, paso, , ayuda]) => `
      <div class="flex flex-col">
        <div class="flex items-baseline justify-between"><span class="text-xs">${titulo}</span><span id="valor-${clave}" class="valor text-xs font-semibold text-primary"></span></div>
        <input type="range" class="deslizador" id="parametro-${clave}" min="${min}" max="${max}" step="${paso}" />
        <span class="text-[11px] leading-snug text-on-surface-variant">${ayuda}</span>
      </div>`,
    ).join("")}
    <div class="flex flex-col gap-2">
      <span class="etiqueta">Topología de movimiento</span>
      <div class="grid grid-cols-2 gap-1" id="vecindad">
        <button type="button" class="btn" data-vecindad="von_neumann">4 direcciones</button>
        <button type="button" class="btn" data-vecindad="moore">8 direcciones</button>
      </div>
      <span class="text-[11px] leading-snug text-on-surface-variant">Con 8 direcciones se mueven en diagonal: pueden cruzar entre dos paredes que se tocan por la esquina.</span>
    </div>
    <div class="flex flex-col gap-2">
      <span class="etiqueta">Semilla determinista</span>
      <div class="flex gap-2">
        <input type="number" id="semilla" class="entrada" min="0" step="1" />
        <button type="button" class="btn" id="btn-semilla" title="Elegir una semilla al azar">Azar</button>
      </div>
      <span class="text-[11px] leading-snug text-on-surface-variant">Con la misma semilla la simulación se repite idéntica.</span>
    </div>
    <button type="button" id="btn-aplicar" class="btn-primario">${icono("reiniciar", 14)} Aplicar y reiniciar</button>
  </aside>
</div>`;

let alMostrarPantalla = () => {};
let alOcultarPantalla = () => {};

export function alMostrar() {
  alMostrarPantalla();
}
export function alOcultar() {
  alOcultarPantalla();
}

export function montar(raiz, app) {
  raiz.innerHTML = PLANTILLA;
  const $ = (selector) => raiz.querySelector(selector);
  const lienzo = $("#lienzo");
  const ctx = lienzo.getContext("2d");

  const parametros = { ...PARAMETROS_POR_DEFECTO };
  let sesion = null;
  let plano = null;
  let estado = null;
  let historia = { pasos: [], evacuados: [] };
  let reproduciendo = false;
  let velocidad = 0;
  let celda = 20;

  // ------------------------------------------------------------- pintar

  function ajustar() {
    if (!plano) return;
    celda = ajustarCanvas(lienzo, $("#contenedor-lienzo"), plano.ancho, plano.alto);
    trazar();
  }

  function trazar() {
    if (plano && estado) dibujarSimulacion(ctx, plano.filas, estado, celda);
  }

  function flujo() {
    // personas que salieron por paso, en los ultimos pasos registrados
    const n = historia.pasos.length;
    if (n < 2) return 0;
    const desde = Math.max(0, n - 1 - PASOS_PARA_EL_FLUJO);
    const pasos = historia.pasos[n - 1] - historia.pasos[desde];
    return pasos > 0 ? (historia.evacuados[n - 1] - historia.evacuados[desde]) / pasos : 0;
  }

  function actualizarTarjetas() {
    if (!estado) return;
    const dentro = estado.total - estado.evacuados;
    const pctBloqueados = dentro > 0 ? (100 * estado.bloqueados) / dentro : 0;
    $("#tarjeta-paso").textContent = estado.paso;
    $("#tarjeta-evacuados").textContent = estado.evacuados;
    $("#tarjeta-total").textContent = `/ ${estado.total}`;
    const pct = estado.total ? (100 * estado.evacuados) / estado.total : 0;
    $("#barra-evacuados").style.width = `${pct}%`;
    $("#tarjeta-porcentaje").textContent = `${pct.toFixed(1)}% a salvo`;
    $("#tarjeta-bloqueados").textContent = estado.bloqueados;
    $("#tarjeta-bloqueados-detalle").textContent = `${pctBloqueados.toFixed(1)}% de quienes siguen dentro`;
    const alta = pctBloqueados >= 50;
    $("#caja-bloqueados").className = `tarjeta p-4 ${alta ? "!border-bloqueo/70 bg-error-container/10" : ""}`;
    $("#tarjeta-bloqueados").className = `valor mt-2 text-2xl font-medium xl:text-3xl ${alta ? "text-bloqueo" : ""}`;
    $("#tarjeta-flujo").textContent = flujo().toFixed(1);

    $("#curva").innerHTML = graficoLineas({
      series: [{ etiqueta: "Evacuados", color: "#0ea5e9", x: historia.pasos, y: historia.evacuados }],
      tope: estado.total,
    });
  }

  function actualizarControles() {
    const terminada = estado?.terminada;
    $("#btn-play").innerHTML = reproduciendo
      ? `${icono("pausa", 14)}<span>Pausar</span>`
      : `${icono("play", 14)}<span>Reproducir</span>`;
    $("#btn-play").disabled = !estado || terminada;
    $("#btn-paso").disabled = !estado || terminada || reproduciendo;
    const texto = terminada ? "TERMINADA" : reproduciendo ? "EN CURSO" : estado?.paso ? "EN PAUSA" : "LISTA";
    const color = terminada ? "text-secondary border-secondary-container" : reproduciendo ? "text-primary border-primary-container" : "text-on-surface-variant";
    $("#estado-texto").className = `ml-auto rounded-full border px-3 py-1 font-mono text-[10px] font-semibold tracking-wider ${color}`;
    $("#estado-texto").textContent = texto;
    raiz.querySelectorAll("[data-velocidad]").forEach((boton) => {
      boton.classList.toggle("btn-activo", Number(boton.dataset.velocidad) === velocidad);
    });
  }

  function mostrarAviso(texto) {
    $("#aviso").classList.toggle("hidden", !texto);
    $("#aviso").textContent = texto || "";
  }

  function sincronizarPanel() {
    for (const [clave, , , , , esPorcentaje] of DESLIZADORES) {
      const valor = esPorcentaje ? Math.round(parametros[clave] * 100) : parametros[clave];
      $(`#parametro-${clave}`).value = valor;
      $(`#valor-${clave}`).textContent = esPorcentaje ? `${valor}%` : valor;
    }
    raiz.querySelectorAll("[data-vecindad]").forEach((boton) => {
      boton.classList.toggle("btn-activo", boton.dataset.vecindad === parametros.tipo_vecindad);
    });
    $("#semilla").value = parametros.semilla;
  }

  // ----------------------------------------------------------- servidor

  function origenDelPlano() {
    const valor = $("#origen").value;
    return valor === DISENO_ACTUAL ? { filas: app.filas, etiqueta: "Diseño actual" } : { recinto: valor };
  }

  async function reiniciar() {
    reproduciendo = false;
    mostrarAviso("");
    if (sesion) api.borrarSimulacion(sesion).catch(() => {});
    sesion = null;
    try {
      const creada = await api.crearSimulacion(origenDelPlano(), parametros);
      sesion = creada.id;
      plano = creada.plano;
      estado = creada.estado;
      historia = { pasos: [estado.paso], evacuados: [estado.evacuados] };
      $("#titulo-plano").textContent = `${plano.etiqueta} · ${plano.ancho}×${plano.alto}`;
      ajustar();
    } catch (error) {
      estado = null;
      mostrarAviso(error.message);
    }
    actualizarTarjetas();
    actualizarControles();
  }

  async function avanzar(cantidad) {
    estado = await api.pasos(sesion, cantidad);
    historia.pasos.push(estado.paso);
    historia.evacuados.push(estado.evacuados);
    trazar();
    actualizarTarjetas();
  }

  async function bucle() {
    const mia = sesion;
    while (reproduciendo && sesion === mia && !estado.terminada) {
      const inicio = performance.now();
      try {
        await avanzar(VELOCIDADES[velocidad].pasosPorTick);
      } catch (error) {
        mostrarAviso(error.message);
        break;
      }
      const espera = Math.max(0, MS_POR_TICK - (performance.now() - inicio));
      await new Promise((resolver) => setTimeout(resolver, espera));
    }
    if (sesion === mia) reproduciendo = false;
    actualizarControles();
  }

  // ------------------------------------------------------------ botones

  $("#btn-play").addEventListener("click", () => {
    if (!estado || estado.terminada) return;
    reproduciendo = !reproduciendo;
    actualizarControles();
    if (reproduciendo) bucle();
  });

  $("#btn-paso").addEventListener("click", async () => {
    if (!estado || estado.terminada || reproduciendo) return;
    try {
      await avanzar(1);
    } catch (error) {
      mostrarAviso(error.message);
    }
    actualizarControles();
  });

  $("#btn-reiniciar").addEventListener("click", reiniciar);
  $("#btn-aplicar").addEventListener("click", reiniciar);
  $("#origen").addEventListener("change", reiniciar);

  raiz.querySelectorAll("[data-velocidad]").forEach((boton) => {
    boton.addEventListener("click", () => {
      velocidad = Number(boton.dataset.velocidad);
      actualizarControles();
    });
  });

  for (const [clave, , , , , esPorcentaje] of DESLIZADORES) {
    $(`#parametro-${clave}`).addEventListener("input", (evento) => {
      const crudo = Number(evento.target.value);
      parametros[clave] = esPorcentaje ? crudo / 100 : crudo;
      sincronizarPanel();
    });
  }
  raiz.querySelectorAll("[data-vecindad]").forEach((boton) => {
    boton.addEventListener("click", () => {
      parametros.tipo_vecindad = boton.dataset.vecindad;
      sincronizarPanel();
    });
  });
  $("#semilla").addEventListener("input", (evento) => {
    parametros.semilla = Math.max(0, Math.floor(Number(evento.target.value) || 0));
  });
  $("#btn-semilla").addEventListener("click", () => {
    parametros.semilla = Math.floor(Math.random() * 100000);
    sincronizarPanel();
  });

  window.addEventListener("resize", () => !raiz.hidden && ajustar());

  // ------------------------------------------------------------- inicio

  function llenarOrigenes(elegido) {
    const opciones = [`<option value="${DISENO_ACTUAL}">Diseño actual (${app.nombre || "sin nombre"})</option>`]
      .concat(app.recintos.map((r) => `<option value="${r.nombre}">${r.nombre}</option>`));
    $("#origen").innerHTML = opciones.join("");
    $("#origen").value = elegido;
  }

  alMostrarPantalla = async () => {
    sincronizarPanel();
    const esPrimeraVez = sesion === null && estado === null;
    if (app.simularDisenoAlEntrar) {
      app.simularDisenoAlEntrar = false;
      llenarOrigenes(DISENO_ACTUAL);
      await reiniciar();
    } else if (esPrimeraVez) {
      const porDefecto = app.recintos.some((r) => r.nombre === "sala_con_puerta")
        ? "sala_con_puerta"
        : app.recintos[0]?.nombre ?? DISENO_ACTUAL;
      llenarOrigenes(porDefecto);
      await reiniciar();
    } else {
      llenarOrigenes($("#origen").value || DISENO_ACTUAL);
      ajustar();
      actualizarControles();
    }
  };

  alOcultarPantalla = () => {
    reproduciendo = false; // no seguir calculando pasos si se cambia de pantalla
    actualizarControles();
  };

  sincronizarPanel();
  actualizarControles();
}
