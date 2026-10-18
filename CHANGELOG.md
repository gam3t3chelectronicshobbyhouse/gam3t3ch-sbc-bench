# Changelog

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
