#!/usr/bin/env bash
# Instala base-harness en esta maquina.
#
#   ./install.sh
#
# Copia la herramienta a ~/.local/share/base-harness y deja un enlace en
# ~/.local/bin. Solo necesita python3: nada de pip, pipx ni uv.
#
# Para actualizar: git pull && ./install.sh
set -euo pipefail

ORIGEN="$(cd "$(dirname "$0")" && pwd)"
SHARE="${XDG_DATA_HOME:-$HOME/.local/share}/base-harness"
BIN="$HOME/.local/bin"

command -v python3 >/dev/null || { echo "hace falta python3"; exit 1; }

rm -rf "$SHARE"
mkdir -p "$(dirname "$SHARE")" "$BIN"
cp -r "$ORIGEN" "$SHARE"
rm -rf "$SHARE/.git"

# Enlace, no copia: `bin/base-harness` resuelve su propia ruta para encontrar la
# plantilla, y `resolve()` sigue el enlace hasta ~/.local/share. Con una copia
# buscaria la plantilla en ~/.local y no la encontraria.
ln -sf "$SHARE/bin/base-harness" "$BIN/base-harness"

echo "instalado: $BIN/base-harness -> $SHARE"
case ":$PATH:" in
  *":$BIN:"*) ;;
  *) echo; echo "  AVISO: $BIN no esta en tu PATH. Anade a ~/.bashrc:";
     echo '    export PATH="$HOME/.local/bin:$PATH"' ;;
esac
echo
echo "Ahora, en cualquier proyecto:  base-harness init"
