#!/usr/bin/env bash
# Install base-harness on this machine.
#
#   ./install.sh
#
# Copies the tool to ~/.local/share/base-harness and leaves a link in
# ~/.local/bin. Only python3 is needed: no pip, no pipx, no uv.
#
# To update: git pull && ./install.sh
set -euo pipefail

SOURCE="$(cd "$(dirname "$0")" && pwd)"
SHARE="${XDG_DATA_HOME:-$HOME/.local/share}/base-harness"
BIN="$HOME/.local/bin"

command -v python3 >/dev/null || { echo "python3 is required"; exit 1; }

rm -rf "$SHARE"
mkdir -p "$(dirname "$SHARE")" "$BIN"
cp -r "$SOURCE" "$SHARE"
rm -rf "$SHARE/.git"

# A link, not a copy: `bin/base-harness` resolves its own path to find the
# template, and `resolve()` follows the link down to ~/.local/share. With a copy
# it would look for the template under ~/.local and not find it.
ln -sf "$SHARE/bin/base-harness" "$BIN/base-harness"

echo "installed: $BIN/base-harness -> $SHARE"
case ":$PATH:" in
  *":$BIN:"*) ;;
  *) echo; echo "  WARNING: $BIN is not on your PATH. Add to ~/.bashrc:";
     echo '    export PATH="$HOME/.local/bin:$PATH"' ;;
esac
echo
echo "Now, in any project:  base-harness init"
