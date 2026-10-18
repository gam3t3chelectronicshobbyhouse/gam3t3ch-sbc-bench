import html
import json
from pathlib import Path


def export_report(data, destination):
    template = (Path(__file__).parent / "report.html").read_text(encoding="utf-8")
    payload = json.dumps(data, allow_nan=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    content = template.replace("__RESULT_DATA__", payload)
    content = content.replace("__TITLE__", html.escape(data["hardware"].get("board_model") or "SBC"))
    content = content.replace("__REFRESH__", "")
    target = Path(destination)
    temp = target.with_suffix(".html.tmp")
    temp.write_text(content, encoding="utf-8")
    temp.replace(target)
