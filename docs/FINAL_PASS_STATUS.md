# 0.5.2 handoff

The Gaia image motivated a GLES shader-precision fix with full linker errors and
bounded random-drive workloads. The original JSON/log is needed to confirm the
exact Gaia failures; a physical V3D/USB HDD rerun is still required.

Implemented: independent CPU/RAM/GPU modes, standard/legacy auto profiles,
on-demand graphics/session/API/USB checks, explicit Godot Vulkan testing with
actual driver metadata, static fullscreen browser cover, sustained SHA256 CPU
load/thermal profiling, opt-in HTTP or iperf3 send/receive, active-run disk/network
counter charts, stage thermal summaries, raw cross-board comparisons and repeat
median/range/N included in browser PDF printing. No overclock/system tweak is
applied automatically. CPU/RAM normalization stays common across boards.

Local Windows checks: 57 tests, 55 pass and Linux fio/iperf integrations skipped;
actual CPU/load/full/HTTP execution and bundled Godot 4.4.1 fullscreen Vulkan
execution passed for available components. Full mode retained one sensor trace;
Windows-inapplicable sensors/GLES/fio remained unavailable. All 57 Linux tests, the Mesa shader probe and all five real GLES scenes passed.
Windows/Linux x86-64/Linux ARM64 package checks passed; v0.5.2 installers and
checksums are public. The published Windows setup upgraded the existing app and
its new frozen load worker passed. Physical Pi qualification remains tracked
in VALIDATION.md.

Still outside scope: controlled zram/memory-pressure benefits, video/audio
quality/latency tests, long endurance, manual power/per-watt and calibrated
per-board ratings. Historical element14 fixes are linked as troubleshooting
references, not generic Pi 5 recommendations. No actual local results ship in
source/packages. Network transfers require explicit acknowledgement.
