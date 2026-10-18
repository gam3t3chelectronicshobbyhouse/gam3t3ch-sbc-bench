"""Remove a validated user installation; preserve results by default."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from .integration import app_prefix, REPOSITORY


def owned_shortcut(path, prefix):
    path = path.resolve()
    if path == prefix / "g3bench.ps1":
        return True
    if path == Path.home() / ".local" / "bin" / "g3bench":
        return True
    names = {"g3bench.desktop", "g3bench-uninstall.desktop", "GAM3T3CH 3D Benchmark.desktop",
             "GAM3T3CH 3D Benchmark.lnk", "Uninstall GAM3T3CH 3D Benchmark.lnk"}
    if path.name not in names:
        return False
    roots = {Path.home() / ".local" / "share" / "applications", Path.home() / "Desktop"}
    roots.update(Path.home().glob("OneDrive*/Desktop"))
    if os.environ.get("APPDATA"):
        roots.add(Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "GAM3T3CH 3D Benchmark")
    return path.parent in {root.resolve() for root in roots}


def validate_prefix(prefix):
    prefix = Path(prefix).resolve()
    forbidden = {Path(prefix.anchor), Path.home().resolve(), Path(sys.base_prefix).resolve()}
    if prefix in forbidden or prefix in Path.home().resolve().parents or (prefix / ".git").exists():
        raise ValueError("Refusing to uninstall a root, home, Python installation or Git checkout")
    marker = prefix / ".gam3t3ch-install.json"
    if not marker.is_file():
        raise ValueError("No GAM3T3CH installation manifest found. Use the package uninstaller or remove a portable folder manually.")
    data = json.loads(marker.read_text(encoding="utf-8"))
    if data.get("repository") != REPOSITORY or (data.get("prefix") and Path(data["prefix"]).resolve() != prefix):
        raise ValueError("Installation manifest does not match this directory")
    if not (prefix / "launch.py").is_file() and not (prefix / "BUNDLE.json").is_file():
        raise ValueError("Directory does not contain the expected application")
    return prefix, data


def remove_installation(prefix):
    prefix, manifest = validate_prefix(prefix)
    backup = None
    results = prefix / "results"
    if results.exists():
        if results.is_symlink() or results.resolve().parent != prefix:
            raise ValueError("Refusing to move a linked results directory")
        backup = Path.home() / "GAM3T3CH-results-backup" / (datetime.datetime.now().strftime("%Y%m%dT%H%M%S") + "-" + os.urandom(3).hex())
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(results), str(backup))
    for record in manifest.get("shortcuts", []):
        path = Path(record.get("path", ""))
        if owned_shortcut(path, prefix) and path.is_file() and not path.is_symlink() and hashlib.sha256(path.read_bytes()).hexdigest() == record.get("sha256"):
            path.unlink()
            if path.parent.name == "GAM3T3CH 3D Benchmark":
                try:
                    path.parent.rmdir()
                except OSError:
                    pass
    # validate_prefix resolved this explicitly named installation and rejected
    # dangerous ancestors before this single recursive removal.
    shutil.rmtree(prefix)
    return backup


def run_uninstall(args):
    prefix = app_prefix()
    if getattr(sys, "frozen", False) and os.name == "nt":
        uninstaller = prefix / "unins000.exe"
        if uninstaller.is_file():
            subprocess.Popen([str(uninstaller)])
            return 0
        raise ValueError("Portable Windows bundle: close the app, back up results, then delete only its extracted folder.")
    prefix, _ = validate_prefix(prefix)
    print("Close all GAM3T3CH tests/dashboards before continuing.\nRemove application: " + str(prefix))
    print("Saved results outside this application are retained. Installation-local results will be moved to ~/GAM3T3CH-results-backup.")
    if not args.yes and input("Uninstall GAM3T3CH? [y/N] ").strip().lower() not in {"y", "yes"}:
        print("Uninstall cancelled.")
        return 0
    backup = remove_installation(prefix)
    print("GAM3T3CH uninstalled." + (" Results retained at " + str(backup) if backup else " External result folders were retained."))
    return 0
