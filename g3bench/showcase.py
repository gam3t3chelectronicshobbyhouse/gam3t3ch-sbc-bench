"""Optional, finite-lifetime Godot process; no engine is started at import."""
import datetime
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import threading
import time
import webbrowser

from . import VERSION
from .report import export_report
from .scoring import scores
from .system import Sampler, cpu_ticks, hardware, processes

SHOWCASE_ID = "reactor-showcase-0.3"
PROJECT = Path(__file__).resolve().parent.parent / "showcase"


def find_engine(explicit=None):
    installed = PROJECT.parent / "runtime" / "godot"
    bundled = next((str(path) for path in (installed / "godot.exe", installed / "godot", installed / "Godot.app" / "Contents" / "MacOS" / "Godot") if path.is_file()), None)
    candidate = explicit or os.environ.get("G3BENCH_GODOT") or bundled or shutil.which("godot4") or shutil.which("godot")
    if not candidate:
        return None
    path = Path(candidate).expanduser().resolve()
    # Launch the actual engine, not a console wrapper with a separate child.
    if path.name.endswith("_console.exe"):
        direct = path.with_name(path.name.replace("_console.exe", ".exe"))
        if direct.is_file():
            path = direct
    return str(path) if path.is_file() else None


def stop_process(process):
    """Stop only the process tree created for this requested benchmark."""
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, timeout=10)
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        if os.name != "nt":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        process.wait(timeout=5)


def process_options():
    return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}


def run_showcase(args):
    from .__main__ import atomic_json
    stamp = datetime.datetime.now(datetime.timezone.utc)
    folder = Path(args.output).resolve() / (stamp.strftime("%Y%m%dT%H%M%S") + "-showcase-" + os.urandom(3).hex())
    folder.mkdir(parents=True)
    data = {"schema_version": 2, "benchmark_version": VERSION, "workload_id": SHOWCASE_ID,
            "timestamp": stamp.isoformat(), "run_id": folder.name, "hardware": hardware(),
            "configuration": {"mode": "showcase", "resolution": [1280, 720], "scene_seconds": 10,
                              "renderer": "gl_compatibility", "report_updates": "after-run", "fullscreen": args.fullscreen},
            "classification": "SMOKE_TEST" if args.smoke_test else "SHOWCASE",
            "status": "partial", "stage": "Showcase preflight", "test_status": {}, "telemetry": [],
            "results": {}, "scores": scores({}), "errors": {}, "power": None, "comparison_eligible": False}
    stop = threading.Event()
    data["configuration"].update(label=getattr(args, "label", "Stock baseline"), notes=getattr(args, "notes", ""))
    logger = None
    started = time.monotonic()
    session = getattr(args, "_session", None)
    if session:
        session.attach(data, started)
    sampler = None if session else Sampler()
    def sample():
        if session:
            return session.sample()
        value = sampler.sample()
        value.update(elapsed_seconds=round(time.monotonic() - started, 3), stage=data["stage"])
        data["telemetry"].append(value)
    def log_telemetry():
        while not stop.wait(1):
            try:
                sample()
            except Exception as exc:
                data["errors"]["telemetry"] = str(exc)
    def outcome(status, reason):
        data["test_status"]["showcase"] = {"status": status, "reason": reason}
    code = 0
    try:
        engine = find_engine(args.godot)
        if not engine:
            outcome("unavailable", "Godot 4 is optional. Install a compatible engine and pass --godot PATH or set G3BENCH_GODOT.")
        else:
            version = subprocess.check_output([engine, "--version"], text=True, timeout=15).strip()
            data["configuration"]["engine_version"] = version
            if not version.startswith("4."):
                outcome("unsupported", "This showcase requires Godot 4 with the Compatibility renderer.")
            else:
                before, first = cpu_ticks(), processes()
                time.sleep(3)
                after, last = cpu_ticks(), processes()
                utilization = None
                if before and after and after[0] > before[0]:
                    utilization = 100 * (1 - (after[1] - before[1]) / (after[0] - before[0]))
                top = sorted([{"pid": pid, "name": name, "cpu_ticks": ticks - first.get(pid, (name, ticks))[1]}
                              for pid, (name, ticks) in last.items()], key=lambda row: row["cpu_ticks"], reverse=True)[:5]
                data["preflight"] = {"cpu_utilization": utilization, "top_processes": top}
                if utilization is not None and utilization > 10 and not args.as_configured:
                    data["status"] = "cancelled"
                    outcome("skipped", "SYSTEM NOT IDLE. Rerun with --as-configured to accept background load.")
                else:
                    data["stage"] = "Godot reactor showcase"
                    if args.as_configured:
                        data["configuration"]["background_load_accepted"] = True
                    sample()
                    if not session:
                        logger = threading.Thread(target=log_telemetry, daemon=True)
                        logger.start()
                    raw = folder / "showcase.json"
                    command = [engine, "--path", str(PROJECT), "--rendering-method", "gl_compatibility"]
                    if args.smoke_test:
                        command += ["--headless"]
                    if args.fullscreen:
                        command += ["--fullscreen"]
                    command += ["--", "--output", str(raw)]
                    if args.fullscreen and not args.smoke_test:
                        command += ["--presentation-fullscreen"]
                    if args.smoke_test:
                        command += ["--smoke-test"]
                    with (folder / "engine.log").open("w", encoding="utf-8") as log:
                        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, **process_options())
                        try:
                            returncode = process.wait(timeout=90)
                        except (KeyboardInterrupt, subprocess.TimeoutExpired):
                            stop_process(process)
                            raise
                    if returncode or not raw.is_file():
                        raise RuntimeError("Godot could not complete the scene. Inspect engine.log for renderer, driver or script errors.")
                    measurement = json.loads(raw.read_text(encoding="utf-8"))
                    if measurement.get("workload_id") != SHOWCASE_ID or measurement.get("scored") is not False:
                        raise ValueError("Invalid showcase workload identity")
                    status = measurement.get("status")
                    if status not in {"passed", "smoke_validated", "interrupted", "unavailable"}:
                        raise ValueError("Invalid showcase completion status")
                    data["results"]["showcase"] = measurement
                    outcome(status, measurement.get("reason", "Showcase stopped."))
                    data["status"] = "complete" if status in {"passed", "smoke_validated"} else "partial"
                    data["hardware"].update(gpu_renderer=measurement.get("renderer"), graphics_driver=version)
    except KeyboardInterrupt:
        outcome("interrupted", "Stopped by user.")
        data["status"] = "interrupted"
        code = 130
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        outcome("failed", str(exc))
        data["errors"]["showcase"] = str(exc)
        code = 1
    finally:
        stop.set()
        if logger:
            logger.join()
            sample()
        temperatures = [x["temperature_c"] for x in data["telemetry"] if x["temperature_c"] is not None]
        data["thermal_summary"] = {"peak_c": max(temperatures, default=None), "throttling_observed": None}
        data["duration_seconds"] = time.monotonic() - started
        data["stage"] = data["status"].title()
        atomic_json(folder / "result.json", data)
        export_report(data, folder / "report.html")
    if args.open:
        webbrowser.open((folder / "report.html").as_uri())
    print(json.dumps({"status": data["status"], "test_status": data["test_status"], "result": str(folder / "result.json"), "report": str(folder / "report.html")}, indent=2))
    return code
