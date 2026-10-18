"""Build on the target OS/architecture; never cross-label a binary bundle."""
import argparse
import json
import hashlib
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import installer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--compiler")
    parser.add_argument("--iscc", help="Inno Setup compiler for an optional Windows setup.exe")
    args = parser.parse_args()
    version = (ROOT / "VERSION").read_text().strip()
    system, architecture = platform.system(), platform.machine().lower()
    if system not in {"Windows", "Linux"}:
        raise RuntimeError("Standalone builds currently target Windows and Linux. macOS uses the experimental source installer.")
    architecture = {"amd64": "x86_64", "arm64": "aarch64"}.get(architecture, architecture)
    label = {"Windows": "windows", "Linux": "linux", "Darwin": "macos"}[system] + "-" + architecture
    stage = ROOT / "build" / ("bundle-" + label)
    if stage.exists():
        raise RuntimeError("Bundle staging directory exists; choose a fresh checkout/build workspace")
    stage.mkdir(parents=True)
    for folder in ("g3bench", "native", "showcase", "docs"):
        shutil.copytree(ROOT / folder, stage / folder, ignore=shutil.ignore_patterns("__pycache__", ".godot", "*.pyc", "*.gd.uid"))
    for name in ("VERSION", "LICENSE", "README.md"):
        shutil.copy2(ROOT / name, stage / name)
    installer.build(stage, args.compiler)
    bundled_engine = installer.install_godot(stage)
    if not bundled_engine:
        raise RuntimeError("No bundled Godot build for this platform; use the portable source installer")
    licenses = stage / "licenses"
    licenses.mkdir()
    for remote, name in (("LICENSE.txt", "Godot-LICENSE.txt"), ("COPYRIGHT.txt", "Godot-COPYRIGHT.txt")):
        installer.download("https://raw.githubusercontent.com/godotengine/godot/4.4.1-stable/" + remote, licenses / name)
    python_license = next((p for p in (Path(sys.base_prefix) / "LICENSE.txt", Path(sys.base_prefix) / "LICENSE", Path(sys.base_prefix) / "lib" / ("python" + platform.python_version_tuple()[0] + "." + platform.python_version_tuple()[1]) / "LICENSE.txt") if p.is_file()), None)
    if python_license:
        shutil.copy2(python_license, licenses / "Python-LICENSE.txt")
    else:
        installer.download("https://raw.githubusercontent.com/python/cpython/v" + platform.python_version() + "/LICENSE", licenses / "Python-LICENSE.txt")
    shutil.copy2(ROOT / "LICENSE", licenses / "GAM3T3CH-LICENSE.txt")
    installer.download("https://raw.githubusercontent.com/pyinstaller/pyinstaller/v6.16.0/COPYING.txt", licenses / "PyInstaller-COPYING.txt")
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--name", "GAM3T3CH",
               "--paths", str(ROOT), "--distpath", str(ROOT / "build" / "dist" / label),
               "--workpath", str(stage / "pyinstaller"), "--specpath", str(stage)]
    if system == "Windows":
        command.append("--windowed")
    for source, destination in ((stage / "showcase", "showcase"),
                                (stage / "licenses", "licenses"), (stage / "docs", "docs"),
                                (stage / "README.md", "."), (stage / "VERSION", ".")):
        command += ["--add-data", str(source) + os.pathsep + destination]
    # Mark the engine as a binary, so Unix execute permission and its linked
    # libraries survive collection instead of treating it as a data asset.
    command += ["--add-binary", str(bundled_engine) + os.pathsep + "runtime/godot"]
    for name in ("report.html", "dashboard.html", "share.js"):
        command += ["--add-data", str(stage / "g3bench" / name) + os.pathsep + "g3bench"]
    for path in (stage / "build").iterdir():
        if path.name.startswith("g3bench-") and path.is_file():
            command += ["--add-binary", str(path) + os.pathsep + "build"]
    command.append(str(ROOT / "distribution" / "entry.py"))
    subprocess.run(command, check=True)
    bundle = ROOT / "build" / "dist" / label / "GAM3T3CH"
    shutil.copy2(ROOT / "README.md", bundle / "README.md")
    (bundle / "BUNDLE.json").write_text(json.dumps({"suite": version, "platform": label, "godot": "4.4.1-stable", "python": platform.python_version()}, indent=2))
    output = ROOT / "build" / "packages"
    output.mkdir(exist_ok=True)
    artifact = output / ("GAM3T3CH-" + version + "-" + label)
    if system == "Windows":
        shutil.make_archive(str(artifact), "zip", bundle.parent, bundle.name)
        if args.iscc:
            subprocess.run([args.iscc, "/DBundleDir=" + str(bundle), "/DAppVersion=" + version,
                            "/DOutputDir=" + str(output), str(ROOT / "distribution" / "windows.iss")], check=True)
    else:
        # Tar preserves PyInstaller's library symlinks and execute permissions.
        with tarfile.open(str(artifact) + ".tar.gz", "w:gz", dereference=False) as archive:
            archive.add(bundle, arcname="GAM3T3CH")
            archive.add(ROOT / "distribution" / "linux-install.sh", arcname="install.sh")
    lines = []
    for file in sorted(output.glob("GAM3T3CH-" + version + "-" + label + "*")):
        if file.is_file():
            digest = hashlib.sha256()
            with file.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
            lines.append(digest.hexdigest() + "  " + file.name)
    (output / ("SHA256SUMS-" + label + ".txt")).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Standalone packages: " + str(output))


if __name__ == "__main__":
    main()
