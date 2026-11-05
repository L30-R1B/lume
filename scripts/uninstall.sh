#!/usr/bin/env bash
set -euo pipefail
ce_prefix=${CE_PREFIX:-$HOME/.local/share/codex-economy}
ce_bin=${CE_BIN:-$HOME/.local/bin}
if [ "$(readlink "$ce_bin/ce" || true)" = "$ce_prefix/runtime/bin/ce" ]; then
  ce_script=$(cd -- "$(dirname -- "$0")" && pwd)
  "$ce_prefix/runtime/bin/python" "$ce_script/remove_extensions.py"
  "$ce_bin/ce" integrate --remove
  rm -- "$ce_bin/ce"
fi
if [ -L "$ce_prefix/runtime" ]; then
  rm -- "$ce_prefix/runtime"
elif [ -f "$ce_prefix/runtime/pyvenv.cfg" ] && [ -f "$ce_prefix/runtime/bin/ce" ]; then
  rm -rf -- "$ce_prefix/runtime"
fi
if [ -d "$ce_prefix/releases" ] && [ ! -L "$ce_prefix/releases" ]; then
  for ce_release in "$ce_prefix"/releases/*; do
    if [ -f "$ce_release/.ce-release" ] && [ ! -L "$ce_release" ]; then rm -rf -- "$ce_release"; fi
  done
fi
# State, project roots, credentials and optional downloaded toolchains/models remain intact.
