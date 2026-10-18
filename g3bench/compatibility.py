"""Capability-based scheduling: board identity never changes scored work."""
from . import VERSION, WORKLOAD
import subprocess

MEMORY_REQUIRED_BYTES = 96 * 1024 * 1024  # two fixed 32 MiB buffers + 32 MiB headroom


def state(status, reason):
    return {"status": status, "reason": reason}


def memory_check(hw):
    total, available = hw.get("ram_bytes"), hw.get("memory_available_bytes")
    if total is not None and total < MEMORY_REQUIRED_BYTES:
        return state("unsupported", "Fixed memory workload needs at least 96 MiB RAM including headroom; buffer size is not reduced.")
    if available is not None and available < MEMORY_REQUIRED_BYTES:
        return state("unavailable", "Less than 96 MiB RAM currently available. Free memory and rerun; buffer size is not reduced.")
    return state("ready", "Fixed native memory workload; availability rechecked before execution.")


def prepare(hw, native, gpu, execute, *, headless=False, compat=False, fullscreen=False):
    info = None
    native_state = state("unavailable", "Native executable not built. Compile tools for this board/OS architecture.")
    if native:
        try:
            info = execute(native, ["info"], timeout=15)
            if info.get("suite_version") != VERSION or info.get("workload_id") != WORKLOAD:
                raise ValueError("Native suite/workload mismatch; rebuild the tools.")
            native_state = state("ready", "Native executable runs and matches this suite/workload.")
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
            info = None
            native_state = state("unavailable", "Native tool cannot run on this installation: " + str(exc))
    plan = {"cpu": dict(native_state), "memory": memory_check(hw) if info else dict(native_state)}
    if headless:
        plan["gpu"] = state("skipped", "Headless mode requested.")
    elif not gpu:
        plan["gpu"] = state("unavailable", "SDL2/GLES2 executable not built or installed.")
    else:
        flags = ["--probe"] + (["--compat"] if compat else []) + (["--fullscreen"] if fullscreen else [])
        try:
            probe = execute(gpu, flags, timeout=15)
            if probe.get("suite_version") != VERSION or probe.get("workload_id") != WORKLOAD:
                raise ValueError("GPU suite/workload mismatch; rebuild the tools.")
            status = probe.get("status")
            if status not in {"ready", "unavailable", "unsupported"}:
                raise ValueError("Invalid GPU capability response")
            plan["gpu"] = state(status, probe.get("reason", "GLES2 capability probe completed."))
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
            plan["gpu"] = state("unavailable", "GPU capability probe unavailable: " + str(exc))
    return info, plan
