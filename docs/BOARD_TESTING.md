# Raspberry Pi qualification checklist

This is a development baseline. Validate the installer on one Pi 5 first, then
check Pi 1 and original Zero for portability, followed by Pi 2, 3, 4 and CM5 as
available. Zero 2 is a separate model from original Zero. No board is marked
validated until its actual saved results and environment have been reviewed.

| Board | Initial status | Checks |
| --- | --- | --- |
| Pi 1 | Experimental; pending | ARMv6 source build, memory headroom, display/GLES capability |
| Original Zero / Zero W | Experimental; pending | ARMv6 source build, RAM, optional GPU |
| Pi 2 | Pending | ARMv7 build, CPU/memory, GLES2, telemetry |
| Pi 3 | Pending | OS architecture, GLES2, telemetry |
| Pi 4 | Pending | CPU/memory, GLES2, telemetry |
| Pi 5 | Pending | First end-to-end install and results |
| CM5 | Pending | Carrier, storage, cooling, telemetry and baseline |
| Zero 2 W | Pending | Model detection, OS architecture, GLES2, telemetry |

## First installation on each board

Use a supported OS with Python 3.9+; keep its release and image version in your
test notes. Run the installer as the normal user:

```sh
curl -fsSL https://raw.githubusercontent.com/gam3t3chelectronicshobbyhouse/gam3t3ch-sbc-bench/main/install.sh | bash
export PATH="$HOME/.local/bin:$PATH"
g3bench detect
g3bench check
g3bench quick --open
```

For a board without a desktop/display:

```sh
g3bench check --headless
g3bench quick --headless
```

Keep every run directory, including failed/partial runs. Record the Git commit
with `git -C ~/.local/share/gam3t3ch-sbc-bench rev-parse HEAD`. Preserve the full
model, OS/architecture, compiler, power supply, cooling arrangement, ambient
temperature and attached peripherals in the test notes.

Check that READY becomes PASSED for executed tests. Review specific reasons for
UNSUPPORTED, UNAVAILABLE or FAILED; low FPS alone is not failure. CPU/memory
should remain usable if GPU is unavailable. Confirm that thermal readings and
fan/RPM data correspond to sensors the board actually exposes. Unknown sensors
must remain unavailable rather than being invented.

## Repeatability

Run three separate quick tests after returning to a consistent idle temperature.
Keep background services, CPU governor, cooling, display setup and resolution
consistent. Use `--as-configured` only when deliberately retaining background
load; those results are labelled separately. Do not automatically use smaller
workloads on older boards. `--compat` is an explicit diagnostic option and its
graphics results do not share the official 720p comparison group.

Load the saved JSON files in a report to compare results. Review raw durations,
rates, frame times and thermal traces as well as scores. Note failures and
variation before calling the suite repeatable on a board. Results include the
hostname; review personal metadata before sharing them publicly.

## Graphical showcase direction

The scored graphics baseline remains native SDL2/GLES2. A future optional Godot
scene can add a detailed 3D workshop, camera path, lighting and particles. It
must have a separate workload identity, capability status and non-scored result;
it cannot replace or contribute to baseline overall scores. Godot 4's
Compatibility renderer requires GLES3/OpenGL3.3, per the
[official requirements](https://docs.godotengine.org/en/stable/about/system_requirements.html),
so an installed Windows editor does not establish support on older Pi boards.
Godot is not installed or required by this installer.
