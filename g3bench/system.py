import glob
import os
import platform
import re
import shutil
import socket
import subprocess
from pathlib import Path


def read(path):
    try:
        return Path(path).read_text(errors="replace").strip().strip("\x00")
    except OSError:
        return None


def command(args):
    try:
        return subprocess.check_output(args, text=True, timeout=2, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.SubprocessError):
        return None


def memory():
    fields = {}
    for line in (read("/proc/meminfo") or "").splitlines():
        key, value = line.split(":", 1)
        fields[key] = int(value.split()[0]) * 1024
    return fields


def board_profile(model, architecture, revision=None):
    """Identify the board from its model, never from CPU speed or BCM2835."""
    name = (model or "").lower()
    pi = name.startswith("raspberry pi")
    model_id = None
    if pi:
        module = re.search(r"compute module\s*(\d+)?", name)
        numbered = re.search(r"raspberry pi\s+(\d+)\b", name)
        if module:
            model_id = "cm" + (module.group(1) or "1")
        elif "zero 2" in name:
            model_id = "zero-2"
        elif "zero" in name:
            model_id = "zero"
        elif numbered:
            model_id = "pi-" + numbered.group(1)
        elif re.search(r"raspberry pi\s+model\s+[ab]", name):
            model_id = "pi-1"
    legacy = architecture.lower().startswith("armv6") or model_id in {"pi-1", "zero", "cm1"}
    return {"family": "raspberry-pi" if pi else "generic", "model_id": model_id,
            "revision": revision, "support_tier": "experimental-armv6" if legacy else "baseline-unvalidated",
            "notes": ["Requires an ARMv6-compatible OS and locally compiled tools. Fixed workloads are unchanged; hardware validation is pending."] if legacy else []}


def hardware():
    cpu = {}
    for line in (read("/proc/cpuinfo") or "").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            cpu.setdefault(key.strip(), value.strip())
    mounts = command(["findmnt", "-J", "-o", "SOURCE,TARGET,FSTYPE", "/"])
    model = (read("/proc/device-tree/model") or read("/sys/firmware/devicetree/base/model")
             or cpu.get("Model") or read("/sys/class/dmi/id/product_name") or platform.machine())
    mem = memory()
    return {
        "hostname": socket.gethostname(),
        "manufacturer": "Raspberry Pi" if model.startswith("Raspberry Pi") else read("/sys/class/dmi/id/sys_vendor"),
        "board_model": model,
        "board_profile": board_profile(model, platform.machine(), cpu.get("Revision")),
        "cpu": cpu.get("model name") or cpu.get("Hardware") or platform.processor(),
        "architecture": platform.machine(), "core_count": os.cpu_count(),
        "ram_bytes": mem.get("MemTotal"), "memory_available_bytes": mem.get("MemAvailable"),
        "os": read("/etc/os-release") or platform.platform(), "kernel": platform.release(),
        "storage_mount": mounts, "storage_type": None,
        "gpu_renderer": None, "graphics_driver": None,
        "platform": platform.system(),
    }


def cpu_ticks():
    line = (read("/proc/stat") or "").splitlines()
    if not line:
        return None
    values = [int(x) for x in line[0].split()[1:9]]
    return sum(values), values[3] + values[4]


def processes():
    rows = []
    for path in glob.glob("/proc/[0-9]*/stat"):
        value = read(path)
        if value:
            try:
                end = value.rindex(")")
                parts = value[end + 2:].split()
                rows.append((int(Path(path).parent.name), value[value.index("(") + 1:end], int(parts[11]) + int(parts[12])))
            except (ValueError, IndexError):
                pass
    return {pid: (name, ticks) for pid, name, ticks in rows}


class Sampler:
    def __init__(self):
        self.previous = cpu_ticks()
        self.vcgencmd = shutil.which("vcgencmd")

    def sample(self):
        ticks = cpu_ticks()
        utilization = None
        if ticks and self.previous:
            total = ticks[0] - self.previous[0]
            if total > 0:
                utilization = 100 * (1 - (ticks[1] - self.previous[1]) / total)
        self.previous = ticks
        temperatures = []
        for path in sorted(glob.glob("/sys/class/thermal/thermal_zone*/temp")):
            raw = read(path)
            try:
                temperatures.append({"sensor": str(Path(path).parent.name), "type": read(str(Path(path).parent / "type")), "celsius": float(raw) / 1000})
            except (TypeError, ValueError):
                pass
        throttle = None
        if self.vcgencmd:
            raw = command([self.vcgencmd, "get_throttled"])
            try:
                throttle = int(raw.split("=")[1], 16)
            except (AttributeError, ValueError, IndexError):
                pass
            if not temperatures:
                raw = command([self.vcgencmd, "measure_temp"])
                try:
                    temperatures.append({"sensor": "vcgencmd", "type": "SoC", "celsius": float(raw.split("=")[1].split("'")[0])})
                except (AttributeError, ValueError, IndexError):
                    pass
        frequencies = []
        for path in sorted(glob.glob("/sys/devices/system/cpu/cpufreq/policy*/scaling_cur_freq")):
            try:
                frequencies.append(float(read(path)) / 1000)
            except (TypeError, ValueError):
                pass
        if not frequencies and self.vcgencmd:
            raw = command([self.vcgencmd, "measure_clock", "arm"])
            try:
                frequencies.append(float(raw.split("=")[1]) / 1e6)
            except (AttributeError, ValueError, IndexError):
                pass
        cooling = {}
        for pattern in ("/sys/class/hwmon/hwmon*/fan*_input", "/sys/class/hwmon/hwmon*/pwm[0-9]", "/sys/class/thermal/cooling_device*/cur_state"):
            for path in sorted(glob.glob(pattern)):
                cooling[path] = read(path)
        mem = memory()
        return {"temperature_c": max((v["celsius"] for v in temperatures), default=None),
                "sensors": temperatures, "cpu_mhz": max(frequencies, default=None),
                "cpu_utilization": utilization,
                "memory_used_bytes": mem.get("MemTotal", 0) - mem.get("MemAvailable", 0) if "MemAvailable" in mem else None,
                "throttled_bits": throttle, "cooling": cooling}
