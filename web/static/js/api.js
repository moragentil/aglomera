// Llamadas a la API (todas devuelven JSON). Un error del servidor se convierte
// en una excepcion con el mensaje ya listo para mostrarle al usuario.

export class ErrorApi extends Error {
  constructor(mensaje, estado) {
    super(mensaje);
    this.estado = estado;
  }
}

async function pedir(ruta, opciones = {}) {
  const respuesta = await fetch(ruta, {
    headers: { "Content-Type": "application/json" },
    ...opciones,
  });
  if (!respuesta.ok) {
    let mensaje = `Error ${respuesta.status}`;
    try {
      const { detail } = await respuesta.json();
      // pydantic devuelve una lista de errores; las demas rutas, un texto
      mensaje = Array.isArray(detail) ? detail.map((e) => e.msg).join("; ") : detail || mensaje;
    } catch {
      /* sin cuerpo: queda el mensaje generico */
    }
    throw new ErrorApi(mensaje, respuesta.status);
  }
  return respuesta.status === 204 ? null : respuesta.json();
}

const enviar = (metodo, cuerpo) => ({ method: metodo, body: JSON.stringify(cuerpo) });

export const api = {
  recintos: () => pedir("/api/recintos"),
  validar: (filas) => pedir("/api/validar", enviar("POST", { filas })),
  guardar: (nombre, filas, sobrescribir) =>
    pedir("/api/recintos", enviar("POST", { nombre, filas, sobrescribir })),
  crearSimulacion: (plano, parametros, ocupacion = "azar") =>
    pedir("/api/simulaciones", enviar("POST", { plano, parametros, ocupacion })),
  sensores: (recinto) => pedir(`/api/sensores/${recinto}`),
  encenderSensores: (recinto, cuerpo) =>
    pedir(`/api/sensores/${recinto}/simulador`, enviar("POST", cuerpo)),
  apagarSensores: (recinto) => pedir(`/api/sensores/${recinto}/simulador`, { method: "DELETE" }),
  pasos: (id, cantidad) => pedir(`/api/simulaciones/${id}/pasos`, enviar("POST", { cantidad })),
  borrarSimulacion: (id) => pedir(`/api/simulaciones/${id}`, { method: "DELETE" }),
  comparar: (planos, semillas, parametros) =>
    pedir("/api/comparaciones", enviar("POST", { planos, semillas, parametros })),
};
