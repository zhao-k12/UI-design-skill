"""Native fidelity gate for the fixed default-font checked Checkbox."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image

from scripts.checkbox_pixel_diagnostics_v02 import on_white
from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT


SOURCE = ROOT / "artifacts/task-058/checkbox-source"
TASK = ROOT / "artifacts/task-061"
POLICY = ROOT / "validators/visual/DEFAULT_FONT_CHECKBOX_POLICY.md"
FILES = ("native-read.json", "native.png", "native-repeat.png", "native.svg")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def pixels(reference, candidate):
    original, native = on_white(reference), on_white(candidate)
    if original.size != native.size or original.size != (52, 21):
        return {"sizeMismatch": [original.size, native.size], "pass": False}
    corners = {(x, y) for y in (2, 3, 16, 17) for x in (0, 1, 14, 15)}
    mark_area = {(x, y) for y in range(5, 15) for x in range(3, 14)}
    outside = []
    corner_deltas = []
    for y in range(21):
        for x in range(16):
            delta = max(abs(a - b) for a, b in zip(original.getpixel((x, y)), native.getpixel((x, y))))
            if delta and (x, y) not in mark_area:
                if (x, y) in corners:
                    corner_deltas.append(delta)
                else:
                    outside.append([x, y, delta])
    def bright(image):
        return {position for position in mark_area if min(image.getpixel(position)) >= 220}
    source_mark, native_mark = bright(original), bright(native)
    extra, missing = native_mark - source_mark, source_mark - native_mark
    iou = len(source_mark & native_mark) / len(source_mark | native_mark)
    result = {"nonMarkChangesOutsideCorners": outside,
              "cornerMaximumChannelDelta": max(corner_deltas, default=0),
              "sourceMarkPixels": len(source_mark), "nativeMarkPixels": len(native_mark),
              "missingSourceMarkPixels": sorted([list(p) for p in missing]),
              "extraNativeMarkPixels": sorted([list(p) for p in extra]),
              "markIntersectionOverUnion": round(iou, 4)}
    result["pass"] = not outside and result["cornerMaximumChannelDelta"] <= 40 \
        and not missing and len(extra) <= 2 and iou >= 0.875
    return result


def glyphs(path):
    image = on_white(path)
    counts = [sum(min(image.getpixel((x, y))) < 200
                  for y in range(2, 19) for x in range(left, right))
              for left, right in ((20, 34), (34, 48))]
    edge = sum(min(image.getpixel((x, y))) < 200
               for y in range(21) for x in range(20, 52)
               if x == 51 or y in (0, 20))
    return {"perCharacterDarkPixels": counts, "textOuterEdgeInkPixels": edge,
            "pass": min(counts) >= 20 and edge == 0}


def structure(platform, observed, candidate):
    if platform == "figma":
        component, box, tick, label, instance = (observed[k] for k in ("component", "box", "tick", "label", "instance"))
        def rgb(paint):
            return tuple(round(paint["color"][channel] * 255) for channel in ("r", "g", "b"))
        return (observed["fileReference"] == candidate["fileReference"] and
                observed["pageId"] == candidate["pageReference"] and
                component["id"] == candidate["componentId"] and component["type"] == "COMPONENT" and
                (component["width"], component["height"]) == (52, 21) and
                component["layoutMode"] == "NONE" and
                [(child["id"], child["type"]) for child in component["children"]] ==
                [(box["id"], "FRAME"), (label["id"], "TEXT")] and
                (box["x"], box["y"], box["width"], box["height"], box["radius"]) == (0, 2, 16, 16, 2) and
                rgb(box["fills"][0]) == rgb(box["strokes"][0]) == (45, 140, 240) and
                (tick["strokeWeight"], tick["strokeCap"]) == (2, "SQUARE") and
                bool(tick["vectorPaths"]) and
                (label["text"], label["fontName"]["family"], label["fontName"]["style"], label["fontSize"]) ==
                ("启用", "Inter", "Regular", 14) and
                (label["x"], label["y"], label["width"], label["height"]) == (20, 0, 28, 21) and
                rgb(label["fills"][0]) == (81, 90, 110) and
                instance["id"] == candidate["instanceId"] and instance["mainComponentId"] == component["id"])
    main, box, tick, label, instance = (observed[k] for k in ("main", "box", "tick", "label", "instance"))
    return (observed["fileId"] == candidate["fileReference"] and
            observed["pageId"] == candidate["pageReference"] and
            observed["componentId"] == candidate["componentId"] and observed["fileValidation"] == 0 and
            (main["width"], main["height"]) == (52, 21) and
            (box["x"] - main["x"], box["y"] - main["y"], box["width"], box["height"], box["radius"]) ==
            (0, 2, 16, 16, 2) and
            box["fills"][0]["fillColor"].upper() == box["strokes"][0]["strokeColor"].upper() == "#2D8CF0" and
            tick["type"] == "path" and tick["strokes"][0]["strokeColor"].upper() == "#FFFFFF" and
            tick["strokes"][0]["strokeWidth"] == 2 and tick["strokes"][0]["strokeCapStart"] == "square" and
            (label["text"], label["fontId"], label["fontVariantId"], label["fontSize"], label["lineHeight"]) ==
            ("启用", "sourcesanspro", "regular", "14", "1.5") and
            (label["x"] - main["x"], label["y"] - main["y"], label["width"], label["height"]) ==
            (20, 0, 28, 21) and label["fills"][0]["fillColor"].upper() == "#515A6E" and
            instance["id"] == candidate["instanceId"] and instance["componentId"] == candidate["componentId"] and
            instance["isCopy"] is True)


def svg_semantics(platform, path):
    root = ET.fromstring(path.read_bytes())
    if root.tag.split("}")[-1] != "svg" or (root.attrib.get("width"), root.attrib.get("height")) != ("52", "21"):
        return False
    content = path.read_text(encoding="utf-8").lower()
    if platform == "figma":
        return all(value in content for value in ("#2d8cf0", "#515a6e", 'stroke="white"', "m4.5 10.1l6.6 12.2l11.5 7.25"))
    return all(value in content for value in ("rgb(45, 140, 240)", "rgb(81, 90, 110)",
                                                 "rgb(255, 255, 255)", "sourcesanspro", "启用"))


def run():
    issues = verify_artifacts(SOURCE, expected_types={"Checkbox"})
    source = read(SOURCE / "component_ir.json")["components"][0]
    if source["logicalComponentId"] != "form.checkbox.default.enabled" or source["content"]["text"] != "启用":
        issues.append({"code": "wrong_checkbox_source"})
    review = read(TASK / "visual-review.json")
    reference = SOURCE / source["screenshot"]["path"]
    rows = {}
    for platform in ("figma", "penpot"):
        folder = TASK / platform
        candidate_path = ROOT / f"adapters/{platform}/metadata/checkbox-default-font-candidate-0.2.0.json"
        candidate, observed = read(candidate_path), read(folder / "native-read.json")
        native, repeat, svg = (folder / name for name in FILES[1:])
        pixels_result, glyph_result = pixels(reference, native), glyphs(native)
        visual = review["platforms"][platform]
        checks = {
            "candidateSourceLocked": candidate["status"] == "CANDIDATE_REVIEW" and all(candidate["checks"].values())
                and candidate["componentIrSha256"] == sha(SOURCE / "component_ir.json"),
            "independentNativeStructure": structure(platform, observed, candidate),
            "nativeRepeatStable": sha(native) == sha(repeat),
            "nativeSvgSemantics": svg_semantics(platform, svg),
            "sourceColorsAndMarkRaster": pixels_result["pass"],
            "twoVisibleUnclippedGlyphs": glyph_result["pass"],
            "hashBoundVisualReview": review["status"] == "PASS" and review["expectedText"] == "启用" and
                review["effectiveCjkFontIdentity"] == "UNVERIFIED" and
                visual["nativePngSha256"] == sha(native) and visual["legibleText"] == "启用" and
                visual["completeGlyphs"] is True and visual["clippedText"] is False and
                visual["emptyOrDetached"] is False and visual["checkedMarkVisible"] is True,
        }
        rows[platform] = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
                          "fileReference": candidate["fileReference"], "componentId": candidate["componentId"],
                          "instanceId": candidate["instanceId"], "pixelDiagnostics": pixels_result,
                          "glyphDiagnostics": glyph_result,
                          "evidenceSha256": {name: sha(folder / name) for name in FILES},
                          "candidateMetadataSha256": sha(candidate_path)}
    passed = not issues and all(row["status"] == "PASS" for row in rows.values())
    return {"scope": "production", "gateVersion": "0.2.6", "status": "PASS" if passed else "FAIL",
            "logicalComponentId": source["logicalComponentId"], "componentType": "Checkbox",
            "variants": ["default"], "sourceVersion": source["provenance"]["sourceVersion"],
            "componentIrSha256": sha(SOURCE / "component_ir.json"),
            "admissionEligible": passed, "issues": issues if issues else ([] if passed else ["checkbox_fidelity_failed"]),
            "platforms": rows, "evidenceSha256": {"sourceScreenshot": sha(reference),
                "visualReview": sha(TASK / "visual-review.json"), "policy": sha(POLICY)},
            "contentScopeProposal": {"kind": "fixed-native-content", "text": "启用", **source["props"],
                                     "width": 52, "height": 21},
            "effectiveCjkFontIdentity": "UNVERIFIED", "registryAdmission": "NOT_RUN",
            "readyForPageGeneration": False, "releaseReady": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        parser.error("Output must stay in artifacts")
    output.parent.mkdir(parents=True, exist_ok=True)
    report = run()
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "admissionEligible": report["admissionEligible"],
                      "platforms": {key: row["status"] for key, row in report["platforms"].items()}}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
