# GAM3T3CH 3D Benchmark

A local benchmark application for Raspberry Pi, Linux SBCs and development PCs.
The repository is `gam3t3ch-sbc-bench`; the source command is `g3bench`.
Tests run on the machine being measured. Reports contain measured rates and
sensor readings; unavailable measurements stay unavailable rather than being
replaced with estimates or demo values.

**0.5.2 hardware-testing prerelease is available.** Standalone Windows,
Linux ARM64 and Linux PC packages include Godot 4.4.1; the editor is not needed.
All package checks and 57 Linux tests passed, including real GLES scenes, fio
and iperf3. Gaia's V3D/USB HDD rerun remains required. See
[downloads](https://github.com/gam3t3chelectronicshobbyhouse/gam3t3ch-sbc-bench/releases/tag/v0.5.2)
and [validation](docs/VALIDATION.md).


## 0.5.2: diagnostics, sustained load and useful comparisons

- If a compositor cannot disable/verify vsync, GLES still runs with explicit
  display-pacing metadata and raw FPS; GPU/overall points are withheld. The
  report does not mistake a display-rate cap for the board's GPU ceiling.
- **CPU only / RAM only / Portable GPU only** run independently. Reactor Lab
  remains a separate scene test; its mean FPS is visible even without a baseline
  GPU score. Godot Compatibility uses OpenGL, not Vulkan. Choose **Vulkan Mobile**
  explicitly to test Vulkan; actual driver, API version and display server are
  recorded, and a fallback cannot masquerade as a Vulkan pass.
- **Auto profile** selects legacy 360p GLES for Pi 1/original Zero/ARMv6 and common
  720p for other boards. You can override it. CPU/RAM workloads and normalization
  stay common across boards. There are no invented Pi-specific rating scales.
- **Check graphics / system** runs on demand: X11/Wayland session, GLX renderer,
  Vulkan probe, KMS modules, DRM nodes and USB topology. A missing diagnostic tool
  is distinguished from an API test failure. No driver/settings are changed.
- **Full checkup** adds a sustained CPU load phase (default 60 seconds, up to
  eight SHA-256 workers automatically). **Sustained CPU / heat** runs it alone.
  Duration is adjustable; CLI `full --load-seconds 0` explicitly skips this phase.
  It measures parallel SHA-256 throughput and supported thermal/load telemetry,
  not a complete hardware stability or memory-pressure certification.
- The dashboard requests a static fullscreen **TESTING IN PROGRESS** cover for
  fullscreen runs. Native graphics windows request foreground presentation above
  it. Show dashboard/Stop controls remains available; browser/desktop focus rules
  can restrict requests. This cover is a browser feature, not a CLI display.
- Drive tests keep sequential I/O byte-bounded, but random 4 KiB stages now run
  for **20 seconds each** over the selected working-file size. A slow mechanical
  disk need not finish a whole GiB of random writes. Independent reads continue
  after a random-write failure when initial file population succeeded. Timeouts
  remain incomplete results; direct I/O is never silently changed to buffered.
- Reports add per-stage heat summaries, disk/interface activity, overlaid loaded
  run charts, raw workload deltas and repeated-configuration median/min/max/N.
  Load previous `result.json` files, then **Print / save full report as PDF** to
  include the comparisons. Existing PDF images cannot restore missing raw data.
  Whole-system I/O activity includes other processes and is not application-only
  workload bandwidth. Loaded runs stay local; report viewing makes no requests.

A Vulkan probe may enumerate software adapters alongside hardware. Check the
**actual benchmark renderer/backend** before treating a software-adapter warning
as proof that the measured run used software rendering.

### Network send / receive

Network is **opt in**, including in Full checkup. With no LAN server specified,
acknowledge traffic to run three 4 MiB downloads, three 2 MiB uploads and five
response-latency requests against Cloudflare. Approximately 18 MiB of payload
plus protocol overhead is transferred; Cloudflare sees the client's public IP.
Rates include TCP/TLS/server/path overhead and are not a line-rate capacity
estimate. Response-start latency and its standard deviation are HTTP metrics,
not ICMP ping, packet loss or loaded-latency measurements. No benchmark result
or system metadata is uploaded to Cloudflare.

For a LAN test, install `iperf3` on both machines. Run `iperf3 -s` on the peer,
then enter its address in the dashboard's LAN server field. This runs one TCP
stream for 10 seconds in each direction and retains iperf3 JSON. Traffic volume
scales with link speed. The peer must be reachable on its iperf3 port (5201);
no firewall rule or persistent server is installed by GAM3T3CH.

```sh
# Optional diagnostic tools and LAN measurement, Raspberry Pi OS/Debian
sudo apt-get install mesa-utils vulkan-tools usbutils iperf3

g3bench diagnostics
g3bench graphics --profile standard --open
g3bench cpu --open
g3bench memory --open
g3bench load --load-seconds 60 --open
g3bench showcase --renderer vulkan --open
g3bench network --allow-network --open
g3bench network --iperf-host 192.168.1.10 --allow-network --open
g3bench full --allow-writes --load-seconds 60 --allow-network --open
```

See [Gaia findings, stock-setting checks and references](docs/DIAGNOSTICS_AND_TUNING.md)
for the shader/drive changes and the limits of historical Pi tweaks.

## Choose an installation

| Machine | Installation / limits |
| --- | --- |
| Windows x86-64 | Standalone setup/portable ZIP includes Python, native CPU/memory tests and Godot. Linux sensors and fio drive tests are unavailable. Windows results are development results, outside Linux baseline scoring groups. |
| Raspberry Pi / Linux ARM64 | Standalone tar bundle includes Python, native tools and Godot. Targets glibc-based Raspberry Pi OS/Debian Bookworm or newer, with a compatible graphical session/driver for 3D. Physical Pi qualification is pending. |
| Linux x86-64 | Equivalent standalone tar bundle, or the source installer. Graphics still requires a working system display/driver. |
| Pi 2/3 on 32-bit Linux | Source installer. Native/GLES capability determines available tests. Godot ARM32 may be installed, but engine/driver/OS compatibility is not guaranteed. |
| Pi 1 / original Zero / ARMv6 | Experimental source build. Godot 4 is not bundled for ARMv6. CPU/memory and GLES2 remain independent of Godot availability. |
| macOS | Experimental source-installer path with Python 3.9+ and a native compiler or local Zig toolchain. Godot download mapping is included, but no standalone macOS artifact is currently qualified. Linux sensors/storage tests are unavailable. |

No installer can supply missing GPU features or an operating-system graphics
driver. A missing Godot/GPU must not prevent independent CPU/memory tests.

### Standalone installation

The package workflow builds these platform-specific artifacts:

- `GAM3T3CH-0.5.2-windows-x86_64-setup.exe`
- `GAM3T3CH-0.5.2-windows-x86_64.zip`
- `GAM3T3CH-0.5.2-linux-aarch64.tar.gz`
- `GAM3T3CH-0.5.2-linux-x86_64.tar.gz`

Use the package matching the **OS architecture**, not just the board's processor.
Download it and the corresponding SHA256SUMS file from the
[0.5.2 release page](https://github.com/gam3t3chelectronicshobbyhouse/gam3t3ch-sbc-bench/releases/tag/v0.5.2).

Windows: run the setup executable as your normal user, then open GAM3T3CH from
the desktop or Start menu. The desktop shortcut is selected by default; the
Start menu also includes **Uninstall GAM3T3CH 3D Benchmark**. The portable ZIP can
instead be extracted into a user-owned folder; run `GAM3T3CH/GAM3T3CH.exe`.
Keep its `_internal` folder beside the executable.

Linux: extract the matching tar file into a user-owned folder and run:

```sh
tar -xzf GAM3T3CH-0.5.2-linux-aarch64.tar.gz
./GAM3T3CH/GAM3T3CH
```

To install the Linux bundle into your user account with desktop/menu shortcuts
and an uninstall menu entry, run `bash ./install.sh` beside the extracted
`GAM3T3CH` directory. Some desktops require right-clicking the desktop shortcut
and choosing **Allow Launching**. For an extracted portable bundle, use
`./GAM3T3CH/GAM3T3CH shortcuts` to register its current location instead.

Substitute `x86_64` for a Linux PC. Keep the entire extracted directory intact.
The package contains the Python runtime and optional 3D engine, so users do not
install Python or Godot separately. fio remains an optional Linux package for
storage tests (`sudo apt-get install fio` on Raspberry Pi OS/Debian).

### Source one-line installation

These commands fetch the published `main` branch.
The source installer needs internet for dependencies and the optional Godot
engine; the standalone packages above are intended to contain those runtimes.

Linux / Raspberry Pi OS / macOS Terminal:

```sh
curl -fsSL https://raw.githubusercontent.com/gam3t3chelectronicshobbyhouse/gam3t3ch-sbc-bench/main/install.sh | bash
```

Windows PowerShell:

```powershell
irm 'https://raw.githubusercontent.com/gam3t3chelectronicshobbyhouse/gam3t3ch-sbc-bench/main/install.ps1' | iex
```

Run as the normal user. Linux bootstrap supports apt, dnf, pacman and zypper
package commands; only the Debian-family baseline has CI coverage so far.
macOS requires Python 3.9+ (Homebrew can install it when present). Windows uses
an existing Python 3.9+ or attempts a user Python install through winget; if
neither is available, install Python from python.org first. The Windows/macOS
native compiler fallback is a pinned user-local Zig package.

Source installation builds native tests, attempts a checksum-verified official
Godot 4.4.1 download for supported platforms, creates a launcher and opens the
local dashboard. Godot download failure leaves portable tests available. No
service, startup task, overclock, swap change or firewall rule is installed.
Desktop/menu shortcuts and a menu uninstaller are created where supported.

Default source locations:

- Linux/macOS: `~/.local/share/gam3t3ch-sbc-bench`, launcher `~/.local/bin/g3bench`.
- Windows: `%LOCALAPPDATA%\GAM3T3CH\sbc-bench`, launcher `g3bench.ps1` there.

A recognized new-style installation is retained and relaunched, without an
implicit update. Unrelated existing directories are not overwritten. For a
custom/offline source build, run `python3 installer.py --help`. Options include
`--prefix`, `--no-launch`, `--skip-godot`, `--source` and `--compiler`.

To upgrade Windows setup installs, close the dashboard and run the newer setup;
external results are retained. For an existing source/Linux user installation,
back up results, run its uninstaller, then install the new version. The source
one-liner deliberately relaunches an existing recognized installation rather
than silently overwriting it.

Existing installations made from the older Git-based installer can be updated
manually after saving results:

```sh
git -C ~/.local/share/gam3t3ch-sbc-bench pull --ff-only
cmake -S ~/.local/share/gam3t3ch-sbc-bench -B ~/.local/share/gam3t3ch-sbc-bench/build -DCMAKE_BUILD_TYPE=Release
cmake --build ~/.local/share/gam3t3ch-sbc-bench/build --parallel 2
```

A folder installed from a source ZIP is not a Git checkout: keep its results and
install a newer version into a fresh folder instead.

## Launch and run tests

Open the standalone app, or run `g3bench ui` from a source installation. From a
checkout use `python3 -m g3bench ui` (`python -m g3bench ui` on Windows).
Open the `http://127.0.0.1:PORT` address printed by the application; ports can vary.
Localhost means the machine where the application is running.

The dashboard starts no renderer or telemetry loop while idle. It collects a
hardware snapshot once, then waits for interaction. Benchmarks start only when
requested. Renderers exit after a run, and charts are generated afterward.
Closing a browser tab alone leaves its local server waiting; use **Exit
dashboard** to stop the server and any results inbox.

- **Portable benchmark:** five single-thread CPU tests, three memory tests and
  five fixed GLES2 scenes when available. Subsystem buttons run them independently.
- **Reactor Lab 3D:** bundled/found Godot engine, three fixed 3D stages, real FPS
  and 1% lows. Separate and unscored.
- **Storage:** select mounted drives and acknowledge temporary writes. Four
  direct-I/O tests per selected filesystem, with real MB/s, IOPS and mean/p99
  completion latency. No formatting or raw-device writes.
- **Full checkup:** runs all currently implemented tests in sequence: portable
  CPU/memory/GLES2, connected-drive storage, then Reactor Lab. It keeps one
  temperature/load/memory trace throughout, saves each component report and a
  combined report, and continues past independent unavailable/failed components.
  Acknowledge temporary storage writes; no drive selection means one eligible
  filesystem per physical drive. Full mode is a distinct comparison group.

Graphics defaults to fullscreen and requests focus/topmost presentation when
launched. Godot renders a fixed 1280x720 viewport and scales/letterboxes it to
the screen; monitor resolution does not increase its internal 3D workload.
The native GLES2 baseline requests its exact 720p fullscreen drawable and rejects
an unavailable configuration instead of silently changing resolution. OS focus
policies can still restrict focus requests. Escape stops the renderer; the
screen returns to the desktop after exit. Untick Fullscreen or use `--windowed`
when needed; compare matching presentation modes.

```sh
g3bench detect
g3bench check
g3bench quick --open
g3bench quick --headless
g3bench quick --windowed
g3bench showcase --open
g3bench showcase --godot /path/to/godot4 --open
g3bench drives
g3bench storage --all --allow-writes --label 'Stock baseline' --open
g3bench storage --target /media/user/ssd/bench --allow-writes --open
g3bench full --allow-writes --open
g3bench full --skip-storage --headless
```

Standalone CLI equivalent: `./GAM3T3CH quick --headless` from its extracted Linux
folder. The Windows app can also receive command arguments; saved files, rather
than terminal output, are the primary interface of its windowed executable.

Portable/showcase preflight checks background CPU usage for three seconds;
above 10% cancels unless **Accept background load** / `--as-configured` is set.
Storage has the same idle check. No unknown services are stopped.

## Link machines to collect results

Install and test on **each unit**. The application does not run a Pi benchmark
on the collecting PC's processor. There is no remote test-start agent.

1. On the collecting PC, open its dashboard and click **Enable LAN results inbox**.
2. Select the LAN address reachable by the other units, or enter the PC's LAN
   IPv4 address. Click **Copy results link**.
3. On another unit on the same reachable network, open that complete link in a
   browser. Select the unit's saved `result.json` and click **Send result**.
4. On the collecting dashboard, click **Refresh received results**, then
   **Compare received results**. Refresh is manual; there is no polling loop.
5. Click **Disable inbox** or **Exit dashboard** when collection is finished.

The inbox listens on a separate temporary LAN port only after explicit Enable.
The copied link contains an upload access token in its URL fragment. It accepts
JSON results only (8 MiB/file, 20 results/session); it cannot start tests, read
arbitrary files or serve the collecting machine's dashboard to the LAN.
Uploads are paused while the collector runs a benchmark.
Use a trusted local network: this is HTTP, not an encrypted internet service.
Uploads retain the result's hostname/system metadata, so send files only to the
intended collector. Firewall rules are not changed automatically; if blocked,
allow the shown port/application only on your intended private network.

Received results are retained in the collector's `results/received` directory
under its configured output location, in generated folders with `result.json`
and a standalone `report.html`. Disabling the inbox removes the live link and
session list, not the saved files. Save comparison reports or load those JSON
files again later. A headless unit can copy results to another machine first
and upload them there; a desktop is not needed to run CPU/memory/storage tests.

## Reports, real statistics and comparison

Each run saves `result.json` and `report.html`. Portable runs add `summary.csv`;
storage runs add `storage.csv`. Standalone default output is
`%LOCALAPPDATA%\GAM3T3CH\results` on Windows or
`~/.local/share/GAM3T3CH/results` on Linux. Source CLI runs default to `results/`
in the working directory; the source installer launches with an installation-local
output directory. Use `--output DIR` to choose one explicitly.

Reports open offline in a current browser on Windows/Linux/macOS. No Python or
running dashboard is needed to view a saved HTML report. **Compare saved runs**
loads additional local JSON files; storage runs add drive-comparison bars and
matching-configuration percent changes. Network access is not needed for offline
viewing, and local file loading does not upload anything.

Use **Save stats PNG** in a saved report for a branded community-post image with
graphs, raw rates, test availability, run/workload versions and methodology
references. If the browser does not save automatically, use **Download stats
PNG**. Labels/notes are excluded unless you opt in; hostname, IPs and mount
paths are omitted from the image. Review before posting. **Print / save PDF**
exports the full report through your browser. Neither action uploads data.

Telemetry charts show temperature, CPU frequency/load, RAM, swap, zram physical
allocation and memory pressure where exposed. Samples have elapsed-time axes
and workload-stage tooltips. Absent sensors are labelled unavailable. A falling
clock alone is not proof of thermal throttling. Zram capacity is compressed
memory capacity, not additional physical RAM; dedicated memory-pressure benefit
testing is still future work.

CPU/memory/GPU scores use provisional synthetic normalization constants and
geometric means. They are not calibrated to a claimed reference Pi. Overall
requires all three baseline subsystems; storage, network and Godot do not enter
that aggregate. Slow performance is valid. Missing, unsupported, interrupted or
failed measurements are never filled with zero or an invented score.

Use the same suite/workload versions, file size, rendering mode, resolution,
compiler/engine/driver conditions and run settings for direct comparisons.
Start with stock clocks, record PSU/cooling/ambient conditions, run at least
three repetitions and inspect variation before attributing a tuning gain.
Run labels/notes and governor/swap/zram snapshots help identify configurations.
Screenshots/fixtures explicitly labelled synthetic are layout checks only;
they are not hardware performance evidence and are not shipped as run results.

## Uninstall

First stop any active test and use **Exit dashboard**. Back up every result you
want to keep, including received files; results may live outside the app folder.

- **Windows setup:** Settings > Apps > Installed apps > GAM3T3CH 3D Benchmark >
  Uninstall (or its Start-menu uninstaller). Results under
  `%LOCALAPPDATA%\GAM3T3CH\results` are separate and retained. Remove that data
  folder manually only if you want to discard the saved results/logs too.
- **Portable Windows/Linux bundle:** delete only the extracted `GAM3T3CH` app
  directory using your file manager. Remove any shortcut you created. Separately
  remove saved result folders only after backing them up.
- **Installed Linux bundle / source installation:** use its **Uninstall
  GAM3T3CH 3D Benchmark** menu entry or run `g3bench uninstall` (Linux bundle:
  `~/.local/share/GAM3T3CH/app/GAM3T3CH uninstall`). Confirm the displayed app
  folder. Installation-local results are moved to `~/GAM3T3CH-results-backup`;
  external results are retained. Only unchanged shortcuts owned by this
  installation are removed. A source checkout is deliberately not uninstallable.
- **Manual source Linux/macOS cleanup:** remove `~/.local/share/gam3t3ch-sbc-bench` (or your
  chosen prefix), the GAM3T3CH `~/.local/bin/g3bench` launcher, and
  `~/.local/share/applications/g3bench.desktop` if present. Check that the launcher
  belongs to this installation before removing it. Installation-local results
  and downloaded runtime are inside the prefix: copy them out first.
- **Source Windows:** remove `%LOCALAPPDATA%\GAM3T3CH\sbc-bench` (or chosen
  prefix) and any shortcut you created, after copying installation-local results.

The application creates no system service or startup task. Its source installer
may have installed shared packages such as Python, compilers or fio; uninstalling
the benchmark does not remove those packages or change clocks/swap settings.
Temporary storage-test directories normally clean up after completion/cancel;
a power loss/forced kill can leave `.gam3t3ch-storage-*`. Identify the specific
old test directory and ensure no test is active before manually removing it.

## Build, qualification and known limits

Manual native build on Raspberry Pi OS/Debian:

```sh
sudo apt-get install build-essential cmake pkg-config python3 libsdl2-dev libgles2-mesa-dev fio
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
python3 -m unittest discover -s tests -v
```

The standalone package workflow builds on Windows x86-64 and Debian Bookworm
for Linux x86-64/ARM64. It bundles Python/native executables/Godot and license
notices, then exercises the frozen native worker and bundled Godot headlessly.
Tag-triggered builds create a **draft** GitHub release, leaving publication until
the artifacts are reviewed. See [distribution notes](distribution/README.md).

Physical Pi qualification and repeated-run testing remain required. Pi 1/Zero
are experimental. Long endurance presets,
manual power entry/per-watt reporting and a controlled zram
memory-pressure workload are not implemented. The local results inbox is a
file-transfer feature. Use the separate Network test for throughput measurements.

See [methodology](docs/METHODOLOGY.md), [scores](docs/SCORING.md),
[storage/tuning](docs/STORAGE_AND_TUNING.md), [board checklist](docs/BOARD_TESTING.md),
[support limits](docs/SUPPORT.md) and [validation](docs/VALIDATION.md).

MIT; see [LICENSE](LICENSE). Bundled third-party license notices accompany
standalone builds. The project is independent of Element14.
