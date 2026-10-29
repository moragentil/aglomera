// Arranque de la app: estado compartido entre pantallas y navegacion.
//
// Cada pantalla (diseno.js, simulacion.js, comparar.js) exporta
// `montar(raiz, app)`, que arma su HTML una sola vez, y `alMostrar()`, que se
// llama cada vez que el usuario vuelve a ella.

import { api } from "./api.js";
import { planoInicial } from "./dibujo.js";
import * as diseno from "./diseno.js";
import * as simulacion from "./simulacion.js";
import * as comparar from "./comparar.js";

export const app = {
  filas: planoInicial(30, 16), // el diseño que se esta editando
  nombre: "mi_plano",
  recintos: [], // los guardados en recintos/
  simularDisenoAlEntrar: false,

  async cargarRecintos() {
    this.recintos = await api.recintos();
    return this.recintos;
  },

  irA(vista) {
    location.hash = vista;
  },

  ponerChip(texto) {
    document.getElementById("chip-diseno").textContent = texto;
  },
};

const VISTAS = { diseno, simular: simulacion, comparar };
const raices = {};

let vistaActual = null;

function mostrar() {
  const pedida = location.hash.replace("#", "");
  const nombre = pedida in VISTAS ? pedida : "diseno";
  if (vistaActual && vistaActual !== nombre) VISTAS[vistaActual].alOcultar?.();
  vistaActual = nombre;
  for (const [id, raiz] of Object.entries(raices)) raiz.hidden = id !== nombre;
  document.querySelectorAll("#navegacion a").forEach((a) => {
    a.classList.toggle("activa", a.dataset.vista === nombre);
  });
  VISTAS[nombre].alMostrar?.();
}

async function iniciar() {
  for (const [id, modulo] of Object.entries(VISTAS)) {
    raices[id] = document.getElementById(`vista-${id}`);
    modulo.montar(raices[id], app);
  }
  try {
    await app.cargarRecintos();
  } catch (error) {
    console.error("No se pudo leer la lista de recintos", error);
  }
  app.ponerChip(app.nombre);
  window.addEventListener("hashchange", mostrar);
  mostrar();
}

iniciar();
