# Scoring — suite 0.1.0 / baseline-0.1

Scores are provisional development scores. Every rate is normalized as
`1000 × measured rate / fixed reference rate`. References are synthetic units,
not measurements of a claimed Raspberry Pi reference board.

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
withholds eligibility. No claim of final official scoring is made by 0.1.0.

Workload, constants or measurement changes require a new suite version. There
are no migration rules across versions. Never merge version groups silently.
