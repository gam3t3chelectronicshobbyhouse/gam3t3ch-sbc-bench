# Standalone package builds

Status: Windows 0.4.0 standalone ZIP and Inno Setup executable have been built
locally with verified official Godot 4.4.1 included. A real frozen full checkup
completed CPU/memory and all three fullscreen Godot stages. Linux architecture
builds and physical Pi qualification are tracked separately in docs/VALIDATION.md.

Build on each target OS/CPU architecture. Python 3.9+ and a native C compiler
are build dependencies, not requirements for the resulting standalone app.
Install `pyinstaller==6.16.0` into a build virtual environment. Windows can use
the pinned `ziglang==0.16.0` compiler; supply its zig.exe via `--compiler`.

```sh
python3 -m venv build/package-venv
build/package-venv/bin/pip install pyinstaller==6.16.0
build/package-venv/bin/python distribution/build_bundle.py
```

Windows equivalent uses `build/package-venv/Scripts/python.exe`, then:

```powershell
python distribution/build_bundle.py --compiler C:\path\to\zig.exe --iscc 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
```

The script creates a fresh platform-specific staging folder and refuses to
overwrite one. It copies only application sources/assets, builds native tools,
downloads official Godot 4.4.1 with its SHA-512 checksum manifest, includes
Godot/Python/PyInstaller/application license notices, and creates an onedir
PyInstaller application. One directory avoids repeatedly unpacking a large
engine at launch. No Godot process runs until a test starts.

Windows outputs a portable ZIP and, with an Inno Setup compiler, a user-local
setup executable with uninstall support. Linux outputs a tar.gz preserving
permissions and PyInstaller symlinks. SHA-256 manifests accompany the archives.
Packages do not include real machine results, previews, developer toolchains,
network credentials or the source checkout's build cache.

The workflow uses Debian Bookworm containers for Linux x86-64/ARM64. This avoids
building against a newer host glibc than the intended Pi OS baseline. Native
drivers and a working display stack are still host requirements. fio is not
bundled; install the distribution package for optional direct-I/O storage tests.

Run `.github/workflows/packages.yml` manually or on a reviewed version tag.
Every platform must pass actual frozen CPU/memory worker execution and bundled
Godot headless initialization (`distribution/check_bundle.py`). The Windows
job also needs the Inno Setup compiler on its runner. A tag build creates a
**draft** release only after all package jobs succeed. Verify the installer,
foreground/fullscreen behavior, local inbox and uninstall behavior on clean
machines before publishing that draft. Headless initialization is not a GPU
performance or fullscreen validation.

No signing/notarization certificate is configured. Build identity and SHA-256
checksums are available, but they are not a publisher signature. macOS source
installation remains experimental; no qualified macOS standalone artifact is
included in the current package workflow.
