"""Check files written by actual frozen workers, never substitute fixture data."""
import json
from pathlib import Path
import sys

native = json.loads(next(Path(sys.argv[1]).glob("*/result.json")).read_text())
showcase = json.loads(next(Path(sys.argv[2]).glob("*/result.json")).read_text())
assert native["test_status"]["cpu"]["status"] == "passed", native["test_status"]
assert native["test_status"]["memory"]["status"] == "passed", native["test_status"]
assert native["scores"]["overall"] is None
assert showcase["test_status"]["showcase"]["status"] == "smoke_validated", showcase["test_status"]
assert showcase["results"]["showcase"]["width"] == 1280
assert showcase["results"]["showcase"]["height"] == 720
assert all(value is None for value in showcase["scores"].values())
print("Frozen native workers and embedded Godot source initialized correctly.")
