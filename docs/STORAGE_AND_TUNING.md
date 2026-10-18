# Connected drives and tuning — suite 0.3.0

Storage workload: `storage-file-0.1`. CPU/memory/GLES workloads remain
`baseline-0.1`. Storage is a separate, unscored experiment; it never changes
baseline overall scores. Suite 0.3.0 adds telemetry reads, so preserve suite
version groups even though native operation counts are unchanged.

## Discovery and selection

`g3bench drives` combines Linux `lsblk` and `findmnt` JSON. SD and eMMC are
distinguished using the kernel MMC device type, not transfer speed. USB, SATA
and NVMe transport/model information comes from lsblk; unknown remains unknown.
Physical disks without a mounted filesystem remain listed as unavailable.
RAM disks/zram, loop devices and network filesystems are not storage targets.
Encrypted or layered filesystems are included when lsblk exposes physical
ancestry; unusual mappings may require further support. Bind mounts are deduped
by major/minor identity. This is mounted-filesystem performance, not bare-media
speed or a claim to identify every enclosure's internal medium.

Automatic selection chooses one writable filesystem per physical drive, with
root preferred and boot/EFI mounts excluded. HOME is used when it shares a
filesystem with the candidate mount and is writable. The dashboard lets users
select other listed filesystems. CLI `--target DIR` supports existing writable
subdirectories, including a user-owned directory on an otherwise unwritable
mount. Discovery never mounts, formats, partitions or changes permissions.

```sh
sudo apt-get install fio util-linux
g3bench drives
g3bench storage --all --allow-writes --label 'Stock baseline' --open
g3bench storage --target /media/user/ssd/bench --allow-writes --open
g3bench storage --all --allow-writes --size-mib 256 --label '256 MiB experiment'
```

Run as the normal user. No raw block device is opened. Each target gets a new
private temporary directory and exclusively-created regular file. fio is given
only that file and cannot create its own filenames. Free space must cover the
file plus at least 256 MiB or 10% of its size, whichever is greater. The mount is
rechecked before each drive. An open directory descriptor anchors file creation
and fio paths to that filesystem so a lazy unmount cannot redirect writes to root. Test drives sequentially; a missing/unavailable
drive does not prevent independent drives from running.

Testing performs writes and causes media wear. Explicit `--allow-writes` or the
dashboard acknowledgement is required. Normal completion, handled failures,
timeout and Ctrl+C clean the private directory. A power loss, forced process
kill or filesystem failure can leave `.gam3t3ch-storage-*` behind; remove only
the identified test directory after checking that no test is active. No storage
test starts merely from opening the dashboard or running the portable baseline.

## Work performed

Default file size is 1024 MiB. Each stage transfers exactly one file size:

| Order | Workload | Block size | Measurement |
| --- | --- | --- | --- |
| 1 | Sequential write, populating the file | 1 MiB | MB/s, IOPS, latency |
| 2 | Sequential read | 1 MiB | MB/s, IOPS, latency |
| 3 | Random write | 4 KiB | MB/s, IOPS, latency |
| 4 | Random read | 4 KiB | MB/s, IOPS, latency |

One psync job, queue depth one, direct I/O, repeatable random seed 731,
buffer refilling/scrambling, invalidation and end-of-write fsync are requested.
Sequential write must finish before reads are valid. An error stops that drive's
remaining stages. There is no buffered fallback or smaller automatic workload.
Default timeout is 600 seconds per stage; `--timeout` can extend it up to 7200.
An unfinished test fails rather than receiving a short-run speed result.

Direct I/O bypasses normal filesystem page caching where supported. Filesystem,
controller caches, USB bridge, CPU overhead, encryption, compression and drive
firmware still matter. Random buffer generation also consumes CPU. This is QD1 filesystem responsiveness/throughput, not
maximum advertised SSD speed. End fsync is requested, but the displayed fio
bandwidth and per-I/O completion latency must not be interpreted as a
power-loss-safe transaction rate. Wall time including process/setup/final sync
is saved separately. No per-I/O fsync is requested.

Units: MB/s = decimal bytes/second / 1,000,000; file sizes use binary MiB.
Latency reports fio mean and p99 completion latency converted from ns to ms.
Full fio JSON, including other percentiles and sync statistics, is preserved
for every successful stage. This is not a media health, data-retention or
end-to-end data-integrity test. There is no SSD steady-state preconditioning.

## Reports and comparisons

Every storage run saves result.json, standalone report.html and storage.csv.
Reports show per-drive bars, MB/s, IOPS, mean/p99 latency and individual status.
Load more local JSON files to compare drives or configuration changes.
Percent changes use the first loaded passing drive for each matching test group:
suite/workload, file size, direct I/O, engine, queue depth, job count and fio
version. Differently sized runs can be viewed but receive separate delta groups.
No combined score averages together unrelated drives.

Use at least three repetitions and inspect variation before attributing a gain.
Start with stock clocks and keep power supply, OS/build, cooling, ambient
temperature and drive fill level consistent. Change one factor at a time.
Record mount options, interfaces, shared buses and the test order; other drive
activity and thermal history can affect results. Compare a drive change and a
clock change as separate experiments.

## Tuning metadata and thermal context

All run types capture CPU governor/driver and frequency limits, swap devices,
swappiness, zswap enabled state, and zram size/compression/statistics when exposed.
No overclock is inferred from observed frequency. Run label and notes let the
user identify exact stock/overclock, cooling, PSU and software settings. The
benchmark never enables/disables zram, changes clocks, installs Pi-Apps add-ons
or tunes the kernel itself.

Active telemetry adds swap used, zram physical allocation and raw kernel memory
pressure data. Offline charts include temperature, frequency, CPU load, RAM,
swap, zram physical use and memory-pressure `some avg10` where available. Charts
have elapsed-time/value axes and sample tooltips with the active workload stage.
Missing sensors are explicitly unavailable. These samples have overhead and
are consistent within this suite version. There are no idle monitoring timers.

Zram is compressed memory, not additional physical RAM. Its configured disk
size must not be added to installed RAM. The current small compute test may
never exercise swap. A dedicated controlled memory-pressure workload and
application scenarios remain future work; current zram telemetry alone does
not establish whether a Pi-Apps memory configuration improved performance.

Method references: [fio options and JSON](https://fio.readthedocs.io/en/latest/fio_doc.html),
[Linux zram statistics](https://docs.kernel.org/admin-guide/blockdev/zram.html).
