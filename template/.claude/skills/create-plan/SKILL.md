---
name: create-plan
description: Crear un plan en `.pacto/plans`, o llevar uno existente a la estructura ejecutable. Usala cuando se pida un plan, una hoja de ruta o una estrategia de implementacion, y cuando un plan tenga que hacerse ejecutable antes de trabajarlo (sin `tasks.md`, fases en prosa, o `pacto status` contando 0 tareas).
---

# Create Plan

Crear planes estructurados siguiendo las convenciones del workspace de Pacto.
Ejecutar una tarea de un plan que ya tiene esta estructura es la skill
`plan-task`.

## Donde viven

Bajo `.pacto/plans/<estado>/<slug>/`, donde `<estado>` es uno de: `current`,
`to-implement`, `done`, `outdated`.

## El layout canonico

```bash
pacto new <estado> <slug> --root .pacto/plans
```

Crea cuatro archivos, y esos cuatro son los unicos documentos primarios:

| Archivo | Para que |
|---------|----------|
| `README.md` | Titulo, estado, fecha, descripcion e indice a los otros tres |
| `spec.md` | Alcance, problema, requisitos, criterios de aceptacion, escenarios |
| `design.md` | Decisiones tecnicas, modulos, diagramas, tablas de opciones, riesgos |
| `tasks.md` | Fases numeradas con checkboxes, evidencia, bloqueadores |

**Rellena esos cuatro.** No los sustituyas por un unico archivo monolitico, y no
dupliques el mismo contenido largo en un quinto.

Como repartir "el plan" entre ellos:

1. **README** — uno o dos parrafos y los enlaces a los otros tres.
2. **spec** — que tiene que ser cierto al terminar: requisitos numerados y
   criterios de aceptacion comprobables. Tambien lo que queda fuera.
3. **design** — como: componentes, modelo de datos, interfaces, valores por
   defecto. Mermaid aqui si ayuda.
4. **tasks** — el orden de ejecucion: fases, checkboxes, rutas concretas.

## Numeracion de tareas

`pacto exec --step` solo puede apuntar a `N.M`, y eso impone tres reglas que
cuesta caro descubrir tarde:

| Forma | Vale |
|-------|------|
| `1.1`, `2.13` | Si |
| `1.0`, `3.0` | **No**: `--step` no las puede apuntar |
| `1.1b`, `1b.1`, `1.5-bis` | **No**: letras a cualquier lado del punto rompen el parseo |
| El mismo numero dos veces | **No**: `--step` no sabe a cual de las dos apunta |

Si hace falta meter una tarea en medio, se renumera. `base-harness check`
comprueba las cuatro y bloquea el merge.

## La seccion `## Bloqueadores`

`pacto status` deriva el estado de un plan leyendo esa seccion **linea a
linea**, y no distingue contenido de andamiaje:

| Situacion | Como se escribe |
|-----------|-----------------|
| No hay bloqueadores | La seccion, **vacia**. Sin tabla y sin "Ninguno registrado" |
| Hay bloqueadores | Una linea `- ` por bloqueador, con lo que bloquea y desde cuando |

Una tabla hace que la cabecera y el separador cuenten como dos bloqueadores, y
un "Ninguno registrado" declara bloqueado un plan que dice justo lo contrario.

Y en el **texto de una tarea** no se escribe "bloqueado" ni "bloqueador":
`pacto status` cuenta como bloqueada cualquier tarea que los contenga, aunque
hablen de otra cosa. Se dice "impedimento", "detenido", "obligatorio". Otras
formas ("bloqueo", "bloquear", "bloqueante") no disparan.

### Un bloqueador se comprueba antes de declararlo

Un plan se escribe desde fuera, y desde fuera ante la duda se declara la
dependencia porque parece lo prudente. Luego nadie vuelve a revisarla, y esa
suposicion se convierte en semanas de camino critico que no existe.

| El bloqueador dice... | Como se declara |
|-----------------------|-----------------|
| "el plan X no esta hecho" | Basta nombrarlo: `pacto status` dice si lo esta |
| **cualquier cosa sobre el codigo** | **Con su ancla `archivo:linea`**, comprobada antes de escribirla |

Un bloqueador que afirma algo del codigo sin ancla es una suposicion con
aspecto de hecho.

## Reconocer antes de decidir

Todo plan abre con una tarea de reconocimiento, **antes** de las decisiones:

```markdown
- [ ] 1.1 Reconocimiento: leer el codigo que este plan toca y registrar cada
      hallazgo donde toque -decision corregida, alcance anadido o impedimento-
      antes de resolver nada.
```

Resolver las decisiones de un plan sin haber mirado el codigo es decidir a
ciegas. Cuando el proyecto tenga suficiente superficie, automatiza la parte
mecanica de esto en un `scripts/plan-recon.py` que liste los archivos del area,
su tamano y sus dependencias.

## Estimar al crear, medir al cerrar

Todo plan lleva su estimacion en los metadatos de `tasks.md`, escrita **cuando
se crea**:

```markdown
- Estimación: 12.5 h
```

```
horas = tareas x ritmo medido x factor / 60
```

**El ritmo no se inventa**: sale de `base-harness ritmo`, que promedia los
planes ya cerrados de este repositorio.

> **Mientras no haya dos planes cerrados aqui**, `--ritmo` no tiene con que
> promediar. Usa **5,0 min por tarea** como ritmo prestado —medido sobre 71
> tareas en otro repositorio— y **escribe en la linea que es prestado**. En
> cuanto cierres dos planes, recalcula con los tuyos y borra el prestamo.

El **factor** es cuanto mas cuesta este plan que el mas simple. Sube con cada
componente adicional que toca, con el frontend, con el esquema compartido y con
las dependencias externas.

El **colateral** va aparte, como un porcentaje encima del total, y **solo se
aplica a los planes que tocan codigo que ya existe**: son los tests que estaban
rojos, la migracion que derivo, el fallo que aparece al mover algo.

| El plan... | Colateral |
|------------|-----------|
| Toca codigo existente | **+25%** (recalibra con tus propios cierres) |
| Es greenfield: archivos nuevos que no rompen nada | **~0%** |
| Mezcla las dos cosas | El porcentaje, solo sobre la parte que toca lo existente |

**No confundas las dos dimensiones**, que es facil y cuesta caro:

| | Que mide |
|---|---|
| **Factor** | Cuanto tarda cada tarea |
| **Colateral** | Cuanto trabajo imprevisto provoca |

Un plan de documentacion tiene colateral casi nulo —archivos nuevos que no
rompen nada— y factor **alto**, porque escribir contenido es lento. Bajarle las
dos por parecer "solo texto" produce una estimacion de un tercio de lo real.

Y un error que cuesta caro: **no dividas el reloj entre las tareas.** Eso cuenta
las pausas como trabajo e infla la estimacion casi al doble.

Ejemplo de linea completa al crear:

```markdown
- Estimación: 2.0 h  (12 tareas x 5.0 min prestados x factor 2)  ·  colateral 0%: greenfield
```

Estimar al crear no es burocracia: es lo unico que convierte el cierre en
informacion. Sin la cifra escrita antes, al terminar solo se sabe cuanto costo,
que no sirve para estimar el siguiente.

## Simplicidad: KISS, DRY, YAGNI

Como **restriccion durante**, no como revision al final. En `tasks.md`, antes de
la primera tarea que escribe codigo:

```markdown
- [ ] N.M Checklist previo a codigo: alcance limitado a lo que el plan pide
      (YAGNI), solucion minima sin abstracciones anticipadas (KISS), y cero
      duplicacion con lo que ya existe (DRY) — comprobado buscandolo, no
      suponiendolo.
```

El tercero es el que mas se incumple. Buscar antes de escribir cuesta minutos.

## Documentar es parte de construir

**Cada plan documenta lo suyo.** No hay un plan central de documentacion que
recoja despues lo que los demas hicieron: quien construye una capacidad es quien
sabe explicarla, y quien lo deje para otro escribira algo generico.

Dos tareas en todo plan que anada capacidades. Una al principio:

```markdown
- [ ] 1.N Enumerar las capacidades que este plan anade, con los seis campos del
      formato (ver skill `plan-task`). Es la lista contra la que se comprueba el
      cierre; escribirla ahora obliga a saber que se va a construir.
```

Y otra al cerrar:

```markdown
- [ ] N.M Verificar que cada capacidad de la lista esta declarada donde se
      consume.
```

La lista del principio es lo que hace verificable el cierre. Sin ella, "esta
todo documentado" es una opinion.

## Probar es parte de construir

Documentar tiene sus dos puntas —una lista al principio y su verificacion al
cerrar— y **probar solo tenia el final**: `plan-task` pide un `test_ref` verde
para cerrar cada tarea, pero nada obligaba a decidir antes que habia que
demostrar. Asi, quien cierra la tarea escribe el test que la pone verde, y
"funciona" acaba significando "pasa el test que me invente", que es justo lo que
la regla de documentacion existe para evitar.

Mismas dos tareas, aplicadas a probar. Una al principio:

```markdown
- [ ] 1.N Enumerar que hay que demostrar para decir que este plan funciona: por
      cada capacidad, la comprobacion que la prueba y a que nivel. Es la lista
      contra la que se comprueba el cierre.
```

Y otra al cerrar:

```markdown
- [ ] N.M Verificar que cada comprobacion de la lista existe y salio verde, con
      su `test_ref`. Una que no se pueda senalar no esta hecha.
```

**Una capacidad sin comprobacion en esa lista no se construye**: o se le anade
una, o se saca del alcance. Es la decision que se puede discutir mientras se
escribe el plan y ya no cuando hay que cerrarlo.

Que nivel es el correcto lo dice lo que se esta construyendo, no una regla fija.
Sirve la pregunta: **si esto se rompe, ¿por donde se enteraria alguien?** Si la
respuesta es "un usuario", la comprobacion esta demasiado arriba.

## Llevar a contrato un plan que ya existe

Un plan viejo no suele estar caduco de contenido: le falta la estructura que
`pacto exec` necesita. Se arregla **uno cada vez, cuando le toca el turno de
ejecutarse**, nunca en una pasada masiva.

Preguntale a la herramienta que tiene:

```bash
pacto status --root .pacto/plans --repo-root . --format table
```

El recuento de tareas es la respuesta. **0 tareas significa que no hay
numeracion `N.M`**, y esa es la condicion bloqueante.

| Lo que falta | Donde va |
|--------------|----------|
| El problema y la intencion | `spec.md` |
| Escenarios (DADO / CUANDO / ENTONCES) | `spec.md` |
| Criterios de aceptacion comprobables | `spec.md` |
| Tareas numeradas `N.M` | `tasks.md` — la bloqueante |
| Seccion de evidencia | `tasks.md` |

**`pacto normalize` no es el checker de este layout**: analiza un unico
documento por plan, asi que reporta `missing_core_*` por secciones que si
existen, solo que en un archivo hermano. Sirve para planes legacy de un solo
archivo. Y nunca lo corras con `--write`: reescribe todos los planes del ambito
de golpe y solo toca cosmetica.

## Roadmap: cuando varios requerimientos son varios planes

Un requerimiento es un plan. Los que forman la hoja de ruta llevan en su
`spec.md`:

```markdown
- Fase: 2
```

Esa marca es lo unico que hace que `base-harness check` los **bloquee** en CI; el
resto solo se reportan. Sirve para encender la puerta plan a plan en vez de
dejar el repo en rojo el primer dia, que es como se acaba desactivando una
comprobacion.

## Notas

- Prefiere `pacto new` a crear la carpeta a mano.
- No mantengas un inventario de planes en markdown: para eso esta `pacto status`.
