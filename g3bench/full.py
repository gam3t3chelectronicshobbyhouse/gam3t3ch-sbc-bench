"""Sequential full checkup with one continuous sensor sampler."""
import argparse
import csv
import datetime
import json
import os
from pathlib import Path
import threading
import time
import webbrowser

from . import VERSION, WORKLOAD
from .report import export_report
from .scoring import scores
from .system import hardware, Sampler

FULL_ID = "full-checkup-0.1"


class ContinuousTelemetry:
    def __init__(self, data):
        self.data = data
        self.sampler = Sampler()
        self.started = time.monotonic()
        self.active = None
        self.child_started = None
        self.prefix = "Preparing"
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._log, daemon=True)

    def attach(self, data, started):
        with self.lock:
            self.active, self.child_started = data, started
            data["configuration"]["full_session"] = self.data["run_id"]
            data["comparison_eligible"] = False

    def detach(self):
        with self.lock:
            self.active = self.child_started = None

    def sample(self):
        with self.lock:
            value = self.sampler.sample()
            now = time.monotonic()
            stage = self.prefix + (" / " + self.active["stage"] if self.active else "")
            value.update(elapsed_seconds=round(now - self.started, 3), stage=stage)
            self.data["stage"] = stage
            self.data["telemetry"].append(value)
            if self.active is not None:
                self.active["telemetry"].append({**value, "elapsed_seconds": round(now - self.child_started, 3)})

    def _log(self):
        while not self.stop.wait(1):
            try:
                self.sample()
            except Exception as exc:
                self.data["errors"]["telemetry"] = str(exc)

    def close(self):
        self.stop.set()
        self.thread.join()
        self.detach()
        self.sample()


def run_full(args):
    from .__main__ import run, atomic_json
    from .storage import run_storage, STORAGE_ID
    from .showcase import run_showcase, SHOWCASE_ID
    if not args.skip_storage and not args.allow_writes:
        raise ValueError("Full checkup includes temporary drive writes. Use --allow-writes, or explicitly choose --skip-storage.")
    if not 16 <= args.size_mib <= 16384 or not 10 <= args.timeout <= 7200:
        raise ValueError("Invalid storage file size or timeout")
    stamp = datetime.datetime.now(datetime.timezone.utc)
    folder = Path(args.output).resolve() / (stamp.strftime("%Y%m%dT%H%M%S") + "-full-" + os.urandom(3).hex())
    folder.mkdir(parents=True)
    data = {"schema_version": 2, "benchmark_version": VERSION, "workload_id": FULL_ID,
            "timestamp": stamp.isoformat(), "run_id": folder.name, "hardware": hardware(),
            "configuration": {"mode": "full", "label": args.label, "notes": args.notes,
                              "resolution": [640, 360] if args.compat else [1280, 720], "fullscreen": args.fullscreen,
                              "threads": 1, "memory_buffer_bytes": 33554432, "size_mib": args.size_mib,
                              "storage_skipped": args.skip_storage, "headless": args.headless,
                              "background_load_accepted": args.as_configured,
                              "component_workloads": [WORKLOAD, STORAGE_ID, SHOWCASE_ID],
                              "telemetry_policy": "one-continuous-sampler"},
            "classification": "FULL_CHECKUP", "status": "running", "stage": "Preparing full checkup",
            "test_status": {}, "results": {}, "telemetry": [], "errors": {}, "power": None,
            "scores": scores({}), "comparison_eligible": False, "components": []}
    session = ContinuousTelemetry(data)
    session.sample()
    session.thread.start()
    code = 0
    try:
        jobs = [("portable", run)]
        if args.skip_storage:
            data["test_status"]["storage"] = {"status": "skipped", "reason": "Storage explicitly omitted; no temporary drive writes."}
        else:
            jobs.append(("storage", run_storage))
        if args.headless:
            data["test_status"]["showcase"] = {"status": "skipped", "reason": "Headless full checkup omits the graphical Godot scene."}
        else:
            jobs.append(("showcase", run_showcase))
        for index, (name, runner) in enumerate(jobs):
            session.prefix = name.upper()
            atomic_json(folder / "result.json", data)
            options = vars(args).copy()
            options.update(output=str(folder / "components" / name), open=False, _session=session,
                           smoke_test=False, all=not bool(args.target))
            result_code = runner(argparse.Namespace(**options))
            session.detach()
            paths = list((folder / "components" / name).glob("*/result.json"))
            if not paths:
                raise RuntimeError(name + " did not save a result")
            component = json.loads(paths[-1].read_text(encoding="utf-8"))
            data["components"].append({"name": name, "workload_id": component["workload_id"],
                                       "status": component["status"], "path": str(paths[-1].relative_to(folder))})
            data["results"].update(component["results"])
            if name == "storage" and "storage" in data["results"]:
                data["results"]["storage"]["configuration"] = component["configuration"]
            for key, status in component.get("test_status", {}).items():
                data["test_status"][("storage / " if name == "storage" else "") + key] = status
            for key, error in component.get("errors", {}).items():
                data["errors"][name + " / " + key] = error
            if name == "portable":
                data["native_build"] = component.get("native_build")
            for field in ("gpu_renderer", "graphics_driver"):
                if component["hardware"].get(field) and not data["hardware"].get(field):
                    data["hardware"][field] = component["hardware"][field]
            interrupted = any(row["status"] == "interrupted" for row in component.get("test_status", {}).values())
            if result_code == 130 or component["status"] in {"interrupted", "cancelled"} or interrupted:
                data["status"] = "interrupted" if interrupted else component["status"]
                for remaining, _ in jobs[index + 1:]:
                    data["test_status"].setdefault(remaining, {"status": "skipped", "reason": "Full checkup was stopped before this component."})
                code = result_code or 130
                break
            if result_code:
                code = 1
        else:
            statuses = [value["status"] for value in data["test_status"].values()]
            data["status"] = "complete" if statuses and all(status in {"passed", "skipped"} for status in statuses) and not data["errors"] else "partial"
    except KeyboardInterrupt:
        data["status"] = "interrupted"
        code = 130
    except (OSError, RuntimeError, ValueError) as exc:
        data["status"] = "partial"
        data["errors"]["full"] = str(exc)
        code = 1
    finally:
        session.close()
        data["duration_seconds"] = round(time.monotonic() - session.started, 3)
        temperatures = [s["temperature_c"] for s in data["telemetry"] if isinstance(s.get("temperature_c"), (int, float))]
        bits = [s["throttled_bits"] for s in data["telemetry"] if s.get("throttled_bits") is not None]
        data["thermal_summary"] = {"start_c": temperatures[0] if temperatures else None,
                                   "end_c": temperatures[-1] if temperatures else None,
                                   "peak_c": max(temperatures, default=None),
                                   "average_c": sum(temperatures) / len(temperatures) if temperatures else None,
                                   "throttling_observed": any(value & 4 for value in bits) if bits else None}
        data["scores"] = scores(data["results"], args.compat)
        data["stage"] = data["status"].title()
        atomic_json(folder / "result.json", data)
        export_report(data, folder / "report.html")
        with (folder / "summary.csv").open("w", newline="", encoding="utf-8") as output:
            writer = csv.writer(output)
            writer.writerow(["test", "status", "reason"])
            writer.writerows((name, test["status"], test["reason"]) for name, test in data["test_status"].items())
    if args.open:
        webbrowser.open((folder / "report.html").as_uri())
    print(json.dumps({"status": data["status"], "result": str(folder / "result.json"), "report": str(folder / "report.html")}, indent=2))
    return code
