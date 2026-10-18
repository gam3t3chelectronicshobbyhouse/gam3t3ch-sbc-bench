"""On-demand loopback dashboard. No timers, telemetry or render loop while idle."""
import json
import os
from pathlib import Path
import secrets
import selectors
import signal
import socket
import socketserver
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs
import webbrowser

from . import VERSION
from .system import hardware
from .showcase import find_engine, process_options, stop_process, SHOWCASE_ID
from .report import export_report
from .scoring import scores
from .branding import apply_branding, PRODUCT_NAME
from .install_commands import INSTALL_COMMANDS

ROOT = Path(__file__).resolve().parent.parent


class Dashboard:
    def __init__(self, output, engine=None):
        self.output = Path(output).resolve()
        self.engine = find_engine(engine)  # file lookup only; never launches Godot
        self.hardware = hardware()  # one snapshot; no idle sampler
        self.lock = threading.Lock()
        self.done = threading.Event()
        self.done.set()
        self.process = None
        self.worker = None
        self.phase = "idle"
        self.message = "Ready. Renderers and telemetry are off."
        self.result_path = None
        self.report_path = None
        self.cancel_requested = False
        self.inbox = None  # LAN listener exists only after explicit Enable.

    def snapshot(self):
        with self.lock:
            return {"phase": self.phase, "message": self.message, "report_available": self.report_path is not None}

    def start(self, kind, headless=False, fullscreen=True, as_configured=False, options=None):
        if not isinstance(kind, str) or kind not in {"quick", "showcase", "storage", "full", "graphics", "cpu", "memory", "network", "load"}:
            raise ValueError("Unknown benchmark mode")
        options = options or {}
        for key, limit in (("label", 120), ("notes", 1000)):
            if not isinstance(options.get(key, ""), str) or len(options.get(key, "")) > limit:
                raise ValueError("Invalid run label or notes")
        if kind in {"storage", "full"}:
            targets = options.get("targets")
            size = options.get("size_mib", 1024)
            if not isinstance(targets, list) or not (0 if kind == "full" else 1) <= len(targets) <= 32 or any(not isinstance(t, str) or len(t) > 1024 for t in targets):
                raise ValueError("Select at least one mounted drive")
            if type(size) is not int or not 16 <= size <= 16384:
                raise ValueError("File size must be 16–16384 MiB")
            if options.get("allow_writes") is not True:
                raise ValueError("Acknowledge temporary-file writes before starting storage tests")
        if type(options.get('load_seconds',60)) is not int or not 1<=options.get('load_seconds',60)<=600:raise ValueError('Load duration must be 1–600 seconds')
        if options.get('iperf_host') and (not isinstance(options['iperf_host'],str) or len(options['iperf_host'])>253):raise ValueError('Invalid iperf host')
        if options.get('profile','auto') not in {'auto','standard','legacy'}:raise ValueError('Invalid test profile')
        if options.get('renderer','compatibility') not in {'compatibility','vulkan'}:raise ValueError('Invalid renderer')
        if kind == 'network' and options.get('allow_network') is not True:raise ValueError('Acknowledge external network traffic first')
        with self.lock:
            if self.phase == "running":
                raise ValueError("A benchmark is already running")
            if kind == "showcase" and not self.engine:
                raise ValueError("Godot 4 not found. Start the dashboard with --godot PATH.")
            self.phase = "running"
            self.message = "Benchmark running. Dashboard updates are paused until it exits."
            self.result_path = self.report_path = None
            self.cancel_requested = False
            self.done = threading.Event()
            folder = self.output / ("dashboard-" + time.strftime("%Y%m%dT%H%M%S") + "-" + secrets.token_hex(3))
            self.worker = threading.Thread(target=self._run, args=(folder, kind, headless, fullscreen, as_configured, options), daemon=True)
            self.worker.start()

    def _run(self, folder, kind, headless, fullscreen, as_configured, options):
        try:
            folder.mkdir(parents=True)
            command = ([sys.executable] if getattr(sys, "frozen", False) else [sys.executable, "-m", "g3bench"]) + [kind, "--output", str(folder)]
            command += ["--label=" + options.get("label", "Stock baseline"), "--notes=" + options.get("notes", "")]
            if kind in {'quick','graphics','cpu','memory','full'}:command += ['--profile',options.get('profile','auto')]
            if kind in {'showcase','full'}:command += ['--renderer',options.get('renderer','compatibility')]
            if kind in {'network','full'} and options.get('iperf_host'):command += ['--iperf-host',options['iperf_host']]
            if kind in {'full','load'}:command += ['--load-seconds',str(options.get('load_seconds',60))]
            if kind in {'network','full'} and options.get('allow_network') is True:command += ['--allow-network']
            if kind == "showcase":
                command += ["--godot", self.engine]
            if kind in {"storage", "full"}:
                command += ["--allow-writes", "--size-mib=" + str(options.get("size_mib", 1024))]
                command += ["--target=" + target for target in options["targets"]]
            if kind == "full" and self.engine:
                command += ["--godot", self.engine]
            if headless and kind in {"quick", "full"}:
                command += ["--headless"]
            if fullscreen and kind not in {"storage","network","load"}:
                command += ["--fullscreen"]
            elif kind not in {"storage","network","load"}:
                command += ["--windowed"]
            if as_configured:
                command += ["--as-configured"]
            with (folder / "runner.log").open("w", encoding="utf-8") as log:
                with self.lock:
                    if self.cancel_requested:
                        self.phase, self.message = "cancelled", "Cancelled before launch."
                        return
                    self.process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, **process_options())
                    process = self.process
                code = process.wait()
            results = sorted(folder.glob("*/result.json"))
            if not results and self.cancel_requested:
                cancelled = folder / "cancelled"
                cancelled.mkdir()
                result = {"schema_version": 2, "benchmark_version": VERSION,
                          "workload_id": SHOWCASE_ID if kind == "showcase" else "storage-file-0.1" if kind == "storage" else "baseline-0.1",
                          "hardware": self.hardware, "configuration": {"mode": kind},
                          "classification": "SHOWCASE" if kind == "showcase" else "INTERRUPTED",
                          "status": "cancelled", "stage": "Cancelled by user", "telemetry": [],
                          "test_status": {"run": {"status": "interrupted", "reason": "Process tree stopped by user. Incomplete measurements were discarded."}},
                          "results": {}, "scores": scores({}), "errors": {}, "power": None,
                          "comparison_eligible": False}
                (cancelled / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
                export_report(result, cancelled / "report.html")
                results = [cancelled / "result.json"]
            with self.lock:
                if results:
                    self.result_path = results[-1]
                    self.report_path = self.result_path.with_name("report.html")
                    result = json.loads(self.result_path.read_text(encoding="utf-8"))
                    if result["status"] in {"running", "preflight"}:
                        result.update(status="cancelled" if self.cancel_requested else "partial", stage="Worker stopped before completion",
                                      scores=scores({}), comparison_eligible=False)
                        result.setdefault("test_status", {})["run"] = {"status": "interrupted" if self.cancel_requested else "failed", "reason": "Worker exited before final results were saved."}
                        self.result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
                        export_report(result, self.report_path)
                    self.phase = result["status"]
                    statuses = result.get("test_status", {})
                    self.message = " · ".join(f"{name.upper()}: {test['status']}" for name, test in statuses.items())
                else:
                    self.phase = "cancelled" if self.cancel_requested else "failed"
                    self.message = "Stopped; no completed report. See " + str(folder / "runner.log")
                if code and self.phase == "complete":
                    self.phase = "failed"
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            with self.lock:
                self.phase, self.message = "failed", str(exc)
        finally:
            with self.lock:
                self.process = None
                self.done.set()

    def cancel(self):
        with self.lock:
            self.cancel_requested = True
            process = self.process
        if process and process.poll() is None:
            if os.name != "nt":
                try:
                    os.killpg(process.pid, signal.SIGINT)
                    process.wait(timeout=15)
                except ProcessLookupError:
                    pass
                except subprocess.TimeoutExpired:
                    stop_process(process)
            else:
                stop_process(process)


def serve(args, ready=None):
    dashboard = Dashboard(args.output, args.godot)
    token = secrets.token_urlsafe(32)
    wake_read, wake_write = socket.socketpair()
    closing = threading.Event()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *unused):
            pass

        def reply(self, value, code=200, content_type="application/json"):
            body = value if isinstance(value, bytes) else json.dumps(value).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def host_ok(self):
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

        def do_GET(self):
            if not self.host_ok():
                return self.reply({"error": "Loopback host required"}, 403)
            route = urlsplit(self.path)
            if route.path == "/":
                data = {"version": VERSION, "hardware": dashboard.hardware, "engine_available": bool(dashboard.engine), "token": token, "state": dashboard.snapshot(), "install_commands": INSTALL_COMMANDS}
                payload = json.dumps(data).replace("<", "\\u003c").replace("&", "\\u0026")
                page = apply_branding(Path(__file__).with_name("dashboard.html").read_text(encoding="utf-8")).replace("__DASHBOARD_DATA__", payload)
                return self.reply(page.encode("utf-8"), content_type="text/html; charset=utf-8")
            if route.path == "/events":
                if parse_qs(route.query).get("token") != [token]:
                    return self.reply({"error": "Invalid token"}, 403)
                with dashboard.lock:
                    done = dashboard.done
                # Blocks without polling or heartbeats; one event after the worker exits.
                done.wait()
                payload = "data: " + json.dumps(dashboard.snapshot()) + "\n\n"
                try:
                    return self.reply(payload.encode("utf-8"), content_type="text/event-stream")
                except (BrokenPipeError, ConnectionResetError):
                    return
            if route.path == "/diagnostics":
                if dashboard.snapshot()['phase']=='running':return self.reply({'error':'Wait for the active benchmark'},409)
                from .diagnostics import collect, advice, test_profile
                result={'hardware':dashboard.hardware,'configuration':{},'diagnostics':collect(),'telemetry':[]}
                result['recommendations']=advice(result);result['recommended_profile']=test_profile(dashboard.hardware)
                return self.reply(result)
            if route.path == "/drives":
                if dashboard.snapshot()["phase"] == "running":
                    return self.reply({"error": "Wait for the active run before rediscovering drives"}, 409)
                from .storage import discover
                try:
                    return self.reply({"drives": discover(), "reason": "Drive tests require Linux / Raspberry Pi OS." if os.name == "nt" else None})
                except (OSError, ValueError) as exc:
                    return self.reply({"error": str(exc)}, 400)
            if route.path == "/inbox":
                return self.reply(dashboard.inbox.snapshot() if dashboard.inbox else {"enabled": False, "results": []})
            if route.path == "/inbox/compare":
                inbox = dashboard.inbox
                if not inbox:
                    return self.reply({"error": "Results inbox is disabled"}, 404)
                rows = inbox.snapshot()["results"]
                if not rows:
                    return self.reply({"error": "No received results"}, 404)
                records = [json.loads(inbox.result_path(row["id"]).read_text(encoding="utf-8")) for row in rows]
                destination = inbox.output / "comparison.html"
                export_report(records[0], destination, comparisons=records[1:])
                return self.reply(destination.read_bytes(), content_type="text/html; charset=utf-8")
            if route.path in {"/report", "/result.json"}:
                with dashboard.lock:
                    path = dashboard.report_path if route.path == "/report" else dashboard.result_path
                if not path or not path.is_file():
                    return self.reply({"error": "No completed result yet"}, 404)
                return self.reply(path.read_bytes(), content_type="text/html; charset=utf-8" if route.path == "/report" else "application/json")
            return self.reply({"error": "Not found"}, 404)

        def do_POST(self):
            origin = self.headers.get("Origin")
            expected_origin = f"http://127.0.0.1:{self.server.server_port}"
            if not self.host_ok() or origin != expected_origin or not secrets.compare_digest(self.headers.get("X-G3Bench-Token", ""), token):
                return self.reply({"error": "Local dashboard authorization required"}, 403)
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 <= length <= 16384:
                    raise ValueError("Invalid request size")
                data = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(data, dict):
                    raise ValueError("Expected an object")
                if self.path == "/start":
                    for key in ("headless", "fullscreen", "as_configured"):
                        if key in data and not isinstance(data[key], bool):
                            raise ValueError("Options must be boolean")
                    options = data.get("options", {})
                    if not isinstance(options, dict):
                        raise ValueError("Expected run options")
                    dashboard.start(data.get("kind"), data.get("headless", False), data.get("fullscreen", True), data.get("as_configured", False), options)
                elif self.path == "/cancel":
                    dashboard.cancel()
                elif self.path == "/inbox/start":
                    if dashboard.snapshot()["phase"] == "running":
                        raise ValueError("Wait for the active test before enabling the results inbox")
                    if not dashboard.inbox:
                        from .inbox import ResultsInbox
                        dashboard.inbox = ResultsInbox(dashboard.output, can_accept=lambda: dashboard.snapshot()["phase"] != "running")
                    return self.reply(dashboard.inbox.snapshot())
                elif self.path == "/inbox/stop":
                    if dashboard.inbox:
                        dashboard.inbox.close()
                        dashboard.inbox = None
                    return self.reply({"enabled": False, "results": []})
                elif self.path == "/shutdown":
                    if dashboard.snapshot()["phase"] == "running":
                        raise ValueError("Stop the benchmark before closing the dashboard")
                    closing.set()
                    wake_write.send(b"x")
                else:
                    return self.reply({"error": "Not found"}, 404)
                return self.reply(dashboard.snapshot())
            except (ValueError, OSError, subprocess.SubprocessError) as exc:
                return self.reply({"error": str(exc)}, 400)

    class LocalServer(ThreadingHTTPServer):
        def server_bind(self):
            # Avoid HTTPServer's reverse-DNS lookup; this server is loopback only.
            socketserver.TCPServer.server_bind(self)
            self.server_name = "127.0.0.1"
            self.server_port = self.server_address[1]
    server = LocalServer(("127.0.0.1", args.port), Handler)
    server.daemon_threads = True
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"{PRODUCT_NAME} dashboard: {url}\nNo renderers or telemetry run while idle. Ctrl+C to exit.", flush=True)
    if ready:
        ready(url, dashboard)
    if not args.no_open:
        webbrowser.open(url)
    selector = selectors.DefaultSelector()
    selector.register(server, selectors.EVENT_READ)
    selector.register(wake_read, selectors.EVENT_READ)
    try:
        while not closing.is_set():
            for key, _ in selector.select():  # no timeout: sleeps until a socket is ready
                if key.fileobj is server:
                    server._handle_request_noblock()
                else:
                    wake_read.recv(1)
    except KeyboardInterrupt:
        dashboard.cancel()
    finally:
        if dashboard.inbox:
            dashboard.inbox.close()
        if dashboard.worker:
            dashboard.worker.join(timeout=20)
        selector.close()
        server.server_close()
        wake_read.close()
        wake_write.close()
    return 0
