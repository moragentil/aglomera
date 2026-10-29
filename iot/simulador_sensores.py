"""Simulador de sensores de ocupación: hace de gateway de juguete.

En un recinto real habría contadores o cámaras que informan cuánta gente hay en
cada sector. Como no hay hardware, este script hace ese papel: pregunta a la
API qué zonas tiene un recinto, genera conteos plausibles y los envía cada
pocos segundos, igual que lo haría un gateway real (ver docs/iot.md).

Con el servidor andando (venv/bin/uvicorn web.app:app --port 8000):

    venv/bin/python -m iot.simulador_sensores --recinto sala_con_puerta

Después, en la pestaña Simular de la app, el panel de sensores muestra las
lecturas en vivo y se puede arrancar la simulación con esa ocupación.

Para mostrar qué pasa cuando un sensor se rompe, `--falla B1:10` hace que el
sensor de la zona B1 deje de reportar después de 10 envíos: la zona pasa a
SIN SEÑAL y deja de usarse.

La lógica de generar los conteos son funciones puras (se prueban sin red); lo
único que usa la red es `main`, con la biblioteca estándar: no hace falta
instalar nada.
"""

import argparse
import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

URL_POR_DEFECTO = "http://localhost:8000"
FACTOR_DE_LA_ZONA_LLENA = 6  # en el escenario "concentrado", cuanto pesa esa zona frente a las demás


def repartir(total, pesos, capacidades):
    """Reparte `total` personas entre zonas en proporción a `pesos`, sin pasar la
    capacidad de ninguna. Si no hay lugar para todos, reparte los que entran.
    Devuelve una lista de enteros (método del mayor resto)."""
    resultado = [0] * len(pesos)
    restante = min(total, sum(capacidades))
    abiertas = [i for i in range(len(pesos)) if capacidades[i] > 0 and pesos[i] > 0]

    while restante > 0 and abiertas:
        suma = sum(pesos[i] for i in abiertas)
        ideal = {i: restante * pesos[i] / suma for i in abiertas}
        base = {i: int(ideal[i]) for i in abiertas}
        faltan = restante - sum(base.values())
        for i in sorted(abiertas, key=lambda i: ideal[i] - base[i], reverse=True)[:faltan]:
            base[i] += 1
        for i in abiertas:
            dar = min(base[i], capacidades[i] - resultado[i])
            resultado[i] += dar
            restante -= dar
        abiertas = [i for i in abiertas if resultado[i] < capacidades[i]]
    return resultado


def pesos_del_escenario(escenario, capacidades, ids, zona_llena=None):
    """Cómo se distribuye la gente: "parejo" (misma densidad en todo el recinto)
    o "concentrado" (una zona mucho más llena que las otras)."""
    pesos = [float(c) for c in capacidades]
    if escenario == "concentrado":
        elegida = zona_llena if zona_llena in ids else ids[0]
        pesos[ids.index(elegida)] *= FACTOR_DE_LA_ZONA_LLENA
    return pesos


def conteos_en_un_instante(total, pesos_base, capacidades, ruido, azar):
    """Los conteos de un instante: la distribución base con algo de variación,
    porque en la vida real la gente se mueve entre sectores. El total se mantiene."""
    pesos = [max(0.05, 1 + azar.gauss(0, ruido)) * peso for peso in pesos_base]
    return repartir(total, pesos, capacidades)


def construir_mensaje(columnas, filas, ids, conteos, ahora, silenciadas=()):
    """El mensaje que manda el gateway. Las zonas `silenciadas` no reportan."""
    momento = ahora.isoformat(timespec="seconds")
    return {
        "columnas": columnas,
        "filas": filas,
        "lecturas": [
            {"sensor": f"sensor-{zona.lower()}", "zona": zona, "personas": personas, "momento": momento}
            for zona, personas in zip(ids, conteos)
            if zona not in silenciadas
        ],
    }


# ------------------------------------------------------------------- red


def _pedir(url, cuerpo=None):
    datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
    pedido = urllib.request.Request(url, data=datos, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(pedido, timeout=10) as respuesta:
        return json.load(respuesta)


def _leer_argumentos(argv):
    parser = argparse.ArgumentParser(description="Simula sensores de ocupación que informan a la API.")
    parser.add_argument("--recinto", required=True, help="nombre de un recinto guardado (por ejemplo sala_con_puerta)")
    parser.add_argument("--url", default=URL_POR_DEFECTO, help="dónde está la API (por defecto %(default)s)")
    parser.add_argument("--columnas", type=int, default=3, help="zonas a lo ancho (por defecto %(default)s)")
    parser.add_argument("--filas", type=int, default=2, help="zonas a lo alto (por defecto %(default)s)")
    parser.add_argument("--total", type=int, default=40, help="personas en el recinto (por defecto %(default)s)")
    parser.add_argument("--intervalo", type=float, default=2.0, help="segundos entre envíos (por defecto %(default)s)")
    parser.add_argument("--lecturas", type=int, default=0, help="cuántos envíos hacer; 0 es sin parar")
    parser.add_argument("--escenario", choices=["parejo", "concentrado"], default="parejo")
    parser.add_argument("--zona-llena", help="en el escenario concentrado, qué zona es la llena (por ejemplo B1)")
    parser.add_argument("--ruido", type=float, default=0.15, help="variación entre envíos (por defecto %(default)s)")
    parser.add_argument("--semilla", type=int, default=1, help="para repetir la misma secuencia")
    parser.add_argument("--falla", help="ZONA:ENVIOS, ej. B1:10: ese sensor deja de reportar tras esos envíos")
    return parser.parse_args(argv)


def main(argv=None):
    args = _leer_argumentos(argv)
    base = args.url.rstrip("/")
    consulta = urllib.parse.urlencode({"columnas": args.columnas, "filas": args.filas})

    try:
        zonas = _pedir(f"{base}/api/recintos/{args.recinto}/zonas?{consulta}")
    except urllib.error.HTTPError as error:
        sys.exit(f"La API rechazó el pedido ({error.code}): {error.read().decode('utf-8', 'replace')}")
    except urllib.error.URLError as error:
        sys.exit(f"No pude conectarme a {base}: {error.reason}. ¿Está andando el servidor?")

    ids = [z["id"] for z in zonas]
    capacidades = [z["capacidad"] for z in zonas]
    pesos = pesos_del_escenario(args.escenario, capacidades, ids, args.zona_llena)
    azar = random.Random(args.semilla)

    zona_con_falla, envios_hasta_la_falla = (None, None)
    if args.falla:
        zona_con_falla, _, envios = args.falla.partition(":")
        envios_hasta_la_falla = int(envios or 0)

    print(f"Recinto {args.recinto}: {len(ids)} zonas ({', '.join(ids)}), {args.total} personas, "
          f"escenario {args.escenario}. Ctrl+C para cortar.")

    envio = 0
    try:
        while args.lecturas == 0 or envio < args.lecturas:
            envio += 1
            conteos = conteos_en_un_instante(args.total, pesos, capacidades, args.ruido, azar)
            silenciadas = {zona_con_falla} if zona_con_falla and envio > envios_hasta_la_falla else set()
            mensaje = construir_mensaje(args.columnas, args.filas, ids, conteos, datetime.now(timezone.utc), silenciadas)
            try:
                _pedir(f"{base}/api/sensores/{args.recinto}", mensaje)
                detalle = " ".join(f"{z}={n}" for z, n in zip(ids, conteos) if z not in silenciadas)
                caidas = f"  (sin reportar: {', '.join(sorted(silenciadas))})" if silenciadas else ""
                print(f"[{datetime.now().strftime('%H:%M:%S')}] envío {envio}: {detalle}{caidas}")
            except (urllib.error.URLError, OSError) as error:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] no se pudo enviar: {error}", file=sys.stderr)
            if args.lecturas == 0 or envio < args.lecturas:
                time.sleep(args.intervalo)
    except KeyboardInterrupt:
        print("\nCortado.")


if __name__ == "__main__":
    main()
