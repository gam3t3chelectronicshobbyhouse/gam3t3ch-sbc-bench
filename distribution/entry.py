"""Frozen desktop/CLI entry point. Native workers reuse this executable."""
import os
from pathlib import Path
import sys

from g3bench.__main__ import main

if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.argv.append("ui")
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        log = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local" / "share"))) / "GAM3T3CH"
        log.mkdir(parents=True, exist_ok=True)
        sys.stderr = (log / "application.log").open("a", encoding="utf-8")
    sys.exit(main())
