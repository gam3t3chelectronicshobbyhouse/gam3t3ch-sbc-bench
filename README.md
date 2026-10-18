# GAM3T3CH SBC Bench

A repeatable Linux single-board computer benchmark, designed for Raspberry Pi 2,
3, 4, 5 and Compute Module 5, with future ARM Linux boards in mind.

**0.1.0 is the first development baseline. No board is hardware-validated yet.**
It contains hardware detection, temperature/cooling telemetry, native CPU and
memory workloads, an optional SDL2/OpenGL ES 2 benchmark, JSON/CSV output and a
standalone dark results screen. The CLI works without the graphical interface.
Storage, network, endurance and manual power entry are later milestones.

## Build and run

On Debian / Raspberry Pi OS:

```sh
sudo apt-get update
sudo apt-get install build-essential cmake pkg-config python3 libsdl2-dev libgles2-mesa-dev
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
python3 -m g3bench detect
python3 -m g3bench check
python3 -m g3bench quick --open
```

Python 3.9+ and CMake 3.16+ are required. Python uses only its standard library.
The native benchmarks use C99. No Vulkan, Godot, Python packages or internet
service is required. A working SDL2 GLES 2 context and display are needed for GPU.

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

Each run gets its own directory under `results/` containing `result.json`,
`report.html` and `summary.csv`. Open the report in a browser. During testing it
refreshes every three seconds, showing current stage and elapsed-time telemetry
graphs. Completed reports work offline and accept multiple saved JSON files for
comparison. Files remain local; the report loads no external assets.

Headless/incomplete runs keep their measured subsystem scores but do not receive
an overall score. Missing GPU support never prevents CPU and memory tests.
Board detection recognizes Pi generations, Compute Modules and Zero variants.
Pi 1 / original Zero / ARMv6 support is experimental. Tests are scheduled by
actual capabilities, with PASSED, FAILED, UNSUPPORTED, UNAVAILABLE or SKIPPED
statuses and reasons. Slow results do not fail merely for being slow. See
[board compatibility](docs/COMPATIBILITY.md).

## One-line installer

Public source repository: `gam3t3chelectronicshobbyhouse/gam3t3ch-sbc-bench`.

```sh
curl -fsSL https://raw.githubusercontent.com/gam3t3chelectronicshobbyhouse/gam3t3ch-sbc-bench/main/install.sh | bash
g3bench quick --open
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
