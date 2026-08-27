# base-harness

El esqueleto que hace que un proyecto se pueda desarrollar con agentes y que
**cada plan diga lo que costo sin que nadie apunte nada**. Se instala en
cualquier proyecto, del lenguaje que sea.

```bash
./bootstrap.sh /ruta/al/proyecto
```

Nueve archivos. Dos scripts. Ningun generador.

## Un contrato, sin adaptadores

`AGENTS.md` es el contrato y **no tiene copias**. Codex, Cursor, Zed, Aider y
las demas lo leen de forma nativa. Claude Code lee `CLAUDE.md`, asi que el
repositorio lleva un `CLAUDE.md` de **una linea**:

```
@AGENTS.md
```

Eso es todo el "adaptador" que hay, y no cambia nunca: su contenido no depende
de lo que diga `AGENTS.md`. Si manana aparece una herramienta que quiere su
propio archivo, es otra linea, no otro generador.

Lo mismo con las skills. Viven **una sola vez** en `.claude/skills/`. Claude
Code las registra por estar en esa ruta; cualquier otra herramienta llega a
ellas porque `AGENTS.md` trae una tabla que dice cual leer y cuando. No se
copian a `.cursor/`, ni a `.agents/`, ni a ningun sitio.

> El diseno anterior generaba adaptadores para cinco herramientas con un script
> de 240 lineas, un hook y un job de CI. Un proyecto que usa una o dos IAs
> pagaba mantener sincronizados archivos que nadie lee — y el dia que CI se pone
> rojo por uno de esos, lo que se apaga es la comprobacion entera. Un puntero de
> una linea hace el mismo trabajo.

Contrapartida honesta: un import puede fallar en silencio —Claude arranca sin
contexto y no avisa—. Se comprueba una vez, preguntandole al agente que dice
`AGENTS.md`. Una comprobacion de diez segundos contra un generador permanente.

## Que instala

| | Que hace |
|---|---|
| `AGENTS.md` | El contrato. Lo unico que hay que rellenar |
| `CLAUDE.md` | Una linea: `@AGENTS.md` |
| `scripts/plan-time.py` | Mide lo que costo un plan y el ritmo real de los cerrados |
| `scripts/plans-check.py` | Puerta de CI: falla si un plan no trae estimacion, o si uno cerrado no trae su medicion |
| `.claude/skills/create-plan` | Como se escribe un plan: estructura, numeracion, estimacion |
| `.claude/skills/plan-task` | Como se ejecuta y se cierra una tarea con evidencia |
| `.github/workflows/ci.yml`, `Makefile`, `.gitignore` | El andamiaje |

## Como mide el tiempo

No hay cronometro y no se mide el reloj. Salen de **dos relojes que ya
funcionan**: la hora que `pacto exec` deja en cada tarea cerrada, y la que
`git` deja en cada commit. Cada hueco entre dos senales es una de tres cosas:

| El hueco... | Cuenta como |
|---|---|
| Termina en una tarea cerrada | **Trabajo del plan** — ¿acerte al estimar? |
| Termina en un commit de otra cosa | **Colateral** — ¿cuanto cuesta el terreno? |
| Dura mas de 1 h sin ninguna senal | **Sin actividad** |

La tercera es la clave: **las horas de descanso no hay que declararlas**, salen
solas. Y el colateral va aparte a proposito: disuelto dentro del plan, la
siguiente estimacion lo hereda sin que nadie lo vea.

Limite que hay que conocer: **pensar no deja commits**. Un rato largo leyendo
codigo se ve igual que una comida. Por eso la columna se llama "sin actividad"
y no "pausa", y por eso la cifra es un **suelo**, no un total.

## Las tres cosas que no se recuperan despues

Todo lo demas se puede anadir tarde —la medicion es retroactiva, lee timestamps
que ya estan en `tasks.md` y en `git log`—. Estas tres no:

1. **Tareas numeradas `N.M`.** Nada de `1.0` ni letras (`1.1b`, `1b.1`,
   `1.5-bis`): `pacto exec --step` no las puede apuntar.
2. **La linea `- Estimación: X h` escrita ANTES de empezar.** Al cerrar solo
   sabrias cuanto costo, que no sirve para estimar el siguiente.
3. **El prefijo `[N.M]` al principio de cada `--evidence`.** `pacto` no guarda
   a que tarea pertenece cada linea; sin el, la evidencia es una lista de horas
   huerfanas.

## El ritmo es lo unico que no se puede plantillar

`horas = tareas x ritmo x factor / 60`. El ritmo sale de los planes ya cerrados
**de ese repositorio**, con `plan-time.py --ritmo`. Un monorepo grande y un
servicio pequeno no tienen el mismo.

La plantilla viaja con **5,0 min/tarea prestados** —medidos sobre 71 tareas en
otro proyecto—, y la regla es escribir en la linea que son prestados. En cuanto
cierres dos planes propios, recalcula y borra el prestamo.

## Idioma

Los planes se leen en castellano: `plan-time.py` clasifica las tareas en
decidir / construir / verificar por las palabras que usan. Traducirlo es
cambiar el bloque `PALABRA_*` del principio del script — y hay que hacerlo,
porque no traducirlo **no da error**: mete todo en "construir" y produce un
desglose creible y vacio.

## Lo que deliberadamente NO trae

- **Subagentes.** Se anaden cuando el repo tiene superficie que valga la pena
  delegar; el primero que se echa de menos es uno que busque en los planes, y
  no antes de unos 30.
- **Reconocimiento automatico.** Depende de como este organizado el proyecto.
  La tarea de reconocimiento si viene en `create-plan`.
- **Declaracion de capacidades.** `plans-check.py` trae el hueco comentado: se
  activa cuando el proyecto tenga un sitio donde declararlas. Una comprobacion
  que exige texto que no apunta a ninguna parte se acaba desactivando.

## Contrapartida

Esto es una plantilla que se copia, no un paquete. Si arreglas `plan-time.py`
aqui, los proyectos ya creados no se enteran. A esta escala compensa; con diez
proyectos habria que convertirlo en dependencia.
