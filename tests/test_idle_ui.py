import argparse
import contextlib
import http.client
import io
import json
import queue
import re
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

from g3bench.ui import Dashboard, serve
from g3bench.showcase import run_showcase, SHOWCASE_ID
from g3bench.report import export_report

ROOT = Path(__file__).resolve().parent.parent
HW = {"board_model": "Test SBC", "platform": "Linux", "architecture": "aarch64", "core_count": 4}


class IdleDashboardTests(unittest.TestCase):
    def test_idle_initialization_does_not_launch_tools_or_sampler(self):
        with patch("g3bench.ui.hardware", return_value=HW), patch("g3bench.ui.find_engine", return_value="godot"), patch("g3bench.ui.subprocess.Popen") as popen, patch("g3bench.showcase.Sampler") as sampler:
            dashboard = Dashboard(ROOT / "build" / "idle-test")
            for _ in range(10):
                self.assertEqual(dashboard.snapshot()["phase"], "idle")
            self.assertIsNone(dashboard.process)
            self.assertIsNone(dashboard.worker)
            popen.assert_not_called()
            sampler.assert_not_called()

    def test_loopback_dashboard_authentication_and_idle_shutdown(self):
        ready = queue.Queue()
        args = argparse.Namespace(output=ROOT / "build" / "server-test", godot=None, port=0, no_open=True)
        with patch("g3bench.ui.hardware", return_value=HW), patch("g3bench.ui.find_engine", return_value=None), patch("g3bench.ui.subprocess.Popen") as popen, contextlib.redirect_stdout(io.StringIO()):
            thread = threading.Thread(target=serve, args=(args, lambda url, dashboard: ready.put((url, dashboard))), daemon=True)
            thread.start()
            url, dashboard = ready.get(timeout=5)
            parsed = urlsplit(url)
            def request(method, path, body=None, headers=None):
                connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=5)
                try:
                    connection.request(method, path, body=body, headers=headers or {})
                    response = connection.getresponse()
                    return response.status, response.read().decode()
                finally:
                    connection.close()
            token = None
            try:
                code, page = request("GET", "/")
                self.assertEqual(code, 200)
                payload = json.loads(re.search(r'id="data">(.*?)</script>', page).group(1))
                token = payload["token"]
                self.assertEqual(payload["state"]["phase"], "idle")
                code, _ = request("POST", "/start", '{"kind":"quick"}', {"Origin": "https://untrusted.example", "Content-Type": "application/json"})
                self.assertEqual(code, 403)
                headers = {"Origin": url, "X-G3Bench-Token": token, "Content-Type": "application/json"}
                code, _ = request("POST", "/start", '{"kind":"arbitrary-command"}', headers)
                self.assertEqual(code, 400)
                self.assertEqual(dashboard.snapshot()["phase"], "idle")
                code, _ = request("POST", "/iperf/start", '{"address":"127.0.0.1"}')
                self.assertEqual(code, 403)
                code, _ = request("POST", "/iperf/start", '{"address":"0.0.0.0"}', headers)
                self.assertEqual(code, 400)
                with patch.object(dashboard.iperf_server, 'start', return_value={'running': True}) as start_server:
                    code, _ = request("POST", "/iperf/start", '{"address":"127.0.0.1","port":55201}', headers)
                    self.assertEqual(code, 200)
                    start_server.assert_called_once_with('127.0.0.1', 55201)
                    dashboard.phase = 'running'
                    code, _ = request("POST", "/iperf/start", '{"address":"127.0.0.1"}', headers)
                    self.assertEqual(code, 400)
                    self.assertEqual(start_server.call_count, 1)
                    dashboard.phase = 'idle'
                popen.assert_not_called()
            finally:
                if token:
                    code, _ = request("POST", "/shutdown", "{}", {"Origin": url, "X-G3Bench-Token": token, "Content-Type": "application/json"})
                    self.assertEqual(code, 200)
                thread.join(timeout=5)
                self.assertFalse(thread.is_alive(), "Dashboard must stop without a polling timer")

    def test_running_report_never_auto_refreshes(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as folder:
            target = Path(folder) / "report.html"
            export_report({"hardware": HW, "status": "running"}, target)
            self.assertNotIn('http-equiv="refresh"', target.read_text(encoding="utf-8"))

    def test_single_run_and_cancel_leave_no_worker_and_save_cancelled_result(self):
        launched, released = threading.Event(), threading.Event()
        class FakeProcess:
            pid = 424242
            def __init__(self, *args, **kwargs):
                launched.set()
            def poll(self):
                return 0 if released.is_set() else None
            def wait(self, timeout=None):
                if not released.wait(5):
                    raise RuntimeError("Test worker did not stop")
                return 0
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as folder:
            with patch("g3bench.ui.hardware", return_value=HW), patch("g3bench.ui.find_engine", return_value="godot"), patch("g3bench.ui.subprocess.Popen", FakeProcess), patch("g3bench.ui.stop_process", side_effect=lambda process: released.set()), patch("g3bench.ui.os.killpg", side_effect=lambda *args: released.set(), create=True):
                dashboard = Dashboard(folder)
                dashboard.start("showcase")
                try:
                    self.assertTrue(launched.wait(2))
                    with self.assertRaises(ValueError):
                        dashboard.start("quick")
                    dashboard.cancel()
                finally:
                    released.set()
                    dashboard.worker.join(timeout=3)
                self.assertFalse(dashboard.worker.is_alive())
                self.assertIsNone(dashboard.process)
                self.assertTrue(dashboard.done.is_set())
                self.assertEqual(dashboard.snapshot()["phase"], "cancelled")
                result = json.loads(dashboard.result_path.read_text())
                self.assertEqual(result["test_status"]["run"]["status"], "interrupted")
                self.assertTrue(all(value is None for value in result["scores"].values()))


class ShowcaseLifecycleTests(unittest.TestCase):
    def args(self, folder):
        return argparse.Namespace(output=folder, godot=None, smoke_test=False, fullscreen=False, as_configured=False, open=False)

    def test_missing_engine_saves_unavailable_without_spawning_renderer(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as folder:
            with patch("g3bench.showcase.find_engine", return_value=None), patch("g3bench.showcase.hardware", return_value=HW), patch("g3bench.showcase.subprocess.Popen") as popen, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(run_showcase(self.args(folder)), 0)
            result = json.loads(next(Path(folder).glob("*/result.json")).read_text())
            self.assertEqual(result["test_status"]["showcase"]["status"], "unavailable")
            self.assertFalse(result["comparison_eligible"])
            self.assertTrue(all(score is None for score in result["scores"].values()))
            popen.assert_not_called()

    def test_completed_showcase_is_unscored_and_process_is_waited(self):
        waited = threading.Event()
        class FakeProcess:
            def __init__(self, command, **kwargs):
                target = Path(command[command.index("--output") + 1])
                target.write_text(json.dumps({"workload_id": SHOWCASE_ID, "scored": False, "status": "passed", "scenes": [{"average_fps": 123}]}))
            def wait(self, timeout=None):
                waited.set()
                return 0
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as folder:
            with patch("g3bench.showcase.find_engine", return_value="godot"), patch("g3bench.showcase.hardware", return_value=HW), patch("g3bench.showcase.subprocess.check_output", return_value="4.7.2"), patch("g3bench.showcase.subprocess.Popen", FakeProcess), patch("g3bench.showcase.cpu_ticks", side_effect=[(100, 50), (200, 150)]), patch("g3bench.showcase.processes", return_value={}), patch("g3bench.showcase.time.sleep"), patch("g3bench.showcase.Sampler") as sampler, contextlib.redirect_stdout(io.StringIO()):
                sampler.return_value.sample.side_effect = lambda: {"temperature_c": None, "throttled_bits": None, "cpu_mhz": None}
                self.assertEqual(run_showcase(self.args(folder)), 0)
            result = json.loads(next(Path(folder).glob("*/result.json")).read_text())
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["classification"], "SHOWCASE")
            self.assertTrue(waited.is_set())
            self.assertFalse(result["comparison_eligible"])
            self.assertTrue(all(score is None for score in result["scores"].values()))


if __name__ == "__main__":
    unittest.main()
