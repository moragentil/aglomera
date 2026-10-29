// Pantalla 1: DISEÑO. Se dibuja el recinto con el mouse sobre una grilla.
// Las reglas del plano (validar, guardar) las pone el servidor; acá solo se
// dibuja, se pinta y se muestra lo que el servidor contesta.

import { api } from "./api.js";
import { icono } from "./iconos.js";
import {
  PARED,
  SALIDA,
  PISO,
  ajustarCanvas,
  conBorde,
  contar,
  dibujarMiniatura,
  dibujarPlano,
  pintar,
  planoInicial,
  recta,
  redimensionar,
  COLORES,
} from "./dibujo.js";

const HERRAMIENTAS = {
  pared: { caracter: PARED, tecla: "w", etiqueta: "Pared", icono: "pared" },
  salida: { caracter: SALIDA, tecla: "e", etiqueta: "Salida", icono: "salida" },
  borrar: { caracter: PISO, tecla: "x", etiqueta: "Borrar", icono: "borrar" },
};
const LIMITE_DE_DESHACER = 100;

const PLANTILLA = `
<div class="flex h-[calc(100vh-3.5rem)]">
  <div class="flex min-w-0 flex-1 flex-col gap-3 p-4">
    <div class="tarjeta flex flex-wrap items-center justify-between gap-3 px-3 py-2">
      <div class="flex gap-1 rounded-md border border-outline-variant/40 bg-surface-container-lowest p-1" id="herramientas">
        ${Object.entries(HERRAMIENTAS)
          .map(
            ([id, h]) => `
          <button type="button" class="btn !border-transparent !bg-transparent" data-herramienta="${id}">
            ${icono(h.icono, 14)}<span>${h.etiqueta}</span>
            <kbd class="rounded bg-surface-container-lowest px-1 font-mono text-[9px] text-on-surface-variant">${h.tecla.toUpperCase()}</kbd>
          </button>`,
          )
          .join("")}
      </div>
      <div class="flex flex-wrap gap-2">
        <button type="button" class="btn" id="btn-perimetro">${icono("perimetro", 14)} Pared perimetral</button>
        <button type="button" class="btn" id="btn-deshacer">${icono("deshacer", 14)} Deshacer</button>
        <button type="button" class="btn" id="btn-limpiar">${icono("limpiar", 14)} Limpiar</button>
      </div>
      <div class="flex items-center gap-5 font-mono text-xs text-on-surface-variant">
        <label class="flex items-center gap-2">Ancho <span id="val-ancho" class="valor w-5 text-on-surface"></span>
          <input type="range" class="deslizador !w-28" id="ancho" min="5" max="60" /></label>
        <label class="flex items-center gap-2">Alto <span id="val-alto" class="valor w-5 text-on-surface"></span>
          <input type="range" class="deslizador !w-28" id="alto" min="5" max="40" /></label>
      </div>
    </div>

    <div class="tarjeta flex min-h-0 flex-1 flex-col p-3">
      <div class="mb-2 flex flex-wrap items-center justify-between gap-2 font-mono text-[11px] text-on-surface-variant">
        <div class="flex gap-4">
          <span class="flex items-center gap-1.5"><i class="inline-block h-2.5 w-2.5 rounded-sm" style="background:${COLORES.pared}"></i>Pared</span>
          <span class="flex items-center gap-1.5"><i class="inline-block h-2.5 w-2.5 rounded-sm" style="background:${COLORES.salida}"></i>Salida</span>
          <span class="flex items-center gap-1.5"><i class="inline-block h-2.5 w-2.5 rounded-sm border border-outline-variant" style="background:${COLORES.piso}"></i>Espacio transitable</span>
        </div>
        <div><span id="pos" class="text-on-surface">Pos: —</span> <span class="text-outline-variant">|</span> Clic o arrastre para dibujar</div>
      </div>
      <div id="contenedor-lienzo" class="flex min-h-0 flex-1 items-center justify-center">
        <canvas id="lienzo" class="lienzo cursor-crosshair rounded border border-outline-variant/60"></canvas>
      </div>
      <div id="pie" class="mt-2 flex flex-wrap gap-x-4 border-t border-outline-variant/30 pt-2 font-mono text-[11px] text-on-surface-variant"></div>
    </div>
  </div>

  <aside class="flex w-80 shrink-0 flex-col gap-5 overflow-y-auto border-l border-outline-variant/40 bg-surface-container-low p-4">
    <div class="flex flex-col gap-1.5">
      <label class="etiqueta" for="nombre">Nombre del recinto</label>
      <input id="nombre" class="entrada" type="text" maxlength="60" spellcheck="false" />
      <span class="font-mono text-[10px] text-on-surface-variant">Letras, números, guion y guion bajo. Se guarda como recintos/&lt;nombre&gt;.txt</span>
    </div>

    <div class="flex flex-col gap-1.5">
      <span class="etiqueta">Estado de validación</span>
      <div id="validacion" class="rounded border border-outline-variant/40 px-3 py-2 text-xs"></div>
    </div>

    <div class="flex flex-col gap-2">
      <label class="flex items-center gap-2 font-mono text-[11px] text-on-surface-variant">
        <input type="checkbox" id="sobrescribir" class="accent-[#0ea5e9]" /> Sobrescribir si ya existe
      </label>
      <button type="button" id="btn-guardar" class="btn-primario">${icono("ok", 14)} Guardar recinto</button>
      <button type="button" id="btn-simular" class="btn">${icono("play", 14)} Simular este diseño</button>
      <div id="mensaje" class="min-h-[1.25rem] text-xs"></div>
    </div>

    <div class="flex flex-col gap-2 border-t border-outline-variant/30 pt-4">
      <span class="etiqueta">Recintos guardados</span>
      <div id="libreria" class="flex flex-col gap-2"></div>
    </div>
  </aside>
</div>`;

// lo define montar(): necesita el estado local de la pantalla
let alMostrarPantalla = () => {};

export function alMostrar() {
  alMostrarPantalla();
}

export function montar(raiz, app) {
  raiz.innerHTML = PLANTILLA;
  const $ = (selector) => raiz.querySelector(selector);
  const lienzo = $("#lienzo");
  const ctx = lienzo.getContext("2d");

  let herramienta = "pared";
  let celda = 20;
  let pintando = false;
  let ultimaCelda = null;
  let historial = [];
  let temporizadorDeValidacion = null;
  let valido = false;

  // ------------------------------------------------------------- dibujo

  function trazar() {
    dibujarPlano(ctx, app.filas, celda);
  }

  function ajustar() {
    const alto = app.filas.length;
    const ancho = app.filas[0].length;
    celda = ajustarCanvas(lienzo, $("#contenedor-lienzo"), ancho, alto);
    trazar();
    $("#ancho").value = ancho;
    $("#alto").value = alto;
    $("#val-ancho").textContent = ancho;
    $("#val-alto").textContent = alto;
    actualizarPie();
  }

  function actualizarPie() {
    const { paredes, salidas, transitables } = contar(app.filas);
    const alto = app.filas.length;
    const ancho = app.filas[0].length;
    $("#pie").innerHTML =
      `<span>Matriz: ${ancho} × ${alto} (${ancho * alto} celdas)</span>` +
      `<span>Paredes: <b class="font-normal text-on-surface">${paredes}</b></span>` +
      `<span>Salidas: <b class="font-normal text-secondary">${salidas}</b></span>` +
      `<span>Celdas transitables: <b class="font-normal text-primary">${transitables}</b></span>`;
  }

  function marcarHerramienta() {
    raiz.querySelectorAll("[data-herramienta]").forEach((boton) => {
      boton.classList.toggle("btn-activo", boton.dataset.herramienta === herramienta);
    });
  }

  // --------------------------------------------------------- validacion

  function pedirValidacion() {
    clearTimeout(temporizadorDeValidacion);
    temporizadorDeValidacion = setTimeout(async () => {
      try {
        const resultado = await api.validar(app.filas);
        valido = resultado.valido;
        $("#validacion").className = `rounded border px-3 py-2 text-xs ${
          valido ? "border-secondary-container/60 bg-secondary-container/10 text-secondary" : "border-tertiary/50 bg-error-container/20 text-tertiary"
        }`;
        $("#validacion").innerHTML = valido
          ? `<div class="flex items-center gap-2">${icono("ok", 14)} Plano válido: ${resultado.ancho}×${resultado.alto} celdas y ${resultado.salidas} de salida.</div>`
          : `<div class="flex items-start gap-2">${icono("alerta", 14)}<span>Todavía no sirve para simular: ${resultado.mensaje}</span></div>`;
      } catch (error) {
        valido = false;
        $("#validacion").textContent = `No se pudo validar: ${error.message}`;
      }
      actualizarBotones();
    }, 200);
  }

  function actualizarBotones() {
    const nombreValido = /^[A-Za-z0-9_-]+$/.test(app.nombre);
    $("#btn-guardar").disabled = !valido || !nombreValido;
    $("#btn-simular").disabled = !valido;
  }

  function huboCambios() {
    actualizarPie();
    pedirValidacion();
  }

  // ---------------------------------------------------------- historial

  function recordar() {
    historial.push(app.filas);
    if (historial.length > LIMITE_DE_DESHACER) historial.shift();
  }

  function deshacer() {
    if (!historial.length) return;
    app.filas = historial.pop();
    ajustar();
    huboCambios();
  }

  // -------------------------------------------------------------- mouse

  function celdaDe(evento) {
    const caja = lienzo.getBoundingClientRect();
    const x = Math.floor((evento.clientX - caja.left) / celda);
    const y = Math.floor((evento.clientY - caja.top) / celda);
    return [x, y];
  }

  function pintarHasta(destino) {
    const caracter = HERRAMIENTAS[herramienta].caracter;
    for (const [x, y] of recta(ultimaCelda, destino)) app.filas = pintar(app.filas, x, y, caracter);
    ultimaCelda = destino;
    trazar();
    actualizarPie();
  }

  lienzo.addEventListener("pointerdown", (evento) => {
    lienzo.setPointerCapture(evento.pointerId);
    recordar();
    pintando = true;
    ultimaCelda = celdaDe(evento);
    pintarHasta(ultimaCelda);
  });

  lienzo.addEventListener("pointermove", (evento) => {
    const [x, y] = celdaDe(evento);
    const dentro = y >= 0 && y < app.filas.length && x >= 0 && x < app.filas[0].length;
    $("#pos").textContent = dentro ? `Pos: [${String(x).padStart(2, "0")}, ${String(y).padStart(2, "0")}]` : "Pos: —";
    if (pintando) pintarHasta([x, y]);
  });

  const soltar = () => {
    if (!pintando) return;
    pintando = false;
    huboCambios();
  };
  lienzo.addEventListener("pointerup", soltar);
  lienzo.addEventListener("pointercancel", soltar);
  lienzo.addEventListener("pointerleave", () => ($("#pos").textContent = "Pos: —"));

  // ------------------------------------------------------------ botones

  raiz.querySelectorAll("[data-herramienta]").forEach((boton) => {
    boton.addEventListener("click", () => {
      herramienta = boton.dataset.herramienta;
      marcarHerramienta();
    });
  });

  $("#btn-perimetro").addEventListener("click", () => {
    recordar();
    app.filas = conBorde(app.filas);
    trazar();
    huboCambios();
  });
  $("#btn-limpiar").addEventListener("click", () => {
    recordar();
    app.filas = planoInicial(app.filas[0].length, app.filas.length);
    trazar();
    huboCambios();
  });
  $("#btn-deshacer").addEventListener("click", deshacer);

  for (const id of ["ancho", "alto"]) {
    $(`#${id}`).addEventListener("input", () => {
      const ancho = Number($("#ancho").value);
      const alto = Number($("#alto").value);
      if (ancho === app.filas[0].length && alto === app.filas.length) return;
      recordar();
      app.filas = redimensionar(app.filas, ancho, alto);
      ajustar();
      huboCambios();
    });
  }

  document.addEventListener("keydown", (evento) => {
    if (raiz.hidden || ["INPUT", "TEXTAREA"].includes(evento.target.tagName)) return;
    if ((evento.ctrlKey || evento.metaKey) && evento.key.toLowerCase() === "z") {
      evento.preventDefault();
      deshacer();
      return;
    }
    const elegida = Object.entries(HERRAMIENTAS).find(([, h]) => h.tecla === evento.key.toLowerCase());
    if (elegida && !evento.ctrlKey && !evento.metaKey) {
      herramienta = elegida[0];
      marcarHerramienta();
    }
  });

  window.addEventListener("resize", () => !raiz.hidden && ajustar());

  // ------------------------------------------------------------- nombre

  $("#nombre").addEventListener("input", () => {
    app.nombre = $("#nombre").value.trim();
    app.ponerChip(app.nombre || "sin nombre");
    $("#mensaje").textContent = "";
    actualizarBotones();
  });

  // ----------------------------------------------------- guardar y simular

  function mostrarMensaje(tipo, texto) {
    const colores = { ok: "text-secondary", error: "text-tertiary" };
    $("#mensaje").className = `min-h-[1.25rem] text-xs ${colores[tipo]}`;
    $("#mensaje").textContent = texto;
  }

  $("#btn-guardar").addEventListener("click", async () => {
    try {
      await api.guardar(app.nombre, app.filas, $("#sobrescribir").checked);
      mostrarMensaje("ok", `Guardado en recintos/${app.nombre}.txt`);
      await app.cargarRecintos();
      renderLibreria();
    } catch (error) {
      mostrarMensaje("error", error.message);
    }
  });

  $("#btn-simular").addEventListener("click", () => {
    app.simularDisenoAlEntrar = true;
    app.irA("simular");
  });

  // ----------------------------------------------------------- libreria

  function renderLibreria() {
    const contenedor = $("#libreria");
    if (!app.recintos.length) {
      contenedor.innerHTML = `<p class="text-xs text-on-surface-variant">Todavía no hay recintos guardados.</p>`;
      return;
    }
    contenedor.innerHTML = app.recintos
      .map(
        (r, i) => `
      <div class="tarjeta flex items-center gap-3 p-2">
        <canvas width="88" height="56" data-miniatura="${i}" class="shrink-0 rounded border border-outline-variant/40"></canvas>
        <div class="min-w-0 flex-1">
          <div class="truncate font-mono text-xs text-on-surface">${r.nombre}</div>
          <div class="font-mono text-[10px] text-on-surface-variant">${r.ancho}×${r.alto} · ${r.salidas} salida${r.salidas === 1 ? "" : "s"}</div>
        </div>
        <button type="button" class="btn !px-2 !py-1" data-abrir="${i}">Abrir</button>
      </div>`,
      )
      .join("");
    contenedor.querySelectorAll("[data-miniatura]").forEach((canvas) => {
      dibujarMiniatura(canvas, app.recintos[Number(canvas.dataset.miniatura)].filas);
    });
    contenedor.querySelectorAll("[data-abrir]").forEach((boton) => {
      boton.addEventListener("click", () => {
        const recinto = app.recintos[Number(boton.dataset.abrir)];
        recordar();
        app.filas = recinto.filas.slice();
        app.nombre = recinto.nombre;
        $("#nombre").value = app.nombre;
        app.ponerChip(app.nombre);
        $("#mensaje").textContent = "";
        ajustar();
        huboCambios();
      });
    });
  }

  // ------------------------------------------------------------- inicio

  alMostrarPantalla = () => {
    $("#nombre").value = app.nombre;
    app.ponerChip(app.nombre || "sin nombre");
    marcarHerramienta();
    ajustar();
    renderLibreria();
    huboCambios();
  };
}

