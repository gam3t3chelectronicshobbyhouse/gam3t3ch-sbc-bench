# 0.4.0 handoff

The app now has full-checkup sequencing, continuous supported telemetry, branded
stats PNG export, default desktop/menu shortcuts, a menu uninstaller, optional
LAN result collection, and bundled Godot 4.4.1 for supported standalone builds.
The editor is not required. Idle mode launches no renderer or telemetry loop.

Windows standalone CPU/memory and all three fullscreen Godot stages have run
successfully from the frozen application. The test suite passed 46 of 47 checks,
with the Linux-only fio check skipped on Windows. Real loopback upload and
listener shutdown passed. The exported PNG was downloaded and visually checked.
See VALIDATION.md and distribution/README.md for evidence and platform limits.

Physical Raspberry Pi testing, repeated-run tuning characterization and real
cross-machine LAN checks still require the intended hardware. Missing sensors
and workloads remain unavailable, never zero or fabricated. Full checkup means
all implemented workloads, not network throughput, endurance, multicore CPU or
a controlled zram benefit workload, which remain future work.

Installer artifacts, source and package-CI publication state should be checked
on the GitHub releases/actions pages. Real local machine results stay under
ignored build/ and are not included in packages or source history.
