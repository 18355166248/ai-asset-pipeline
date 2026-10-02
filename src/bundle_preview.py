"""生成离线预览：只嵌入本次产物，不依赖网络或本地文件 fetch。"""
from __future__ import annotations

import base64
import json
from pathlib import Path


def write_preview(root: Path, manifest: dict, report: dict) -> None:
    data = {"manifest": manifest, "report": report, "images": {}}
    paths = [item["path"] for item in manifest.get("images", [])]
    if manifest.get("atlas"):
        paths.append(manifest["atlas"])
    for path in paths:
        data["images"][path] = "data:image/png;base64," + base64.b64encode(
            (root / path).read_bytes()).decode("ascii")
    # 文件名、标题和来源都可能来自外部；JSON 中的 < 必须转义，文本只写 textContent。
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    template = Path(__file__).with_name("bundle_preview.html").read_text(encoding="utf-8")
    (root / "preview.html").write_text(template.replace("__BUNDLE_DATA__", payload), encoding="utf-8")
