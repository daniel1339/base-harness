#!/usr/bin/env python3
"""Mide cuanto costo un plan de verdad, sin que nadie apunte nada.

Existe porque un cronometro no se arranca: cualquier medida que dependa de
acordarse no se registra. Estas dos series ya existen y no hay que pedirlas:

  - `pacto exec` pone la hora a cada tarea que se cierra (en `tasks.md`)
  - `git` pone la hora a cada commit

Con las dos, un hueco entre actividad es una de tres cosas, y hay que separarlas
porque significan lo contrario:

  | Hueco                      | Que es                                       |
  |----------------------------|----------------------------------------------|
  | Termina en cierre de tarea | TRABAJO DEL PLAN                             |
  | Termina en commit ajeno    | COLATERAL: esfuerzo real, pero de otra cosa  |
  | Mas largo que el umbral    | SIN ACTIVIDAD: ni commits ni tareas          |

Medido el 2026-08-20: entre dos tareas del plan `estados-de-ejecucion` pasaron
2 h 48 min. Un cronometro habria dicho que esa tarea costo tres horas. Costo
cinco minutos: en el hueco se arreglaron los tests, un 500 en produccion y una
migracion. Ni fue la tarea, ni fue una pausa.

LIMITE QUE HAY QUE CONOCER: pensar no deja commits. Un rato largo de analisis,
de leer codigo o de decidir con alguien se ve exactamente igual que una comida,
y cae en "sin actividad". Por eso la columna NO se llama pausa: dice lo unico
que se puede afirmar, que no quedo rastro. La cifra de esfuerzo es un SUELO.

    python3 scripts/plan-time.py <slug>          # un plan
    python3 scripts/plan-time.py --ritmo         # el ritmo real de todos los cerrados
    python3 scripts/plan-time.py --autotest      # comprueba la aritmetica
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLANS = ROOT / ".pacto" / "plans"

# `pacto exec` deja esta linea al cerrar una tarea. El `[N.M]` del principio no
# lo pone pacto: es la convencion de la skill `plan-task`, y es lo unico que
# permite saber a que tarea pertenece cada hora.
EVIDENCIA = re.compile(r"^- (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})\s+`?\[?(\d+\.\d+)?\]?", re.M)
TAREA = re.compile(r"^- \[([ x])\] (\d+\.\d+) (.+)$", re.M)

# --- Idioma de los planes -------------------------------------------------
# Este script lee planes escritos en castellano. Si los tuyos van en otro
# idioma, esto es lo UNICO que hay que traducir.
#
# Y hay que traducirlo, porque no traducirlo **no da error**: el script sigue
# corriendo, clasifica todas las tareas como "construir" y produce un desglose
# creible y vacio, que es peor que no tener ninguno. `PALABRA_ESTIMACION` tiene
# que coincidir ademas con la que busca `scripts/plans-check.py`.
PALABRA_ESTIMACION = r"Estimaci[oó]n"
PALABRAS_DECIDIR = r"resolver|decidir|declarar|reconocimiento|enumerar|checklist|acotar"
PALABRAS_VERIFICAR = r"verificar|confirmar|revisar|comprobar"
PALABRA_CIERRE = "cierra"   # en el asunto de un commit: lo marca como del plan

ESTIMACION = re.compile(rf"^- {PALABRA_ESTIMACION}:\s*([\d.,]+)\s*h", re.M | re.I)

# Que clase de trabajo es cada tarea, por lo que dice. Sirve para responder la
# pregunta que mas cambia como se trabaja: si el tiempo se va en decidir o en
# construir.
DECIDIR = re.compile(PALABRAS_DECIDIR, re.I)
VERIFICAR = re.compile(PALABRAS_VERIFICAR, re.I)


def clase_de(texto: str) -> str:
    if DECIDIR.search(texto):
        return "decidir"
    if VERIFICAR.search(texto):
        return "verificar"
    return "construir"


def buscar_plan(slug: str) -> Path | None:
    for tasks in PLANS.glob(f"*/{slug}/tasks.md"):
        return tasks
    return None


def commits_en(desde: datetime, hasta: datetime, slug: str):
    """Commits del intervalo, marcando cuales son del plan.

    Un commit es del plan si nombra su slug o dice que cierra una tarea. El
    resto es colateral: trabajo real ocurrido mientras, pero de otra cosa.
    """
    salida = subprocess.run(
        ["git", "log", "--since", desde.isoformat(), "--until", hasta.isoformat(),
         "--pretty=%at%x09%s%x09%b", "--all"],
        cwd=ROOT, capture_output=True, text=True,
    ).stdout
    fuera = []
    for linea in salida.splitlines():
        ts, _, resto = linea.partition("\t")
        try:
            cuando = datetime.fromtimestamp(int(ts))
        except ValueError:
            continue
        texto = resto.lower()
        propio = slug in texto or PALABRA_CIERRE in texto
        fuera.append((cuando, "plan" if propio else "colateral", None))
    return fuera


def repartir(eventos, umbral_min: int):
    """El nucleo: reparte los huecos entre las tres cestas.

    Separado a proposito para poder comprobarlo sin git ni ficheros (--autotest).
    Equivocarse aqui produce numeros creibles y falsos, que es lo peor que puede
    pasarle a una medicion.
    """
    umbral = timedelta(minutes=umbral_min)
    cestas = {"plan": timedelta(), "colateral": timedelta(), "sin_actividad": timedelta()}
    por_clase: dict[str, timedelta] = {}

    for (t0, _, _), (t1, tipo, clase) in zip(eventos, eventos[1:]):
        hueco = t1 - t0
        if hueco > umbral:
            cestas["sin_actividad"] += hueco
        elif tipo == "plan":
            cestas["plan"] += hueco
            if clase:
                por_clase[clase] = por_clase.get(clase, timedelta()) + hueco
        else:
            cestas["colateral"] += hueco
    return cestas, por_clase


def medir(tasks: Path, slug: str, umbral_min: int):
    texto = tasks.read_text()

    clases = {num: clase_de(txt) for _, num, txt in TAREA.findall(texto)}

    marcas = []
    for d, h, num in EVIDENCIA.findall(texto):
        marcas.append((datetime.strptime(f"{d} {h}", "%Y-%m-%d %H:%M"),
                       "plan", clases.get(num) if num else None))
    if len(marcas) < 2:
        return None

    # Se ordena por fecha y se desempata con texto, **nunca con la clase cruda**:
    # una nota de ejecucion sin prefijo `[N.M]` no tiene tarea, asi que su clase
    # es None, y en cuanto coincidia en fecha con otra marca el sort comparaba
    # None con una cadena y reventaba. Se vio el 2026-08-25 cerrando
    # `brain-agente-maestro`, que es justo cuando este script hace falta.
    eventos = sorted(
        marcas + commits_en(
            min(m[0] for m in marcas),
            max(m[0] for m in marcas) + timedelta(minutes=1),
            slug),
        key=lambda e: (e[0], str(e[1] or ""), str(e[2] or "")),
    )
    cestas, por_clase = repartir(eventos, umbral_min)

    tareas = TAREA.findall(texto)
    est = ESTIMACION.search(texto)
    return {
        "estado": tasks.parent.parent.name,
        "tareas": len(tareas),
        "cerradas": sum(1 for m, _, _ in tareas if m == "x"),
        "inicio": min(m[0] for m in marcas),
        "fin": max(m[0] for m in marcas),
        "con_numero": sum(1 for _, _, c in marcas if c),
        **cestas,
        "por_clase": por_clase,
        "estimacion": float(est.group(1).replace(",", ".")) if est else None,
    }


def horas(d: timedelta) -> float:
    return round(d.total_seconds() / 3600, 1)


def ritmo_medido(umbral_min: int):
    """El ritmo real de los planes ya cerrados.

    Es lo que hace que el sistema se afine solo: la estimacion del plan
    siguiente sale de lo que costaron los anteriores, no del criterio de nadie.
    """
    total_min = 0.0
    total_tareas = 0
    planes = []
    descartados = []
    for tasks in sorted(PLANS.glob("done/*/tasks.md")):
        m = medir(tasks, tasks.parent.name, umbral_min)
        if not m or not m["cerradas"]:
            continue
        minutos = m["plan"].total_seconds() / 60
        esfuerzo = m["plan"] + m["colateral"]

        # Un plan ejecutado a ratos durante semanas no se puede medir asi: casi
        # todo cae en "sin actividad" y el poco tiempo que queda produce un
        # ritmo falso. Mejor descartarlo y decirlo que promediar basura.
        if esfuerzo.total_seconds() and m["sin_actividad"] > esfuerzo * 5:
            descartados.append((tasks.parent.name, "ejecutado a ratos, no en sesiones"))
            continue

        total_min += minutos
        total_tareas += m["cerradas"]
        planes.append((tasks.parent.name, m["cerradas"], minutos / m["cerradas"]))
    return planes, (total_min / total_tareas if total_tareas else None), descartados


def informe(slug: str, umbral_min: int) -> int:
    tasks = buscar_plan(slug)
    if tasks is None:
        print(f"no encuentro el plan '{slug}'")
        return 1
    m = medir(tasks, slug, umbral_min)
    if m is None:
        print(f"{slug}: menos de dos tareas cerradas, todavia no hay nada que medir")
        return 0

    total = m["plan"] + m["colateral"]
    print(f"\n{slug}  ({m['cerradas']}/{m['tareas']} tareas · {m['estado']})")
    print(f"  del {m['inicio']:%d/%m %H:%M} al {m['fin']:%d/%m %H:%M}")
    print()
    print(f"  trabajo del plan     {horas(m['plan']):6.1f} h")
    print(f"  colateral            {horas(m['colateral']):6.1f} h", end="")
    print(f"   ({100 * m['colateral'] / total:.0f}% del esfuerzo)" if total.total_seconds() else "")
    print(f"  sin actividad        {horas(m['sin_actividad']):6.1f} h   (descanso, o analisis sin commits)")
    print(f"  {'-' * 30}")
    print(f"  esfuerzo registrado  {horas(total):6.1f} h   (suelo: lo que dejo rastro)")

    if m["por_clase"]:
        print("\n  en que se fue el tiempo del plan:")
        for clase in ("decidir", "construir", "verificar"):
            if clase in m["por_clase"]:
                d = m["por_clase"][clase]
                print(f"    {clase:11} {horas(d):5.1f} h  ({100 * d / m['plan']:.0f}%)")
    elif m["cerradas"]:
        print("\n  sin desglose: la evidencia no empieza por `[N.M]` (ver skill plan-task)")

    if m["cerradas"]:
        ritmo = m["plan"].total_seconds() / 60 / m["cerradas"]
        print(f"\n  ritmo: {ritmo:.0f} min por tarea")
        _, media, _ = ritmo_medido(umbral_min)
        if media:
            print(f"  media de los planes cerrados: {media:.0f} min por tarea")

    if m["estimacion"]:
        real = horas(m["plan"])
        desvio = 100 * (real - m["estimacion"]) / m["estimacion"]
        print(f"\n  estimado {m['estimacion']:.1f} h  ->  llevamos {real:.1f} h   desvio {desvio:+.0f}%")

        # Aviso a mitad de vuelo: saber el desvio cuando el plan ya termino no
        # sirve para nada. Con la mitad hecha ya se puede proyectar.
        pendientes = m["tareas"] - m["cerradas"]
        if pendientes and m["cerradas"]:
            proyeccion = real / m["cerradas"] * m["tareas"]
            print(f"  proyeccion a las {m['tareas']} tareas: {proyeccion:.1f} h", end="")
            if proyeccion > m["estimacion"] * 1.2:
                print(f"   <-- se va a pasar un {100 * (proyeccion / m['estimacion'] - 1):.0f}%")
            else:
                print("   (dentro de lo estimado)")
    else:
        print("\n  sin estimacion escrita: anade `- Estimación: N h` en los metadatos de tasks.md")
    return 0


def autotest() -> int:
    """Comprueba el reparto con horas inventadas.

    La aritmetica de intervalos falla en silencio: produce numeros creibles y
    falsos. Esto la fija.
    """
    t = lambda h, m: datetime(2026, 1, 1, h, m)
    ev = [
        (t(9, 0), "plan", "decidir"),      # arranque
        (t(9, 30), "plan", "decidir"),     # 30 min decidiendo
        (t(9, 50), "colateral", None),     # 20 min de otra cosa
        (t(12, 0), "plan", "construir"),   # 130 min sin nada -> sin actividad
        (t(12, 20), "plan", "construir"),  # 20 min construyendo
    ]
    cestas, clases = repartir(ev, 60)
    fallos = []
    esperado = {"plan": 50, "colateral": 20, "sin_actividad": 130}
    for k, v in esperado.items():
        real = cestas[k].total_seconds() / 60
        if real != v:
            fallos.append(f"{k}: esperaba {v} min, salio {real:.0f}")
    if clases.get("decidir", timedelta()).total_seconds() / 60 != 30:
        fallos.append("decidir: esperaba 30 min")
    if clases.get("construir", timedelta()).total_seconds() / 60 != 20:
        fallos.append("construir: esperaba 20 min")

    for f in fallos:
        print(f"  FALLO  {f}")
    print("  autotest: correcto" if not fallos else f"  autotest: {len(fallos)} fallos")
    return 1 if fallos else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", nargs="?")
    ap.add_argument("--umbral", type=int, default=60,
                    help="minutos sin actividad a partir de los cuales no se cuenta (por defecto 60)")
    ap.add_argument("--ritmo", action="store_true", help="ritmo real de los planes ya cerrados")
    ap.add_argument("--autotest", action="store_true", help="comprueba la aritmetica del reparto")
    args = ap.parse_args()

    if args.autotest:
        return autotest()

    if args.ritmo:
        planes, media, descartados = ritmo_medido(args.umbral)
        if not planes:
            print("todavia no hay planes cerrados con medicion")
            return 0
        print("\nritmo real de los planes cerrados")
        for n, tareas, r in planes:
            print(f"  {n:34} {tareas:3} tareas   {r:5.1f} min/tarea")
        print(f"\n  media: {media:.1f} min por tarea   ({sum(p[1] for p in planes)} tareas medidas)")
        print(f"  usar esta cifra al estimar el siguiente plan, no una del pasado")
        for n, por in descartados:
            print(f"\n  descartado {n}: {por}")
        return 0

    if not args.slug:
        ap.print_help()
        return 1
    return informe(args.slug, args.umbral)


if __name__ == "__main__":
    sys.exit(main())
