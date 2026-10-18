# Changelog

## 0.5.0

- Correct shared GLES shader precision and retain full program-link diagnostics.
- Add on-demand X11/Wayland/OpenGL/Vulkan/USB checks and evidence-based stock
  tuning advice, without changing drivers, governors, clocks or system settings.
- Add CPU/RAM/GPU-only modes, auto standard/legacy profiles, a static fullscreen
  browser cover and explicit Godot Vulkan Mobile testing with actual API metadata.
- Add sustained parallel SHA-256 CPU load/thermal profiling, separate throughput
  and a default 60-second phase in full-checkup-0.2.
- Advance drive workloads to storage-file-0.2: 20-second random stages rather
  than whole-file random transfers, concise timeouts and independent read recovery.
- Add opt-in Cloudflare HTTP send/receive/latency and iperf3 LAN bidirectional tests.
- Add active-run disk/interface telemetry, stage thermal summaries, cross-board
  raw metrics/deltas, repeat summaries and comparison plots included in PDF printing.
- Keep unsupported readings unavailable and common CPU/RAM scoring; no invented
  per-board normalization. Physical Gaia/Pi rerun remains required.

## 0.4.0

- Default graphics to fullscreen, with focus/topmost requests and an explicit
  windowed override. Godot uses a fixed 720p internal viewport; the new
  reactor-showcase-0.3 records internal/window dimensions and presentation mode.
- Add shared Linux/macOS/Windows source-bootstrap code, public copyable
  install/start commands, and optional pinned Godot runtime discovery.
- Add standalone Windows setup/ZIP and Linux ARM64/x86-64 tar build recipes,
  bundled Python/Godot/license notices, checksum manifests and a draft-release
  workflow. Windows standalone includes the runtime and has passed a real
  frozen full checkup with bundled Godot 4.4.1 fullscreen rendering.
- Add a full checkup sequence with continuous telemetry and component reports.
- Add desktop/menu shortcuts, a menu uninstaller, and result-preserving source
  uninstall support. Windows setup defaults to creating the desktop shortcut.
- Add offline branded stats PNG export and printable full reports, with raw
  measurements, availability reasons, versions and methodology references.
- Add an explicitly enabled LAN results inbox: token-authenticated JSON uploads,
  generated file paths, offline comparison reports, manual refresh and clean
  shutdown. No remote test execution. Physical-network validation is pending.
- Document installation, launch, per-unit testing, result collection, real
  measurement limits, data paths, updates and uninstalling in the README.

## 0.3.0

- Add connected-drive discovery and separate file-only fio tests: sequential and
  4 KiB random reads/writes, MB/s, IOPS, mean/p99 latency, raw fio JSON and CSV.
- Add dashboard drive selection, write acknowledgement, file size, run labels
  and notes. Automatic selection uses one eligible filesystem per physical drive.
- Add CPU policy, swap, zram and zswap snapshots; active swap/zram/memory-pressure
  telemetry. Offline charts have axes and stage tooltips, with per-drive bars and
  matching-configuration deltas across saved runs.
- Add optional fio installation and Linux direct-I/O integration checks. Storage
  remains unscored. Native workload counts stay unchanged; the extra telemetry
  makes this a separate suite-version comparison group.

## 0.2.1

- Unify the dashboard, reports, desktop entry and scene under GAM3T3CH 3D Benchmark branding.
- Add a shared inline G3 emblem, branded HUD, runtime window icon and four 3D GAM3T3CH signs.
- Advance the optional scene to reactor-showcase-0.2 to identify its added text geometry.
- Preserve static idle presentation and unchanged native baseline workloads/constants.

## 0.2.0

- Add a static, on-demand benchmark dashboard with no idle renderer, telemetry or polling.
- Add the optional Godot 4 Reactor Lab showcase with fixed scenes and separate, unscored FPS.
- Stop renderer processes after a run; provide cancellation and explicit dashboard shutdown.
- Defer browser/report work until after measurements and keep telemetry in memory during tests.
- Bump suite version to separate results recorded with the new reporting policy.

## Unreleased

- Detect Pi model families and mark ARMv6/Pi 1/original Zero as experimental targets.
- Add capability-based scheduling and a `g3bench check` command with a hidden GLES2 probe.
- Record per-test status/reason in CLI, HTML and JSON schema 2; preserve other tests when a dependency is unavailable.
- Check memory headroom while retaining fixed buffers and unchanged score methodology.

## 0.1.0

- Initial fixed native CPU and memory baseline.
- Linux hardware detection, idle-load guard and thermal/cooling telemetry.
- Optional SDL2/GLES 2 fixed-scene renderer with frame-time metrics.
- Versioned JSON, CSV and offline HTML reports with telemetry graphs and local comparison.
- Debian-family installer skeleton and methodology documentation.
