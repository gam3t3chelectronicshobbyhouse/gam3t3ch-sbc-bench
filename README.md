# GAM3T3CH 3D Benchmark

GAM3T3CH SBC Bench is the portable system-testing core of GAM3T3CH 3D Benchmark.
The repository remains `gam3t3ch-sbc-bench` and the command remains `g3bench`.

A repeatable Linux single-board computer benchmark, designed for Raspberry Pi 2,
3, 4, 5 and Compute Module 5, with future ARM Linux boards in mind.

**0.3.0 is a development suite. No Pi board is hardware-validated yet.**
It contains hardware detection, temperature/cooling telemetry, native CPU and
memory workloads, an optional SDL2/OpenGL ES 2 benchmark, JSON/CSV output and a
standalone dark results screen, an on-demand dashboard and an optional Godot 4
reactor showcase. The CLI works without the graphical interface.
Per-drive storage tests use optional fio on Linux. Network, endurance, controlled
memory-pressure testing and manual power entry remain later milestones.

## Running on a PC or several Raspberry Pis

The dashboard runs on the machine where you start `g3bench ui`. Its address is
`http://127.0.0.1:PORT`; use the port printed in the terminal. Localhost always
means the current machine. Benchmarks measure that machine's CPU, memory,
graphics and selected drives.

| Use case | Current support |
| --- | --- |
| Benchmark a Raspberry Pi or other Linux SBC | Install and run the suite on that board; available tests depend on its capabilities. |
| Benchmark a Linux PC | Build/run on the PC using the same Linux instructions. The installer supports Debian-family distributions, including x86-64 PCs. Hardware qualification is still pending. |
| Use a Windows PC | Dashboard/report development, locally compiled native CPU/memory tests and the optional compatible Godot showcase are supported for development. Linux telemetry and fio drive tests are unavailable; Windows runs are excluded from baseline comparisons. The shell installer is Linux-only. |
| View results on a PC | Open a saved standalone `report.html` in a current browser on Windows, Linux or macOS. Viewing reports needs no benchmark installation, Python or running dashboard. macOS benchmark execution is not currently validated. |
| Test several Pis | Install the suite on each Pi and run its tests there. Copy the saved results to one PC for comparison. |

For example, run the same suite version on your Pi 3, Pi 4 and Pi 5. Preserve
each run's `result.json` and `report.html`, copy them into separate folders on
your PC, open one report, and use **Compare saved runs** to load the JSON files.
Storage runs also populate the drive comparison bars. Match workloads and
settings when comparing performance; the report keeps incompatible groups
separate. No files are uploaded by this workflow.

A single PC installation currently does not discover, remotely start tests on,
or automatically collect results from other Pis. Central control would require
a future remote-runner feature. The dashboard currently binds to loopback only
and is not a LAN server.

## Build and run

On Debian / Raspberry Pi OS:

```sh
sudo apt-get update
sudo apt-get install build-essential cmake pkg-config python3 libsdl2-dev libgles2-mesa-dev
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
python3 -m g3bench detect
python3 -m g3bench check
python3 -m g3bench ui
python3 -m g3bench quick --open
```

Python 3.9+ and CMake 3.16+ are required. Python uses only its standard library.
The native benchmarks use C99. No Vulkan, Godot, Python packages or internet
service is required for the portable baseline. A working SDL2 GLES 2 context and
display are needed for its GPU test. Godot 4 is optional and is only needed for
the separate, unscored showcase.

## Dashboard and optional 3D showcase

```sh
g3bench ui
g3bench ui --godot /path/to/godot4
g3bench showcase --godot /path/to/godot4 --open
```

Use `python3 -m g3bench` instead of `g3bench` when running from a source checkout.
The engine can also be selected with `G3BENCH_GODOT`, or found as `godot4`/`godot`
on PATH. Godot is not downloaded or installed by the benchmark installer.

The dashboard is local to `127.0.0.1`. It uses a static preview, takes one
hardware snapshot, and sleeps waiting for user requests. No renderer, telemetry
loop, automatic benchmark or browser polling runs while idle. A single completion
notification waits for a started benchmark to exit. During measurements the
dashboard pauses; telemetry is collected in memory and graphs render afterward.
Click **Exit dashboard** or press Ctrl+C in its terminal to stop the local server.
Closing only the browser tab leaves the small sleeping server running.

Reactor Lab contains three ten-second scenes, each with a two-second warmup:
reactor geometry, 192 moving satellites, then a 1,536-instance particle field.
It uses a fixed camera path, 1280×720, Compatibility rendering and 2× MSAA.
Scene FPS and 1% lows are recorded separately with engine/renderer metadata.
The engine exits after completion; Escape/window-close and the dashboard Stop
control stop the scene. See [showcase and idle policy](docs/IDLE_AND_SHOWCASE.md).

```sh
python3 -m g3bench quick --headless
python3 -m g3bench quick --compat        # 640×360; separate comparison class
python3 -m g3bench quick --fullscreen
python3 -m g3bench quick --as-configured # accept background load explicitly
python3 -m g3bench report results/RUN_ID/result.json
python3 -m unittest discover -s tests -v
```

The idle check samples CPU usage for three seconds. More than 10% utilization
stops the run and prints the busiest observed processes. No services are stopped.
`--as-configured` accepts this condition and labels the run. Unsupported sensors
are recorded as null, including on a Windows development machine.

Each run gets its own directory under `results/` containing `result.json` and
`report.html`. Baseline runs add `summary.csv`; storage runs add `storage.csv`. Open the report in a browser after testing;
`--open` opens it only when the run finishes. Telemetry remains active during
tests, but HTML is not rewritten every second and reports never auto-refresh.
Completed reports show telemetry graphs offline and accept saved JSON files for
comparison. Files remain local; the report loads no external assets.

Headless/incomplete runs keep their measured subsystem scores but do not receive
an overall score. Missing GPU support never prevents CPU and memory tests.
Board detection recognizes Pi generations, Compute Modules and Zero variants.
Pi 1 / original Zero / ARMv6 support is experimental. Tests are scheduled by
actual capabilities, with PASSED, FAILED, UNSUPPORTED, UNAVAILABLE or SKIPPED
statuses and reasons. Slow results do not fail merely for being slow. See
[board compatibility](docs/COMPATIBILITY.md).

## Connected drives and tuning experiments

```sh
g3bench drives
g3bench storage --all --allow-writes --label 'Stock baseline' --open
g3bench storage --target /media/user/ssd/bench --allow-writes --open
```

The dashboard has drive selection and an explicit temporary-write acknowledgement.
Automatic selection tests one writable filesystem per physical drive, excluding
boot/EFI partitions. Unmounted/read-only drives are listed with reasons. Each
drive gets sequential read/write and 4 KiB random read/write tests using a private
temporary file (default 1 GiB), direct I/O, one job and queue depth one. File size
and timeout are configurable. Tests never format drives or write raw devices.
Storage stays unscored and separate from compute scores.

Post-run reports show MB/s, IOPS, mean/p99 latency, drive comparison bars and
configuration deltas when settings match. Temperature/load charts include axes
and stage tooltips, plus swap/zram use and memory pressure where exposed.
Run labels/notes and automatic governor/swap/zram snapshots support later tuning
experiments. The suite never changes clocks or memory configuration. Zram
benefits need memory-pressure workloads that are not implemented yet.
See [storage methodology and tuning](docs/STORAGE_AND_TUNING.md).

## One-line installer

Public source repository: `gam3t3chelectronicshobbyhouse/gam3t3ch-sbc-bench`.

```sh
curl -fsSL https://raw.githubusercontent.com/gam3t3chelectronicshobbyhouse/gam3t3ch-sbc-bench/main/install.sh | bash
g3bench ui
```

The installer supports Debian-family Linux, builds in
`~/.local/share/gam3t3ch-sbc-bench`, installs a `~/.local/bin/g3bench` launcher,
and creates a desktop entry when a desktop is detected. Add `~/.local/bin` to
PATH if needed. It uses sudo only for distribution packages, never runs the
benchmark as root, and refuses to overwrite an existing installation.
Optional graphics packages may fail without blocking the headless build.
The installer has passed syntax checks; execution on Raspberry Pi hardware is
pending. Follow the [board test checklist](docs/BOARD_TESTING.md) for first runs.

See [methodology](docs/METHODOLOGY.md), [scoring](docs/SCORING.md),
[supported systems and limitations](docs/SUPPORT.md), and [validation](docs/VALIDATION.md).

## Public results and Element14 RoadTest

Keep cooling, power supply, OS image, compiler, governor, peripherals and ambient
temperature consistent and document changes. Preserve the original JSON.
Results deliberately include hostname and system metadata: review these before
publishing a report. No real machine results or personal information belong in
the source repository. This project is independent of Element14.

## License

MIT; see [LICENSE](LICENSE).
