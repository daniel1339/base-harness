---
name: plan-task
description: Ejecutar una tarea de un plan de Pacto de principio a fin — leerla, implementarla, correr los tests y registrar evidencia verificable con `pacto exec`. Usala al avanzar un plan de `.pacto/plans/current`, al cerrar una tarea `N.M`, o cuando haya que marcar una tarea como hecha.
---

# Ejecutar una tarea de un plan

Una tarea cada vez. Una tarea se cierra cuando el codigo funciona **y** el plan
lleva evidencia que una maquina pueda volver a comprobar — no cuando alguien
escribe que esta hecha.

Crear un plan, o darle a uno viejo la estructura que esto exige, es la skill
`create-plan`. Esta empieza cuando `tasks.md` ya tiene tareas numeradas.

## Precondiciones

Preguntale a la herramienta, no mires la carpeta a ojo:

```bash
pacto status --root .pacto/plans --repo-root . --format table
```

El plan es ejecutable cuando su recuento de tareas es **mayor que 0**. `pacto
exec` solo puede apuntar a `N.M`, y solo mientras el plan este en `current`.

- El plan no esta en `current` → `pacto move <estado> <slug> current --root .pacto/plans`
- 0 tareas, o fases en prosa → parar y llevarlo a contrato primero
  (`create-plan`). Solo ese plan, nunca en una pasada masiva sobre el workspace.
- Comprueba el binario antes de ejecutar: `pacto version` 0.1.26 o superior.

No uses `pacto normalize` como puerta: analiza un unico documento por plan, asi
que reporta `missing_core_*` por secciones que existen en un archivo hermano.

## El bucle

```
leer          → que pide de verdad la tarea N.M
localizar     → donde vive eso, en file:line
implementar   → en el hilo principal
probar        → correr la suite y quedarse con los TEST_REFS
pacto exec    → marcar N.M y registrar la evidencia
```

Delega la lectura ancha —"donde esta X", "como fluye Y"— a un subagente que
devuelva `file:line`, y nunca dejes que pegue el cuerpo de un archivo o un log
entero de vuelta: eso anula el motivo de haber delegado. La implementacion
ocurre siempre en el hilo principal.

## Que cuenta como evidencia

`pacto status` extrae afirmaciones de los documentos del plan y las valida
contra el repositorio, reportando cada una como `verified`, `partial` o
`unverified`. Entiende cuatro categorias, asi que la evidencia se escribe en
esos terminos:

| Categoria | Como se escribe | Ejemplo |
|---|---|---|
| `paths` | Rutas relativas al repo | `src/flows/scheduler.py` |
| `symbols` | Funciones o clases que existen | `FlowScheduler` |
| `endpoints` | Rutas tal y como las expone el servicio | `POST /api/v1/flows/` |
| `test_refs` | Archivos o node ids de test que corrieron | `tests/test_scheduler.py::test_retry` |

Prosa como "se implemento la deduplicacion" no verifica nada. Lo minimo para
cerrar: las rutas tocadas, y un `test_ref` que salio verde. Si la tarea cambio
una superficie de API, nombra tambien el endpoint.

## Una capacidad sin declarar no existe

Si la tarea **anade una capacidad** —un endpoint, una herramienta, una accion,
un estado, un permiso, algo que un usuario pueda pedir— no se cierra hasta que
esa capacidad esta declarada donde se consume.

Esto **no se aplaza al final del plan**. Documentar en una tanda al terminar es
la forma habitual de no documentar: cuando llega el momento, nadie recuerda los
matices y lo que se escribe es generico.

### Seis campos, siempre los mismos

Sin formato fijo cada uno escribe algo distinto y la documentacion se llena de
prosa que no se puede consultar:

| Campo | Que responde | Ejemplo |
|-------|--------------|---------|
| **Nombre** | Como se llama, en el vocabulario del usuario | "Pausar una automatizacion" |
| **Que hace** | Una frase, sin jerga interna | Detiene las ejecuciones sin perder la configuracion |
| **Donde vive** | Seccion del producto | Automatizaciones → control operativo |
| **Requisitos previos** | Que debe existir antes | La automatizacion debe estar creada |
| **Como se invoca** | Endpoint, herramienta o ruta de interfaz | `POST /api/v1/flows/{id}/pause` |
| **Si no se puede** | Que responder cuando no esta disponible | "Ya estaba pausada" |

Los dos que se saltan siempre son los que mas valen: **requisitos previos**, que
es lo que permite guiar en orden; y **si no se puede**, que es lo que evita que
un agente improvise cuando algo falta.

## Registrarlo

```bash
pacto exec current <slug> --root .pacto/plans --step 1.2 \
  --evidence "[1.2] src/flows/scheduler.py; tests: tests/test_scheduler.py::test_retry" \
  --dry-run                     # previsualiza primero; quitalo para escribir
```

**La evidencia empieza por `[N.M]`.** `pacto` no guarda a que tarea pertenece
cada linea, asi que sin ese prefijo la seccion de evidencia es una lista de
horas huerfanas: no se puede leer, y `plan-time.py` no puede decir si el tiempo
se fue en decidir o en construir. Son cinco caracteres y es la unica forma de
saberlo.

`pacto exec` escribe solo artefactos del plan, nunca codigo fuente. Marcar una
tarea editando a mano el checkbox de `tasks.md` se salta el rastro de evidencia
—y con el, la medicion de tiempos—. Usa la CLI.

Detenida en vez de hecha:

```bash
pacto exec current <slug> --root .pacto/plans --step 1.2 \
  --blocker "faltan las credenciales del sandbox"
```

Una tarea cuyos tests fallan **no** se cierra con una nota que lo diga. O se
arregla, o se registra como impedimento.

## Cerrar el plan

Antes de moverlo, registrar lo que costo de verdad:

```bash
python3 scripts/plan-time.py <slug>
```

Y escribir el resultado junto a la estimacion, en los metadatos de `tasks.md`:

```markdown
- Estimación: 2.0 h  ·  Real: 2.4 h  ·  desvío +20%  ·  colateral 0.3 h
```

Sin esa linea el plan se cierra y la informacion se pierde: al siguiente que
estime le queda la misma intuicion que habia antes. `plans-check.py` falla en CI
si un plan en `done` no la lleva.

Cuando todas las fases esten marcadas, `pacto status --root .pacto/plans
--repo-root .` no deberia mostrar afirmaciones `unverified` para ese slug.
Entonces:

```bash
pacto move current <slug> done --root .pacto/plans
```

Y commitea los artefactos del plan junto al codigo que describen, para que la
evidencia y el cambio caigan en el mismo diff.
