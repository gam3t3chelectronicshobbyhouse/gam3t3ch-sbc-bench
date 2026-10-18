import argparse
import contextlib
import io
import json
import http.client
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import zipfile

import installer
from g3bench import VERSION
from g3bench.__main__ import main
from g3bench.inbox import ResultsInbox, validate_result
from g3bench.report import export_report
from g3bench.ui import Dashboard

ROOT = Path(__file__).resolve().parent.parent


def result():
    return {"benchmark_version": VERSION, "workload_id": "baseline-0.1", "hardware": {"board_model": "Test Pi"},
            "configuration": {"mode": "quick", "label": "Stock"}, "results": {}, "scores": {}, "errors": {},
            "status": "partial", "classification": "DEVELOPMENT", "telemetry": [], "test_status": {},
            "comparison_eligible": False, "stage": "Complete"}


class DistributionTests(unittest.TestCase):
    def test_archive_cannot_escape_install_directory(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as folder:
            archive = Path(folder) / "bad.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("../escape.txt", "bad")
            with self.assertRaises(ValueError):
                installer.extract(archive, Path(folder) / "install")
            self.assertFalse((Path(folder) / "escape.txt").exists())

    def test_godot_platform_map_keeps_armv6_portable(self):
        self.assertIsNone(installer.godot_asset("Linux", "armv6l"))
        self.assertTrue(installer.godot_asset("Linux", "aarch64").endswith("linux.arm64.zip"))
        self.assertTrue(installer.godot_asset("Windows", "AMD64").endswith("win64.exe.zip"))
        self.assertIn("macos.universal", installer.godot_asset("Darwin", "arm64"))

    def test_existing_unrelated_destination_is_not_overwritten(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as folder:
            sentinel = Path(folder) / "keep.txt"
            sentinel.write_text("keep")
            args = argparse.Namespace(prefix=folder, no_launch=True)
            with self.assertRaises(ValueError):
                installer.install(args)
            self.assertEqual(sentinel.read_text(), "keep")

    def test_fullscreen_default_and_explicit_windowed(self):
        for flags, expected in (([], True), (["--windowed"], False)):
            with patch("sys.argv", ["g3bench", "showcase", *flags]), patch("g3bench.showcase.run_showcase", return_value=0) as run:
                self.assertEqual(main(), 0)
                self.assertEqual(run.call_args.args[0].fullscreen, expected)

    def test_packaged_worker_uses_app_executable_and_fullscreen(self):
        commands = []
        class Process:
            def __init__(self, command, **kwargs):
                commands.append(command)
            def wait(self):
                return 0
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as folder, patch("g3bench.ui.hardware", return_value={}), patch("g3bench.ui.find_engine", return_value="engine"), patch("g3bench.ui.subprocess.Popen", Process), patch("g3bench.ui.sys.frozen", True, create=True):
            dashboard = Dashboard(folder)
            self.assertIsNone(dashboard.inbox)
            dashboard.start("showcase")
            dashboard.worker.join(timeout=5)
            self.assertNotIn("-m", commands[0])
            self.assertEqual(commands[0][1], "showcase")
            self.assertIn("--fullscreen", commands[0])

    def test_report_comparison_json_does_not_replace_payload_markers(self):
        first, second = result(), result()
        first["hardware"]["board_model"] = "__COMPARISON_DATA__ __TITLE__"
        second["hardware"]["board_model"] = "</script><script>bad()</script>"
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as folder:
            target = Path(folder) / "report.html"
            export_report(first, target, comparisons=[second])
            text = target.read_text(encoding="utf-8")
            import re
            stored = json.loads(re.search(r'id="result" type="application/json">(.*?)</script>', text).group(1))
            extras = json.loads(re.search(r'id="extra-results">(.*?)</script>', text).group(1))
            self.assertEqual(stored, first)
            self.assertEqual(extras, [second])
            self.assertNotIn(second["hardware"]["board_model"], text)


class InboxTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("G3BENCH_RUN_SOCKET_TESTS") == "1", "Enable socket integration in an unrestricted test environment")
    def test_real_loopback_upload_and_shutdown(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as folder:
            inbox = ResultsInbox(folder, host="127.0.0.1")
            def request(path, token, body):
                connection = http.client.HTTPConnection("127.0.0.1", inbox.server.server_port, timeout=5)
                try:
                    connection.request("POST", path, body, {"X-G3Bench-Inbox": token, "Content-Type": "application/json"})
                    response = connection.getresponse()
                    return response.status, json.loads(response.read())
                finally:
                    connection.close()
            try:
                body = json.dumps(result())
                self.assertEqual(request("/upload", "wrong", body)[0], 403)
                code, received = request("/upload", inbox.token, body)
                self.assertEqual(code, 200)
                self.assertEqual(received["board"], "Test Pi")
                self.assertTrue(inbox.result_path(received["id"]).is_file())
                self.assertEqual(request("/start", inbox.token, body)[0], 404)
            finally:
                inbox.close()
            self.assertFalse(inbox.thread.is_alive())

    def test_invalid_result_shapes_are_rejected(self):
        for bad in ([], {}, {**result(), "telemetry": ["bad"]}, {**result(), "results": {"storage": {"drives": ["bad"]}}}):
            with self.assertRaises(ValueError):
                validate_result(bad)
        self.assertEqual(validate_result(result()), result())

    def handler(self, inbox, body, token):
        handler = inbox.server.handler.__new__(inbox.server.handler)
        handler.path = "/upload"
        handler.headers = {"Content-Length": str(len(body)), "X-G3Bench-Inbox": token}
        handler.rfile, handler.wfile = io.BytesIO(body), io.BytesIO()
        handler.connection = MagicMock()
        handler.send_response = lambda value: setattr(handler, "status", value)
        handler.send_header = lambda *args: None
        handler.end_headers = lambda: None
        return handler

    def test_upload_authentication_persistence_and_generated_paths_without_listener(self):
        class Server:
            def __init__(self, address, handler):
                self.handler = handler
                self.server_port = 1234
            def server_close(self):
                pass
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as folder, patch("g3bench.inbox.ThreadingHTTPServer", Server), patch("g3bench.inbox.socket.socketpair", return_value=(MagicMock(), MagicMock())), patch("g3bench.inbox.threading.Thread"):
            accepting = [True]
            inbox = ResultsInbox(folder, can_accept=lambda: accepting[0])
            try:
                data = result()
                data["hardware"]["board_model"] = "../../untrusted name"
                body = json.dumps(data).encode()
                denied = self.handler(inbox, body, "wrong")
                denied.do_POST()
                self.assertEqual(denied.status, 403)
                self.assertFalse(inbox.output.exists())
                accepted = self.handler(inbox, body, inbox.token)
                accepted.do_POST()
                self.assertEqual(accepted.status, 200)
                row = inbox.rows[0]
                self.assertRegex(row["id"], r"^[0-9a-f]{24}$")
                self.assertEqual(json.loads(inbox.result_path(row["id"]).read_text()), data)
                self.assertTrue(inbox.result_path(row["id"], report=True).is_file())
                accepting[0] = False
                paused = self.handler(inbox, body, inbox.token)
                paused.do_POST()
                self.assertEqual(paused.status, 409)
                accepting[0] = True
                with self.assertRaises(ValueError):
                    inbox.result_path("../../outside")
                invalid = self.handler(inbox, b"{}", inbox.token)
                invalid.do_POST()
                self.assertEqual(invalid.status, 400)
                self.assertEqual(len(inbox.rows), 1)
                oversized = self.handler(inbox, b"{}", inbox.token)
                oversized.headers["Content-Length"] = str(8*1024*1024 + 1)
                oversized.do_POST()
                self.assertEqual(oversized.status, 400)
            finally:
                inbox.close()


if __name__ == "__main__":
    unittest.main()
