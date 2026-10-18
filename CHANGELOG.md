# Changelog

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
