# AGENTS.md

Date: <!-- RELLENA: YYYY-MM-DD -->

Fuente unica de verdad para el contexto de agentes en este repositorio.
**Este archivo es el contrato, y no tiene copias.** Cualquier herramienta LLM
lo lee: Codex, Cursor, Zed, Aider y las demas de forma nativa; Claude Code a
traves de un `CLAUDE.md` de una linea que lo importa.

## Read This First

- Este archivo primero: arquitectura, comandos y forma de trabajar.
- Al editar dentro de un subproyecto, lee tambien su `AGENTS.md` anidado.

## Skills

Los procedimientos largos no viven aqui: viven en `.claude/skills/`, uno por
carpeta, y se leen **solo cuando hacen falta**. Este archivo viaja en cada
turno; una skill, solo cuando toca.

| Lee esta skill | Cuando |
|---|---|
| `.claude/skills/create-plan/SKILL.md` | Vayas a escribir un plan, o a darle estructura a uno que no la tiene |
| `.claude/skills/plan-task/SKILL.md` | Vayas a ejecutar o cerrar una tarea `N.M` de un plan |

Son archivos `SKILL.md` normales, sin nada especifico de ninguna IA. Claude
Code las registra solo por estar en esa ruta; cualquier otra herramienta las
lee desde aqui, que es para lo que existe esta tabla.

**No se copian a `.cursor/`, `.agents/` ni a ningun otro directorio.** Una copia
por herramienta deriva de las demas, y a partir de ese momento cada agente
trabaja con una version distinta sin que nadie lo note.

## Pacto

Los planes viven en `.pacto/plans/`, gobernados por la CLI `pacto`, que genera
sus propias skills `pacto-*`. Un plan es ejecutable cuando su carpeta lleva
`spec.md`, `design.md` y `tasks.md` con tareas numeradas `N.M`: ese numero es lo
unico que `pacto exec` puede apuntar.

No lo juzgues a ojo:

```bash
pacto status --root .pacto/plans --repo-root . --format table
```

Un plan con `0` tareas no tiene nada que ejecutar. Y ojo con el falso verde: el
scaffold de `pacto new` deja una tarea `1.1 <tarea>` que cuenta como tarea sin
serlo.

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

### Comprobaciones del harness

`base-harness` esta instalado en la maquina, no en el repositorio: aqui no hay
scripts que mantener. Si falta, se instala una vez desde su repo.

```bash
base-harness planes            # que le falta a cada plan
base-harness check             # lo mismo, pero falla (es lo que corre CI)
base-harness time <slug>       # lo que costo un plan
base-harness ritmo             # el ritmo real de los planes cerrados
base-harness donde             # que rutas esta usando, si algo no cuadra
```

## Estimating And Measuring A Plan

Todo plan lleva su estimacion, escrita al crearlo, y lo que costo de verdad,
medido al cerrarlo. CI falla si falta cualquiera de las dos.

Nadie arranca un cronometro: sale de dos relojes que ya funcionan —la hora que
`pacto exec` deja en cada tarea cerrada y la que `git` deja en cada commit—.
`base-harness time` reparte los huecos entre trabajo del plan, trabajo
colateral y falta de actividad, asi que **las horas de descanso no hay que
declararlas**.

El ritmo sale de los datos: `base-harness ritmo` promedia los planes ya
cerrados. Mientras no haya dos planes cerrados aqui se usa el ritmo prestado
que dice la skill `create-plan`, y se escribe en la linea que es prestado.

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
cerrar, y `base-harness check` falla en CI cuando un plan no las lleva.

## Documentation Rules

- La documentacion de un subproyecto vive bajo `<subproyecto>/docs/`
- Todo documento nuevo lleva su fecha
- Diagramas en Mermaid

## How to Explore Efficiently

1. Este archivo, y luego el `AGENTS.md` del area que vas a tocar
2. `rg` para simbolos y texto exacto
3. Lecturas pequenas y dirigidas, nunca archivos enteros grandes
4. Delega las lecturas anchas a un subagente en vez de traerlas a la conversacion

## Git Conventions

- Prefijo en todo commit: `feat:`, `fix:`, `change:`, `docs:`, `refactor:`
- Mensajes cortos y utiles
- Mira `git status` antes de preparar el commit, y evita `git add .`: pacto deja
  cambios en el arbol que no son tuyos
