#!/usr/bin/env bash
set -Eeuo pipefail

update=0
if [[ "${1:-}" == "--update" ]]; then
  update=1
elif [[ $# -ne 0 ]]; then
  echo "Usage: $0 [--update]" >&2
  exit 2
fi

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
codex_home="${CODEX_HOME:-${HOME:?HOME is not set}/.codex}"
skills_root="$codex_home/skills"
mkdir -p -- "$skills_root"

for skill in lume lume-task; do
  source_dir="$repo_root/skills/$skill"
  destination="$skills_root/$skill"

  if [[ ! -f "$source_dir/SKILL.md" ]]; then
    echo "Missing skill entrypoint: $source_dir/SKILL.md" >&2
    exit 1
  fi
  if [[ -L "$destination" ]]; then
    echo "Refusing to replace symlinked skill: $destination" >&2
    exit 1
  fi
  if [[ -e "$destination" ]]; then
    if [[ ! -d "$destination" ]]; then
      echo "Refusing to replace non-directory skill path: $destination" >&2
      exit 1
    fi
    if diff -qr -- "$source_dir" "$destination" >/dev/null; then
      printf 'Already current: %s\n' "$destination"
      continue
    fi
    if (( update == 0 )); then
      echo "Skill differs from the repository copy; preserve it or rerun with --update: $destination" >&2
      exit 1
    fi
    backup="$destination.backup-$(date -u +%Y%m%dT%H%M%SZ)"
    mv -- "$destination" "$backup"
    printf 'Backed up previous skill: %s\n' "$backup"
  fi

  cp -a -- "$source_dir" "$destination"
  printf 'Installed: %s\n' "$destination"
done
