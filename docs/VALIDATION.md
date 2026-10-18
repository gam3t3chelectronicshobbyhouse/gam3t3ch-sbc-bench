# Validation — 2026-10-18

## Suite 0.4.0

- Full Windows regression with `G3BENCH_RUN_SOCKET_TESTS=1`: 47 tests,
  46 passed and one Linux-only real-fio integration test skipped. Includes real
  loopback upload/listener shutdown, authentication/limits, frozen command
  construction, sequential full-checkup failure isolation, one shared sampler,
  archive safety and result-preserving uninstall/shortcut ownership checks.
- Python compilation, PowerShell parser, JavaScript and shell syntax passed.
- Windows standalone ZIP and Inno Setup executable built with PyInstaller
  6.16.0, native workers and checksum-verified official Godot 4.4.1.
- A real frozen full checkup completed in approximately 50 seconds. CPU/memory
  passed and all three Godot stages passed. Godot recorded fullscreen mode 3,
  1920x1080 presentation and fixed 1280x720 internal rendering, then exited.
  Native GLES and Linux fio/sensors were explicitly unavailable on this Windows
  host, so the combined run was correctly partial, with no invented readings.
- Browser stats PNG export produced a real 1600-pixel-wide image, inspected for
  raw measurements, availability reasons, versions and methodology references.
  It omits hostname/IP/mount paths and notes by default; export makes no upload.
- Windows installer cycle passed: setup created desktop/app/uninstall menu
  shortcuts, its installed native worker produced a result, uninstall removed
  app files/shortcuts and retained external results, then the app was installed
  into the default per-user location with the desktop/menu entries verified.
- The installed Windows dashboard's Full checkup completed in 49.676 seconds
  with 55 continuous samples. CPU/memory/Godot passed, Windows-inapplicable
  GLES/fio were unavailable/unsupported, and Godot exited. The waiting dashboard
  used 0.00 additional CPU seconds over a five-second idle observation.
- GitHub Linux baseline run 39166197822 passed all 47 tests, including real fio,
  and Godot headless initialization. Package run 39166198010 passed Windows,
  Linux x86-64 and native Linux ARM64 frozen-worker/bundled-engine checks.
  Its seven package/checksum assets are published as the v0.4.0 prerelease.
- Real local development results remain ignored under build/. They are not Pi
  benchmark evidence or calibrated reference scores.

Remaining qualification: additional clean target-system checks,
physical LAN transfer between machines, and actual Pi/removable-drive tests.
Focus/topmost are requests subject to desktop policy. Headless engine startup
is not a substitute for graphical validation on each Pi. ARMv6 remains
experimental; no qualified standalone macOS package is supplied.

An earlier packaging-tool approval failure due to account usage limits cleared;
tools and real packaging/full-run checks subsequently completed normally.

## Suite 0.3.0 storage and tuning

Added Linux physical-backed filesystem discovery, explicit file-write selection,
four separate fio workloads per drive, drive-level failures/cleanup and unscored
JSON/CSV/report output. Added run labels/notes, governor/swap/zram snapshots,
active swap/zram/memory-pressure samples and offline comparison bars/charts.
Native CPU/memory rebuilt for 0.3.0; operation counts remain unchanged.

Local Windows regression run: 32 tests, 31 passed, one Linux real-fio test
skipped (6.783 seconds). Includes discovery with SD/eMMC/USB/NVMe, read-only and
unmounted drives, bind-mount deduplication, file isolation, free-space headroom,
timeout cleanup, write acknowledgement, missing fio, removed-drive isolation
and tuning snapshots. Loopback tests run outside the development sandbox.
The Windows storage CLI saved an explicit UNSUPPORTED report without drive I/O.
Installer shell syntax and Python compilation passed. The Linux CI job installs
fio and runs a real 16 MiB direct-I/O test of all four workloads with cleanup.
Actual Pi/removable-drive validation and repeated-run characterization remain
pending. Synthetic report fixtures are kept only under ignored build/.

## Suite 0.2.1 branding

Unified the dashboard, reports, desktop entry and optional scene under
GAM3T3CH 3D Benchmark. A shared SVG G3 mark is embedded in standalone reports
and the dashboard, used for browser/desktop icons and loaded directly by the
Godot window without requiring an asset-import step. Added a branded HUD,
signature and four fixed 3D wordmark signs. No idle animation or background
renderer was added. The native workloads/constants remain unchanged.

The additional scene text geometry advances its identity to
`reactor-showcase-0.2`. The Windows Godot scene initialized headlessly and
completed a real graphical run; the dashboard, icon, HUD and scene wordmarks
were visually checked. All 22 existing regression/lifecycle tests passed
(6.618 seconds), and the shared SVG parsed successfully as XML. Physical Pi
graphics/idle validation remains pending.

## Suite 0.2.0 dashboard and optional Godot showcase

- Added an on-demand loopback dashboard with a static preview and no idle
  renderer, telemetry thread, polling or animation loop. Measurements pause the
  dashboard; results and graphs render afterward.
- Added Reactor Lab as an explicitly launched Godot 4 Compatibility scene with
  three fixed stages, separate FPS/1% lows, finite lifetime and no baseline score.
- Rebuilt native tools for suite 0.2.0. CPU/memory operation counts and constants
  are unchanged; report activity changed, so suite comparison groups are separate.
- All 22 Python/native/lifecycle tests passed on Windows in 6.645 seconds.
  Loopback integration tests were run outside the development sandbox, which
  blocks Python's internal loopback socket-pair connection. Tests include idle
  startup, host/origin/token authorization, shutdown, cancellation, single-job
  enforcement, missing engines, unscored results and child-process waiting.
- Real `quick --headless` passed CPU/memory with GPU SKIPPED and null overall.
- Godot 4.7.2 initialized the source scene in headless smoke mode, then rendered
  full three-stage runs with the development NVIDIA GPU at 1280×720. The scene
  and final HUD were visually inspected. Godot exited after the fixed run;
  the existing project-manager window was left intact. Pi graphics validation
  remains pending. The dashboard Stop path was also exercised against a live
  renderer and records cancellation without using incomplete scores.
- Idle dashboard process measurement over 10.039 seconds: 0.000 additional CPU
  seconds, approximately 29.9 MiB working set. This excludes browser use and is
  bounded by CPU-time resolution, not a claim of zero whole-system load.
- Linux CI now also initializes the scene headlessly with pinned Godot 4.4.1;
  that check does not claim GPU performance or physical Pi support.

See IDLE_AND_SHOWCASE.md for methodology, remaining limitations and lifecycle.

## Board compatibility update — 2026-10-18

Added Pi model/profile detection, per-test status/reasons, memory headroom checks,
`g3bench check` and an unscored hidden GLES2 capability probe. Scored workloads
and normalization are unchanged. JSON schema is now 2. See COMPATIBILITY.md.

`python -m unittest discover -s tests -v` passed all 16 tests (6.529 seconds),
including Pi 1/Zero/Zero 2/CM5/model detection, CPU-info fallback, insufficient
capacity versus memory pressure, missing/incompatible tools, GPU capability
results and a failed-CPU/unsupported-GPU run preserving a valid memory result.
`python -m g3bench check --headless` reported CPU and memory READY and GPU SKIPPED.
A real Windows `quick --headless` run recorded CPU PASSED, memory PASSED, GPU
SKIPPED and null overall in `results/20261018T153406-92b519/`. The report's new
compatibility table was verified in the browser. Pi 1 remains experimental and
has not been tested on physical hardware.

Official SDL2 2.30.9 headers and Khronos GLES2/KHR headers were downloaded into
the ignored build folder for compile checks. The updated GPU source compiled
without warnings to ARM64 and ARMv6 objects; the native CPU/memory source also
compiled to an ARMv6 object. For Zig, the ARMv6 target used
`-target arm-linux-musleabihf -mcpu=arm1176jzf_s`; `-march=armv6` was rejected by
this compiler and replaced with its supported CPU identifier. These are object
compilation checks, not linking or runtime validation. No SDL/GLES system
packages were installed. `bash -n install.sh` passed after adding `armv6l`.

The initial baseline validation below is retained as the historical build log.

## Files created

- `native/bench.c`, `native/gpu.c`, `native/suite.h`: fixed native workloads and version identity.
- `g3bench/__init__.py`, `__main__.py`, `system.py`, `scoring.py`: CLI, orchestration, hardware/telemetry, score rules.
- `g3bench/report.py`, `report.html`: offline results screen, graph rendering and local result comparison.
- `CMakeLists.txt`, `install.sh`, `VERSION`: source builds and Debian-family installer skeleton.
- `tests/test_baseline.py`, `.github/workflows/build.yml`: local regression checks and Linux build workflow.
- `README.md`, `CHANGELOG.md`, `LICENSE`, `docs/*.md`: installation, methodology, scoring, support and validation.
- `.gitignore`, `.gitattributes`: exclude local results/builds and preserve shell-script line endings.

Build artifacts, downloaded compiler and actual machine results are ignored.
At the time of initial local validation, no public repository had been created.
Publication uses `gam3t3chelectronicshobbyhouse/gam3t3ch-sbc-bench`; the installer
and README use that owner. The later board-testing checklist covers installation
and qualification on the available Pi collection.

## Dependencies

Runtime: Python 3.9+ standard library and the compiled native tool. Optional GPU:
SDL2 and GLES 2/Mesa with a working display. Build: C99 compiler, CMake 3.16+,
pkg-config and a build tool. Debian packages are listed in README. fio and iperf3
are not dependencies of this milestone.

The development machine is Windows x86-64 with Python 3.13 and CMake 3.30.
It has no host C compiler/build tool on PATH, no installed WSL environment and no
SDL2/GLES 2 development packages. For local validation only, `ziglang 0.16.0`
was downloaded from PyPI under the ignored `build/toolchain` directory. Its C
compiler identifies as Clang 21.1.0. This is not a project runtime dependency.

## Commands and results

PowerShell, from the project root:

```powershell
python -m pip install --no-cache-dir --target build/toolchain ziglang
$env:ZIG_GLOBAL_CACHE_DIR = "$PWD\build\zig-global-native"
$env:ZIG_LOCAL_CACHE_DIR = "$PWD\build\zig-cache-native"
& .\build\toolchain\ziglang\zig.exe cc -O2 -Wall -Wextra -Wpedantic native/bench.c -o build/g3bench-native.exe
& .\build\toolchain\ziglang\zig.exe cc -target arm-linux-musleabihf -O2 -Wall -Wextra -Wpedantic -c native/bench.c -o build/bench-armv7.o
& .\build\toolchain\ziglang\zig.exe cc -target aarch64-linux-musl -O2 -Wall -Wextra -Wpedantic -c native/bench.c -o build/bench-aarch64.o
python -m unittest discover -s tests -v
python -m g3bench detect
python -m g3bench quick --headless
python -m compileall -q g3bench tests
& 'C:\Program Files\Git\bin\bash.exe' -n install.sh
git diff --check
```

The final native Windows compile and both ARM object compilations exited 0,
with no compiler warnings. ARM object builds check source compilation only;
they do not establish linking, runtime correctness or board support. CMake
configuration on this Windows host failed because NMake/host C compiler were
absent; the Linux CMake/GPU build workflow is prepared but has not run here.

Final unit/integration output:

```text
Ran 8 tests in 6.441s
OK
```

Coverage includes repeated native workload checksums/rates, geometric scoring,
missing and compatibility scores, sysfs units and throttle bits, missing
sensors, HTML script-injection escaping, JSON persistence and idle-load
cancellation before workloads. The busy-system warning printed during tests is
from the deliberate simulated load check, not a measurement of this host.

Final measured development run:

```text
[3.3s] CPU
[5.7s] MEMORY
[6.4s] GPU
status: partial
CPU: 4375.43
Memory: 5482.68
GPU / Storage / Network / Overall: null
classification: DEVELOPMENT
GPU: skipped, headless requested
```

JSON, CSV and standalone HTML were generated in
`results/20261018T152817-225ac1/`. These are synthetic-reference development
points, not Raspberry Pi scores. Missing Linux sensors remain null. The
generated report was opened in the app browser and its score cards, missing
sensor states, hardware details, comparison table and measurements were
verified. A screenshot review confirmed the dark layout at desktop width.
Installer syntax and Python bytecode compilation passed. The installer was not
executed, and no packages were installed system-wide.

## Remaining validation / next milestone

Run the same tagged source on Pi 2 ARMv7 and Pi 5/CM5 AArch64. Verify GLES 2
compilation/rendering, actual resolution, swap behavior, real thermal sensors,
throttling bits, cooling data and full installer execution. Measure repeated-run
variance with consistent cooling/governor/ambient conditions before calling any
results official. Then add explicit opt-in fio storage tests with write warnings
and a separately versioned score methodology. Standard/full/endurance modes,
network, manual power entry and enhanced 3D graphics remain deferred.
