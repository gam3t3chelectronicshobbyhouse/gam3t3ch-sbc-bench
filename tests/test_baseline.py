import json
import math
import tempfile
import unittest
import argparse
from pathlib import Path
from unittest.mock import patch

from g3bench.report import export_report
from g3bench.scoring import NORMALIZATION, geometric, scores
from g3bench.system import Sampler, hardware
from g3bench.__main__ import atomic_json, execute, binary, run


class ScoringTests(unittest.TestCase):
    def reference(self):
        result = {group: {key: {"value": value} for key, value in entries.items()} for group, entries in NORMALIZATION.items()}
        result["gpu"] = {"width": 1280, "height": 720, "scenes": [{"average_fps": 60} for _ in range(5)]}
        return result

    def test_reference_normalization(self):
        for key in ("cpu", "memory", "gpu", "overall"):
            self.assertAlmostEqual(scores(self.reference())[key], 1000)

    def test_missing_and_compatibility_never_gain_overall(self):
        self.assertIsNone(scores({})["overall"])
        self.assertIsNone(scores(self.reference(), True)["gpu"])
        self.assertIsNone(scores(self.reference(), True)["overall"])
        result = self.reference()
        result["gpu"]["width"] = 640
        self.assertIsNone(scores(result)["gpu"])

    def test_geometric_mean_and_invalid_rates(self):
        self.assertAlmostEqual(geometric([100, 10000]), 1000)
        for rate in (0, -1, math.inf, math.nan):
            self.assertIsNone(geometric([100, rate]))


class ArtifactTests(unittest.TestCase):
    def test_json_roundtrip_and_html_script_injection(self):
        data = {"hardware": {"board_model": '</script><script>alert("bad")</script>'}, "status": "complete"}
        # Keep test artifacts within the checkout on restricted development hosts.
        test_root = Path(__file__).resolve().parent.parent / "build"
        test_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=test_root) as folder:
            target = Path(folder) / "result.json"
            atomic_json(target, data)
            self.assertEqual(json.loads(target.read_text()), data)
            report = target.with_suffix(".html")
            export_report(data, report)
            text = report.read_text(encoding="utf-8")
            self.assertNotIn(data["hardware"]["board_model"], text)
            self.assertIn("\\u003c/script", text)
            self.assertNotIn("__RESULT_DATA__", text)

    def test_missing_linux_telemetry_is_unknown(self):
        with patch("g3bench.system.read", return_value=None), patch("g3bench.system.glob.glob", return_value=[]), patch("g3bench.system.shutil.which", return_value=None):
            sample = Sampler().sample()
            self.assertIsNone(sample["temperature_c"])
            self.assertIsNone(sample["throttled_bits"])
            self.assertIsNone(sample["cpu_utilization"])
            self.assertEqual(sample["cooling"], {})

    def test_linux_sensor_units_and_throttle_bits(self):
        zone = "/sys/class/thermal/thermal_zone0/temp"
        clock = "/sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq"
        values = {zone: "53000", zone.replace("temp", "type"): "cpu-thermal",
                  clock: "1500000", "/proc/meminfo": "MemTotal: 1024 kB\nMemAvailable: 256 kB"}
        def paths(pattern):
            return [zone] if "thermal_zone" in pattern else [clock] if "scaling_cur_freq" in pattern else []
        with patch("g3bench.system.read", side_effect=values.get), patch("g3bench.system.glob.glob", side_effect=paths), patch("g3bench.system.shutil.which", return_value="vcgencmd"), patch("g3bench.system.command", return_value="throttled=0x40004"), patch("g3bench.system.cpu_ticks", side_effect=[(100, 80), (200, 100)]):
            sample = Sampler().sample()
        self.assertEqual(sample["temperature_c"], 53)
        self.assertEqual(sample["cpu_mhz"], 1500)
        self.assertEqual(sample["memory_used_bytes"], 768 * 1024)
        self.assertEqual(sample["cpu_utilization"], 80)
        self.assertEqual(sample["throttled_bits"], 0x40004)
        self.assertEqual(sample["cooling"], {})

    def test_busy_system_cancels_before_native_workloads(self):
        test_root = Path(__file__).resolve().parent.parent / "build"
        test_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=test_root) as folder:
            args = argparse.Namespace(output=folder, compat=False, fullscreen=False, as_configured=False, headless=True, open=False)
            with patch("g3bench.__main__.binary", return_value="native"), patch("g3bench.__main__.execute", return_value={"compiler": "test", "suite_version": "0.1.0", "workload_id": "baseline-0.1"}) as tool, patch("g3bench.__main__.hardware", return_value={"board_model": "Test", "platform": "Linux"}), patch("g3bench.__main__.Sampler") as sampler, patch("g3bench.__main__.cpu_ticks", side_effect=[(100, 50), (200, 50)]), patch("g3bench.__main__.processes", return_value={}), patch("g3bench.__main__.time.sleep"):
                sampler.return_value.sample.return_value = {"temperature_c": None}
                self.assertEqual(run(args), 2)
                self.assertEqual(tool.call_count, 1)  # build info only, no CPU/memory
            result = json.loads(next(Path(folder).glob("*/result.json")).read_text())
            self.assertEqual(result["status"], "cancelled")
            self.assertEqual(result["results"], {})


@unittest.skipUnless(binary("g3bench-native"), "native executable not built")
class NativeTests(unittest.TestCase):
    def test_deterministic_workloads_and_real_rates(self):
        for category in ("cpu", "memory"):
            first = execute(binary("g3bench-native"), [category])
            second = execute(binary("g3bench-native"), [category])
            self.assertEqual(first["checksum"], second["checksum"])
            for key in NORMALIZATION[category]:
                self.assertGreater(first[key]["value"], 0)
                self.assertGreater(first[key]["seconds"], 0)


if __name__ == "__main__":
    unittest.main()
