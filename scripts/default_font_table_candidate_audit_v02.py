"""Audit fixed 3x3 Table candidates against the official runtime capture."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validators.visual.fidelity import digest


ROOT = Path(__file__).resolve().parents[1]
TASK = ROOT / "artifacts/task-039"
SOURCE = ROOT / "examples/acceptance-prototype/source-geometry.json"
REFERENCE = ROOT / "adapters/figma/metadata/table-reference/data.table.default.png"
CELLS = ("张三", "启用", "管理员", "李四", "启用", "编辑", "王五", "停用", "访客")
TEXT_X = (18, 482.328125, 946.65625)
TEXT_Y = (12, 60, 108)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def pixel_review(reference, candidate):
    source = Image.open(reference).convert("RGB")
    native = Image.open(candidate).convert("RGB")
    if source.size != native.size or source.size != (1392, 144):
        raise ValueError("Table geometry changed")
    counts = {"textDifferences": 0, "nonTextDifferences": 0}
    for y in range(144):
        for x in range(1392):
            text_zone = any(y0 <= y < y0 + 27 and x0 - 4 <= x < x0 + 61
                            for y0 in (10, 58, 106) for x0 in (18, 482, 946))
            key = "textDifferences" if text_zone else "nonTextDifferences"
            counts[key] += source.getpixel((x, y)) != native.getpixel((x, y))
    return counts


def ordered_text(capture, platform):
    values = capture["texts" if platform == "figma" else "text"]
    if platform == "figma":
        return values
    return sorted(values, key=lambda t: (t["y"], t["x"]))


def audit():
    ir = read(SOURCE)
    source = next(c for c in ir["components"] if c["logicalComponentId"] == "data.table.default")
    expected_columns = [{"title": title, "key": key, "width": 464} for title, key in
                        (("姓名", "name"), ("状态", "status"), ("角色", "role"))]
    expected_data = [dict(zip(("name", "status", "role"), CELLS[i:i + 3])) for i in (0, 3, 6)]
    if (ir["status"] != "PASS" or sha(REFERENCE) != source["screenshot"]["sha256"]
            or source["screenshot"]["path"] != "data.table.default.png"
            or source["rootBounds"] != {"width": 1392, "height": 144}
            or source["props"] != {"showHeader": False, "border": False, "stripe": False,
                                   "columns": expected_columns, "data": expected_data}):
        raise ValueError("Official Table source changed")
    review = read(TASK / "visual-review.json")
    rows = {}
    for platform in ("figma", "penpot"):
        folder = TASK / platform
        creation = read(folder / "creation.json")
        capture = read(folder / "independent-capture.json")
        repeated = read(folder / "repeat-native-read.json")
        target = read(ROOT / f"adapters/{platform}/metadata/default-font-target-0.2.{0 if platform == 'figma' else 1}.json")
        structure = read(folder / ("structure.json" if platform == "figma" else "creation.json"))
        nodes = structure["nodes"]
        texts = ordered_text(capture, platform)
        repeat_texts = ordered_text(repeated, platform)
        metrics = pixel_review(REFERENCE, folder / "component-native.png")
        font_ok = (all(t["fontName"]["family"] == "Inter" and t["fontName"]["style"] == "Regular"
                       and t["fontSize"] == 14 and t["fontWeight"] == 400
                       and t["lineHeight"] == {"unit": "PIXELS", "value": 21}
                       and t["hasMissingFont"] is False for t in texts)
                   if platform == "figma" else
                   all(t["fontId"] == "sourcesanspro" and t["fontVariantId"] == "regular"
                       and t["fontSize"] == "14" and t["fontWeight"] == "400"
                       and t["lineHeight"] == "1.5" for t in texts)
                   and capture["fileValidation"] == [])
        native_type = "TEXT" if platform == "figma" else "text"
        rectangle_type = "RECTANGLE" if platform == "figma" else "rectangle"
        checks = {
            "sameNativeMainAndInstance": (
                all(x["fileReference"] == target["fileReference"] for x in (creation, capture, repeated))
                and len({x["pageReference"] for x in (creation, capture, repeated)}) == 1
                and len({x["componentId"] for x in (creation, capture, repeated)}) == 1
                and len({x["instanceId"] for x in (creation, capture, repeated)}) == 1
                and capture["instanceMainComponentId" if platform == "figma" else "instanceComponentId"] == capture["componentId"]
                and all(x["componentBounds"] == {"width": 1392, "height": 144} for x in (creation, capture, repeated))),
            "fixedDataAndDefaultFont": (len(texts) == 9 and tuple(t["characters"] for t in texts) == CELLS
                                        and font_ok and target["defaultFont"]["family"] ==
                                        ("Inter" if platform == "figma" else "sourcesanspro")),
            "nativeRepeatStable": (sha(folder / "component-native.png") == sha(folder / "repeat-native.png")
                                   and [(t["id"], t["characters"]) for t in texts] ==
                                   [(t["id"], t["characters"]) for t in repeat_texts]),
            "nativeHierarchy": (len(nodes) == 26 and sum(n["type"] == native_type for n in nodes) == 9
                                and sum(n["type"] == rectangle_type for n in nodes) == 4
                                and len({n["id"] for n in nodes}) == 26
                                and all(n["parentId"] is None or n["parentId"] in {p["id"] for p in nodes}
                                        or n["id"] == capture["componentId"] for n in nodes)),
            "nonTextPixelsExact": metrics["nonTextDifferences"] == 0,
            "textVisible": metrics["textDifferences"] > 0,
            "visualReview": (review["status"] == "PASS"
                             and review["platforms"][platform]["nativePngSha256"] == sha(folder / "component-native.png")
                             and tuple(review["platforms"][platform]["legibleCells"]) == CELLS
                             and review["platforms"][platform]["glyphsComplete"] is True
                             and review["platforms"][platform]["clippedText"] is False
                             and review["platforms"][platform]["tofuOrMissingGlyph"] is False),
        }
        rows[platform] = {
            "status": "CANDIDATE_REVIEW" if all(checks.values()) else "FAIL",
            "checks": checks,
            "pixelDiagnostics": metrics,
            "fileReference": capture["fileReference"],
            "pageReference": capture["pageReference"],
            "componentId": capture["componentId"],
            "instanceId": capture["instanceId"],
            "evidenceSha256": {name: sha(folder / name) for name in
                               ("creation.json", "independent-capture.json", "component-native.png",
                                "repeat-native-read.json", "repeat-native.png")
                               + (("structure.json",) if platform == "figma" else ())},
        }
    status = "CANDIDATE_REVIEW" if all(row["status"] == "CANDIDATE_REVIEW" for row in rows.values()) else "FAIL"
    return {"scope": "v02-default-font-table-candidate", "status": status,
            "logicalComponentId": source["logicalComponentId"],
            "sourceVersion": source["provenance"]["sourceVersion"],
            "componentIrSha256": digest(source),
            "sourceScreenshotSha256": sha(REFERENCE),
            "visualReviewSha256": sha(TASK / "visual-review.json"),
            "platforms": rows, "effectiveCjkFontIdentity": "UNVERIFIED",
            "nativeAdmission": "NOT_RUN", "releaseReady": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        parser.error("Output must stay in artifacts")
    output.parent.mkdir(parents=True, exist_ok=True)
    result = audit()
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "platforms": {k: v["status"] for k, v in result["platforms"].items()}}, ensure_ascii=False))
    return 0 if result["status"] == "CANDIDATE_REVIEW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
