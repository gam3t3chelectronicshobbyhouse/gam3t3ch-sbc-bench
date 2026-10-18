# Idle behavior and Reactor Lab — suite 0.2.1

## Lifecycle

The dashboard is an explicitly launched, loopback-only Python HTTP server with
a static browser interface. It installs no service or startup task. It reads
hardware information once and checks the engine file's existence, without
starting Godot. The server's selector blocks with no timeout until a request or
shutdown wakeup arrives. Idle UI has no JavaScript interval, animation loop,
animated background, video, telemetry sampler or loaded 3D renderer. It still
occupies memory; the browser's own resource use is additional.

Clicking a test starts a separate worker process. One waiting completion event
updates the browser after it exits, without polling or stage-by-stage DOM work.
No repeated HTML generation or browser refreshing runs during a timed test.
Baseline telemetry still samples approximately once a second into memory;
sensor access itself has overhead and is retained consistently for thermals.
Native CLI stage snapshots are written only outside timed native calls.

The dashboard can stop its own benchmark process tree. On POSIX it first sends
an interrupt, allowing result cleanup; Windows uses process-tree termination if
the dashboard Stop control is used. If that interrupts the runner before it can
save a result, the dashboard writes a cancelled JSON/report with null scores;
incomplete measurements are discarded. Escape/window-close inside Godot
writes an interrupted result before exit. No unrelated services are stopped.

The optional engine is a finite child process, never an animated menu. Its
telemetry thread is stopped and joined at completion. Results are rendered
after it exits. An explicit Exit dashboard action wakes and closes the server;
closing the browser alone leaves the server asleep. Stop an active test before
using Exit. The CLI always remains available for a machine without a desktop.

## Showcase methodology

Workload identity: `reactor-showcase-0.2`. This is **unscored** and has no baseline
normalization or comparison eligibility. The baseline remains `baseline-0.1`.
No Godot result can populate CPU/memory/GPU/overall baseline scores.

Godot 4 uses its Compatibility renderer (GLES3/OpenGL3.3), not Vulkan. The
installed engine must be compatible with the board/OS; ARMv6 support is not
claimed. Missing Godot produces UNAVAILABLE with a saved report and does not
affect the portable benchmark. Startup/renderer/script failures keep an engine
log and a FAILED result. Engine version is recorded for repeatability; different
engine versions/drivers should not be treated as identical measurements.

The source scene contains four fixed GAM3T3CH signs with extruded lettering,
a platform, floor grid, twelve pylons, rotating torus
rings and core, a directional light and four omni lights. Stage two adds 192
orbiting mesh satellites; stage three adds a fixed 1,536-instance moving field.
The latter is a geometric particle field, not a claim of transparent-particle
fill-rate performance. All stages use a fixed camera function and geometry.

Each stage has a two-second unmeasured warmup and ten seconds of measured
application frame deltas. 1280×720 and 2× MSAA are requested; actual window size,
renderer and MSAA mode are recorded. Vsync and the engine FPS cap are disabled.
Presentation/compositor behavior may still limit throughput. Average FPS is
frames divided by accumulated delta. The 1% low is the inverse of the mean of
the slowest ceil(1%) deltas. Warmup also excludes initial context/scene creation;
first-time driver compilation can still affect behavior. A slow final frame
can extend duration. The engine must finish within the runner's 90-second bound.
The live HUD updates twice per second, not every frame. Scene initialization
can be checked headlessly with `showcase --smoke-test`, which records
SMOKE_TEST/smoke_validated and makes no performance claim.

## Versioning

Suite 0.2.0 changes report/measurement activity and adds the dashboard/showcase.
Native workload operation counts and normalization constants remain the same,
but results are grouped by suite version. Do not silently merge 0.1.0 and 0.2.0
overall comparisons. Older native binaries are rejected until rebuilt.

Suite 0.2.1 adds static GAM3T3CH branding and a shared G3 emblem. The native
baseline is unchanged. The added 3D signs change the optional scene geometry,
so it advances from reactor-showcase-0.1 to reactor-showcase-0.2. These scene
versions must not be treated as the same graphics workload.

## Development checks

On the Windows development machine, the idle dashboard accumulated 0.000
additional CPU seconds over 10.039 seconds and used approximately 29.9 MiB
working set, excluding the browser. This is bounded by Windows CPU-time
resolution and does not claim mathematically zero CPU or zero whole-system
load. Physical Pi resource use still needs measurement. The real Godot scene
was run on the development GPU and exited afterward; Pi rendering support is
still unvalidated. Unit/integration tests cover inactive startup, local request
authorization, shutdown, missing engines, unscored results and process waiting.

## Suite 0.4.0 release-candidate changes

Graphics defaults to fullscreen and requests foreground/topmost presentation;
--windowed is explicit. Godot stretches a fixed 1280x720 viewport to the display
with preserved aspect. Rendered dimensions and actual window dimensions/mode
are recorded separately, and a requested fullscreen run that ends windowed is
reported unavailable. The presentation change advances the optional workload to
reactor-showcase-0.3. Older scene versions are separate comparison groups.

Source bootstrap and standalone build recipes discover an installed/bundled
Godot engine by file lookup only. Frozen dashboard workers launch the bundled
application executable directly rather than treating it as a Python interpreter.

The optional LAN inbox starts only on explicit Enable. Its selector also waits
without a periodic timeout; uploaded result files are validated before saving.
It exposes no benchmark execution endpoint. Uploads pause during a collector
benchmark. Disabling/exiting stops the listener, while saved results persist.
Actual standalone packages and physical LAN/Pi qualification remain pending.
