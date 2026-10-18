import math

# Synthetic reference rates, fixed for suite 0.1.0; not a measured reference board.
NORMALIZATION = {
    "cpu": {"integer": 100_000_000, "floating_point": 100_000_000,
            "hash_fnv1a": 500, "rle_roundtrip": 500, "matrix": 1000},
    "memory": {"copy": 1000, "read": 1000, "write": 1000},
}


def geometric(values):
    if not values or any(not math.isfinite(x) or x <= 0 for x in values):
        return None
    return math.exp(sum(math.log(x) for x in values) / len(values))


def scores(results, compatibility=False):
    out = {"cpu": None, "memory": None, "gpu": None, "storage": None, "network": None, "overall": None}
    for group, constants in NORMALIZATION.items():
        data = results.get(group, {})
        if all(key in data for key in constants):
            out[group] = geometric([1000 * data[key]["value"] / reference for key, reference in constants.items()])
    gpu = results.get("gpu", {})
    if not compatibility and gpu.get("width") == 1280 and gpu.get("height") == 720 and len(gpu.get("scenes", [])) == 5:
        out["gpu"] = geometric([1000 * scene["average_fps"] / 60 for scene in gpu["scenes"]])
    # The baseline compute aggregate requires every implemented compute subsystem.
    if all(out[key] is not None for key in ("cpu", "memory", "gpu")):
        out["overall"] = geometric([out[key] for key in ("cpu", "memory", "gpu")])
    return out
