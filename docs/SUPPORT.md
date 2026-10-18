# Supported systems and limitations

| System | Intended baseline | Hardware validation |
| --- | --- | --- |
| Pi 1 / original Zero / original CM, ARMv6 | Experimental native tests; GPU subject to capability probe | Pending |
| Raspberry Pi 2 / 3, ARMv7 32-bit | Native CPU, memory; GLES 2 if driver available | Pending |
| Raspberry Pi 3 / 4 / 5 / CM5, AArch64 | Native CPU, memory; GLES 2 if driver available | Pending |
| Other ARM Linux SBCs | Generic sysfs and SDL2/GLES 2 | Pending |
| x86-64 Linux | Development/reference host | Pending |
| Windows | Portable native CPU/memory and report development only | See validation log |

Use a supported Debian-family image with Python 3.9+ and CMake 3.16+. Old OS
releases may need upgrading. ARMv6 Pi 1/Zero is an experimental target. A headless system
can run CPU/memory with unknown GPU and no overall score. SDL display backends,
GLES drivers, 32-bit ABIs and memory constraints require real-board testing.

The first GPU implementation is deliberately basic. It does not measure Vulkan,
Godot, modern 3D engines or maximum GPU compute. Official publication should wait
for repeatability checks on Pi 2 and CM5, compositor/vsync checks, and workload
calibration. The installer is a source-build skeleton, not a tested release
distribution. No prebuilt binaries or hardware qualification are provided.

The optional Godot Reactor Lab has been validated on the Windows development
machine only; Pi GPU/engine compatibility is pending. It is never scored. The
dashboard is static and starts renderers only on an explicit run. See
IDLE_AND_SHOWCASE.md for lifecycle and measured idle overhead.

Standard/full/endurance modes, storage/fio, network/iperf3 server/client, manual
power data, performance-per-watt, a results database, multicore CPU and enhanced
3D scenes are deliberately deferred. Local JSON loading is the current results
comparison mechanism. The report uses a current browser (including Array.at).

The next milestone should qualify ARMv7 and ARM64 boards, add repeated-run
statistics and thermal/frequency analysis, then introduce opt-in fio storage
with explicit write warnings and a versioned full-suite aggregate.
