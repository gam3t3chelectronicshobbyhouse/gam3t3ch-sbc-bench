import argparse
import contextlib
import io
import json
import platform
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from g3bench.storage import discover, measure_drive, resolve_target, run_storage, MIB, JOBS
from g3bench.system import tuning_snapshot
from g3bench.ui import Dashboard

ROOT = Path(__file__).resolve().parent.parent


class InventoryTests(unittest.TestCase):
    def test_single_sd_and_multiple_physical_drives_no_boot_or_ram_duplicates(self):
        tree = {"blockdevices": [
            {"name": "mmcblk0", "path": "/dev/mmcblk0", "type": "disk", "maj:min": "179:0", "children": [
                {"path": "/dev/mmcblk0p1", "type": "part", "maj:min": "179:1"},
                {"path": "/dev/mmcblk0p2", "type": "part", "maj:min": "179:2"}]},
            {"name": "mmcblk1", "path": "/dev/mmcblk1", "type": "disk", "maj:min": "179:32"},
            {"name": "sda", "path": "/dev/sda", "type": "disk", "tran": "usb", "maj:min": "8:0", "children": [
                {"path": "/dev/sda1", "type": "part", "maj:min": "8:1"}]},
            {"name": "nvme0n1", "path": "/dev/nvme0n1", "type": "disk", "tran": "nvme", "maj:min": "259:0"},
            {"name": "zram0", "path": "/dev/zram0", "type": "disk", "maj:min": "252:0"}]}
        mounts = {"filesystems": [
            {"source": "/dev/mmcblk0p1", "target": "/boot", "options": "rw", "maj:min": "179:1"},
            {"source": "/dev/mmcblk0p2", "target": "/", "options": "rw", "maj:min": "179:2"},
            {"source": "/dev/mmcblk0p2", "target": "/bind", "options": "rw", "maj:min": "179:2"},
            {"source": "/dev/mmcblk1", "target": "/emmc", "options": "ro", "maj:min": "179:32"},
            {"source": "/dev/sda1", "target": "/media/usb", "options": "rw", "maj:min": "8:1"},
            {"source": "/dev/zram0", "target": "/ram", "options": "rw", "maj:min": "252:0"}]}
        def device_type(path):
            return "SD" if "mmcblk0" in path else "MMC" if "mmcblk1" in path else None
        with patch("g3bench.storage.platform.system", return_value="Linux"), patch("g3bench.storage.json_command", side_effect=[tree, mounts]), patch("g3bench.storage.read", side_effect=device_type), patch("g3bench.storage.os.access", return_value=True), patch.object(Path, "is_dir", return_value=True), patch.object(Path, "stat", side_effect=OSError):
            rows = discover()
        self.assertEqual(len(rows), 5)
        self.assertEqual({r["source"] for r in rows if r["selected_by_default"]}, {"/dev/mmcblk0p2", "/dev/sda1"})
        emmc = next(row for row in rows if row.get("mount") == "/emmc")
        self.assertEqual(emmc["media"], "eMMC")
        self.assertFalse(emmc["eligible"])
        self.assertTrue(any(r["device"] == "/dev/nvme0n1" and not r["eligible"] for r in rows))

    def test_explicit_directory_must_match_known_local_filesystem(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as folder:
            mount = {"filesystems": [{"maj:min": "1:1", "options": "rw"}]}
            with patch("g3bench.storage.json_command", return_value=mount):
                with self.assertRaises(ValueError):
                    resolve_target(folder, [])
                target = resolve_target(folder, [{"id": "1:1", "source": "/dev/test"}])
                self.assertEqual(target["directory"], str(Path(folder).resolve()))


class FileWorkloadTests(unittest.TestCase):
    def test_failed_initial_write_cleans_up_and_skips_reads_without_touching_other_files(self):
        class Failed:
            returncode = 1
            def __init__(self, command, **kwargs):
                filename = Path(next(arg.split("=", 1)[1] for arg in command if arg.startswith("--filename=")))
                self.assertion = filename.is_file()
            def communicate(self, timeout=None):
                return json.dumps({"jobs": [{"error": 22}]}), "Direct I/O not supported"
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as folder:
            sentinel = Path(folder) / "keep.txt"
            sentinel.write_text("existing user data")
            with patch("g3bench.storage.subprocess.Popen", Failed), patch("g3bench.storage.shutil.disk_usage", return_value=argparse.Namespace(free=2**40)):
                result = measure_drive({"directory": folder}, "fio", 16, 10, lambda *args: None)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["tests"]["sequential_read"]["status"], "skipped")
            self.assertEqual(list(Path(folder).iterdir()), [sentinel])
            self.assertEqual(sentinel.read_text(), "existing user data")

    def test_space_headroom_prevents_io(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as folder, patch("g3bench.storage.shutil.disk_usage", return_value=argparse.Namespace(free=16*MIB)), patch("g3bench.storage.subprocess.Popen") as process:
            result = measure_drive({"directory": folder}, "fio", 16, 10, lambda *args: None)
            self.assertEqual(result["status"], "unavailable")
            process.assert_not_called()

    def test_timeout_terminates_fio_and_cleans_private_directory(self):
        class Timeout:
            returncode = -15
            calls = 0
            terminated = False
            def __init__(self, *args, **kwargs):
                pass
            def communicate(self, timeout=None):
                self.calls += 1
                if self.calls == 1:
                    raise subprocess.TimeoutExpired("fio", timeout)
                return "", ""
            def terminate(self):
                Timeout.terminated = True
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as folder, patch("g3bench.storage.subprocess.Popen", Timeout), patch("g3bench.storage.shutil.disk_usage", return_value=argparse.Namespace(free=2**40)):
            result = measure_drive({"directory": folder}, "fio", 16, 10, lambda *args: None)
            self.assertTrue(Timeout.terminated)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(list(Path(folder).iterdir()), [])

    @unittest.skipUnless(platform.system() == "Linux" and shutil.which("fio"), "Linux fio integration")
    def test_real_direct_io_four_workloads_and_cleanup(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as folder:
            sentinel = Path(folder) / "keep.txt"
            sentinel.write_text("keep")
            result = measure_drive({"directory": folder}, shutil.which("fio"), 16, 60, lambda *args: None)
            self.assertEqual(result["status"], "passed", result)
            for name, _, _ in JOBS:
                test = result["tests"][name]
                self.assertEqual(test["bytes"], 16*MIB)
                self.assertGreater(test["mb_s"], 0)
                self.assertGreater(test["iops"], 0)
                self.assertGreaterEqual(test["latency_mean_ms"], 0)
            self.assertEqual(list(Path(folder).iterdir()), [sentinel])


class StorageRunnerTests(unittest.TestCase):
    def args(self, folder):
        return argparse.Namespace(size_mib=16, timeout=60, target=None, all=True, allow_writes=True,
                                  output=folder, label="Stock", notes="Test", as_configured=True, open=False)

    def test_missing_fio_writes_report_without_io_and_requires_acknowledgement(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as folder:
            args = self.args(folder)
            args.allow_writes = False
            with patch("g3bench.storage.discover", return_value=[]), patch("g3bench.storage.measure_drive") as measure:
                with self.assertRaises(ValueError):
                    run_storage(args)
                args.allow_writes = True
                with patch("g3bench.storage.platform.system", return_value="Linux"), patch("g3bench.storage.shutil.which", return_value=None), contextlib.redirect_stdout(io.StringIO()):
                    run_storage(args)
                measure.assert_not_called()
            result = json.loads(next(Path(folder).glob("*/result.json")).read_text())
            self.assertEqual(result["test_status"]["storage"]["status"], "unavailable")
            self.assertTrue(all(value is None for value in result["scores"].values()))

    def test_removed_drive_does_not_prevent_other_drive_measurement(self):
        rows = [{"id": "1:1", "directory": "/gone", "source": "/dev/a", "mount": "/gone", "selected_by_default": True},
                {"id": "1:2", "directory": "/good", "source": "/dev/b", "mount": "/good", "selected_by_default": True}]
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as folder:
            with patch("g3bench.storage.discover", return_value=rows), patch("g3bench.storage.resolve_target", side_effect=[ValueError("unplugged"), rows[1]]), patch("g3bench.storage.measure_drive", return_value={"status": "passed", "reason": "ok", "tests": {}}) as measure, patch("g3bench.storage.platform.system", return_value="Linux"), patch("g3bench.storage.shutil.which", return_value="fio"), patch("g3bench.storage.command", return_value="fio-3.33"), patch("g3bench.storage.time.sleep"), contextlib.redirect_stdout(io.StringIO()):
                code = run_storage(self.args(folder))
            result = json.loads(next(Path(folder).glob("*/result.json")).read_text())
            self.assertEqual(code, 1)
            self.assertEqual([d["status"] for d in result["results"]["storage"]["drives"]], ["unavailable", "passed"])
            measure.assert_called_once()

    def test_dashboard_refuses_storage_without_write_ack(self):
        with patch("g3bench.ui.hardware", return_value={}), patch("g3bench.ui.find_engine", return_value=None), patch("g3bench.ui.subprocess.Popen") as process:
            dashboard = Dashboard(ROOT / "build")
            with self.assertRaises(ValueError):
                dashboard.start("storage", options={"targets": ["/home/test"], "size_mib": 1024})
            process.assert_not_called()

    def test_tuning_captures_compression_and_governor_without_mutation(self):
        def paths(pattern):
            return ["/sys/block/zram0"] if "zram" in pattern else ["/sys/devices/system/cpu/cpufreq/policy0"]
        values = {"/sys/block/zram0/disksize": "1073741824", "/sys/block/zram0/comp_algorithm": "lzo [lz4]",
                  "/sys/devices/system/cpu/cpufreq/policy0/scaling_governor": "ondemand", "/proc/sys/vm/swappiness": "100"}
        with patch("g3bench.system.glob.glob", side_effect=paths), patch("g3bench.system.read", side_effect=values.get):
            tuning = tuning_snapshot()
        self.assertEqual(tuning["swappiness"], "100")
        self.assertEqual(tuning["zram"][0]["comp_algorithm"], "lzo [lz4]")
        self.assertEqual(tuning["cpu_policies"][0]["scaling_governor"], "ondemand")


if __name__ == "__main__":
    unittest.main()
