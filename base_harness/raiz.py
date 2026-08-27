"""De donde cuelga el proyecto sobre el que se trabaja.

Antes esto salia de `__file__`, porque los scripts vivian dentro del proyecto.
Ahora la herramienta esta instalada una vez en la maquina y el proyecto es otra
cosa, asi que hay que encontrarlo: se sube desde el directorio actual hasta dar
con la senal.

`.pacto` va antes que `.git` a proposito: un repositorio puede contener varios
workspaces de planes, y el que interesa es el mas cercano al sitio desde el que
se ejecuta.
"""

from __future__ import annotations

from pathlib import Path

SENALES = (".pacto", ".git")


def raiz(desde: Path | None = None) -> Path:
    actual = (desde or Path.cwd()).resolve()
    for d in (actual, *actual.parents):
        for senal in SENALES:
            if (d / senal).exists():
                return d
    return actual
