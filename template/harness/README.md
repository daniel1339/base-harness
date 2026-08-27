# Harness

La capa canonica de la que sale todo lo que leen las herramientas LLM.

## La regla

Cada archivo del arbol es una de dos cosas:

| | Quien lo escribe | Donde vive |
|---|---|---|
| **Canonico** | Una persona, a mano, una sola vez | `AGENTS.md`, `harness/skills/` |
| **Generado** | `scripts/harness-sync.py` | `CLAUDE.md`, `.claude/skills/`, `.cursor/`, `.agents/`, `.github/copilot-instructions.md` |

Todo lo generado va envuelto en marcadores `harness:managed:start` /
`harness:managed:end` y lleva el sha del origen. **Nunca se edita a mano**, y
nunca se copia una skill de un directorio de herramienta a otro: se anade a
`harness/skills/` y se regenera.

```bash
python3 scripts/harness-sync.py            # escribe los adaptadores
python3 scripts/harness-sync.py --check    # falla si alguno esta stale

make harness-sync                          # atajo, si tienes make
make harness-check
```

Sin symlinks a proposito: se rompen en Windows sin `core.symlinks` y en
indexadores que no los resuelven. Todo adaptador es un archivo real.

## Por que existe

Antes de esto habia una copia por herramienta, escritas a mano. Derivaban entre
si, y a partir de ese momento cada agente trabajaba con una version distinta del
contrato sin que nadie lo notase. `harness-check` en CI es lo que convierte esa
regla en algo que no se puede saltar.

El hook `scripts/harness-autosync.py` regenera al vuelo cuando Claude Code toca
un archivo canonico. Es comodidad; la garantia es el job de CI.

## Pacto

`pacto` es el otro generador del repositorio: crea sus propias skills `pacto-*`
bajo `.claude/` y `.agents/`. `harness-sync` las ignora (las reconoce por el
marcador `pacto:managed`) y no las borra. Instalacion y version:

```bash
pipx install pacto        # o el metodo que uses
pacto version             # 0.1.26 o superior
pacto doctor
```
