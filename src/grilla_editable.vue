<template>
  <div
    class="grilla-editable"
    :style="{ gridTemplateColumns: 'repeat(' + ancho + ', ' + lado + 'px)' }"
    @mouseup="terminar"
    @mouseleave="terminar"
  >
    <div
      v-for="(celda, i) in vista"
      :key="i"
      :class="'celda ' + celda"
      :style="{ width: lado + 'px', height: lado + 'px' }"
      @mousedown.prevent="empezar(i)"
      @mouseenter="seguir(i)"
    ></div>
  </div>
</template>

<script>
// Python guarda el plano y manda `celdas`: una lista plana, una clase por celda
// ("piso", "pared" o "salida"), recorrida fila por fila desde arriba.
//
// Para que arrastrar el mouse sea fluido, cada celda pintada se muestra enseguida
// en el navegador (`cambios`) sin esperar la vuelta de Python, y a la vez se le
// avisa a Python (event_pintar). Cuando Python manda un plano nuevo, `cambios`
// se vacía: de ahi en adelante manda lo que dice Python.
module.exports = {
  data() {
    return { pintando: false, ultima: null, cambios: {} };
  },
  computed: {
    vista() {
      const celdas = (this.celdas || []).slice();
      for (const i in this.cambios) celdas[i] = this.cambios[i];
      return celdas;
    },
  },
  watch: {
    celdas() {
      this.cambios = {};
    },
  },
  methods: {
    empezar(i) {
      this.pintando = true;
      this.ultima = i;
      this.pintar_celda(i);
    },
    seguir(i) {
      if (!this.pintando) return;
      // si el mouse se mueve rapido el navegador se saltea celdas: se unen con una recta
      for (const celda of this.recta(this.ultima, i)) this.pintar_celda(celda);
      this.ultima = i;
    },
    terminar() {
      this.pintando = false;
      this.ultima = null;
    },
    // indices de las celdas entre `desde` y `hasta` (algoritmo de Bresenham)
    recta(desde, hasta) {
      let x = desde % this.ancho;
      let y = Math.floor(desde / this.ancho);
      const x_final = hasta % this.ancho;
      const y_final = Math.floor(hasta / this.ancho);
      const dx = Math.abs(x_final - x);
      const dy = Math.abs(y_final - y);
      const paso_x = x < x_final ? 1 : -1;
      const paso_y = y < y_final ? 1 : -1;
      let error = dx - dy;
      const celdas = [];
      for (;;) {
        celdas.push(y * this.ancho + x);
        if (x === x_final && y === y_final) return celdas;
        const doble = 2 * error;
        if (doble > -dy) {
          error -= dy;
          x += paso_x;
        }
        if (doble < dx) {
          error += dx;
          y += paso_y;
        }
      }
    },
    pintar_celda(i) {
      if (this.vista[i] === this.herramienta) return;
      this.$set(this.cambios, i, this.herramienta);
      this.event_pintar({
        x: i % this.ancho,
        y: Math.floor(i / this.ancho),
        herramienta: this.herramienta,
      });
    },
  },
};
</script>

<style id="grilla-editable-estilos">
.grilla-editable {
  display: grid;
  width: max-content;
  gap: 1px;
  padding: 1px;
  background: #9e9e9e;
  user-select: none;
  cursor: crosshair;
}
.grilla-editable .celda.piso {
  background: #ffffff;
}
.grilla-editable .celda.pared {
  background: #000000;
}
.grilla-editable .celda.salida {
  background: #2ca02c;
}
</style>
