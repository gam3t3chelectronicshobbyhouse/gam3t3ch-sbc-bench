"""File-only Linux storage measurements. Never opens a raw block device."""
import datetime
import csv
from contextlib import contextmanager
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import threading
import time
import webbrowser

from . import VERSION
from .report import export_report
from .scoring import scores
from .system import Sampler, command, cpu_ticks, hardware, processes, read

STORAGE_ID = "storage-file-0.1"
MIB = 1024 * 1024
JOBS = (("sequential_write", "write", "1M"), ("sequential_read", "read", "1M"),
        ("random_write_4k", "randwrite", "4k"), ("random_read_4k", "randread", "4k"))


def json_command(args):
    value = command(args)
    return json.loads(value) if value else {}


def discover():
    """Inventory physical-backed filesystems, including unavailable drives."""
    if platform.system() != "Linux":
        return []
    tree = json_command(["lsblk", "--json", "--bytes", "--output",
                         "NAME,PATH,TYPE,SIZE,MODEL,TRAN,RO,MAJ:MIN,FSTYPE"])
    mounts = json_command(["findmnt", "--json", "--list", "--output", "SOURCE,TARGET,FSTYPE,OPTIONS,MAJ:MIN"])
    devices = {}
    disks = {}
    def walk(node, parents):
        if node.get("type") == "disk":
            if str(node.get("name", "")).startswith(("loop", "ram", "zram")):
                return
            parents = parents + [node["path"]]
            kind = read("/sys/class/block/" + node["name"] + "/device/type")
            disks[node["path"]] = {"device": node["path"], "model": node.get("model"),
                                  "transport": node.get("tran"), "capacity_bytes": node.get("size"),
                                  "media": "eMMC" if kind == "MMC" else "SD" if kind == "SD" else node.get("tran") or "unknown"}
        if parents:
            devices[node.get("maj:min")] = (node, parents)
        for child in node.get("children", []):
            walk(child, parents)
    for node in tree.get("blockdevices", []):
        walk(node, [])
    rows, seen, represented = [], set(), set()
    for mount in mounts.get("filesystems", []):
        key = mount.get("maj:min")
        if key not in devices or key in seen:
            continue
        seen.add(key)
        node, parents = devices[key]
        represented.update(parents)
        target = mount["target"]
        candidate = Path(target)
        # Root and system mounts are usually not writable by the normal user.
        # Prefer HOME when it is on exactly the same filesystem.
        home = Path.home()
        try:
            if home.stat().st_dev == candidate.stat().st_dev and os.access(home, os.W_OK | os.X_OK):
                candidate = home
        except OSError:
            pass
        readonly = "ro" in mount.get("options", "").split(",") or node.get("ro") in (True, 1, "1")
        eligible = not readonly and candidate.is_dir() and os.access(candidate, os.W_OK | os.X_OK)
        reason = "Writable mounted filesystem" if eligible else "Read-only filesystem" if readonly else "No writable test directory; choose a directory with --target"
        rows.append({**disks[parents[0]], "id": key, "parents": parents, "source": mount.get("source"),
                     "mount": target, "filesystem": mount.get("fstype"), "mount_options": mount.get("options"),
                     "directory": str(candidate), "eligible": eligible, "selected_by_default": False,
                     "status": "ready" if eligible else "unavailable", "reason": reason})
    for device, info in disks.items():
        if device not in represented:
            rows.append({**info, "id": device, "parents": [device], "directory": None, "mount": None,
                         "eligible": False, "selected_by_default": False, "status": "unavailable",
                         "reason": "No mounted filesystem detected. Mount it normally before testing."})
    selected = set()
    # Root first; avoid automatically selecting boot/EFI partitions.
    for row in sorted(rows, key=lambda r: (r.get("mount") != "/", r.get("mount") or "")):
        boot = (row.get("mount") or "").startswith(("/boot", "/efi"))
        if row["eligible"] and not boot and not selected.intersection(row["parents"]):
            row["selected_by_default"] = True
            selected.update(row["parents"])
    return rows


def resolve_target(directory, inventory):
    path = Path(directory).expanduser().resolve(strict=True)
    if not path.is_dir() or not os.access(path, os.W_OK | os.X_OK):
        raise ValueError("Target must be an existing writable directory")
    # Reject device paths even if the caller runs with elevated privileges.
    if path == Path("/dev") or Path("/dev") in path.parents:
        raise ValueError("Raw devices and /dev targets are not allowed")
    if os.name != "nt" and any(character in str(path) for character in (":", "\\", "\n", "\r")):
        raise ValueError("Choose a directory without fio filename-list separator characters")
    mount = json_command(["findmnt", "--json", "--target", str(path), "--output", "MAJ:MIN,OPTIONS"])
    matches = mount.get("filesystems", [])
    key = matches[0].get("maj:min") if matches else None
    row = next((r for r in inventory if r["id"] == key), None)
    if not row or "ro" in matches[0].get("options", "").split(","):
        raise ValueError("Target must be on a mounted local physical-backed writable filesystem")
    return {**row, "directory": str(path), "eligible": True}


def fio_command(engine, filename, name, rw, block, size_mib):
    return [engine, "--name=" + name, "--filename=" + str(filename), "--rw=" + rw,
            "--bs=" + block, "--size=" + str(size_mib * MIB), "--io_size=" + str(size_mib * MIB),
            "--ioengine=psync", "--iodepth=1", "--numjobs=1", "--direct=1", "--invalidate=1",
            "--randrepeat=1", "--randseed=731", "--refill_buffers=1", "--scramble_buffers=1",
            "--end_fsync=1", "--allow_file_create=0", "--eta=never", "--output-format=json"]


@contextmanager
def scratch_directory(target):
    descriptor = None
    directory = target["directory"]
    try:
        if os.name == "posix":
            descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            device = os.fstat(descriptor).st_dev
            identity = str(os.major(device)) + ":" + str(os.minor(device))
            if target.get("id") and identity != target["id"]:
                raise ValueError("Target filesystem changed before file creation")
            # Anchor through our open directory, so a lazy unmount cannot redirect
            # later fio opens onto the underlying/root mount.
            directory = "/proc/" + str(os.getpid()) + "/fd/" + str(descriptor)
        with tempfile.TemporaryDirectory(prefix=".gam3t3ch-storage-", dir=directory) as scratch:
            yield scratch
    finally:
        if descriptor is not None:
            os.close(descriptor)


def measure_drive(target, engine, size_mib, timeout, stage):
    results = {}
    required = size_mib * MIB
    directory = Path(target["directory"])
    if shutil.disk_usage(directory).free < required + max(256 * MIB, required // 10):
        return {"status": "unavailable", "reason": "Insufficient free space with reserved headroom", "tests": {}}
    # A private directory and exclusive regular file keep fio away from user files.
    # Cleanup touches only this freshly-created directory, never an input path.
    with scratch_directory(target) as scratch:
        filename = Path(scratch) / "payload.bin"
        with filename.open("xb") as output:
            output.truncate(required)
        for name, rw, block in JOBS:
            stage(target, name)
            started = time.monotonic()
            try:
                process = subprocess.Popen(fio_command(engine, filename, name, rw, block, size_mib),
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                try:
                    stdout, stderr = process.communicate(timeout=timeout)
                except BaseException:
                    process.terminate()
                    try:
                        process.communicate(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.communicate()
                    raise
                raw = json.loads(stdout) if stdout.strip() else {}
                job = raw.get("jobs", [{}])[0]
                if process.returncode or job.get("error"):
                    raise RuntimeError(stderr.strip() or job.get("error") or stdout[:1000] or "fio failed")
                direction = "write" if "write" in rw else "read"
                io = job[direction]
                if io.get("io_bytes", 0) != required or io.get("runtime", 0) <= 0:
                    raise RuntimeError("fio did not complete the full requested byte count")
                latency = io.get("clat_ns", {})
                percentiles = latency.get("percentile", {})
                results[name] = {"status": "passed", "mb_s": io.get("bw_bytes", io.get("bw", 0) * 1024) / 1e6,
                                 "iops": io["iops"], "latency_mean_ms": latency.get("mean", 0) / 1e6 if latency else None,
                                 "latency_p99_ms": percentiles.get("99.000000", 0) / 1e6 if percentiles else None,
                                 "bytes": io["io_bytes"], "seconds": io["runtime"] / 1000,
                                 "wall_seconds": time.monotonic() - started, "fio": raw}
            except (OSError, RuntimeError, ValueError, KeyError, subprocess.SubprocessError) as exc:
                results[name] = {"status": "failed", "reason": str(exc)}
                # Reads are invalid if the initial file population did not finish.
                break
    for name, _, _ in JOBS:
        results.setdefault(name, {"status": "skipped", "reason": "An earlier storage stage failed"})
    passed = all(test["status"] == "passed" for test in results.values())
    return {"status": "passed" if passed else "failed", "reason": "Four fixed file workloads completed" if passed else "See individual test errors; no buffered fallback", "tests": results}


def run_storage(args):
    from .__main__ import atomic_json
    if not 16 <= args.size_mib <= 16384 or args.size_mib % 1:
        raise ValueError("Storage size must be 16–16384 MiB")
    if not 10 <= args.timeout <= 7200:
        raise ValueError("Per-stage timeout must be 10–7200 seconds")
    inventory = discover()
    targets = []
    selection_errors = []
    for directory in (args.target or []) if platform.system() == "Linux" else []:
        try:
            target = resolve_target(directory, inventory)
        except (OSError, ValueError) as exc:
            selection_errors.append({"target": {"directory": directory, "source": directory, "mount": None},
                                     "status": "unavailable", "reason": str(exc), "tests": {}})
            continue
        if target["id"] in {row["id"] for row in targets}:
            raise ValueError("Choose only one test directory per filesystem")
        targets.append(target)
    if args.all:
        if args.target:
            raise ValueError("Choose --all or --target, not both")
        targets = [row for row in inventory if row["selected_by_default"]]
    if not args.allow_writes:
        raise ValueError("Storage testing writes temporary files. Review g3bench drives, then use --allow-writes with --all or --target DIR")
    if not args.all and not args.target:
        raise ValueError("Select --all or at least one --target DIR")
    stamp = datetime.datetime.now(datetime.timezone.utc)
    folder = Path(args.output).resolve() / (stamp.strftime("%Y%m%dT%H%M%S") + "-storage-" + os.urandom(3).hex())
    folder.mkdir(parents=True)
    data = {"schema_version": 2, "benchmark_version": VERSION, "workload_id": STORAGE_ID,
            "timestamp": stamp.isoformat(), "run_id": folder.name, "hardware": hardware(),
            "configuration": {"mode": "storage", "size_mib": args.size_mib, "direct": True, "ioengine": "psync",
                              "iodepth": 1, "numjobs": 1, "timeout_seconds": args.timeout,
                              "label": args.label, "notes": args.notes},
            "classification": "STORAGE", "status": "partial", "stage": "Storage preflight", "telemetry": [],
            "test_status": {}, "results": {"storage": {"inventory": inventory, "drives": []}},
            "errors": {}, "scores": scores({}), "power": None, "comparison_eligible": False}
    data["results"]["storage"]["drives"].extend(selection_errors)
    for index, entry in enumerate(selection_errors):
        data["test_status"]["selection-" + str(index)] = {"status": entry["status"], "reason": entry["target"]["directory"] + ": " + entry["reason"]}
    start = time.monotonic()
    stop = threading.Event()
    sampler = Sampler()
    def sample():
        value = sampler.sample()
        value.update(elapsed_seconds=round(time.monotonic() - start, 3), stage=data["stage"])
        data["telemetry"].append(value)
    def logger():
        while not stop.wait(1):
            try:
                sample()
            except Exception as exc:
                data["errors"]["telemetry"] = str(exc)
    thread = None
    code = 0
    try:
        engine = shutil.which("fio")
        version = command([engine, "--version"]) if engine else None
        if platform.system() != "Linux":
            data["test_status"]["storage"] = {"status": "unsupported", "reason": "Direct-I/O storage module currently requires Linux"}
        elif not engine or not (version or "").startswith("fio-"):
            data["test_status"]["storage"] = {"status": "unavailable", "reason": "Install Flexible I/O Tester (Debian package fio)"}
        elif not targets:
            data["test_status"]["storage"] = {"status": "unavailable", "reason": "No eligible mounted writable drives selected"}
        else:
            data["configuration"]["fio_version"] = version
            before, first = cpu_ticks(), processes()
            time.sleep(3)
            after, last = cpu_ticks(), processes()
            usage = 100 * (1 - (after[1] - before[1]) / (after[0] - before[0])) if before and after and after[0] > before[0] else None
            data["preflight"] = {"cpu_utilization": usage, "top_processes": sorted(
                [{"pid": pid, "name": name, "cpu_ticks": ticks - first.get(pid, (name, ticks))[1]} for pid, (name, ticks) in last.items()],
                key=lambda row: row["cpu_ticks"], reverse=True)[:5]}
            if usage is not None and usage > 10 and not args.as_configured:
                data["status"] = "cancelled"
                data["test_status"]["storage"] = {"status": "skipped", "reason": "SYSTEM NOT IDLE; use --as-configured to accept background load"}
            else:
                data["configuration"]["background_load_accepted"] = args.as_configured
                sample()
                thread = threading.Thread(target=logger, daemon=True)
                thread.start()
                for target in targets:
                    # Re-resolve immediately before writing: unplugged/remounted drives must not silently fall back to root.
                    entry = {"target": target, "status": "running", "tests": {}}
                    data["results"]["storage"]["drives"].append(entry)
                    try:
                        current = resolve_target(target["directory"], discover())
                        if current["id"] != target["id"] or current["source"] != target["source"]:
                            raise ValueError("Drive mount changed since selection; rediscover drives")
                        def stage(row, name):
                            data["stage"] = row["source"] + " / " + name
                        entry.update(measure_drive(current, engine, args.size_mib, args.timeout, stage))
                    except (OSError, ValueError) as exc:
                        entry.update(status="unavailable", reason=str(exc))
                    data["test_status"][target["id"]] = {"status": entry["status"], "reason": target["source"] + ": " + entry["reason"]}
                data["status"] = "complete" if all(row["status"] == "passed" for row in data["results"]["storage"]["drives"]) else "partial"
                code = 0 if data["status"] == "complete" else 1
    except KeyboardInterrupt:
        data["status"] = "interrupted"
        code = 130
        data["test_status"]["storage"] = {"status": "interrupted", "reason": "Stopped by user; temporary test files cleaned up"}
        for entry in data["results"]["storage"]["drives"]:
            if entry["status"] == "running":
                entry.update(status="interrupted", reason="Stopped by user")
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        data["errors"]["storage"] = str(exc)
        data["test_status"]["storage"] = {"status": "failed", "reason": str(exc)}
        code = 1
    finally:
        stop.set()
        if thread:
            thread.join()
        sample()
        temperatures = [x["temperature_c"] for x in data["telemetry"] if x["temperature_c"] is not None]
        bits = [x["throttled_bits"] for x in data["telemetry"] if x["throttled_bits"] is not None]
        data["thermal_summary"] = {"start_c": temperatures[0] if temperatures else None,
                                   "end_c": temperatures[-1] if temperatures else None,
                                   "average_c": sum(temperatures) / len(temperatures) if temperatures else None,
                                   "peak_c": max(temperatures, default=None),
                                   "throttling_observed": any(v & 4 for v in bits) if bits else None}
        data["duration_seconds"] = time.monotonic() - start
        data["stage"] = data["status"].title()
        atomic_json(folder / "result.json", data)
        export_report(data, folder / "report.html")
        with (folder / "storage.csv").open("w", newline="", encoding="utf-8") as output:
            writer = csv.writer(output)
            writer.writerow(["label", "source", "mount", "workload", "size_mib", "status", "MB/s", "IOPS", "mean_ms", "p99_ms"])
            for drive in data["results"]["storage"]["drives"]:
                for name, test in drive["tests"].items():
                    writer.writerow([args.label, drive["target"]["source"], drive["target"]["mount"], name, args.size_mib,
                                     test["status"], test.get("mb_s"), test.get("iops"), test.get("latency_mean_ms"), test.get("latency_p99_ms")])
    if args.open:
        webbrowser.open((folder / "report.html").as_uri())
    print(json.dumps({"status": data["status"], "test_status": data["test_status"], "result": str(folder / "result.json"), "report": str(folder / "report.html")}, indent=2))
    return code
