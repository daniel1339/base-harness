#!/usr/bin/env python3
"""Verifica que todo plan del roadmap lleva las obligaciones del harness.

Existe porque estar escrito en la skill `create-plan` no garantiza nada: quien
cree un plan sin seguirla, o lo genere con otra herramienta, se las salta y
nadie se entera hasta que el plan se ejecuta sin checklist ni documentacion.

Aplica a todo plan con el layout de cuatro archivos, pero **bloquea solo los
del roadmap** (los que llevan `- Fase: N` en su `spec.md`). Los demas se
REPORTAN. Esa distincion no es cosmetica: activar la puerta sobre todos de golpe
deja el repo en rojo, y un repo en rojo acaba con alguien desactivando la
comprobacion. Cada plan deja de reportarse cuando le toca el turno.

    python3 scripts/plans-check.py           # informa de todo
    python3 scripts/plans-check.py --check   # falla solo por los del roadmap
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# El proyecto lo fija el CLI antes de llamar a `main`. Por defecto, el
# directorio actual: asi `python3 -m base_harness.plan_time` sigue funcionando
# desde la raiz de un proyecto sin pasar por el CLI.
PROG = "base-harness check"

ROOT = Path.cwd()
PLANS = ROOT / ".pacto" / "plans"


def configurar(root: Path) -> None:
    """Fija sobre que proyecto se trabaja. La llama `bin/base-harness`."""
    global ROOT, PLANS
    ROOT = root
    PLANS = root / ".pacto" / "plans"

# Cada obligacion: como se detecta y por que existe.
REQUIRED = [
    ("Estimación:", "estimacion en los metadatos, escrita al crear el plan"),
    ("Reconocimiento:", "tarea de reconocimiento antes de decidir"),
    ("YAGNI", "checklist KISS/DRY/YAGNI antes de escribir codigo"),
    # Cuando el proyecto tenga un sitio donde declarar sus capacidades -un
    # catalogo, un contrato de API, un harness de producto- anadir aqui la
    # obligacion de enumerarlas al abrir el plan y verificarlas al cerrarlo.
    # Antes de que ese sitio exista, la comprobacion pediria texto que no
    # apunta a ninguna parte.
]

# Acepta [ ] y [x]: una tarea cerrada sigue existiendo. Con solo [ ], un plan
# terminado se reportaba como "sin tareas" y las referencias a tareas ya hechas
# parecian rotas.
# Extensiones que cuentan como ancla `archivo:linea` en un bloqueador. Anade
# las de tu proyecto: si falta la tuya, TODO bloqueador legitimo se reporta
# como "sin ancla" y la comprobacion se vuelve ruido, que es como se acaba
# desactivando.
EXTENSIONES = "|".join([
    "py", "ts", "tsx", "js", "jsx", "go", "rs", "rb", "php", "java", "kt",
    "cs", "swift", "c", "h", "cpp", "sql", "sh", "md", "yml", "yaml", "json",
    "toml", "tf", "html", "css",
])

TASK = re.compile(r"^\s*-\s*\[[ x]\] (\d+)\.(\d+)", re.M)

# `pacto status` marca una tarea como bloqueada por PALABRA, no por estructura:
# le basta con que su texto contenga "bloqueado" o "bloqueador" (verificado el
# 2026-08-20; "bloqueante", "bloqueo" y "bloquear" no disparan). La tarea de
# reconocimiento decia "...o bloqueador- antes de resolver nada" y dejaba los 17
# planes del roadmap reportando `blocked` para siempre, con lo que el estado
# dejaba de distinguir un plan detenido de uno que solo menciona la palabra.
DISPARA_BLOQUEO = re.compile(r"\bbloquead(?:o|or)\w*\b|\bblock(?:ed|er)\b", re.I)
TAREA_ABIERTA = re.compile(r"^\s*-\s*\[ \] \d+\.\d+.*$", re.M)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog=PROG)
    ap.add_argument("--check", action="store_true", help="falla si falta algo")
    args = ap.parse_args(argv)

    problems: list[str] = []      # del roadmap: bloquean
    pending: list[str] = []       # del resto: solo se reportan
    checked = 0

    for spec in sorted(PLANS.glob("*/*/spec.md")):
        roadmap = bool(re.search(r"^- Fase: \d", spec.read_text(), re.M))
        bucket = problems if roadmap else pending
        checked += 1
        slug = spec.parent.name
        tasks_file = spec.parent / "tasks.md"
        if not tasks_file.is_file():
            bucket.append(f"{slug}: sin tasks.md")
            continue
        body = tasks_file.read_text()

        for needle, why in REQUIRED:
            if needle not in body:
                bucket.append(f"{slug}: falta {why}")

        # `pacto exec --step` rechaza los numeros terminados en .0: el 2026-08-20
        # las 17 tareas de reconocimiento se anadieron como 1.0 y ninguna era
        # ejecutable. Se descubrio al intentar cerrar la primera de verdad.
        # Letras a los DOS lados del punto. La version anterior solo miraba
        # despues -cazaba `1.1b` y dejaba pasar `1b.1`-, y el 2026-08-21 se
        # colaron dos fases enteras numeradas asi sin que nada avisara.
        raros = re.findall(
            r"^\s*-\s*\[[ x]\] (\d*[a-z]\w*\.\d+|\d+\.\d*[a-z]\w*) ", body, re.M
        )
        if raros:
            bucket.append(
                f"{slug}: numeros de tarea no validos para `pacto exec` -> {', '.join(sorted(set(raros)))}"
            )

        ceros = re.findall(r"^\s*-\s*\[[ x]\] (\d+\.0) ", body, re.M)
        if ceros:
            bucket.append(
                f"{slug}: tareas .0 que `pacto exec --step` no puede targetear -> {', '.join(sorted(set(ceros)))}"
            )

        # Referencias cruzadas: "conforme a 2.3" debe apuntar a una tarea que
        # exista. El 2026-08-20 un renumerado masivo dejo 55 referencias
        # apuntando una posicion por delante, en silencio: los numeros seguian
        # existiendo, solo que significaban otra cosa.
        existentes = {f"{a}.{b}" for a, b in TASK.findall(body)}
        for m in re.finditer(
            r"(?:conforme a|segun|según|ver|de|en|con)\s+(\d+\.\d+)\b", body
        ):
            if m.group(1) not in existentes:
                bucket.append(f"{slug}: referencia a la tarea {m.group(1)}, que no existe")

        # Una tarea abierta no puede llevar la palabra que dispara el bloqueo.
        for linea in TAREA_ABIERTA.findall(body):
            if DISPARA_BLOQUEO.search(linea):
                num = linea.split("]", 1)[1].strip().split(" ", 1)[0]
                bucket.append(
                    f"{slug}: la tarea {num} contiene 'bloqueado/bloqueador' y "
                    f"`pacto status` la cuenta como bloqueada -> reescribela "
                    f"(impedimento, detenido, obligatorio...)"
                )

        # La seccion de bloqueadores: o vacia, o una linea `- ` por bloqueador real.
        # Una tabla hace que pacto lea la cabecera y el separador como dos
        # bloqueadores, y un "Ninguno registrado" declara bloqueado un plan que
        # dice justo lo contrario.
        m_bloq = re.search(r"^## Bloqueadores\s*\n(.*?)(?=^## |\Z)", body, re.M | re.S)
        if m_bloq:
            lineas = [l.strip() for l in m_bloq.group(1).strip().splitlines() if l.strip()]
            malas = [l for l in lineas if not l.startswith("- ")]
            if malas:
                bucket.append(
                    f"{slug}: la seccion Bloqueadores debe estar vacia o llevar una "
                    f"linea `- ` por bloqueador; `pacto status` lee cada linea como "
                    f"uno -> sobra {malas[0][:50]!r}"
                )
            # Un bloqueador o nombra el plan del que depende -y entonces
            # `pacto status` puede decir si sigue vivo- o afirma algo del
            # codigo, y entonces necesita su ancla. Sin una de las dos cosas es
            # una suposicion con aspecto de hecho, y nadie vuelve a revisarla.
            for l in lineas:
                if not l.startswith("- "):
                    continue
                nombra_plan = re.search(r"`([a-z0-9]+-[a-z0-9-]+)`", l)
                tiene_ancla = re.search(r"[\w/.-]+\.(" + EXTENSIONES + r")(:\d+)?", l)
                if not nombra_plan and not tiene_ancla:
                    bucket.append(
                        f"{slug}: bloqueador sin plan ni ancla que lo respalde -> {l[:60]!r}. "
                        f"Nombra el plan del que depende, o pon el `archivo:linea` que lo prueba"
                    )

            vacios = [l for l in lineas if re.match(r"- (ninguno|ninguna|sin bloqueador|n/?a)\b", l, re.I)]
            if vacios:
                bucket.append(
                    f"{slug}: 'Ninguno registrado' bajo Bloqueadores declara el plan "
                    f"bloqueado; para decir que no hay, deja la seccion vacia"
                )

        # Un plan cerrado sin su medicion real pierde la unica informacion que
        # hace mejor la estimacion siguiente. Y depender de acordarse ya ha
        # fallado antes: un hook que debia dispararse solo y no lo hizo, y un
        # checklist de documentacion que nadie repasaba.
        if spec.parent.parent.name == "done" and "Real:" not in body:
            bucket.append(
                f"{slug}: plan cerrado sin medicion real -> corre "
                f"`python3 scripts/plan-time.py {slug}` y anade el resultado "
                f"junto a la estimacion"
            )

        nums = TASK.findall(body)
        if not nums:
            bucket.append(f"{slug}: sin tareas N.M, `pacto exec` no puede apuntar")
        # numeros repetidos rompen `pacto exec --step`
        seen = [f"{a}.{b}" for a, b in nums]
        dupes = sorted({x for x in seen if seen.count(x) > 1})
        if dupes:
            bucket.append(f"{slug}: tareas duplicadas -> {', '.join(dupes)}")

    if pending:
        faltan = len({p.split(":")[0] for p in pending})
        print(f"[info] {faltan} plan(es) fuera del roadmap sin las obligaciones.")
        print("       Se arreglan al llevarlos a contrato, uno a uno, no en bloque.\n")

    if not problems:
        print(f"planes del roadmap: sin problemas ({checked} planes revisados)")
        return 0

    print(f"Planes del roadmap con problemas ({checked} revisados):\n")
    for p in problems:
        print(f"  {p}")
    print("\nLas obligaciones estan en la skill `create-plan`. Este check existe")
    print("porque una instruccion se puede saltar y nadie se entera.")
    return 1 if args.check else 0


if __name__ == "__main__":
    sys.exit(main())
