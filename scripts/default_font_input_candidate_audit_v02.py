"""Source-locked candidate audit for the V0.2 default-font Input placeholder."""
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
SOURCE = ROOT / "artifacts/task-023/replay-final/first/component_ir.json"
PLATFORMS = {
    "figma": ("default-font-target-0.2.0.json", "Inter", "Regular", 400),
    "penpot": ("default-font-target-0.2.1.json", "sourcesanspro", "regular", "400"),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def review_pixels(reference_path, native_path):
    source = Image.open(reference_path).convert("RGBA")
    native = Image.open(native_path).convert("RGBA")
    if source.size != native.size or source.size != (240, 32):
        raise ValueError("Input native geometry changed")
    white = Image.new("RGBA", source.size, "white")
    white.alpha_composite(native)
    native = white.convert("RGB")
    source = source.convert("RGB")
    regions = {"textZoneDifferences": 0, "cornerDifferences": 0,
               "nonTextDifferences": 0, "visibleInkByCharacter": [0] * 5}
    for y in range(32):
        for x in range(240):
            a, b = source.getpixel((x, y)), native.getpixel((x, y))
            if 5 <= x < 100 and 3 <= y < 29:
                regions["textZoneDifferences"] += a != b
                if 7 <= x < 77 and 7 <= y < 26 and max(abs(b[k] - (197, 200, 206)[k]) for k in range(3)) < 30:
                    regions["visibleInkByCharacter"][(x - 7) // 14] += 1
            elif (x < 5 or x >= 235) and (y < 5 or y >= 27):
                regions["cornerDifferences"] += a != b
            else:
                regions["nonTextDifferences"] += a != b
    return regions


def audit():
    bundle = json.loads(SOURCE.read_bytes())
    visual = json.loads((ROOT / "artifacts/task-033/visual-review.json").read_bytes())
    source = next(item for item in bundle["components"] if item["logicalComponentId"] == "form.input.default.medium")
    reference = SOURCE.parent / source["screenshot"]["path"]
    field = next(item for item in source["nodes"] if item["path"] == "0.1")
    placeholder = field["attributes"]["placeholder"]
    css = field["computedStyle"]
    if (bundle["status"] != "PASS" or sha(reference) != source["screenshot"]["sha256"]
            or source["rootBounds"] != {"width": 240, "height": 32}
            or source["props"]["modelValue"] != "" or placeholder != "请输入姓名"
            or css["border-top-color"] != "rgb(220, 222, 226)"
            or field["pseudoElements"]["::placeholder"]["color"] != "rgb(197, 200, 206)"):
        raise ValueError("Official Input source changed")
    rows = {}
    for platform, (target_name, family, style, weight) in PLATFORMS.items():
        folder = ROOT / "artifacts/task-033" / platform
        creation = json.loads((folder / "creation.json").read_bytes())
        current = json.loads((folder / "independent-capture.json").read_bytes())
        repeated = json.loads((folder / "repeat-native-read.json").read_bytes())
        target = json.loads((ROOT / f"adapters/{platform}/metadata/{target_name}").read_bytes())
        expected_file = target["fileReference"]
        text = current["label"]
        metrics = review_pixels(reference, folder / "component-native.png")
        seen = visual["platforms"][platform]
        checks = {
            "sameNativeComponentAndInstance": (creation["fileReference" if platform == "figma" else "fileId"]
                == current["fileReference"] == repeated["fileReference"] == expected_file
                and creation["componentId"] == current["componentId"] == repeated["componentId"]
                and creation["instanceId"] == current["instanceId"] == repeated["instanceId"]
                and current["instanceMainComponentId" if platform == "figma" else "instanceComponentId"] == creation["componentId"]),
            "sourceGeometryAndField": (current["componentBounds"] == source["rootBounds"]
                and current["fieldBounds"] == source["rootBounds"]
                and current["strokeWeight"] == 1 and current["radius"] == 4
                and current["padding"] == {"left": 7, "right": 7, "top": 4, "bottom": 4}),
            "placeholderAndDefaultFont": (text["characters"] == placeholder
                and (text["fontName"]["family"] == family and text["fontName"]["style"] == style
                     and text["fontWeight"] == weight and text["fontSize"] == 14
                     and text["lineHeight"] == {"unit": "PIXELS", "value": 21}
                     and text["hasMissingFont"] is False if platform == "figma"
                     else text["fontId"] == family and text["fontVariantId"] == style
                     and text["fontWeight"] == weight and text["fontSize"] == "14"
                     and text["lineHeight"] == "1.5" and current["fileValidation"] == [])),
            "nativeRepeatStable": (sha(folder / "component-native.png") == sha(folder / "repeat-native.png")
                and repeated["label"]["characters"] == placeholder),
            "nonTextPixelsExact": metrics["nonTextDifferences"] == 0,
            "visibleFiveGlyphs": all(count > 2 for count in metrics["visibleInkByCharacter"]),
            "hashBoundVisualReview": (visual["status"] == "PASS"
                and visual["expectedPlaceholder"] == placeholder
                and visual["effectiveCjkFontIdentity"] == "UNVERIFIED"
                and seen["nativePngSha256"] == sha(folder / "component-native.png")
                and seen["legiblePlaceholder"] == placeholder and seen["glyphsComplete"] is True
                and seen["clippedText"] is False and seen["tofuOrMissingGlyph"] is False),
        }
        rows[platform] = {"status": "CANDIDATE_REVIEW" if all(checks.values()) else "FAIL",
                          "checks": checks, "pixelDiagnostics": metrics,
                          "fileReference": current["fileReference"], "componentId": current["componentId"],
                          "evidenceSha256": {name: sha(folder / name) for name in
                              ("creation.json", "independent-capture.json", "component-native.png",
                               "repeat-native-read.json", "repeat-native.png")},
                          "targetMetadataSha256": sha(ROOT / f"adapters/{platform}/metadata/{target_name}")}
    passed = all(row["status"] == "CANDIDATE_REVIEW" for row in rows.values())
    return {"scope": "v02-default-font-input-candidate", "status": "CANDIDATE_REVIEW" if passed else "FAIL",
            "logicalComponentId": source["logicalComponentId"], "sourceVersion": source["provenance"]["sourceVersion"],
            "componentIrSha256": digest(source), "sourceScreenshotSha256": sha(reference),
            "visualReviewSha256": sha(ROOT / "artifacts/task-033/visual-review.json"),
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
    print(json.dumps({"status": result["status"], "platforms": {k: v["status"] for k, v in result["platforms"].items()},
                      "nativeAdmission": "NOT_RUN"}, ensure_ascii=False))
    return 0 if result["status"] == "CANDIDATE_REVIEW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
