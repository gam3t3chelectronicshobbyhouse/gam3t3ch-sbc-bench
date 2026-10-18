# Scoring — suite 0.3.0 / baseline-0.1

Scores are provisional development scores. Every rate is normalized as
`1000 × measured rate / fixed reference rate`. References are synthetic units,
not measurements of a claimed Raspberry Pi reference board.

Constants match suite 0.1.0, but 0.2.0 uses a quieter reporting policy and forms
a separate comparison group. The optional Godot showcase is never scored.

| Workload | Reference rate |
| --- | ---: |
| Integer | 100,000,000 iterations/s |
| Floating point | 100,000,000 iterations/s |
| FNV-1a | 500 MB/s |
| RLE roundtrip | 500 MB/s input |
| Matrix multiply | 1000 MFLOP/s |
| Memory copy / read / write | 1000 MB/s each |
| GPU scenes 1–5 | 60 FPS each |

CPU and memory scores are the geometric mean of their normalized subtests. GPU
is the geometric mean of its five normalized scene rates. Baseline overall is
the geometric mean of CPU, memory and GPU, requiring all three. It is **not**
the future full-suite overall including storage. Network and power efficiency
will remain separate. Missing values are null; no zeros or reweighting hide a
missing subsystem. Compatibility GPU has raw FPS but no official GPU/overall.

Direct comparisons require identical suite version, workload ID, mode, GPU
resolution, memory size and thread count, plus matching build/driver conditions.
The report exposes comparison groups; hardware/build conditions need human
review. Partial, cancelled, interrupted, as-configured, compatibility and
non-Linux runs are ineligible for baseline comparison. A missing idle check also
withholds eligibility. No claim of final official scoring is made by this development suite.

Workload, constants or measurement changes require a new suite version. There
are no migration rules across versions. Never merge version groups silently.

Suite 0.3.0 adds separate per-drive file tests and tuning telemetry. See
[storage and tuning](STORAGE_AND_TUNING.md). Storage is unscored and is not
part of baseline overall. Native workload counts remain unchanged; compare
matching suite versions because telemetry reads changed.

Suite 0.4.0 reports also separate fullscreen/windowed
presentation in baseline comparison groups. Native counts/constants remain
unchanged. Optional reactor-showcase-0.3 and storage remain unscored. Binary
installer checks passed on Windows; physical Pi validation remains pending.
Full checkup retains the portable CPU/memory/GPU scores where valid, with a
separate mode/workload identity. It does not add storage or Godot into overall.

Suite 0.5.0 adds explicit matching GLES shader precision without changing CPU/RAM
operation counts. storage-file-0.2 keeps fixed sequential bytes but uses 20-second
random stages. full-checkup-0.2 adds sustained SHA256 load (default 60 seconds,
auto up to eight workers) and opt-in HTTP or iperf3 network trials. These rates
are separate and unscored. Common CPU/RAM normalization stays fixed; legacy
360p GPU work is a different group, never an adjusted official GPU score.
Reports can compare compatible raw metrics even when overall is unavailable;
repeat summaries show median/range/N, not statistical significance. Disk/interface
activity is whole-system counter deltas during the run. See DIAGNOSTICS_AND_TUNING.md.
