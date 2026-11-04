#!/usr/bin/env bash
set -euo pipefail
ce_prefix=${CE_PREFIX:-$HOME/.local/share/codex-economy}
ce_bin=${CE_BIN:-$HOME/.local/bin}
if [ "$(readlink "$ce_bin/ce" || true)" = "$ce_prefix/runtime/bin/ce" ]; then
  "$ce_bin/ce" integrate --remove
  rm -- "$ce_bin/ce"
fi
# Keep state, backups, credentials and all registered projects.
if [ -f "$ce_prefix/runtime/pyvenv.cfg" ] && [ -f "$ce_prefix/runtime/bin/ce" ]; then
  rm -rf -- "$ce_prefix/runtime"
fi
