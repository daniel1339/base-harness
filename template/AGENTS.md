# AGENTS.md

Date: <!-- RELLENA: YYYY-MM-DD -->

Fuente unica de verdad para el contexto de agentes en este repositorio.
Cualquier herramienta LLM lee este archivo: Codex y Cursor de forma nativa,
Claude Code y Copilot a traves de copias generadas (`CLAUDE.md`,
`.github/copilot-instructions.md`).

## Read This First

- Este archivo primero: arquitectura, comandos y forma de trabajar.
- Al editar dentro de un subproyecto, lee tambien su `AGENTS.md` anidado.

## Harness Layout

Cada archivo es **canonico** (escrito a mano, existe una vez) o **generado**
(envuelto en marcadores managed, nunca se edita a mano). No hay copias
manuales.

- `AGENTS.md` (este archivo) y los `AGENTS.md` anidados: contrato canonico
- `harness/skills/`: skills canonicas, copiadas a `.claude/`, `.cursor/` y
  `.agents/` por el generador — el formato `SKILL.md` es comun a las tres
- `.claude/agents/`: subagentes (solo Claude Code; sin equivalente en el resto)
- `.cursor/rules/`, `.agent/rules/`, `.kilocode/rules/`: punteros generados
- `make harness-check` verifica el arbol; CI falla si deriva

Nunca edites entre `managed:start` / `managed:end`, y nunca copies una skill
de un directorio de herramienta a otro: se anade a `harness/skills/`.

### Pacto

Los planes viven en `.pacto/plans/`, gobernados por la CLI `pacto`. Es el
segundo generador del repo: crea sus propias skills `pacto-*`, y `harness-sync`
no toca sus archivos ni al reves.

Un plan es ejecutable cuando su carpeta lleva `spec.md`, `design.md` y
`tasks.md` con tareas numeradas `N.M`: ese numero es lo unico que `pacto exec`
puede apuntar. No lo juzgues a ojo —`pacto status --root .pacto/plans
--repo-root .` dice cuantas tareas tiene cada plan, y `0` significa que no hay
nada que ejecutar.

Dos skills se reparten el trabajo, y la frontera es la estructura:

- `create-plan` — escribir un plan nuevo, o darle a uno viejo lo que le falta
- `plan-task` — ejecutar la tarea `N.M`: implementar, probar, dejar evidencia

Una tarea se cierra con evidencia que `pacto status` pueda re-verificar
—`paths`, `symbols`, `endpoints`, `test_refs`—, nunca con prosa que diga que
esta hecha.

## Project Overview

<!-- RELLENA: que hace este proyecto, para quien, y los limites explicitos
     ("esto NO lo hacemos"). Los limites valen mas que la descripcion: son lo
     que evita que un agente construya de mas. -->

## Repo Map

<!-- RELLENA: directorios de primer nivel, una linea cada uno -->

## Development Commands

<!-- RELLENA: como se levanta, como se prueba, como se despliega -->

### Harness

`make` es un atajo y no esta instalado en todas partes; el script siempre
funciona, y es lo que llama CI.

```bash
python3 scripts/harness-sync.py            # regenera los adaptadores
python3 scripts/harness-sync.py --check    # falla si uno esta stale
python3 scripts/plans-check.py --check     # falla si un plan no trae lo suyo

make harness-sync                          # equivalentes, si tienes make
make harness-check
```

## Estimating And Measuring A Plan

Todo plan lleva su estimacion, escrita al crearlo, y lo que costo de verdad,
medido al cerrarlo. CI falla si falta cualquiera de las dos.

Nadie arranca un cronometro: sale de dos relojes que ya funcionan —la hora que
`pacto exec` deja en cada tarea cerrada y la que `git` deja en cada commit—.
`scripts/plan-time.py` reparte los huecos entre trabajo del plan, trabajo
colateral y falta de actividad, asi que **las horas de descanso no hay que
declararlas**.

El ritmo sale de los datos: `plan-time.py --ritmo` promedia los planes ya
cerrados. Mientras no haya dos planes cerrados aqui, se usa el ritmo prestado
que diga la skill `create-plan`, y se dice en la linea que es prestado.

## Building A Feature

Dos reglas para **toda** funcionalidad, dentro de un plan o fuera. Estan aqui y
no en una skill porque una skill solo se carga cuando alguien la invoca.

**1. Una funcionalidad se documenta mientras se construye, nunca despues.**
Todo lo que un usuario pueda pedir o el sistema pueda invocar se declara con
seis campos: nombre en palabras del usuario, que hace, donde vive, requisitos
previos, como se invoca, y que responder cuando no esta disponible. Documentar
en una tanda al final es la forma habitual de no documentar.

**2. Antes de escribir codigo: KISS, DRY, YAGNI.** Alcance limitado a lo que se
pidio, solucion minima sin abstracciones anticipadas, y cero duplicacion con lo
que ya existe — **comprobado buscando, no suponiendo**.

`create-plan` convierte las dos en tareas de cada plan, `plan-task` las exige al
cerrar, y `scripts/plans-check.py` falla en CI cuando un plan no las lleva.

## Documentation Rules

- La documentacion de un subproyecto vive bajo `<subproyecto>/docs/`
- Todo documento nuevo lleva su fecha
- Diagramas en Mermaid

## How to Explore Efficiently

1. Este archivo, y luego el `AGENTS.md` del area que vas a tocar
2. Busqueda semantica para "como / donde / que"
3. `rg` para simbolos y texto exacto
4. Lecturas pequenas y dirigidas, nunca archivos enteros grandes
5. Delega las lecturas anchas a un subagente en vez de traerlas a la conversacion

## Git Conventions

- Prefijo en todo commit: `feat:`, `fix:`, `change:`, `docs:`, `refactor:`
- Mensajes cortos y utiles
- Mira `git status` antes de preparar el commit, y evita `git add .`: los
  generadores dejan cambios en el arbol que no son tuyos
