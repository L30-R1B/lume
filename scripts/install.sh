#!/usr/bin/env bash
set -euo pipefail
ce_source=$(cd -- "$(dirname -- "$0")/.." && pwd)
ce_prefix=${CE_PREFIX:-$HOME/.local/share/codex-economy}
ce_bin=${CE_BIN:-$HOME/.local/bin}
mkdir -p "$ce_prefix/releases" "$ce_bin"
if [ -e "$ce_bin/ce" ] && [ "$(readlink "$ce_bin/ce" || true)" != "$ce_prefix/runtime/bin/ce" ]; then
  echo 'Existing unrelated ce executable: choose CE_BIN' >&2
  exit 1
fi
ce_build=$(mktemp -d)
trap 'rm -rf -- "$ce_build"' EXIT
python3 -m venv "$ce_build/builder"
"$ce_build/builder/bin/python" -m pip install --upgrade pip
"$ce_build/builder/bin/python" -m pip wheel --no-deps --wheel-dir "$ce_build" "$ce_source"
ce_wheel=$(find "$ce_build" -maxdepth 1 -name 'codex_economy-*.whl' -print -quit)
ce_digest=$(sha256sum "$ce_wheel" | cut -c 1-16)
ce_new="$ce_prefix/releases/$ce_digest"
if [ ! -f "$ce_new/.ce-release" ]; then
  python3 -m venv "$ce_new"
  "$ce_new/bin/python" -m pip install --upgrade pip
  if [ -f "$ce_source/requirements-runtime.lock" ]; then
    awk '!/^codex-economy([ =@]|$)/' "$ce_source/requirements-runtime.lock" > "$ce_build/constraints.txt"
    "$ce_new/bin/python" -m pip install --constraint "$ce_build/constraints.txt" "$ce_wheel"
  else
    "$ce_new/bin/python" -m pip install "$ce_wheel"
  fi
  CE_HOME="$ce_build/state" "$ce_new/bin/ce" integrity
  printf 'codex-economy\n' > "$ce_new/.ce-release"
fi
# Database upgrades are explicit here and have a preserved pre-upgrade snapshot.
if [ -f "${CE_HOME:-$HOME/.local/state/codex-economy}/state.sqlite" ]; then
  python3 "$ce_source/scripts/pre_upgrade_backup.py"
fi
ce_previous=$(readlink "$ce_prefix/runtime" || true)
if [ -d "$ce_prefix/runtime" ] && [ ! -L "$ce_prefix/runtime" ]; then
  ce_previous="$ce_prefix/releases/legacy-$(date +%s)"
  mv -- "$ce_prefix/runtime" "$ce_previous"
  printf 'legacy\n' > "$ce_previous/.ce-release"
fi
printf '%s\n' "$ce_previous" > "$ce_prefix/previous-runtime"
ln -s "$ce_new" "$ce_prefix/.runtime-next"
mv -Tf -- "$ce_prefix/.runtime-next" "$ce_prefix/runtime"
ln -sfn "$ce_prefix/runtime/bin/ce" "$ce_bin/ce"
"$ce_bin/ce" integrity
