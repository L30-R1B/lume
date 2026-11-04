#!/usr/bin/env bash
set -euo pipefail
ce_source=$(cd -- "$(dirname -- "$0")/.." && pwd)
ce_prefix=${CE_PREFIX:-$HOME/.local/share/codex-economy}
ce_bin=${CE_BIN:-$HOME/.local/bin}
mkdir -p "$ce_prefix" "$ce_bin"
if [ -e "$ce_bin/ce" ] && [ "$(readlink "$ce_bin/ce" || true)" != "$ce_prefix/runtime/bin/ce" ]; then
  echo 'Existing unrelated ce executable: choose CE_BIN' >&2
  exit 1
fi
python3 -m venv "$ce_prefix/runtime"
"$ce_prefix/runtime/bin/pip" install "$ce_source"
ln -sfn "$ce_prefix/runtime/bin/ce" "$ce_bin/ce"
"$ce_bin/ce" integrity
