#!/usr/bin/env python3
"""User-local source installer shared by the shell and PowerShell entry points."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

REPOSITORY = "gam3t3chelectronicshobbyhouse/gam3t3ch-sbc-bench"
GODOT_VERSION = "4.4.1-stable"


def download(url, target):
    request = urllib.request.Request(url, headers={"User-Agent": "GAM3T3CH-installer"})
    with urllib.request.urlopen(request, timeout=120) as response, Path(target).open("wb") as output:
        shutil.copyfileobj(response, output)


def extract(archive, destination):
    destination = Path(destination).resolve()
    with zipfile.ZipFile(archive) as source:
        for entry in source.infolist():
            target = (destination / entry.filename).resolve()
            if destination != target and destination not in target.parents:
                raise ValueError("Unsafe path in downloaded archive")
            if stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError("Symlinks in downloaded archives are not accepted")
        source.extractall(destination)


def godot_asset(system, machine):
    arch = machine.lower()
    if system == "Windows" and arch in {"amd64", "x86_64"}:
        return "Godot_v4.4.1-stable_win64.exe.zip"
    if system == "Darwin" and arch in {"arm64", "aarch64", "x86_64"}:
        return "Godot_v4.4.1-stable_macos.universal.zip"
    if system == "Linux":
        suffix = {"x86_64": "x86_64", "amd64": "x86_64", "aarch64": "arm64", "arm64": "arm64", "armv7l": "arm32"}.get(arch)
        if suffix:
            return "Godot_v4.4.1-stable_linux." + suffix + ".zip"
    return None


def install_godot(prefix):
    asset = godot_asset(platform.system(), platform.machine())
    if not asset:
        print("Optional Godot engine unavailable for this OS/architecture; portable tests remain usable.")
        return None
    base = "https://github.com/godotengine/godot/releases/download/" + GODOT_VERSION + "/"
    with tempfile.TemporaryDirectory() as folder:
        archive, checksums = Path(folder) / asset, Path(folder) / "SHA512-SUMS.txt"
        print("Downloading optional Godot " + GODOT_VERSION + " for " + platform.machine())
        download(base + asset, archive)
        download(base + "SHA512-SUMS.txt", checksums)
        entries = {line.split()[-1].lstrip("*"): line.split()[0] for line in checksums.read_text().splitlines() if len(line.split()) >= 2}
        digest = hashlib.sha512()
        with archive.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        if entries.get(asset) != digest.hexdigest():
            raise ValueError("Official Godot SHA-512 checksum did not match")
        runtime = prefix / "runtime" / "godot"
        runtime.mkdir(parents=True)
        extract(archive, runtime)
        if platform.system() == "Darwin":
            engine = runtime / "Godot.app" / "Contents" / "MacOS" / "Godot"
        else:
            candidates = [p for p in runtime.iterdir() if p.is_file() and p.name.startswith("Godot") and "console" not in p.name]
            engine = candidates[0]
            engine = engine.rename(runtime / ("godot.exe" if os.name == "nt" else "godot"))
        engine.chmod(engine.stat().st_mode | 0o755)
        return str(engine)


def compiler(prefix, explicit=None):
    if explicit:
        path = Path(explicit).resolve(strict=True)
        return [str(path), "cc"] if path.stem == "zig" else [str(path)]
    for name in ("cc", "gcc", "clang"):
        found = shutil.which(name)
        if found:
            # Avoid macOS opening an interactive Command Line Tools installer.
            if platform.system() == "Darwin" and subprocess.run(["xcode-select", "-p"], capture_output=True).returncode:
                break
            return [found]
    if os.name == "nt" or platform.system() == "Darwin":
        toolchain = prefix / "runtime" / "toolchain"
        subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--only-binary=:all:",
                        "--target", str(toolchain), "ziglang==0.16.0"], check=True)
        return [str(toolchain / "ziglang" / ("zig.exe" if os.name == "nt" else "zig")), "cc"]
    raise RuntimeError("A C compiler is required. Install build dependencies with install.sh or your distribution package manager.")


def build(prefix, explicit=None):
    cc = compiler(prefix, explicit)
    target = prefix / "build"
    target.mkdir(exist_ok=True)
    suffix = ".exe" if os.name == "nt" else ""
    env = dict(os.environ, ZIG_GLOBAL_CACHE_DIR=str(target / "zig-global"), ZIG_LOCAL_CACHE_DIR=str(target / "zig-cache"))
    flags = ["-O2", "-Wall", "-Wextra", "-Wpedantic"]
    subprocess.run(cc + flags + [str(prefix / "native" / "bench.c"), "-o", str(target / ("g3bench-native" + suffix))]
                   + ([] if os.name == "nt" else ["-lm"]), check=True, env=env)
    if platform.system() == "Linux" and shutil.which("pkg-config"):
        packages = subprocess.run(["pkg-config", "--cflags", "--libs", "sdl2", "glesv2"], capture_output=True, text=True)
        if packages.returncode == 0:
            subprocess.run(cc + flags + [str(prefix / "native" / "gpu.c"), "-o", str(target / "g3bench-gpu")]
                           + shlex.split(packages.stdout) + ["-lm"], check=True, env=env)
        else:
            print("SDL2/GLES2 build dependencies unavailable; native GPU test will report UNAVAILABLE.")


def write_launcher(prefix):
    launcher = prefix / "launch.py"
    launcher.write_text("import sys\nfrom pathlib import Path\nsys.path.insert(0,str(Path(__file__).resolve().parent))\n"
                        "from g3bench.__main__ import main\nif len(sys.argv)==1: sys.argv.append('ui')\nsys.exit(main())\n", encoding="utf-8")
    if os.name == "nt":
        # PowerShell invocation avoids cmd.exe metacharacter expansion in paths.
        quote = lambda value: "'" + str(value).replace("'", "''") + "'"
        script = "& " + quote(sys.executable) + " " + quote(launcher) + " @args\n"
        (prefix / "g3bench.ps1").write_text(script, encoding="utf-8")
        return prefix / "g3bench.ps1"
    bindir = Path.home() / ".local" / "bin"
    bindir.mkdir(parents=True, exist_ok=True)
    entry = bindir / "g3bench"
    # Refuse to replace an unrelated command.
    if entry.exists() and "GAM3T3CH launcher" not in entry.read_text(errors="replace"):
        print("Existing ~/.local/bin/g3bench retained; launch with: " + shlex.quote(sys.executable) + " " + shlex.quote(str(launcher)))
        return launcher
    entry.write_text("#!/bin/sh\n# GAM3T3CH launcher\nexec " + shlex.quote(sys.executable) + " " + shlex.quote(str(launcher)) + ' "$@"\n', encoding="utf-8")
    entry.chmod(0o755)
    if platform.system() == "Linux":
        desktop = Path.home() / ".local" / "share" / "applications"
        desktop.mkdir(parents=True, exist_ok=True)
        # Desktop Entry escaping is different from shell escaping.
        escaped = str(entry).replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$").replace("%", "%%")
        (desktop / "g3bench.desktop").write_text('[Desktop Entry]\nType=Application\nName=GAM3T3CH 3D Benchmark\nExec="' + escaped + '" ui\nIcon=' + str(prefix / "showcase" / "brand" / "g3-mark.svg") + '\nTerminal=true\nCategories=System;Utility;\n', encoding="utf-8")
    return entry


def install(args):
    if sys.version_info < (3, 9):
        raise RuntimeError("Python 3.9 or newer is required")
    system = platform.system()
    if system not in {"Linux", "Darwin", "Windows"}:
        raise RuntimeError("Installer targets Linux, Windows and macOS; this operating system is unsupported")
    prefix = Path(args.prefix).expanduser().resolve()
    if prefix.exists():
        marker = prefix / ".gam3t3ch-install.json"
        if marker.is_file() and (prefix / "launch.py").is_file():
            print("Existing installation retained. Launching without updating its files.")
            if not args.no_launch:
                return subprocess.call([sys.executable, str(prefix / "launch.py"), "ui"])
            return 0
        raise ValueError("Destination already exists; choose a new --prefix or update the existing checkout manually")
    with tempfile.TemporaryDirectory() as folder:
        if args.source:
            source = Path(args.source).resolve(strict=True)
        else:
            archive = Path(folder) / "source.zip"
            download("https://codeload.github.com/" + REPOSITORY + "/zip/refs/heads/main", archive)
            extracted = Path(folder) / "source"
            extract(archive, extracted)
            source = next(extracted.iterdir())
        if not (source / "native" / "bench.c").is_file() or not (source / "g3bench" / "__main__.py").is_file():
            raise ValueError("Source archive is not a GAM3T3CH checkout")
        # Limit copies to shipped source: no build outputs, results or local metadata.
        prefix.mkdir(parents=True)
        for name in ("g3bench", "native", "showcase", "docs"):
            shutil.copytree(source / name, prefix / name, ignore=shutil.ignore_patterns("__pycache__", ".godot", "*.pyc", "*.gd.uid"))
        for name in ("README.md", "LICENSE", "VERSION", "CMakeLists.txt", "installer.py"):
            shutil.copy2(source / name, prefix / name)
    build(prefix, args.compiler)
    engine = None
    if not args.skip_godot:
        try:
            engine = install_godot(prefix)
        except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
            print("Optional Godot download failed: " + str(exc) + ". CPU/memory remain available; use --godot PATH later.")
    launcher = write_launcher(prefix)
    marker = {"repository": REPOSITORY, "engine": engine, "python": sys.executable, "prefix": str(prefix), "shortcuts": []}
    (prefix / ".gam3t3ch-install.json").write_text(json.dumps(marker), encoding="utf-8")
    sys.path.insert(0, str(prefix))
    from g3bench.integration import install_shortcuts
    try:
        shortcuts = install_shortcuts(prefix, [sys.executable, str(prefix / "launch.py")])
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print("Desktop integration could not complete: " + str(exc) + ". Retry the installed command with shortcuts later.")
        shortcuts = []
    if launcher.is_file():
        shortcuts.append({"path": str(launcher.resolve()), "sha256": hashlib.sha256(launcher.read_bytes()).hexdigest()})
    marker["shortcuts"] = shortcuts
    (prefix / ".gam3t3ch-install.json").write_text(json.dumps(marker), encoding="utf-8")
    print("Installed GAM3T3CH at " + str(prefix) + "\nLauncher: " + str(launcher))
    print("Tests measure this machine. Other units need their own installation. No remote pairing is performed.")
    if not args.no_launch:
        os.chdir(prefix)
        return subprocess.call([sys.executable, str(prefix / "launch.py"), "ui", "--output", str(prefix / "results")])
    return 0


def main():
    parser = argparse.ArgumentParser(description="Install and launch GAM3T3CH 3D Benchmark locally")
    default = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "GAM3T3CH" / "sbc-bench" if os.name == "nt" else Path.home() / ".local" / "share" / "gam3t3ch-sbc-bench"
    parser.add_argument("--prefix", default=str(default))
    parser.add_argument("--no-launch", action="store_true")
    parser.add_argument("--skip-godot", action="store_true")
    parser.add_argument("--source", help="Local source checkout, primarily for offline builds/CI")
    parser.add_argument("--compiler", help="Existing C compiler or Zig executable")
    args = parser.parse_args()
    try:
        return install(args)
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
        print("Installation failed: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
