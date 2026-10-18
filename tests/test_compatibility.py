import argparse
import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from g3bench import VERSION, WORKLOAD
from g3bench.compatibility import prepare, memory_check
from g3bench.system import board_profile, hardware
from g3bench.__main__ import run
from g3bench.scoring import NORMALIZATION


INFO = {"suite_version": VERSION, "workload_id": WORKLOAD}


class BoardDetectionTests(unittest.TestCase):
    def test_models_and_legacy_profiles(self):
        models = [
            ("Raspberry Pi Model B Rev 2", "armv6l", "pi-1", True),
            ("Raspberry Pi 1 Model B+ Rev 1.2", "armv6l", "pi-1", True),
            ("Raspberry Pi Zero W Rev 1.1", "armv6l", "zero", True),
            ("Raspberry Pi Zero 2 W Rev 1.0", "aarch64", "zero-2", False),
            ("Raspberry Pi Compute Module Rev 1.0", "armv6l", "cm1", True),
            ("Raspberry Pi Compute Module 5 Rev 1.0", "aarch64", "cm5", False),
            ("Raspberry Pi 2 Model B Rev 1.1", "armv7l", "pi-2", False),
            ("Raspberry Pi 3 Model B Rev 1.2", "armv7l", "pi-3", False),
            ("Raspberry Pi 4 Model B Rev 1.5", "aarch64", "pi-4", False),
            ("Raspberry Pi 5 Model B Rev 1.0", "aarch64", "pi-5", False),
            ("Orange Pi 5", "aarch64", None, False),
        ]
        for model, arch, expected, legacy in models:
            with self.subTest(model=model):
                profile = board_profile(model, arch, "test-revision")
                self.assertEqual(profile["model_id"], expected)
                self.assertEqual(profile["support_tier"] == "experimental-armv6", legacy)

    def test_cpuinfo_model_fallback_and_bcm2835_not_used_as_pi_version(self):
        values = {"/proc/cpuinfo": "Hardware: BCM2835\nModel: Raspberry Pi 5 Model B Rev 1.0\nRevision: d04170"}
        with patch("g3bench.system.read", side_effect=values.get), patch("g3bench.system.command", return_value=None):
            self.assertEqual(hardware()["board_profile"]["model_id"], "pi-5")
        self.assertIsNone(board_profile("BCM2835", "aarch64")["model_id"])


class CapabilityTests(unittest.TestCase):
    def test_pi1_is_not_denied_cpu_workloads_by_model_name(self):
        hw = {"board_profile": board_profile("Raspberry Pi Model B", "armv6l"), "ram_bytes": 256 * 1024**2}
        info, plan = prepare(hw, "native", None, lambda *a, **k: INFO)
        self.assertEqual(info, INFO)
        self.assertEqual(plan["cpu"]["status"], "ready")
        self.assertEqual(plan["memory"]["status"], "ready")
        self.assertEqual(plan["gpu"]["status"], "unavailable")

    def test_memory_capacity_differs_from_temporary_pressure(self):
        self.assertEqual(memory_check({"ram_bytes": 64 * 1024**2})["status"], "unsupported")
        self.assertEqual(memory_check({"ram_bytes": 256 * 1024**2, "memory_available_bytes": 50 * 1024**2})["status"], "unavailable")
        self.assertEqual(memory_check({})["status"], "ready")

    def test_bad_native_does_not_disable_independent_gpu(self):
        for error in (OSError("Exec format error"), subprocess.TimeoutExpired("native", 15)):
            def tool(path, args, **kwargs):
                if path == "native":
                    raise error
                return {**INFO, "status": "ready"}
            _, plan = prepare({}, "native", "gpu", tool)
            self.assertEqual(plan["cpu"]["status"], "unavailable")
            self.assertEqual(plan["gpu"]["status"], "ready")

    def test_gpu_probe_distinguishes_unsupported_from_unavailable(self):
        for status in ("unsupported", "unavailable"):
            _, plan = prepare({}, None, "gpu", lambda *a, **k: {**INFO, "status": status, "reason": "driver limitation"})
            self.assertEqual(plan["gpu"]["status"], status)
            self.assertEqual(plan["gpu"]["reason"], "driver limitation")

    def test_headless_does_not_launch_gpu_probe(self):
        def unexpected(*args, **kwargs):
            self.fail("No executable should run")
        _, plan = prepare({}, None, "gpu", unexpected, headless=True)
        self.assertEqual(plan["gpu"]["status"], "skipped")

    def test_unsupported_gpu_and_failed_cpu_preserve_memory_result(self):
        root = Path(__file__).resolve().parent.parent / "build"
        root.mkdir(exist_ok=True)
        calls = []
        def tool(path, flags, **kwargs):
            calls.append((path, flags))
            if flags == ["info"]:
                return INFO
            if "--probe" in flags:
                return {**INFO, "status": "unsupported", "reason": "GLES2 context unavailable"}
            if flags == ["cpu"]:
                raise RuntimeError("Native checksum verification failed")
            if flags == ["memory"]:
                return {key: {"value": value, "seconds": 1, "unit": "MB/s"} for key, value in NORMALIZATION["memory"].items()}
            self.fail("Unsupported GPU benchmark was launched")
        def sample():
            return {"temperature_c": None, "throttled_bits": None, "cpu_mhz": None}
        with tempfile.TemporaryDirectory(dir=root) as folder:
            args = argparse.Namespace(output=folder, compat=False, fullscreen=False, as_configured=False, headless=False, open=False)
            with patch("g3bench.__main__.binary", side_effect=lambda name: name), patch("g3bench.__main__.execute", side_effect=tool), patch("g3bench.__main__.hardware", return_value={"board_model": "Test Pi 1", "platform": "Linux"}), patch("g3bench.__main__.memory", return_value={}), patch("g3bench.__main__.Sampler") as sampler, patch("g3bench.__main__.cpu_ticks", side_effect=[(100, 50), (200, 150)]), patch("g3bench.__main__.processes", return_value={}), patch("g3bench.__main__.time.sleep"), contextlib.redirect_stdout(io.StringIO()):
                sampler.return_value.sample.side_effect = sample
                self.assertEqual(run(args), 1)
            data = json.loads(next(Path(folder).glob("*/result.json")).read_text())
            self.assertEqual(data["schema_version"], 2)
            self.assertEqual(data["test_status"]["cpu"]["status"], "failed")
            self.assertEqual(data["test_status"]["memory"]["status"], "passed")
            self.assertEqual(data["test_status"]["gpu"]["status"], "unsupported")
            self.assertAlmostEqual(data["scores"]["memory"], 1000)
            self.assertIsNone(data["scores"]["overall"])
            self.assertFalse(data["comparison_eligible"])


if __name__ == "__main__":
    unittest.main()
