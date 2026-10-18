#!/usr/bin/env bash
set -euo pipefail
# Native packages are platform-specific; installation/launch is shared.
if [[ $EUID -eq 0 ]]; then echo 'Run as your normal user; sudo is used only for packages.' >&2; exit 1; fi
system="$(uname -s)"
case "$system" in
  Linux)
    case "$(uname -m)" in armv6l) echo 'Pi 1/original Zero support is experimental; Godot 4 is skipped on ARMv6.' ;; armv7l|aarch64|arm64|x86_64) ;; *) echo 'Architecture is not currently supported by this installer.' >&2; exit 1 ;; esac
    if command -v apt-get >/dev/null; then
      sudo apt-get update
      sudo apt-get install -y build-essential pkg-config python3 curl ca-certificates
      sudo apt-get install -y libsdl2-dev libgles2-mesa-dev fio util-linux || echo 'Some optional GPU/storage packages unavailable.' >&2
    elif command -v dnf >/dev/null; then
      sudo dnf install -y gcc pkgconf-pkg-config python3 curl ca-certificates
      sudo dnf install -y SDL2-devel mesa-libGLES-devel fio util-linux || echo 'Some optional GPU/storage packages unavailable.' >&2
    elif command -v pacman >/dev/null; then
      sudo pacman -S --needed --noconfirm gcc pkgconf python curl ca-certificates
      sudo pacman -S --needed --noconfirm sdl2 mesa fio util-linux || echo 'Some optional GPU/storage packages unavailable.' >&2
    elif command -v zypper >/dev/null; then
      sudo zypper --non-interactive install gcc pkg-config python3 curl ca-certificates
      sudo zypper --non-interactive install libSDL2-devel Mesa-libGLESv2-devel fio util-linux || echo 'Some optional GPU/storage packages unavailable.' >&2
    else
      echo 'No supported package manager detected. Install Python 3.9+, a C compiler and curl manually; optional: pkg-config, SDL2/GLES2 and fio.' >&2
    fi
    ;;
  Darwin)
    if ! command -v python3 >/dev/null; then
      if command -v brew >/dev/null; then brew install python; else
        echo 'Install Python 3.9+ from python.org or Homebrew, then rerun this command.' >&2; exit 1
      fi
    fi
    ;;
  *) echo 'Use install.ps1 in Windows PowerShell. This shell installer targets Linux/macOS.' >&2; exit 1 ;;
esac
if ! command -v python3 >/dev/null; then echo 'Python 3.9+ is required.' >&2; exit 1; fi
python3 -c 'import sys; assert sys.version_info >= (3,9), "Python 3.9+ is required"'
scratch="$(mktemp -d)"
trap 'rm -f -- "$scratch/installer.py"; rmdir -- "$scratch"' EXIT
curl -fsSL https://raw.githubusercontent.com/gam3t3chelectronicshobbyhouse/gam3t3ch-sbc-bench/main/installer.py -o "$scratch/installer.py"
options=()
if [[ -n "${G3BENCH_PREFIX:-}" ]]; then options+=(--prefix "$G3BENCH_PREFIX"); fi
python3 "$scratch/installer.py" "${options[@]}" "$@"
