# Changelog

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
