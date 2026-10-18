"""Shared inline branding; no external assets or animation."""
from pathlib import Path
from urllib.parse import quote

PRODUCT_NAME = "GAM3T3CH 3D Benchmark"


def brand_mark():
    return (Path(__file__).resolve().parent.parent / "showcase" / "brand" / "g3-mark.svg").read_text(encoding="utf-8")


def apply_branding(template):
    mark = brand_mark()
    return template.replace("__BRAND_MARK__", mark).replace("__BRAND_ICON__", "data:image/svg+xml," + quote(mark, safe=""))
