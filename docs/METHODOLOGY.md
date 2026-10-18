# Benchmark methodology — suite 0.1.0

All systems run the same work with one CPU thread. Native code is compiled at
`-O2` (MSVC `/O2` on development Windows), without fast-math or CPU-specific
flags. Compiler version and pointer width are saved. Compiler, ABI and OS still
affect results; compare like builds and preserve metadata.

CPU consists of 384,000,000 xorshift32 iterations, 256,000,000 dependent floating
point updates, FNV-1a over a deterministic 64 KiB buffer 16,384 times, 8,192 RLE
compression/decompression roundtrips (verified against input), and 8,192 32×32
double-precision matrix multiplies with a fixed diagonal input increment each
iteration to keep repeated work observable. Fixed inputs and operation counts never
adapt to board speed. Checksums keep work observable. This small baseline
measures single-core throughput; multicore scaling is future work.

Memory allocates two 32 MiB buffers, pre-touches them, and executes 32 passes
each of byte copy, byte read/reduction and byte write. Volatile accesses prevent
dead-store elimination. Copy counts logical payload bytes once, not combined
read+write bus traffic. MB means 1,000,000 bytes. These portable scalar loops
measure the specified workload, not a claim of maximum libc/DRAM bandwidth.
64 MiB exceeds small caches on target boards; memory pressure and caches still
affect results. Latency/pointer chasing is deferred.

Graphics uses SDL2 with a GLES 2.0 context, fixed 1280×720 drawable, no MSAA and
vsync disabled. Failure to disable vsync or a resolution mismatch rejects GPU
output. Five scenes run for five seconds each with 16, 128, 128, 512 and 1024
rotating procedural checker quads. Scene 3 enables four shader lights; scene 5
enables alpha blending and larger particles for overdraw. Positions and rotations
are analytic functions of elapsed time and object index. The camera is fixed.
Geometry, shader, object counts and duration are fixed on every board. Geometry
and fragment workload never adapt to frame rate. These are a basic 2D/overdraw
baseline, not a finished 3D showcase or an image-texture benchmark.

Each frame completes with `glFinish`, then swaps. Timing includes CPU submission,
GPU completion, swap and event processing. Average FPS is frames/elapsed seconds.
The 1% low is the reciprocal of the arithmetic mean of the slowest ceil(1%)
frame times. Variance is population frame-time variance in ms². Scene duration
can exceed five seconds by one frame on a very slow board. No warm-up phase is
implemented yet. A compositor may still constrain presentation despite the
successful swap-interval request; use a consistent display session and check
for a display-rate ceiling. Software rasterizers are recorded by renderer name
and should be compared separately from hardware GPUs.

Telemetry samples every nominal second throughout workloads, plus initial/final
samples. Generic sysfs thermal zones, cpufreq policies, hwmon fan/PWM and thermal
cooling devices come first. `vcgencmd` adds throttle bits and supplies temperature
and clock fallbacks. Commands have bounded timeouts; sampling intervals may grow
when commands are slow. All temperature sensors are retained; headline
temperature is the hottest available zone, which is not necessarily CPU on every
board. Temperature averages are sample averages, not time-weighted integrals.
Raspberry Pi bit 2 indicates active throttling; bit 18 is historical and may
predate the run. All raw samples remain in JSON. Frequency-drop sample counts
are observations, not proof of thermal throttling. No tachometer means no RPM.

Root storage mount/source is discovered with findmnt. Storage type is left
unknown rather than guessed from speed. Storage and network are not exercised
in this milestone. No storage write test runs. Power is null until manual input
is implemented. CLI output, HTML and JSON expose missing measurements explicitly.
