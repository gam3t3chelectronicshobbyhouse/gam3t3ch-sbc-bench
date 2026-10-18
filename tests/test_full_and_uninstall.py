import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from g3bench import VERSION
from g3bench.full import run_full, FULL_ID
from g3bench.uninstall import remove_installation, validate_prefix
from g3bench.integration import REPOSITORY
from g3bench.scoring import NORMALIZATION

ROOT = Path(__file__).resolve().parent.parent


class FullTests(unittest.TestCase):
    def args(self, folder):
        return argparse.Namespace(output=folder, skip_storage=False, allow_writes=True, size_mib=16, timeout=60,
                                  target=None, headless=False, compat=False, fullscreen=True, godot=None,
                                  as_configured=True, label="Test fixture", notes="", open=False)

    def test_full_continues_independent_tests_after_failed_component_and_saves_whole_trace(self):
        order = []
        def runner(name, error=False):
            def execute(args):
                order.append(name)
                data = {"workload_id": name, "configuration": {}, "hardware": {}, "telemetry": [], "stage": name,
                        "results": {name: {"measured": True}}, "test_status": {name: {"status": "failed" if error else "passed", "reason": "fixture"}},
                        "status": "partial" if error else "complete", "errors": {name: "fixture error"} if error else {}}
                import time
                args._session.attach(data, time.monotonic())
                args._session.sample()
                folder = Path(args.output) / "component"
                folder.mkdir(parents=True)
                (folder / "result.json").write_text(json.dumps(data))
                return 1 if error else 0
            return execute
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as folder, patch("g3bench.__main__.run", runner("portable", True)), patch("g3bench.storage.run_storage", runner("storage")), patch("g3bench.showcase.run_showcase", runner("showcase")), patch("g3bench.full.hardware", return_value={"board_model": "Test"}), patch("g3bench.full.Sampler") as sampler, contextlib.redirect_stdout(io.StringIO()):
            sampler.return_value.sample.side_effect = lambda: {"temperature_c": 55, "throttled_bits": 0}
            self.assertEqual(run_full(self.args(folder)), 1)
            sampler.assert_called_once()
            data = json.loads(next(Path(folder).glob("*/result.json")).read_text())
            self.assertEqual(order, ["portable", "storage", "showcase"])
            self.assertEqual(data["status"], "partial")
            self.assertEqual(data["workload_id"], FULL_ID)
            self.assertEqual(data["thermal_summary"]["peak_c"], 55)
            self.assertTrue(any(s["stage"].startswith("STORAGE") for s in data["telemetry"]))
            self.assertFalse(data["comparison_eligible"])

    def test_headless_full_reuses_single_sampler_inside_real_portable_runner(self):
        def execute(path, args, timeout=600):
            return {name: {"value": rate, "unit": "MB/s", "seconds": 1} for name, rate in NORMALIZATION[args[0]].items()}
        plan = {name: {"status": "ready" if name != "gpu" else "skipped", "reason": "fixture"} for name in ("cpu", "memory", "gpu")}
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as folder, patch("g3bench.full.hardware", return_value={"board_model": "Test"}), patch("g3bench.full.Sampler") as sampler, patch("g3bench.__main__.hardware", return_value={"board_model": "Test", "platform": "Linux"}), patch("g3bench.__main__.prepare", return_value=({}, plan)), patch("g3bench.__main__.execute", side_effect=execute), patch("g3bench.__main__.binary", return_value="native"), patch("g3bench.__main__.Sampler", side_effect=AssertionError("Duplicate sampler")), patch("g3bench.__main__.time.sleep"), patch("g3bench.__main__.cpu_ticks", return_value=None), patch("g3bench.__main__.processes", return_value={}), contextlib.redirect_stdout(io.StringIO()):
            sampler.return_value.sample.side_effect = lambda: {"temperature_c": None, "throttled_bits": None, "cpu_mhz": None}
            args = self.args(folder)
            args.headless, args.skip_storage = True, True
            self.assertEqual(run_full(args), 0)
            data = json.loads(next(Path(folder).glob("*/result.json")).read_text())
            self.assertEqual(data["test_status"]["showcase"]["status"], "skipped")
            self.assertEqual(data["test_status"]["storage"]["status"], "skipped")
            self.assertIsNotNone(data["scores"]["cpu"])
            self.assertIsNone(data["scores"]["overall"])
            sampler.assert_called_once()

    def test_full_requires_explicit_storage_write_ack(self):
        args = self.args(ROOT / "build")
        args.allow_writes = False
        with self.assertRaises(ValueError):
            run_full(args)


class UninstallTests(unittest.TestCase):
    def test_uninstall_preserves_results_and_removes_only_unchanged_owned_shortcuts(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as folder:
            home = Path(folder).resolve()
            prefix = home / "app"
            prefix.mkdir()
            (prefix / "launch.py").write_text("# application")
            (prefix / "results").mkdir()
            (prefix / "results" / "keep.json").write_text('{"keep":true}')
            desktop = home / "Desktop"
            desktop.mkdir()
            shortcut = desktop / "GAM3T3CH 3D Benchmark.desktop"
            shortcut.write_text("owned")
            changed = desktop / "g3bench-uninstall.desktop"
            changed.write_text("modified by user")
            user_file = home / "keep.txt"
            user_file.write_text("unrelated")
            manifest = {"repository": REPOSITORY, "prefix": str(prefix), "shortcuts": [
                {"path": str(shortcut), "sha256": hashlib.sha256(shortcut.read_bytes()).hexdigest()},
                {"path": str(changed), "sha256": hashlib.sha256(b"old").hexdigest()},
                {"path": str(user_file), "sha256": hashlib.sha256(user_file.read_bytes()).hexdigest()}]}
            (prefix / ".gam3t3ch-install.json").write_text(json.dumps(manifest))
            with patch.object(Path, "home", return_value=home):
                backup = remove_installation(prefix)
            self.assertFalse(prefix.exists())
            self.assertFalse(shortcut.exists())
            self.assertTrue(changed.exists())
            self.assertEqual(user_file.read_text(), "unrelated")
            self.assertEqual((backup / "keep.json").read_text(), '{"keep":true}')

    def test_uninstaller_rejects_home_and_git_checkout(self):
        with self.assertRaises(ValueError):
            validate_prefix(Path.home())
        with self.assertRaises(ValueError):
            validate_prefix(ROOT)


if __name__ == "__main__":
    unittest.main()
