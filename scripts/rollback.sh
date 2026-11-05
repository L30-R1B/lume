#!/usr/bin/env bash
set -euo pipefail
ce_prefix=${CE_PREFIX:-$HOME/.local/share/codex-economy}
ce_previous=$(cat "$ce_prefix/previous-runtime")
case "$ce_previous" in "$ce_prefix/releases/"*) ;; *) echo 'Invalid previous runtime' >&2; exit 1;; esac
if [ ! -f "$ce_previous/.ce-release" ]; then echo 'Previous managed runtime unavailable' >&2; exit 1; fi
if [ "$(cat "$ce_previous/.ce-release")" = legacy ]; then
  rm -- "$ce_prefix/runtime"
  mv -- "$ce_previous" "$ce_prefix/runtime"
else
  ln -s "$ce_previous" "$ce_prefix/.runtime-rollback"
  mv -Tf -- "$ce_prefix/.runtime-rollback" "$ce_prefix/runtime"
fi
printf 'Runtime rolled back. A schema downgrade requires the pre-upgrade database backup; do not open newer state with an older release.\n'
