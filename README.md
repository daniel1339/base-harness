# base-harness

Planificar y medir, instalado **una vez por maquina**. Hace que cualquier
proyecto pueda desarrollarse con agentes y que **cada plan diga lo que costo
sin que nadie apunte nada**.

```bash
git clone https://github.com/daniel1339/base-harness && cd base-harness
./install.sh                 # solo necesita python3: ni pip, ni pipx, ni uv

cd /mi/proyecto
base-harness init
```

## La idea: leer va al repo, ejecutar va a la maquina

Lo que un agente tiene que **leer** vive en el proyecto. Lo que solo se
**ejecuta** vive en la herramienta. Esa linea es todo el diseño.

| Vive en el proyecto | Por que |
|---|---|
| `AGENTS.md` | Es el contrato. Lo lee cada IA en cada turno |
| `CLAUDE.md` | Una linea: `@AGENTS.md` |
| `.claude/skills/create-plan`, `plan-task` | Procedimientos que se leen bajo demanda |
| `.github/workflows/ci.yml` | Configuracion de CI, que es del repositorio |

Seis archivos, y ninguno es codigo que mantener. **La medicion y las
comprobaciones no estan ahi**: estan en `~/.local/share/base-harness`, asi que
un arreglo aqui llega a todos los proyectos con `git pull && ./install.sh`, sin
tocar ninguno. Eso es lo que una plantilla copiada no consigue.

## Un contrato, sin adaptadores

`AGENTS.md` es el contrato y **no tiene copias**. Codex, Cursor, Zed, Aider y
las demas lo leen de forma nativa. Claude Code lee `CLAUDE.md`, asi que el
proyecto lleva un `CLAUDE.md` de **una linea**: `@AGENTS.md`. Eso es todo el
adaptador que hay, y no cambia nunca, porque su contenido no depende de lo que
diga `AGENTS.md`.

Las skills viven **una sola vez**, en `.claude/skills/`. Claude Code las
registra por estar en esa ruta; cualquier otra herramienta llega a ellas porque
`AGENTS.md` trae una tabla que dice cual leer y cuando. No se copian a
`.cursor/`, ni a `.agents/`, ni a ningun sitio: una copia por herramienta
deriva de las demas, y a partir de ahi cada agente trabaja con una version
distinta sin que nadie lo note.

Contrapartida honesta: un import puede fallar en silencio —el agente arranca
sin contexto y no avisa—. Se comprueba una vez, preguntandole que dice
`AGENTS.md`. Diez segundos contra un generador permanente.

## Ordenes

```
base-harness init [ruta]     escribe el contrato y las skills en un proyecto
base-harness upgrade [ruta]  refresca lo que es de la herramienta; nunca AGENTS.md
base-harness check           falla si un plan no trae sus obligaciones (CI)
base-harness planes          lo mismo, informativo
base-harness time <slug>     lo que costo un plan
base-harness ritmo           el ritmo real de los planes cerrados
base-harness donde           que rutas esta usando
```

`init` no pisa nada: si un archivo ya existe, para y lo dice. `upgrade` solo
toca lo que es de la herramienta y **nunca** `AGENTS.md` ni `.gitignore`, que
los ha escrito una persona.

## Como mide el tiempo

No hay cronometro y no se mide el reloj. Sale de **dos relojes que ya
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

Sin repositorio git no hay colateral: `init` avisa si el destino no lo es.

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
**de ese repositorio**, con `base-harness ritmo`. Un monorepo grande y un
servicio pequeno no tienen el mismo.

La plantilla viaja con **5,0 min/tarea prestados** —medidos sobre 71 tareas en
otro proyecto—, y la regla es escribir en la linea que son prestados. En cuanto
cierres dos planes propios, recalcula y borra el prestamo.

## Idioma

Los planes se leen en castellano: la clasificacion en decidir / construir /
verificar sale de las palabras que usan las tareas. Traducirlo es cambiar el
bloque `PALABRA_*` de `base_harness/plan_time.py` — y hay que hacerlo, porque
no traducirlo **no da error**: mete todo en "construir" y produce un desglose
creible y vacio.

## Lo que deliberadamente NO trae

- **Nada del lenguaje del proyecto.** El CI que instala solo comprueba planes:
  no hay tests, ni linter, ni dependencias. Eso se anade por proyecto, porque
  un `pytest` y un `npm test` no se parecen en nada.
- **Subagentes.** Se anaden cuando el repo tiene superficie que valga la pena
  delegar; el primero que se echa de menos es uno que busque en los planes, y
  no antes de unos 30.
- **Reconocimiento automatico.** Depende de como este organizado el proyecto.
  La tarea de reconocimiento si viene en `create-plan`.
- **Declaracion de capacidades.** `plans_check.py` trae el hueco comentado: se
  activa cuando el proyecto tenga un sitio donde declararlas. Una comprobacion
  que exige texto que no apunta a ninguna parte se acaba desactivando.

## Estado

Los dos scripts vienen de un monorepo donde ya midieron 2 planes y 71 tareas.
La version recortada esta verificada sobre proyectos vacios, pero **todavia no
se ha cerrado ningun plan con ella**: el primero dira si el ritmo prestado
sirve.
