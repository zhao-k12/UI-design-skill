"""Build a platform-neutral typography envelope from two native readbacks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
FIGMA = HERE / "figma-native-read.json"
PENPOT = HERE / "penpot-native-read.json"
OUTPUT = HERE / "text-envelope.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(figma: dict, penpot: dict, figma_sha: str, penpot_sha: str) -> dict:
    if figma["status"] != "PASS" or penpot["status"] != "PASS":
        raise ValueError("Both native readbacks must pass")
    if figma["platform"] != "figma" or penpot["platform"] != "penpot":
        raise ValueError("Wrong platform evidence")
    if figma["font"] != {"family": "Inter", "style": "Regular", "weight": 400}:
        raise ValueError("Unexpected Figma font")
    if penpot["font"] != {"fontId": "sourcesanspro", "fontVariantId": "regular", "weight": 400}:
        raise ValueError("Unexpected Penpot font")
    f_rows = {r["uiIrId"]: r for r in figma["rows"]}
    p_rows = {r["uiIrId"]: r for r in penpot["rows"]}
    if len(f_rows) != len(figma["rows"]) or len(p_rows) != len(penpot["rows"]):
        raise ValueError("Duplicate text ID")
    if set(f_rows) != set(p_rows) or len(f_rows) != 12:
        raise ValueError("Incomplete platform text set")
    rows = []
    for key in sorted(f_rows):
        f, p = f_rows[key], p_rows[key]
        if f["characters"] != p["characters"]:
            raise ValueError(f"Text mismatch: {key}")
        if f["width"] <= 0 or p["width"] <= 0 or f["height"] <= 0 or p["height"] <= 0:
            raise ValueError(f"Invalid native dimensions: {key}")
        if p["fontId"] != "sourcesanspro" or p["fontVariantId"] != "regular":
            raise ValueError(f"Penpot row font mismatch: {key}")
        size, line = (20, 28) if key == "title" else (14, 22)
        if (f["fontSize"], f["lineHeight"]) != (size, line):
            raise ValueError(f"Figma typography mismatch: {key}")
        if float(p["fontSize"]) != size or abs(float(p["lineHeight"]) * size - line) > 1e-6:
            raise ValueError(f"Penpot typography mismatch: {key}")
        rows.append({
            "uiIrId": key,
            "characters": f["characters"],
            "width": max(f["width"], p["width"]),
            "height": max(f["height"], p["height"]),
            "platformMeasurements": {
                "figma": {"nodeId": f["nodeId"], "width": f["width"], "height": f["height"]},
                "penpot": {"nodeId": p["nodeId"], "width": p["width"], "height": p["height"]},
            },
        })
    return {
        "kind": "platform-neutral-text-envelope",
        "status": "PASS",
        "policy": {"width": "max(figma,penpot)", "height": "max(figma,penpot)"},
        "sources": {
            "figma": {"path": "artifacts/task-050/figma-native-read.json", "sha256": figma_sha,
                      "fileReference": figma["fileReference"], "pageId": figma["pageId"]},
            "penpot": {"path": "artifacts/task-050/penpot-native-read.json", "sha256": penpot_sha,
                       "fileReference": penpot["fileReference"], "pageId": penpot["pageId"]},
        },
        "rows": rows,
    }


def main() -> None:
    result = build(_load(FIGMA), _load(PENPOT), _sha(FIGMA), _sha(PENPOT))
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"TASK-050 text envelope PASS: {len(result['rows'])} rows")


if __name__ == "__main__":
    main()
