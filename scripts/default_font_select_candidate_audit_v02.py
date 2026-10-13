"""Audit the fixed-content Select candidates against the official browser capture."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from PIL import Image

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validators.visual.fidelity import digest


ROOT = Path(__file__).resolve().parents[1]
TASK = ROOT / "artifacts/task-036"
SOURCE = ROOT / "artifacts/task-023/replay-final/first/component_ir.json"
ARROW_PATH = "M0.888672 0L4.375 3.48633L7.86133 0L8.75 0.888672L4.375 5.25L0 0.888672L0.888672 0Z"


def arrow_outline_preserved(svg):
    paths = re.findall(r'<path d="([^"]+)"[^>]+(?:#808695|128, 134, 149)[^>]*>', svg)
    if len(paths) != 1:
        return False
    source = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", ARROW_PATH)]
    native = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", paths[0])]
    return (len(source) == len(native) and
            all(abs(native[i] - source[i] - (219.625 if i % 2 == 0 else 13.25)) <= .001
                for i in range(len(source))))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pixel_review(reference, native):
    source = Image.open(reference).convert("RGB")
    candidate = Image.open(native).convert("RGB")
    if source.size != candidate.size or source.size != (240, 32):
        raise ValueError("Select geometry changed")
    counts = {"textDifferences": 0, "arrowDifferences": 0,
              "arrowAbsoluteError": 0, "cornerDifferences": 0, "nonTextDifferences": 0}
    for y in range(32):
        for x in range(240):
            a, b = source.getpixel((x, y)), candidate.getpixel((x, y))
            if 5 <= x < 60 and 3 <= y < 29:
                key = "textDifferences"
            elif 216 <= x < 231 and 8 <= y < 23:
                key = "arrowDifferences"
                counts["arrowAbsoluteError"] += sum(abs(a[i] - b[i]) for i in range(3))
            elif (x < 6 or x >= 234) and (y < 6 or y >= 26):
                key = "cornerDifferences"
            else:
                key = "nonTextDifferences"
            counts[key] += a != b
    return counts


def audit():
    ir = json.loads(SOURCE.read_text(encoding="utf-8"))
    source = next(c for c in ir["components"] if c["logicalComponentId"] == "form.select.default.medium")
    reference = SOURCE.parent / source["screenshot"]["path"]
    selected = next(n for n in source["nodes"] if n["path"] == "0.0.1.0")
    arrow = next(n for n in source["nodes"] if n["path"] == "0.0.1.1")
    if (ir["status"] != "PASS" or sha(reference) != source["screenshot"]["sha256"]
            or source["rootBounds"] != {"width": 240, "height": 32}
            or source["props"]["modelValue"] != "enabled"
            or selected["computedStyle"]["color"] != "rgb(81, 90, 110)"
            or selected["computedStyle"]["line-height"] != "30px"
            or arrow["computedStyle"]["font-family"] != "Ionicons"
            or arrow["computedStyle"]["color"] != "rgb(128, 134, 149)"):
        raise ValueError("Official Select source changed")
    proof = json.loads((ROOT / "adapters/penpot/metadata/select-native-v1/arrow-glyph-proof.json").read_text(encoding="utf-8"))
    if proof["status"] != "PASS" or not proof["orderedCompleteContoursEqual"]:
        raise ValueError("Official Ionicons glyph proof missing")

    rows = {}
    for platform, font, style in (("figma", "Inter", "Regular"), ("penpot", "sourcesanspro", "regular")):
        folder = TASK / platform
        creation = json.loads((folder / "creation.json").read_text(encoding="utf-8"))
        capture = json.loads((folder / "independent-capture.json").read_text(encoding="utf-8"))
        repeated = json.loads((folder / "repeat-native-read.json").read_text(encoding="utf-8"))
        svg = (folder / "component-native.svg").read_text(encoding="utf-8")
        target = json.loads((ROOT / f"adapters/{platform}/metadata/default-font-target-0.2.{0 if platform == 'figma' else 1}.json").read_text(encoding="utf-8"))
        metrics = pixel_review(reference, folder / "component-native.png")
        font_check = (capture["selected"]["fontName"]["family"] == font
                      and capture["selected"]["fontName"]["style"] == style
                      and capture["selected"]["fontSize"] == 14
                      and capture["selected"]["fontWeight"] == 400
                      and capture["selected"]["lineHeight"] == {"unit": "PIXELS", "value": 30}
                      and capture["selected"]["hasMissingFont"] is False
                      and capture["arrow"]["fontName"]["family"] == "Ionicons"
                      and capture["arrow"]["characters"] == "\uf116"
                      if platform == "figma" else
                      capture["selected"]["fontId"] == font
                      and capture["selected"]["fontVariantId"] == style
                      and capture["selected"]["fontSize"] == "14"
                      and capture["selected"]["fontWeight"] == "400"
                      and capture["selected"]["lineHeight"] == "1.5"
                      and capture["arrow"] == {"type": "group", "x": 219.625, "y": 13.25,
                                                "width": 9, "height": 6}
                      and capture["fileValidation"] == [])
        checks = {
            "sameNativeMainAndInstance": (creation["fileReference"] == capture["fileReference"]
                                          == repeated["fileReference"] == target["fileReference"]
                                          and creation["componentId"] == capture["componentId"] == repeated["componentId"]
                                          and creation["instanceId"] == capture["instanceId"] == repeated["instanceId"]
                                          and capture["instanceMainComponentId" if platform == "figma" else "instanceComponentId"] == capture["componentId"]),
            "fixedSelectedValueAndDefaultFont": capture["selected"]["characters"] == "启用" and font_check,
            "nativeRepeatStable": (sha(folder / "component-native.png") == sha(folder / "repeat-native.png")
                                   and repeated["selected"]["characters"] == "启用"),
            "officialArrowPreserved": arrow_outline_preserved(svg),
            "nonTextPixelsExact": metrics["nonTextDifferences"] == 0,
            "cornerAntialiasWithinPolicy": metrics["cornerDifferences"] <= 48,
            "arrowRasterWithinPolicy": metrics["arrowAbsoluteError"] <= 1500,
            "textVisible": metrics["textDifferences"] > 0,
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
                                "component-native.svg", "repeat-native-read.json", "repeat-native.png")},
        }
    status = "CANDIDATE_REVIEW" if all(row["status"] == "CANDIDATE_REVIEW" for row in rows.values()) else "FAIL"
    return {"scope": "v02-default-font-select-candidate", "status": status,
            "logicalComponentId": source["logicalComponentId"],
            "sourceVersion": source["provenance"]["sourceVersion"],
            "componentIrSha256": digest(source),
            "sourceScreenshotSha256": sha(reference),
            "officialArrowGlyphProofSha256": sha(ROOT / "adapters/penpot/metadata/select-native-v1/arrow-glyph-proof.json"),
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
