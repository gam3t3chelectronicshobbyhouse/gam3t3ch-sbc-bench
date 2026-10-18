#!/usr/bin/env bash
set -euo pipefail
# Debian/Raspberry Pi OS; user-local source build.
if [[ "$(uname -s)" != Linux ]]; then echo 'Linux is required by the installer.' >&2; exit 1; fi
case "$(uname -m)" in armv6l) echo 'ARMv6 / Pi 1 / original Zero support is experimental; a compatible OS/toolchain is required.' >&2 ;; armv7l|aarch64|arm64|x86_64) ;; *) echo 'Unsupported architecture for this baseline.' >&2; exit 1 ;; esac
if [[ ! -r /etc/os-release ]]; then echo 'Cannot identify distribution.' >&2; exit 1; fi
. /etc/os-release
case " ${ID:-} ${ID_LIKE:-} " in *debian*|*raspbian*|*ubuntu*) ;; *) echo 'Install dependencies manually; Debian-family installer only.' >&2; exit 1 ;; esac
if [[ $EUID -eq 0 ]]; then echo 'Run as your normal user; sudo is used only for packages.' >&2; exit 1; fi
prefix="${G3BENCH_PREFIX:-$HOME/.local/share/gam3t3ch-sbc-bench}"
bindir="$HOME/.local/bin"
if [[ -e "$prefix" ]]; then echo "Destination exists: $prefix. Update/build it manually." >&2; exit 1; fi
case "$prefix" in /*) ;; *) echo 'G3BENCH_PREFIX must be an absolute path.' >&2; exit 1 ;; esac
sudo apt-get update
sudo apt-get install -y build-essential cmake pkg-config git python3
if ! sudo apt-get install -y fio util-linux; then
  echo 'Optional storage tools unavailable; CPU/memory/graphics remain usable.' >&2
fi
if ! sudo apt-get install -y libsdl2-dev libgles2-mesa-dev; then
  echo 'Optional graphics dependencies unavailable; building headless baseline.' >&2
fi
git clone --depth 1 --branch main https://github.com/gam3t3chelectronicshobbyhouse/gam3t3ch-sbc-bench.git "$prefix"
cmake -S "$prefix" -B "$prefix/build" -DCMAKE_BUILD_TYPE=Release
cmake --build "$prefix/build" --parallel 2
mkdir -p "$bindir"
# Python wrapper avoids shell expansion of paths in the generated launcher.
python3 - "$prefix" "$bindir/g3bench" <<'PY'
import pathlib, sys
root, target = sys.argv[1:]
pathlib.Path(target).write_text('#!/usr/bin/env python3\nimport sys\nsys.path.insert(0, '+repr(root)+')\nfrom g3bench.__main__ import main\nsys.exit(main())\n')
PY
chmod +x "$bindir/g3bench"
if [[ -d "$HOME/.local/share/applications" || -n "${XDG_CURRENT_DESKTOP:-}" ]]; then
  mkdir -p "$HOME/.local/share/applications"
  printf '[Desktop Entry]\nType=Application\nName=GAM3T3CH 3D Benchmark\nExec="%s/g3bench" ui\nIcon=%s/showcase/brand/g3-mark.svg\nTerminal=true\nCategories=System;Utility;\n' "$bindir" "$prefix" > "$HOME/.local/share/applications/g3bench.desktop"
fi
echo "Installed. Add $bindir to PATH if necessary, then run: g3bench ui"
echo 'This is a development baseline; physical Raspberry Pi qualification is in progress.'
