# Board detection and test availability

`g3bench detect` reads the full board model and revision metadata. Device-tree
model paths are preferred, with `/proc/cpuinfo` Model as a fallback. A Pi is not
identified from clock speed or the CPU Hardware field: Raspberry Pi documents
that many generations report `BCM2835` there. See the
[official board-identification documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#identify-your-model).

Pi 1, Pi 2–5, Compute Modules and Zero variants receive model identifiers in
`hardware.board_profile`. Unknown boards keep their full model and use generic
capability checks. Board profiles describe support and diagnostics; they never
change operation counts, buffers, graphics scenes or scoring constants.

Pi 1, original Zero and original Compute Module / ARMv6 installations are now
experimental targets. They need a compatible OS, Python 3.9+ and a compiler that
builds binaries for that device. Native tests are attempted when the executable
can run; graphics depends on the installed SDL/GLES/display stack. No Pi 1
hardware run has been validated. The installer accepts `armv6l` with a warning.

Use `g3bench check` to check installed tools and graphics capabilities without
running scored workloads. `--headless` skips even the graphics probe. The
graphics check opens a hidden SDL context and validates the requested GLES 2
shaders, resolution and swap interval. Its outcome describes the current
driver/display configuration, not a permanent claim that a board has no GPU.

| Status | Meaning |
| --- | --- |
| READY | Preflight allows this test; not a completed measurement. |
| RUNNING | The fixed workload is executing. |
| PASSED | Workload completed. Slow performance remains a valid result. |
| UNSUPPORTED | A known requirement cannot be met, such as RAM capacity or requested GLES/display configuration. |
| UNAVAILABLE | Tool/dependency cannot run or is missing, display initialization failed, or current available RAM is too low. |
| SKIPPED | Headless mode or a cancelled run deliberately omitted the test. |
| FAILED | A started benchmark encountered an error, crashed or timed out. |
| INTERRUPTED | The user interrupted a running workload. |

The fixed memory test needs two 32 MiB buffers. Preflight reserves an additional
32 MiB headroom: less than 96 MiB total RAM is unsupported, while less than
96 MiB currently available is unavailable. Available memory is rechecked before
execution. Unknown memory availability is not treated as zero; native allocation
still checks for failure. This reduces memory-pressure risk without guaranteeing
allocation or replacing the workload with a smaller one.

Native executable compatibility is checked independently from GPU capability.
A missing/wrong-architecture native executable is reported rather than aborting
the report; independent GPU tests may still run. A missing or unsupported GPU
does not prevent CPU/memory. Every test records its status and reason in the
CLI, `test_status` JSON object and HTML report. JSON schema version is now 2;
the report can still open older results without status metadata.

Only completed subsystems receive scores. Unsupported/unavailable tests get
null, not zero. An incomplete run has no overall score and is excluded from
overall comparisons. Optional low-resolution mode remains an explicit user
choice, labelled separately. No board automatically gets easier scored tests.

The scored work and normalization remain suite 0.1.0 / baseline-0.1. This update
adds detection, scheduling and reporting; it does not change those workloads.
