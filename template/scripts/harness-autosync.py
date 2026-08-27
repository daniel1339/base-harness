#!/usr/bin/env python3
"""Hook de Claude Code: regenera los adaptadores al tocar un archivo canonico.

Antes esto era una instruccion en prosa ("corre make harness-sync tras editar
un canonico") y se descubria el olvido cuando CI se ponia rojo. Un hook lo
convierte en una regla determinista y a coste cero de tokens.

Lee el JSON del evento por stdin. Si el archivo editado no es canonico, sale
en silencio. Ver `harness/README.md` y la seccion Hooks de `AGENTS.md`.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

# Solo estos disparan: son las fuentes de las que sale todo lo generado.
CANONICAL = re.compile(r"(^|/)AGENTS\.md$|(^|/)harness/skills/")

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # payload raro: no es motivo para molestar a nadie

    tool_input = event.get("tool_input") or {}
    tool_response = event.get("tool_response") or {}
    path = tool_response.get("filePath") or tool_input.get("file_path") or ""
    if not path or not CANONICAL.search(path.replace("\\", "/")):
        return 0

    run = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "harness-sync.py")],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    summary = (run.stdout or run.stderr).strip().splitlines()
    summary = summary[-1] if summary else "harness-sync sin salida"

    # Solo se avisa cuando de verdad se escribio algo: si el editor ya estaba
    # sincronizado, un mensaje por cada edicion seria ruido.
    if run.returncode != 0:
        print(json.dumps({"systemMessage": f"harness-sync fallo: {summary}"}))
    elif not summary.startswith("harness-sync: 0 escritos"):
        print(json.dumps({"systemMessage": summary}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
