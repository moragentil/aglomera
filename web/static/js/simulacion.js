// Pantalla 2: SIMULAR. El servidor guarda la simulacion y calcula cada paso;
// esta pantalla pide pasos, dibuja lo que vuelve y muestra las metricas.

import { api } from "./api.js";
import { COLORES, ajustarCanvas, dibujarSimulacion, dibujarZonas } from "./dibujo.js";
import { graficoLineas } from "./graficos.js";
import { icono } from "./iconos.js";

const DISENO_ACTUAL = "__diseno__";
// 1× son 10 pasos por segundo. Las velocidades lentas esperan más entre un paso y
// el siguiente; las rápidas hacen varios pasos cada 100 ms.
const VELOCIDADES = [
  { etiqueta: "0,25×", pasosPorTick: 1, ms: 400 },
  { etiqueta: "0,5×", pasosPorTick: 1, ms: 200 },
  { etiqueta: "0,75×", pasosPorTick: 1, ms: 133 },
  { etiqueta: "1×", pasosPorTick: 1, ms: 100 },
  { etiqueta: "2×", pasosPorTick: 2, ms: 100 },
  { etiqueta: "5×", pasosPorTick: 5, ms: 100 },
  { etiqueta: "10×", pasosPorTick: 10, ms: 100 },
];
const VELOCIDAD_POR_DEFECTO = 3; // 1×
const PASOS_PARA_EL_FLUJO = 10;
const MS_ENTRE_CONSULTAS_DE_SENSORES = 2000;

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
    <div class="flex flex-col gap-3 border-b border-outline-variant/30 pb-5">
      <div class="flex items-center justify-between">
        <span class="etiqueta">Sensores de ocupación (IoT)</span>
        <span id="sensores-estado" class="rounded-full border border-outline-variant/60 px-2 py-0.5 font-mono text-[10px] font-semibold tracking-wider"></span>
      </div>
      <p class="text-[11px] leading-snug text-on-surface-variant">Es opcional. Con sensores, la simulación arranca con la gente que ellos cuentan en cada zona. Sin sensores, usa el slider «Cantidad de peatones».</p>

      <span class="etiqueta !text-primary">Paso 1 · Encender los sensores</span>
      <div id="sensores-contenido" class="text-xs"></div>
      <div id="sensores-simulador" class="flex flex-col gap-2 rounded border border-outline-variant/30 bg-surface-container-lowest p-3">
        <span class="etiqueta">Sensores simulados</span>
        <label class="flex flex-col gap-1 text-[11px] text-on-surface-variant">Personas que hay en el recinto
          <input type="number" id="sim-total" class="entrada !py-1" min="1" max="500" value="40" />
          <span class="leading-snug">Es lo que los sensores falsos fingen contar. En un recinto real lo daría la gente que entró.</span></label>
        <label class="flex flex-col gap-1 text-[11px] text-on-surface-variant">Cómo se reparten
          <select id="sim-escenario" class="entrada !py-1">
            <option value="parejo">Parejo en todo el recinto</option>
            <option value="concentrado">Concentrada en una zona</option>
          </select></label>
        <label class="flex items-center gap-2 text-[11px]">
          <input type="checkbox" id="sim-falla" class="accent-[#0ea5e9]" /> Simular que un sensor falla
        </label>
        <button type="button" id="btn-sensores" class="btn-primario"></button>
        <p id="sim-estado" class="font-mono text-[10px] leading-snug text-on-surface-variant"></p>
      </div>

      <span class="etiqueta !text-primary">Paso 2 · ¿De dónde sale la gente?</span>
      <div class="flex flex-col gap-2">
        <label class="flex items-start gap-2 text-xs">
          <input type="radio" name="fuente" id="fuente-azar" class="mt-0.5 accent-[#0ea5e9]" checked />
          <span>Al azar, según el slider<br /><span class="text-[11px] leading-snug text-on-surface-variant">La cantidad la elegís en «Cantidad de peatones».</span></span>
        </label>
        <label class="flex items-start gap-2 text-xs">
          <input type="radio" name="fuente" id="fuente-sensores" class="mt-0.5 accent-[#0ea5e9]" />
          <span>Medida por los sensores<br /><span id="usar-sensores-detalle" class="text-[11px] leading-snug text-on-surface-variant"></span></span>
        </label>
      </div>
      <p id="fuente-ayuda" class="rounded bg-surface-container-lowest p-2 text-[11px] leading-snug text-on-surface-variant"></p>
      <label class="flex items-center gap-2 text-xs">
        <input type="checkbox" id="ver-zonas" class="accent-[#0ea5e9]" checked /> Ver las zonas en el plano
      </label>
    </div>
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
  let velocidad = VELOCIDAD_POR_DEFECTO;
  let celda = 20;
  let sensores = null; // lo ultimo que informo la API (o null si no hay)
  let usarSensores = false;
  let totalDeSensoresEditado = false;
  let totalMedidoUsado = null; // cuantas personas se ubicaron al iniciar con ocupacion medida
  let temporizadorDeSensores = null;

  // ------------------------------------------------------------- pintar

  function ajustar() {
    if (!plano) return;
    celda = ajustarCanvas(lienzo, $("#contenedor-lienzo"), plano.ancho, plano.alto);
    trazar();
  }

  function trazar() {
    if (!plano || !estado) return;
    dibujarSimulacion(ctx, plano.filas, estado, celda);
    if ($("#ver-zonas").checked && sensores?.hay_datos && esUnRecintoGuardado()) {
      dibujarZonas(ctx, sensores.zonas, celda);
    }
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
    if (!totalDeSensoresEditado && !$("#sim-total").disabled) {
      $("#sim-total").value = Math.min(500, parametros.num_agentes);
    }
    actualizarOpcionDeSensores();
  }

  // ------------------------------------------------------------ sensores

  const esUnRecintoGuardado = () => $("#origen").value !== DISENO_ACTUAL;

  function actualizarOpcionDeSensores() {
    const disponible = esUnRecintoGuardado() && (sensores?.zonas_vigentes ?? 0) > 0;
    if (!disponible) usarSensores = false;
    $("#fuente-sensores").disabled = !disponible;
    $("#fuente-sensores").checked = usarSensores;
    $("#fuente-azar").checked = !usarSensores;
    $("#usar-sensores-detalle").textContent = disponible
      ? `${sensores.total_vigente} personas medidas en ${sensores.zonas_vigentes} zonas activas`
      : "Disponible cuando haya sensores activos (paso 1).";
    let ayuda;
    if (!esUnRecintoGuardado()) ayuda = "Para usar sensores, elegí un recinto guardado en «Recinto».";
    else if (!disponible) ayuda = "Para usar sensores, primero encendelos en el paso 1.";
    else if (!usarSensores) ayuda = "Los sensores ya están informando, pero la simulación todavía usa el slider. Elegí «Medida por los sensores» para usarlos.";
    else ayuda = `La simulación empezó con ${totalMedidoUsado ?? sensores.total_vigente} personas medidas por los sensores; el slider no se usa.`;
    $("#fuente-ayuda").textContent = ayuda;
    // con ocupacion medida la cantidad de peatones la dan los sensores, no el slider
    $("#parametro-num_agentes").disabled = usarSensores;
    $("#valor-num_agentes").textContent = usarSensores
      ? `${totalMedidoUsado ?? sensores.total_vigente} (medidos)`
      : parametros.num_agentes;
  }

  function actualizarControlesDelSimulador() {
    const visible = esUnRecintoGuardado();
    $("#sensores-simulador").classList.toggle("hidden", !visible);
    if (!visible) return;
    const simulador = sensores?.simulador;
    const activo = Boolean(simulador?.activo);
    for (const id of ["#sim-total", "#sim-escenario", "#sim-falla"]) $(id).disabled = activo;
    $("#btn-sensores").className = activo ? "btn" : "btn-primario";
    $("#btn-sensores").innerHTML = activo ? `${icono("pausa", 14)} Apagar sensores simulados` : `${icono("rayo", 14)} Iniciar sensores simulados`;
    if (activo) {
      const falla = simulador.zona_con_falla
        ? ` El sensor de ${simulador.zona_con_falla} falla tras ${simulador.envios_antes_de_la_falla} envíos.`
        : "";
      $("#sim-estado").textContent = `Generando datos cada ${simulador.intervalo_s} s · envío ${simulador.envios}.${falla}`;
    } else {
      $("#sim-estado").textContent = "Apagados. Las lecturas que quedaron caducan solas y las zonas pasan a SIN SEÑAL.";
    }
  }

  function dibujarEstadoDeSensores() {
    const caja = $("#sensores-contenido");
    const pastilla = $("#sensores-estado");
    const colorDeLaPastilla = (clases) => (pastilla.className = `rounded-full border px-2 py-0.5 font-mono text-[10px] font-semibold tracking-wider ${clases}`);

    if (!esUnRecintoGuardado()) {
      colorDeLaPastilla("border-outline-variant/60 text-on-surface-variant");
      pastilla.textContent = "—";
      caja.innerHTML = `<p class="leading-snug text-on-surface-variant">Los sensores se asocian a un recinto guardado. Guardá el diseño en la pestaña Diseño para usarlos.</p>`;
    } else if (!sensores?.hay_datos) {
      colorDeLaPastilla("border-outline-variant/60 text-on-surface-variant");
      pastilla.textContent = "SIN DATOS";
      caja.innerHTML = `<p class="leading-snug text-on-surface-variant">Ningún sensor está informando. Encendé los sensores simulados con el botón de abajo.</p>`;
    } else {
      const activas = sensores.zonas_vigentes;
      const todas = sensores.zonas.length;
      colorDeLaPastilla(activas === todas ? "border-secondary-container text-secondary" : "border-tertiary/60 text-tertiary");
      pastilla.textContent = `${activas}/${todas} ACTIVAS`;
      const color = { ACTIVO: "bg-secondary", "SIN SEÑAL": "bg-bloqueo", "SIN DATOS": "bg-outline" };
      caja.innerHTML = `<table class="w-full font-mono text-[11px]"><thead><tr class="text-left text-on-surface-variant">
          <th class="py-1 font-semibold">ZONA</th><th class="py-1 text-right font-semibold">PERS.</th><th class="py-1 text-right font-semibold">HACE</th><th class="py-1 pl-2 font-semibold">ESTADO</th></tr></thead><tbody>${
        sensores.zonas
          .map(
            (z) => `<tr class="border-t border-outline-variant/30">
          <td class="py-1">${z.id}</td><td class="valor py-1 text-right">${z.personas ?? "—"}</td>
          <td class="valor py-1 text-right text-on-surface-variant">${z.edad_s == null ? "—" : `${Math.round(z.edad_s)} s`}</td>
          <td class="py-1 pl-2"><span class="mr-1 inline-block h-1.5 w-1.5 rounded-full ${color[z.estado]}"></span>${z.estado}</td></tr>`,
          )
          .join("")
      }</tbody></table>
      <p class="mt-2 font-mono text-[10px] text-on-surface-variant">Total vigente: <b class="text-on-surface">${sensores.total_vigente}</b> personas. Una zona sin reportar más de ${sensores.caducidad_s} s pasa a SIN SEÑAL y no se usa.</p>`;
    }
    actualizarControlesDelSimulador();
    actualizarOpcionDeSensores();
  }

  async function consultarSensores() {
    if (!esUnRecintoGuardado()) {
      sensores = null;
    } else {
      try {
        sensores = await api.sensores($("#origen").value);
      } catch {
        sensores = null; // sin servidor o sin recinto: se muestra como sin datos
      }
    }
    dibujarEstadoDeSensores();
    trazar();
  }

  function empezarAConsultarSensores() {
    clearInterval(temporizadorDeSensores);
    consultarSensores();
    temporizadorDeSensores = setInterval(consultarSensores, MS_ENTRE_CONSULTAS_DE_SENSORES);
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
      const creada = await api.crearSimulacion(origenDelPlano(), parametros, usarSensores ? "sensores" : "azar");
      if (creada.ocupacion.avisos.length) mostrarAviso(creada.ocupacion.avisos.join(" "));
      totalMedidoUsado = creada.ocupacion.fuente === "sensores" ? creada.ocupacion.total : null;
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
      const espera = Math.max(0, VELOCIDADES[velocidad].ms - (performance.now() - inicio));
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
  $("#origen").addEventListener("change", async () => {
    usarSensores = false;
    await consultarSensores();
    reiniciar();
  });
  for (const radio of raiz.querySelectorAll('input[name="fuente"]')) {
    radio.addEventListener("change", async () => {
      usarSensores = $("#fuente-sensores").checked;
      totalMedidoUsado = null;
      actualizarOpcionDeSensores();
      await reiniciar();
      actualizarOpcionDeSensores(); // ahora ya se sabe cuantos se usaron
    });
  }
  // el total de los sensores falsos arranca con el valor del slider, salvo que lo cambies a mano
  $("#sim-total").addEventListener("input", () => (totalDeSensoresEditado = true));
  $("#ver-zonas").addEventListener("change", trazar);
  $("#btn-sensores").addEventListener("click", async () => {
    const recinto = $("#origen").value;
    $("#btn-sensores").disabled = true;
    try {
      if (sensores?.simulador?.activo) {
        await api.apagarSensores(recinto);
      } else {
        const total = Math.min(500, Math.max(1, Math.floor(Number($("#sim-total").value) || 40)));
        $("#sim-total").value = total;
        await api.encenderSensores(recinto, {
          total,
          escenario: $("#sim-escenario").value,
          falla: $("#sim-falla").checked,
        });
      }
    } catch (error) {
      mostrarAviso(error.message);
    }
    $("#btn-sensores").disabled = false;
    await consultarSensores();
  });

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
    empezarAConsultarSensores();
  };

  alOcultarPantalla = () => {
    reproduciendo = false; // no seguir calculando pasos si se cambia de pantalla
    clearInterval(temporizadorDeSensores); // ni consultando a la API
    actualizarControles();
  };

  sincronizarPanel();
  actualizarControles();
}
