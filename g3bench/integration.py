"""User-owned launch shortcuts; records hashes for safe uninstall cleanup."""
import base64
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

REPOSITORY = "gam3t3chelectronicshobbyhouse/gam3t3ch-sbc-bench"


def app_prefix():
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent


def command_for(prefix):
    return [sys.executable] if getattr(sys, "frozen", False) else [sys.executable, str(prefix / "launch.py")]


def desktop_quote(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$").replace("%", "%%") + '"'


def install_shortcuts(prefix, command=None):
    prefix = Path(prefix).resolve()
    command = command or command_for(prefix)
    created = []
    if os.name == "nt":
        quote = lambda value: "'" + str(value).replace("'", "''") + "'"
        arguments = subprocess.list2cmdline(command[1:])
        script = "$ErrorActionPreference='Stop';$shell=New-Object -ComObject WScript.Shell;"
        script += "$desktop=[Environment]::GetFolderPath('DesktopDirectory');$menu=Join-Path ([Environment]::GetFolderPath('Programs')) 'GAM3T3CH 3D Benchmark';New-Item -ItemType Directory -Force -Path $menu|Out-Null;$made=@();"
        for folder, name, extra in (("$desktop", "GAM3T3CH 3D Benchmark.lnk", " ui"),
                                    ("$menu", "GAM3T3CH 3D Benchmark.lnk", " ui"),
                                    ("$menu", "Uninstall GAM3T3CH 3D Benchmark.lnk", " uninstall")):
            script += "$path=Join-Path " + folder + " " + quote(name) + ";if(-not(Test-Path -LiteralPath $path)){$link=$shell.CreateShortcut($path);$link.TargetPath=" + quote(command[0]) + ";$link.Arguments=" + quote(arguments + extra) + ";$link.WorkingDirectory=" + quote(prefix) + ";$link.Save();$made+=$path};"
        script += "ConvertTo-Json -InputObject @($made) -Compress"
        encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        result = subprocess.check_output(["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded], text=True)
        paths = json.loads(result.strip() or "[]")
        created = [Path(path) for path in paths]
    else:
        menu = Path.home() / ".local" / "share" / "applications"
        menu.mkdir(parents=True, exist_ok=True)
        executable = " ".join(desktop_quote(part) for part in command)
        icon = Path(__file__).resolve().parent.parent / "showcase" / "brand" / "g3-mark.svg"
        app = '[Desktop Entry]\nType=Application\nName=GAM3T3CH 3D Benchmark\nExec=' + executable + ' ui\nIcon=' + str(icon) + '\nTerminal=true\nCategories=System;Utility;\nActions=Uninstall;\n\n[Desktop Action Uninstall]\nName=Uninstall GAM3T3CH\nExec=' + executable + ' uninstall\n'
        uninstaller = '[Desktop Entry]\nType=Application\nName=Uninstall GAM3T3CH 3D Benchmark\nExec=' + executable + ' uninstall\nTerminal=true\nCategories=System;Utility;\n'
        targets = [(menu / "g3bench.desktop", app), (menu / "g3bench-uninstall.desktop", uninstaller)]
        desktop = Path.home() / "Desktop"
        if platform.system() == "Linux":
            try:
                selected = subprocess.check_output(["xdg-user-dir", "DESKTOP"], text=True, timeout=5).strip()
                if selected:
                    desktop = Path(selected)
            except (OSError, subprocess.SubprocessError):
                pass
        if desktop.is_dir() and desktop.resolve() != Path.home().resolve():
            targets.append((desktop / "GAM3T3CH 3D Benchmark.desktop", app))
        for path, contents in targets:
            if path.exists() and path.name != "g3bench.desktop":
                continue
            if path.exists() and "GAM3T3CH" not in path.read_text(errors="replace"):
                continue
            path.write_text(contents, encoding="utf-8")
            path.chmod(0o755)
            created.append(path)
    return [{"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in created]


def run_shortcuts(args):
    prefix = app_prefix()
    marker = prefix / ".gam3t3ch-install.json"
    data = json.loads(marker.read_text()) if marker.is_file() else {"repository": REPOSITORY}
    if not marker.is_file() and not (prefix / "BUNDLE.json").is_file():
        raise ValueError("Install the source application first, or run this from an extracted standalone bundle")
    data["prefix"] = str(prefix)
    previous = {row["path"]: row for row in data.get("shortcuts", [])}
    previous.update({row["path"]: row for row in install_shortcuts(prefix)})
    data["shortcuts"] = list(previous.values())
    marker.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print("Desktop/menu shortcuts and an uninstall menu entry are ready where supported by this desktop.")
    return 0
