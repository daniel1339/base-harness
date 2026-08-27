#!/usr/bin/env python3
"""Compila la capa canonica del harness a los adaptadores de cada herramienta.

Regla del harness: cada archivo es canonico (escrito a mano, existe una vez) o
generado (marcadores managed, nunca se edita a mano). Este script genera.

    python3 scripts/harness-sync.py            # escribe los adaptadores
    python3 scripts/harness-sync.py --check    # falla si algo esta desincronizado

Sin symlinks a proposito: se rompen en Windows sin core.symlinks y en
indexadores que no los resuelven. Todo adaptador es un archivo real.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANON_SKILLS = ROOT / "harness" / "skills"
CONTRACT = ROOT / "AGENTS.md"

START = "<!-- harness:managed:start -->"
END = "<!-- harness:managed:end -->"
NOTE = "NO EDITAR A MANO. Generado desde {src} por scripts/harness-sync.py"

# CLAUDE.md (raiz y anidados) lleva el contenido completo de su AGENTS.md, igual
# que Copilot. Claude Code tiene un import nativo (`@AGENTS.md`) que ahorraria la
# duplicacion, pero si fallara el sintoma seria silencioso: no da error, arranca
# sin contexto del proyecto. No compensa por unos KB.

# --- Que herramientas usa este repositorio --------------------------------
# Deja solo las que uses de verdad. Cada adaptador de mas es un archivo que
# `--check` exige mantener sincronizado para nadie, y el dia que CI se ponga
# rojo por un archivo que no lee ninguna herramienta, alguien apaga la
# comprobacion entera. Anadir una despues es esta linea y `make harness-sync`.
#
# Y si solo usas una herramienta, plantéate no usar este script: con Claude
# Code a secas basta con escribir `CLAUDE.md` y no tener `AGENTS.md`. Todo
# esto existe para que N herramientas lean una sola fuente.
TOOLS = {"claude", "cursor", "codex"}   # tambien: copilot, kilocode, windsurf

# Herramienta -> donde deja sus skills en formato SKILL.md con frontmatter
# name+description. El formato coincide entre las tres, asi que el cuerpo es
# identico. Codex las lee de `.agents/skills`, no de `.codex/skills`: pacto
# marca esa segunda ruta como legacy (`pacto doctor` -> legacy_pattern).
SKILL_DIRS = {
    "claude": ".claude/skills",
    "cursor": ".cursor/skills",
    "codex": ".agents/skills",
}
SKILL_TARGETS = [d for tool, d in SKILL_DIRS.items() if tool in TOOLS]

# Codex y Cursor leen AGENTS.md nativamente: no necesitan adaptador de contrato.


# Directorios que nunca guardan un contrato nuestro. Se podan al recorrer el
# repo: sin esto la busqueda entra en node_modules, que es lenta y encima trae
# AGENTS.md de terceros.
PRUNE = {
    ".git", "node_modules", "dist", "build", "__pycache__",
    ".venv", "venv", "staticfiles", ".pacto",
}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def nested_contracts() -> list[Path]:
    """AGENTS.md anidados, relativos a ROOT y sin incluir el contrato raiz."""
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in PRUNE]
        if "AGENTS.md" not in filenames:
            continue
        rel = Path(dirpath).relative_to(ROOT) / "AGENTS.md"
        if rel != Path("AGENTS.md"):
            found.append(rel)
    return found


def split_frontmatter(text: str) -> tuple[str, str]:
    """Devuelve (frontmatter, resto). El frontmatter YAML debe quedar en la
    primera linea del archivo o la herramienta no parsea la skill."""
    if not text.startswith("---\n"):
        return "", text
    end = text.find("\n---\n", 4)
    if end == -1:
        return "", text
    return text[: end + 5], text[end + 5 :]


def managed(body: str, src: str) -> str:
    meta = f"<!-- harness:managed:meta source={src} sha256={sha(body)} -->"
    return f"{START}\n{meta}\n<!-- {NOTE.format(src=src)} -->\n{body.strip()}\n{END}\n"


def wrap_markdown(text: str, src: str) -> str:
    """Envuelve markdown preservando el frontmatter al inicio del archivo."""
    front, rest = split_frontmatter(text)
    return front + managed(rest, src)


def planned() -> dict[str, tuple[bytes, bool]]:
    """Mapa ruta -> (contenido esperado, es_ejecutable)."""
    out: dict[str, tuple[bytes, bool]] = {}

    def put(rel: str, text: str, executable: bool = False) -> None:
        out[rel] = (text.encode(), executable)

    # Claude Code no lee AGENTS.md: necesita CLAUDE.md con el contenido dentro.
    def claude_md(src: str) -> str:
        return managed((ROOT / src).read_text(), src)

    if "claude" in TOOLS:
        put("CLAUDE.md", claude_md("AGENTS.md"))

        # AGENTS.md anidados: se cargan on-demand al leer archivos del subarbol,
        # asi el contrato raiz se mantiene pequeño. Cada uno necesita su
        # adaptador, a cualquier profundidad: uno mas abajo se quedaria sin el
        # en silencio, que es el peor fallo posible aqui (Claude arranca sin ese
        # contexto y no avisa). Hay que podar lo ajeno: los paquetes traen los
        # suyos (node_modules/...).
        for rel in sorted(nested_contracts()):
            put(f"{rel.parent.as_posix()}/CLAUDE.md", claude_md(rel.as_posix()))

    # Copilot: no tiene mecanismo de import, necesita el contenido completo.
    if "copilot" in TOOLS:
        put(".github/copilot-instructions.md", managed(CONTRACT.read_text(), "AGENTS.md"))

    # Rules por herramienta: punteros al contrato. Antes eran 469 lineas
    # duplicadas que ya habian derivado entre si.
    pointer = (
        "Read `AGENTS.md` at the repo root first: it is the single source of\n"
        "truth for architecture, commands, conventions and operations."
    )
    if "cursor" in TOOLS:
        put(".cursor/rules/harness.mdc", "---\nalwaysApply: true\n---\n" + managed(pointer, "AGENTS.md"))
    if "windsurf" in TOOLS:
        put(".agent/rules/harness.md", "---\ntrigger: always_on\n---\n" + managed(pointer, "AGENTS.md"))
    # Kilocode auto-inyecta todo .kilocode/rules/* como Custom Rules. Sustituye
    # al memory-bank, que duplicaba AGENTS.md y ademas obligaba a regenerarlo.
    if "kilocode" in TOOLS:
        put(".kilocode/rules/harness.md", managed(pointer, "AGENTS.md"))

    # Skills: copia real por herramienta.
    for f in sorted(CANON_SKILLS.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(CANON_SKILLS).as_posix()
        src = f"harness/skills/{rel}"
        is_exec = os.access(f, os.X_OK)
        for target in SKILL_TARGETS:
            if f.suffix == ".md":
                put(f"{target}/{rel}", wrap_markdown(f.read_text(), src))
            else:
                # scripts y assets: copia literal, no admiten comentarios html
                out[f"{target}/{rel}"] = (f.read_bytes(), is_exec)
    return out


def orphans(files: dict[str, tuple[bytes, bool]]) -> list[str]:
    """Archivos que sobran dentro de los arboles de skills.

    La comparacion de `planned()` solo mira lo que deberia existir: si se borra
    una skill canonica, la copia sobrevive en los tres targets y CI pasa en
    verde. Esto barre al reves.

    Se excluye lo que genera pacto (marcador `pacto:managed`): es el otro
    generador del repo y sus archivos no son nuestros. Todo lo demas que este
    ahi y no este planificado es deuda, porque la regla del harness prohibe las
    copias manuales en estos directorios.
    """
    out: list[str] = []
    for target in SKILL_TARGETS:
        for f in sorted((ROOT / target).rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(ROOT).as_posix()
            if rel in files or b"pacto:managed" in f.read_bytes():
                continue
            out.append(rel)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="no escribe, solo verifica")
    args = ap.parse_args()

    files = planned()
    stale: list[str] = []
    wrote = 0

    for rel, (content, is_exec) in files.items():
        path = ROOT / rel
        current = path.read_bytes() if path.is_file() else None
        mode_ok = (not is_exec) or (path.is_file() and os.access(path, os.X_OK))
        if current == content and mode_ok:
            continue
        if args.check:
            stale.append(rel)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_symlink():
            path.unlink()  # migracion desde el diseño anterior con symlinks
        path.write_bytes(content)
        if is_exec:
            path.chmod(path.stat().st_mode | 0o111)
        wrote += 1

    removed = 0
    for rel in orphans(files):
        if args.check:
            stale.append(f"{rel}: sobra (no sale de harness/skills)")
            continue
        (ROOT / rel).unlink()
        removed += 1
    if not args.check:
        for target in SKILL_TARGETS:
            for d in sorted((ROOT / target).rglob("*"), reverse=True):
                if d.is_dir() and not any(d.iterdir()):
                    d.rmdir()

    if args.check:
        # El drift de los generados lo cubre la comparacion de arriba, pero el
        # archivo canonico no lo vigila nadie. Este lint caza el error mas
        # comun al editarlo a mano: dejar dos secciones que dicen lo mismo.
        for agents_md in [CONTRACT, *(ROOT / rel for rel in sorted(nested_contracts()))]:
            seen: dict[str, int] = {}
            for line in agents_md.read_text().splitlines():
                if line.startswith("#"):
                    seen[line.strip()] = seen.get(line.strip(), 0) + 1
            for heading, count in seen.items():
                if count > 1:
                    rel = agents_md.relative_to(ROOT)
                    stale.append(f"{rel}: seccion duplicada {count}x -> {heading}")

        if stale:
            print("harness desincronizado. Ejecuta: make harness-sync\n")
            for rel in stale:
                print(f"  stale: {rel}")
            return 1
        print(f"harness sincronizado ({len(files)} archivos generados)")
        return 0

    print(f"harness-sync: {wrote} escritos de {len(files)} generados, {removed} borrados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
