"""Where the project under work hangs from.

This used to come from `__file__`, back when the scripts lived inside the
project. The tool is now installed once per machine and the project is
somewhere else, so it has to be found: walk up from the current directory
until a marker shows up.

`.pacto` comes before `.git` on purpose: one repository can hold several plan
workspaces, and the one that matters is the closest to wherever the command was
run from.
"""

from __future__ import annotations

from pathlib import Path

MARKERS = (".pacto", ".git")


def root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for directory in (current, *current.parents):
        for marker in MARKERS:
            if (directory / marker).exists():
                return directory
    return current
