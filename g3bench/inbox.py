"""Opt-in LAN result upload. No benchmark execution or arbitrary file access."""
import ipaddress
import json
from pathlib import Path
import secrets
import selectors
import socket
import socketserver
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .report import export_report

MAX_BYTES = 8 * 1024 * 1024


def validate_result(data):
    if not isinstance(data, dict):
        raise ValueError("Expected a GAM3T3CH result.json object")
    for key in ("hardware", "configuration", "results", "scores", "errors"):
        if not isinstance(data.get(key), dict):
            raise ValueError("Missing or invalid result field: " + key)
    for key in ("benchmark_version", "workload_id", "status", "classification"):
        if not isinstance(data.get(key), str) or not 1 <= len(data[key]) <= 128:
            raise ValueError("Missing or invalid result field: " + key)
    if not isinstance(data["hardware"].get("board_model"), str):
        raise ValueError("Missing board model")
    samples = data.get("telemetry")
    if not isinstance(samples, list) or len(samples) > 20000 or any(not isinstance(row, dict) for row in samples):
        raise ValueError("Invalid or oversized telemetry")
    if any(not isinstance(row.get("elapsed_seconds"), (int, float)) for row in samples):
        raise ValueError("Telemetry must include elapsed seconds")
    profile = data["hardware"].get("board_profile")
    if profile is not None and (not isinstance(profile, dict) or not isinstance(profile.get("notes", []), list)):
        raise ValueError("Invalid board profile")
    statuses = data.get("test_status", {})
    if not isinstance(statuses, dict) or any(not isinstance(row, dict) or not isinstance(row.get("status"), str) for row in statuses.values()):
        raise ValueError("Invalid test status metadata")
    for group in ("gpu", "showcase"):
        result = data["results"].get(group, {})
        if not isinstance(result, dict) or not isinstance(result.get("scenes", []), list) or any(not isinstance(row, dict) for row in result.get("scenes", [])):
            raise ValueError("Invalid scene measurements")
    storage = data["results"].get("storage", {})
    if not isinstance(storage, dict) or not isinstance(storage.get("drives", []), list):
        raise ValueError("Invalid storage result")
    if not isinstance(storage.get("inventory", []), list) or any(not isinstance(row, dict) for row in storage.get("inventory", [])):
        raise ValueError("Invalid drive inventory")
    for drive in storage.get("drives", []):
        if not isinstance(drive, dict) or not isinstance(drive.get("target"), dict) or not isinstance(drive.get("tests"), dict):
            raise ValueError("Invalid drive measurements")
    if data.get("comparison_eligible"):
        resolution = data["configuration"].get("resolution")
        if not isinstance(resolution, list) or len(resolution) != 2:
            raise ValueError("Comparison-eligible results need their original resolution metadata")
    return data


PAGE = b'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GAM3T3CH results inbox</title><style>body{background:#0b1018;color:#eef4fc;font:16px system-ui;max-width:700px;margin:10vh auto;padding:24px}h1{color:#62efd0}button{background:#62efd0;border:0;border-radius:6px;padding:12px 18px;font-weight:700}p{line-height:1.6}input{display:block;margin:24px 0}</style><h1>GAM3T3CH results inbox</h1><p>Send a saved result.json from this unit to the collecting machine. The benchmark runs locally on each unit. This link accepts results only.</p><input type="file" id="file" accept=".json,application/json"><button id="send">Send result</button><p id="status" role="status"></p><script>const token=new URLSearchParams(location.hash.slice(1)).get('token');document.getElementById('send').onclick=async()=>{const status=document.getElementById('status'),file=document.getElementById('file').files[0];try{if(!token)throw Error('Use the complete inbox link copied from the collecting dashboard.');if(!file)throw Error('Choose a saved result.json first.');if(file.size>8388608)throw Error('File exceeds the 8 MiB limit.');const response=await fetch('/upload',{method:'POST',headers:{'Content-Type':'application/json','X-G3Bench-Inbox':token},body:await file.text()});const data=await response.json();if(!response.ok)throw Error(data.error);status.textContent='Received '+data.board+'. You can compare it on the collecting dashboard.';}catch(error){status.textContent=error.message;}};</script></html>'''


class ResultsInbox:
    def __init__(self, output, host="0.0.0.0", port=0, can_accept=lambda: True):
        self.output = Path(output).resolve() / "received"
        self.token = secrets.token_urlsafe(32)
        self.rows = []
        self.lock = threading.Lock()
        self.wake_read, self.wake_write = socket.socketpair()
        self.closed = threading.Event()
        inbox = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def reply(self, body, status=200, content_type="application/json"):
                body = body if isinstance(body, bytes) else json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'")
                self.end_headers()
                self.wfile.write(body)
            def do_GET(self):
                return self.reply(PAGE, content_type="text/html; charset=utf-8") if self.path == "/" else self.reply({"error": "Not found"}, 404)
            def do_POST(self):
                if self.path != "/upload":
                    return self.reply({"error": "Not found"}, 404)
                if not secrets.compare_digest(self.headers.get("X-G3Bench-Inbox", ""), inbox.token):
                    return self.reply({"error": "Invalid inbox access token"}, 403)
                if inbox.closed.is_set() or not can_accept():
                    return self.reply({"error": "Collector benchmark is active; send results after it finishes"}, 409)
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 1 <= length <= MAX_BYTES:
                        raise ValueError("Upload must be between 1 byte and 8 MiB")
                    self.connection.settimeout(15)
                    body = self.rfile.read(length)
                    if len(body) != length:
                        raise ValueError("Incomplete upload")
                    def invalid_constant(value):
                        raise ValueError("Non-finite JSON number")
                    data = validate_result(json.loads(body, parse_constant=invalid_constant))
                    normalized = json.dumps(data, allow_nan=False)
                    with inbox.lock:
                        if len(inbox.rows) >= 20:
                            raise ValueError("Inbox session limit reached (20 results). Save comparison files before starting a new session.")
                    identity = secrets.token_hex(12)
                    # Each upload gets a generated folder, never a supplied filename.
                    folder = inbox.output / identity
                    folder.mkdir(parents=True)
                    (folder / "result.json").write_text(normalized, encoding="utf-8")
                    export_report(data, folder / "report.html")
                    row = {"id": identity, "board": data["hardware"]["board_model"], "label": data["configuration"].get("label", ""), "version": data["benchmark_version"]}
                    with inbox.lock:
                        inbox.rows.append(row)
                    return self.reply({"board": row["board"], "id": identity})
                except (OSError, ValueError, TypeError, RecursionError) as exc:
                    return self.reply({"error": str(exc)}, 400)
        class InboxServer(ThreadingHTTPServer):
            def server_bind(self):
                socketserver.TCPServer.server_bind(self)
                self.server_name = "GAM3T3CH results inbox"
                self.server_port = self.server_address[1]
        try:
            self.server = InboxServer((host, port), Handler)
        except BaseException:
            self.wake_read.close()
            self.wake_write.close()
            raise
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self):
        with selectors.DefaultSelector() as selector:
            selector.register(self.server, selectors.EVENT_READ)
            selector.register(self.wake_read, selectors.EVENT_READ)
            while not self.closed.is_set():
                for key, _ in selector.select():
                    if key.fileobj is self.server:
                        self.server._handle_request_noblock()
                    else:
                        self.wake_read.recv(1)

    def snapshot(self):
        addresses = []
        try:
            for address in socket.gethostbyname_ex(socket.gethostname())[2]:
                ip = ipaddress.ip_address(address)
                if ip.version == 4 and ip.is_private and not ip.is_loopback and address not in addresses:
                    addresses.append(address)
        except OSError:
            pass
        with self.lock:
            return {"enabled": True, "port": self.server.server_port,
                    "local_link": "http://127.0.0.1:" + str(self.server.server_port) + "/#token=" + self.token,
                    "links": ["http://" + address + ":" + str(self.server.server_port) + "/#token=" + self.token for address in addresses],
                    "results": list(self.rows), "directory": str(self.output)}

    def result_path(self, identity, report=False):
        with self.lock:
            if identity not in {row["id"] for row in self.rows}:
                raise ValueError("Unknown received result")
        return self.output / identity / ("report.html" if report else "result.json")

    def close(self):
        self.closed.set()
        self.wake_write.send(b"x")
        self.thread.join(timeout=5)
        self.server.server_close()
        self.wake_read.close()
        self.wake_write.close()
