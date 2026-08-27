#!/usr/bin/env bash
# Instala el harness base en un proyecto.
#
#   ./bootstrap.sh /ruta/al/proyecto
#
# No pisa nada: si un archivo ya existe en el destino, para y lo dice. Un
# AGENTS.md escrito a mano sobrescrito no se recupera.
set -euo pipefail

DESTINO="${1:-}"
[ -n "$DESTINO" ] || { echo "uso: $0 <ruta-del-proyecto>"; exit 1; }
[ -d "$DESTINO" ] || { echo "no existe el directorio: $DESTINO"; exit 1; }

ORIGEN="$(cd "$(dirname "$0")" && pwd)/template"
DESTINO="$(cd "$DESTINO" && pwd)"

choques=()
while IFS= read -r f; do
  rel="${f#"$ORIGEN"/}"
  [ -e "$DESTINO/$rel" ] && choques+=("$rel")
done < <(find "$ORIGEN" -type f)

if [ ${#choques[@]} -gt 0 ]; then
  echo "Estos archivos ya existen en el destino. No he tocado nada:"
  printf '  %s\n' "${choques[@]}"
  echo
  echo "Comparalos a mano y vuelve a lanzarlo cuando el destino este limpio."
  exit 1
fi

cp -r "$ORIGEN/." "$DESTINO/"
echo "harness instalado en $DESTINO"
echo

# git no es opcional aqui: plan-time.py saca el trabajo colateral de `git log`.
# Sin repo solo ve los huecos entre tareas, y esa mitad no se recupera despues
# porque los commits que no hiciste no existen.
if ! git -C "$DESTINO" rev-parse --git-dir >/dev/null 2>&1; then
  echo "  AVISO: el destino no es un repositorio git."
  echo "  plan-time.py mide el trabajo colateral desde git log; sin repo mide"
  echo "  la mitad. Antes de la primera tarea:  git -C $DESTINO init"
  echo
fi

cat <<'HUECOS'
Tres huecos que rellenar, en este orden:

  1. AGENTS.md          los limites del proyecto ("esto NO lo hacemos"),
                        el mapa del repo y los comandos
  2. scripts/harness-sync.py    la linea TOOLS = {...}: deja solo las
                        herramientas que uses de verdad
  3. harness/skills/create-plan/SKILL.md    el ritmo prestado (5,0 min/tarea)
                        se pisa con `plan-time.py --ritmo` al cerrar dos planes

Luego:

  pacto init                                 # si no lo has hecho
  python3 scripts/harness-sync.py            # genera los adaptadores
  python3 scripts/harness-sync.py --check
  python3 scripts/plans-check.py

(`make harness-sync` y `make harness-check` hacen lo mismo, si tienes make:
no esta instalado en todas partes, y por eso CI llama a los scripts.)
HUECOS
