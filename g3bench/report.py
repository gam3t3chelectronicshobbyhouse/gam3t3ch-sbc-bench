import html
import json
import re
from pathlib import Path
from .branding import apply_branding


def export_report(data, destination, comparisons=None):
    from .diagnostics import advice
    template = (Path(__file__).parent / "report.html").read_text(encoding="utf-8")
    payload = json.dumps(data, allow_nan=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    extras = json.dumps(comparisons or [], allow_nan=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    advice_json = json.dumps(advice(data), allow_nan=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    replacements = {"__ADVICE_DATA__": advice_json, "__RESULT_DATA__": payload, "__COMPARISON_DATA__": extras,
                    "__ANALYSIS_SCRIPT__": (Path(__file__).parent / "analysis.js").read_text(encoding="utf-8"),
                    "__SHARE_SCRIPT__": (Path(__file__).parent / "share.js").read_text(encoding="utf-8"),
                    "__TITLE__": html.escape(data["hardware"].get("board_model") or "SBC"), "__REFRESH__": ""}
    content = re.sub("|".join(replacements), lambda match: replacements[match.group()], apply_branding(template))
    target = Path(destination)
    temp = target.with_suffix(".html.tmp")
    temp.write_text(content, encoding="utf-8")
    temp.replace(target)
