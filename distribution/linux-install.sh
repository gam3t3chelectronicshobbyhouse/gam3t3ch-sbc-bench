#!/usr/bin/env bash
set -euo pipefail
base="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
prefix="${G3BENCH_PREFIX:-$HOME/.local/share/GAM3T3CH/app}"
case "$prefix" in /*) ;; *) echo 'Installation path must be absolute.' >&2; exit 1 ;; esac
if [[ ! -f "$base/GAM3T3CH/BUNDLE.json" || ! -x "$base/GAM3T3CH/GAM3T3CH" ]]; then
  echo 'Extract the entire standalone archive before running this installer.' >&2; exit 1
fi
if [[ -e "$prefix" ]]; then echo "Destination exists: $prefix. Keep results and uninstall/update that copy first." >&2; exit 1; fi
mkdir -p -- "$(dirname -- "$prefix")"
cp -a -- "$base/GAM3T3CH" "$prefix"
"$prefix/GAM3T3CH" shortcuts
echo 'Installed with desktop/menu launchers and an uninstall menu entry where supported.'
exec "$prefix/GAM3T3CH" ui
