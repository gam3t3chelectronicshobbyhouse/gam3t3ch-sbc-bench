import argparse
import csv
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
import webbrowser

from . import VERSION, WORKLOAD
from .report import export_report
from .scoring import scores
from .system import Sampler, cpu_ticks, hardware, processes
from .system import memory
from .compatibility import prepare, memory_check, state


def atomic_json(path, data):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2, allow_nan=False), encoding="utf-8")
    temp.replace(path)


def binary(name):
    root = Path(__file__).resolve().parent.parent
    suffix = ".exe" if os.name == "nt" else ""
    for candidate in (root / "build" / (name + suffix), root / "build" / "Release" / (name + suffix)):
        if candidate.is_file():
            return str(candidate)
    return shutil.which(name)


def execute(path, args, timeout=600):
    completed = subprocess.run([path, *args], capture_output=True, text=True, timeout=timeout)
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or f"exit status {completed.returncode}")
    return json.loads(completed.stdout)


def run(args):
    native = binary("g3bench-native")
    gpu_tool = binary("g3bench-gpu")
    hw = hardware()
    native_info, plan = prepare(hw, native, gpu_tool, execute, headless=args.headless, compat=args.compat, fullscreen=args.fullscreen)
    print("Board: " + hw["board_model"])
    for name, test in plan.items():
        print(f"{name.upper()}: {test['status'].upper()} — {test['reason']}")
    root = Path(args.output).resolve()
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc)
    run_id = stamp.strftime("%Y%m%dT%H%M%S") + "-" + os.urandom(3).hex()
    folder = root / run_id
    folder.mkdir()
    start = time.monotonic()
    data = {"schema_version": 2, "benchmark_version": VERSION, "workload_id": WORKLOAD,
            "timestamp": stamp.isoformat(), "run_id": run_id, "hardware": hw,
            "native_build": native_info,
            "test_status": plan,
            "configuration": {"mode": "quick", "compatibility": args.compat, "fullscreen": args.fullscreen,
                              "resolution": [640, 360] if args.compat else [1280, 720],
                              "telemetry_interval_seconds": 1, "idle_seconds": 3, "idle_threshold_percent": 10,
                              "threads": 1, "memory_buffer_bytes": 33554432},
            "status": "preflight", "stage": "Idle check", "telemetry": [], "results": {}, "errors": {},
            "power": None, "scores": scores({}), "classification": "COMPATIBILITY" if args.compat else "BASELINE"}
    data["configuration"]["report_updates"] = "stage-boundaries-and-after-run"
    data["configuration"].update(label=getattr(args, "label", "Stock baseline"), notes=getattr(args, "notes", ""))
    result_path = folder / "result.json"
    report_path = folder / "report.html"
    stop = threading.Event()
    publish_lock = threading.Lock()
    def publish():
        with publish_lock:
            atomic_json(result_path, data)
            export_report(data, report_path)
    sampler = Sampler()
    def sample():
        value = sampler.sample()
        value.update(elapsed_seconds=round(time.monotonic() - start, 3), stage=data["stage"])
        data["telemetry"].append(value)
    def telemetry():
        while not stop.wait(1):
            try:
                sample()
            except Exception as exc:
                data["errors"]["telemetry"] = str(exc)
    sample()
    before, first = cpu_ticks(), processes()
    time.sleep(3)
    after, last = cpu_ticks(), processes()
    utilization = None
    if before and after and after[0] > before[0]:
        utilization = 100 * (1 - (after[1] - before[1]) / (after[0] - before[0]))
    top = sorted([{"pid": pid, "name": name, "cpu_ticks": ticks - first.get(pid, (name, ticks))[1]}
                  for pid, (name, ticks) in last.items()], key=lambda row: row["cpu_ticks"], reverse=True)[:5]
    data["preflight"] = {"cpu_utilization": utilization, "top_processes": top}
    busy = utilization is not None and utilization > 10
    if busy:
        print(f"SYSTEM NOT IDLE: {utilization:.1f}% CPU; major processes: {top}")
    if busy and not args.as_configured:
        data.update(status="cancelled", stage="Cancelled: system not idle")
        for name, test in list(plan.items()):
            if test["status"] == "ready":
                plan[name] = state("skipped", "Run cancelled: system not idle.")
        atomic_json(result_path, data)
        export_report(data, report_path)
        print(f"Saved {result_path}. Rerun with --as-configured to accept background load.")
        return 2
    if args.as_configured:
        data["classification"] = "AS-CONFIGURED"
    if data["hardware"]["platform"] != "Linux":
        data["classification"] = "DEVELOPMENT"
    if utilization is None:
        data["preflight"]["warning"] = "Idle utilization unavailable; comparison eligibility withheld"
    data["status"] = "running"
    thread = threading.Thread(target=telemetry, daemon=True)
    thread.start()
    exit_status = 0
    try:
        for stage in ("cpu", "memory", "gpu"):
            data["stage"] = stage.upper()
            publish()
            print(f"[{time.monotonic()-start:.1f}s] {stage.upper()}", flush=True)
            tool = native if stage != "gpu" else gpu_tool
            if plan[stage]["status"] != "ready":
                continue
            if stage == "memory":
                current_memory = memory()
                check = memory_check({"ram_bytes": current_memory.get("MemTotal"), "memory_available_bytes": current_memory.get("MemAvailable")})
                if check["status"] != "ready":
                    plan[stage] = check
                    continue
            plan[stage] = state("running", "Executing the fixed baseline workload.")
            flags = [stage] if stage != "gpu" else (["--compat"] if args.compat else []) + (["--fullscreen"] if args.fullscreen else [])
            try:
                measurement = execute(tool, flags)
                if stage == "gpu" and (measurement.get("suite_version") != VERSION or measurement.get("workload_id") != WORKLOAD):
                    raise RuntimeError("GPU suite/workload mismatch. Rebuild the native tools.")
                data["results"][stage] = measurement
                plan[stage] = state("passed", "Completed the fixed workload successfully; low performance is still a valid result.")
            except (RuntimeError, OSError, subprocess.SubprocessError, ValueError) as exc:
                data["errors"][stage] = str(exc)
                plan[stage] = state("failed", str(exc))
                exit_status = 1
        data["status"] = "complete" if not data["errors"] and all(test["status"] == "passed" for test in plan.values()) else "partial"
    except KeyboardInterrupt:
        data["status"] = "interrupted"
        for name, test in list(plan.items()):
            if test["status"] in {"ready", "running"}:
                plan[name] = state("interrupted" if test["status"] == "running" else "skipped", "Run interrupted by user.")
        exit_status = 130
    finally:
        stop.set()
        thread.join()
        sample()
        data["duration_seconds"] = time.monotonic() - start
        data["stage"] = data["status"].title()
        data["scores"] = scores(data["results"], args.compat)
        gpu = data["results"].get("gpu", {})
        data["hardware"].update(gpu_renderer=gpu.get("renderer"), graphics_driver=gpu.get("driver"))
        temperatures = [v["temperature_c"] for v in data["telemetry"] if v["temperature_c"] is not None]
        bits = [v["throttled_bits"] for v in data["telemetry"] if v["throttled_bits"] is not None]
        data["thermal_summary"] = {"start_c": temperatures[0] if temperatures else None,
                                   "average_c": sum(temperatures) / len(temperatures) if temperatures else None,
                                   "peak_c": max(temperatures, default=None), "end_c": temperatures[-1] if temperatures else None,
                                   "throttling_observed": any(v & 4 for v in bits) if bits else None,
                                   "historical_throttle_flag": any(v & (1 << 18) for v in bits) if bits else None,
                                   "frequency_reduction_samples": sum(b["cpu_mhz"] < a["cpu_mhz"] for a, b in zip(data["telemetry"], data["telemetry"][1:]) if a["cpu_mhz"] is not None and b["cpu_mhz"] is not None)}
        data["comparison_eligible"] = (data["status"] == "complete" and data["classification"] == "BASELINE" and utilization is not None)
        atomic_json(result_path, data)
        export_report(data, report_path)
        with (folder / "summary.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["version", "run_id", "classification", *data["scores"]])
            writer.writerow([VERSION, run_id, data["classification"], *data["scores"].values()])
    if args.open:
        webbrowser.open(report_path.as_uri())
    print(json.dumps({"status": data["status"], "test_status": plan, "scores": data["scores"], "result": str(result_path), "report": str(report_path)}, indent=2))
    return exit_status


def main():
    parser = argparse.ArgumentParser(description="GAM3T3CH SBC Bench")
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("detect", help="Print hardware and telemetry")
    sub.add_parser("drives", help="List connected Linux drives and writable filesystem candidates; no I/O test")
    storage = sub.add_parser("storage", help="Per-drive temporary-file read/write tests; requires fio on Linux")
    storage.add_argument("--all", action="store_true", help="One eligible filesystem per physical drive")
    storage.add_argument("--target", action="append", help="Existing test directory; repeat for multiple filesystems")
    storage.add_argument("--allow-writes", action="store_true", help="Acknowledge temporary-file writes on selected drives")
    storage.add_argument("--size-mib", type=int, default=1024, help="Fixed file and I/O bytes per stage in MiB (default 1024)")
    storage.add_argument("--timeout", type=int, default=600, help="Per-stage timeout in seconds; incomplete stages fail")
    storage.add_argument("--output", default="results")
    storage.add_argument("--as-configured", action="store_true")
    storage.add_argument("--label", default="Stock baseline")
    storage.add_argument("--notes", default="")
    storage.add_argument("--open", action="store_true")
    ui = sub.add_parser("ui", help="Launch the lightweight local dashboard")
    ui.add_argument("--port", type=int, default=0, help="Loopback port; 0 selects a free port")
    ui.add_argument("--no-open", action="store_true")
    ui.add_argument("--output", default="results")
    ui.add_argument("--godot", help="Optional Godot 4 executable; no engine is launched while idle")
    showcase = sub.add_parser("showcase", help="Optional Godot 4 reactor scene; separate, unscored FPS")
    showcase.add_argument("--godot", help="Godot 4 executable, or set G3BENCH_GODOT")
    showcase.add_argument("--output", default="results")
    showcase.add_argument("--fullscreen", action="store_true")
    showcase.add_argument("--as-configured", action="store_true")
    showcase.add_argument("--open", action="store_true")
    showcase.add_argument("--smoke-test", action="store_true", help="Headless scene validation only; no performance result")
    showcase.add_argument("--label", default="Stock baseline")
    showcase.add_argument("--notes", default="")
    check = sub.add_parser("check", help="Detect board and check test availability without benchmarking")
    check.add_argument("--headless", action="store_true")
    check.add_argument("--compat", action="store_true")
    check.add_argument("--fullscreen", action="store_true")
    quick = sub.add_parser("quick", help="Fixed CPU, memory and optional GPU run")
    quick.add_argument("--headless", action="store_true")
    quick.add_argument("--compat", action="store_true", help="640x360 GPU; excluded from official GPU scoring")
    quick.add_argument("--fullscreen", action="store_true")
    quick.add_argument("--as-configured", action="store_true", help="Accept background load and label the run")
    quick.add_argument("--output", default="results")
    quick.add_argument("--open", action="store_true", help="Open the report after measurement finishes")
    quick.add_argument("--label", default="Stock baseline")
    quick.add_argument("--notes", default="")
    report = sub.add_parser("report", help="Regenerate a standalone HTML report")
    report.add_argument("result", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "drives":
            from .storage import discover
            print(json.dumps({"drives": discover()}, indent=2))
            return 0
        if args.command == "storage":
            from .storage import run_storage
            return run_storage(args)
        if args.command == "ui":
            from .ui import serve
            return serve(args)
        if args.command == "showcase":
            from .showcase import run_showcase
            return run_showcase(args)
        if args.command == "detect":
            print(json.dumps({"hardware": hardware(), "telemetry": Sampler().sample()}, indent=2))
            return 0
        if args.command == "check":
            hw = hardware()
            info, plan = prepare(hw, binary("g3bench-native"), binary("g3bench-gpu"), execute, headless=args.headless, compat=args.compat, fullscreen=args.fullscreen)
            print(json.dumps({"hardware": hw, "native_build": info, "test_status": plan}, indent=2))
            return 0
        if args.command == "report":
            target = args.result.with_suffix(".html")
            export_report(json.loads(args.result.read_text(encoding="utf-8")), target)
            print(target.resolve())
            return 0
        return run(args)
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"g3bench: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
