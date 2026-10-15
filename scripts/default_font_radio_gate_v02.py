"""Independent native fidelity gate for the fixed default-font selected Radio."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET

from scripts.checkbox_pixel_diagnostics_v02 import on_white
from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT


SOURCE = ROOT / "artifacts/task-063/radio-source"
CANDIDATE = ROOT / "artifacts/task-064"
TASK = ROOT / "artifacts/task-065"
POLICY = ROOT / "validators/visual/DEFAULT_FONT_RADIO_POLICY.md"
FILES = ("native-read.json", "native.png", "native-repeat.png", "native.svg")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def pixels(reference, candidate):
    original, native = on_white(reference), on_white(candidate)
    if original.size != (48, 22) or native.size != (48, 21):
        return {"sizeMismatch": [original.size, native.size], "pass": False}
    if any(original.getpixel((x, 0)) != (255, 255, 255) for x in range(48)):
        return {"nonBlankSourceTopRow": True, "pass": False}
    original = original.crop((0, 1, 48, 22))
    deltas = [max(abs(a - b) for a, b in zip(original.getpixel((x, y)), native.getpixel((x, y))))
              for y in range(21) for x in range(16)]
    center = [(x, y) for y in range(7, 13) for x in range(5, 11)]
    exact_center = all(original.getpixel(p) == native.getpixel(p) == (45, 140, 240) for p in center)
    def blue(image):
        return {(x, y) for y in range(21) for x in range(16)
                if image.getpixel((x, y))[2] - image.getpixel((x, y))[0] >= 80}
    source_blue, native_blue = blue(original), blue(native)
    iou = len(source_blue & native_blue) / len(source_blue | native_blue)
    result = {"sourceTopBlankRowCropped": True, "maximumControlChannelDelta": max(deltas),
              "exactBlueCenter": exact_center, "sourceBluePixels": len(source_blue),
              "nativeBluePixels": len(native_blue), "blueIntersectionOverUnion": round(iou, 4)}
    result["pass"] = max(deltas) <= 40 and exact_center and iou >= 0.9
    return result


def glyphs(path):
    image = on_white(path)
    counts = [sum(min(image.getpixel((x, y))) < 200 for y in range(1, 20) for x in range(a, b))
              for a, b in ((20, 34), (34, 48))]
    edges = sum(min(image.getpixel((x, y))) < 200 for y in (0, 20) for x in range(20, 48))
    edges += sum(min(image.getpixel((47, y))) < 200 for y in range(1, 20))
    return {"perCharacterDarkPixels": counts, "textOuterEdgeInkPixels": edges,
            "pass": min(counts) >= 20 and edges == 0}


def structure(platform, observed, candidate):
    ring, dot, label, instance = (observed[k] for k in ("ring", "dot", "label", "instance"))
    main = observed["component"] if platform == "figma" else observed["main"]
    ids = (observed["fileReference"] if platform == "figma" else observed["fileId"]) == candidate["fileReference"] \
        and observed["pageId"] == candidate["pageReference"] \
        and (main["id"] if platform == "figma" else observed["componentId"]) == candidate["componentId"] \
        and instance["id"] == candidate["instanceId"]
    children = main["children"]
    if platform == "figma":
        offsets = lambda node: (node["x"], node["y"])
        rgb = lambda paint: tuple(round(paint["color"][c] * 255) for c in ("r", "g", "b"))
        colors = rgb(ring["fills"][0]) == (255, 255, 255) and rgb(ring["strokes"][0]) \
            == rgb(dot["fills"][0]) == (45, 140, 240) and rgb(label["fills"][0]) == (81, 90, 110)
        typography = label["fontName"]["family"] == "Inter" and label["fontName"]["style"] == "Regular" \
            and label["fontSize"] == 14 and label["lineHeight"] == {"unit": "PIXELS", "value": 21}
        link = main["type"] == "COMPONENT" and instance["type"] == "INSTANCE" \
            and instance["mainComponentId"] == main["id"]
        ring_stroke = ring["strokeWeight"] == 1 and ring["strokeAlign"] == "INSIDE"
        child_types = ["ELLIPSE", "ELLIPSE", "TEXT"]
    else:
        offsets = lambda node: (node["x"] - main["x"], node["y"] - main["y"])
        colors = ring["fills"][0]["fillColor"].upper() == "#FFFFFF" and \
            ring["strokes"][0]["strokeColor"].upper() == dot["fills"][0]["fillColor"].upper() == "#2D8CF0" \
            and label["fills"][0]["fillColor"].upper() == "#515A6E"
        typography = (label["fontId"], label["fontVariantId"], label["fontSize"], label["lineHeight"],
                      label["growType"]) == ("sourcesanspro", "regular", "14", "1.5", "fixed")
        link = main["type"] == "board" and observed["fileValidation"] == 0 \
            and instance["componentId"] == observed["componentId"] and instance["isCopy"] is True
        ring_stroke = ring["strokes"][0]["strokeWidth"] == 1 and ring["strokes"][0]["strokeAlignment"] == "inner"
        child_types = ["ellipse", "ellipse", "text"]
    return ids and link and colors and typography and ring_stroke and \
        (main["width"], main["height"]) == (48, 21) and \
        [(c["id"], c["type"]) for c in children] == \
        list(zip((ring["id"], dot["id"], label["id"]), child_types)) and \
        (offsets(ring), ring["width"], ring["height"]) == ((0, 2), 16, 16) and \
        (offsets(dot), dot["width"], dot["height"]) == ((3, 5), 10, 10) and \
        (offsets(label), label["width"], label["height"], label["text"]) == ((20, 0), 28, 21, "启用")


def svg_semantics(platform, path):
    svg = path.read_text(encoding="utf-8")
    root = ET.fromstring(svg)
    if root.tag.split("}")[-1] != "svg" or (root.attrib.get("width"), root.attrib.get("height")) != ("48", "21"):
        return False
    lower = svg.lower()
    if platform == "figma":
        return all(s in lower for s in ('fill="white"', '#2d8cf0', '#515a6e'))
    return all(s in lower for s in ("rgb(255, 255, 255)", "rgb(45, 140, 240)",
                                    "rgb(81, 90, 110)", "sourcesanspro", "启用"))


def canonical_svg(platform, path):
    content = path.read_text(encoding="utf-8")
    if platform == "penpot":
        content = re.sub(r'strokes-[0-9a-f-]{36}-(0b54f3e1-c822-80b2-8008-caaf72234842)',
                         r'strokes-EXPORT-\1', content)
    return content


def run():
    issues = verify_artifacts(SOURCE, expected_types={"Radio"})
    source = read(SOURCE / "component_ir.json")["components"][0]
    if source["logicalComponentId"] != "form.radio.default.enabled" or source["content"]["text"] != "启用":
        issues.append({"code": "wrong_radio_source"})
    candidate_report = read(CANDIDATE / "candidate-audit.json")
    if candidate_report["status"] != "CANDIDATE_REVIEW":
        issues.append({"code": "candidate_audit_not_passed"})
    review = read(TASK / "visual-review.json")
    reference = SOURCE / source["screenshot"]["path"]
    rows = {}
    for platform in ("figma", "penpot"):
        folder = TASK / platform
        candidate_path = ROOT / f"adapters/{platform}/metadata/radio-default-font-candidate-0.2.0.json"
        candidate, observed = read(candidate_path), read(folder / "native-read.json")
        native, repeat, svg = (folder / f for f in FILES[1:])
        pixel_result, glyph_result = pixels(reference, native), glyphs(native)
        visual = review["platforms"][platform]
        checks = {
            "candidateSourceLocked": candidate["status"] == "CANDIDATE_REVIEW" and all(candidate["checks"].values())
                and candidate["componentIrSha256"] == sha(SOURCE / "component_ir.json")
                and candidate_report["platforms"][platform] == candidate,
            "independentNativeStructure": structure(platform, observed, candidate),
            "nativeRepeatAndCandidateStable": sha(native) == sha(repeat)
                == sha(CANDIDATE / platform / "native.png") and sha(folder / "native-read.json")
                == sha(CANDIDATE / platform / "native-read.json"),
            "nativeSvgSemantics": svg_semantics(platform, svg) and
                canonical_svg(platform, svg) == canonical_svg(platform, CANDIDATE / platform / "native.svg"),
            "sourceColorsAndControlRaster": pixel_result["pass"],
            "twoVisibleUnclippedGlyphs": glyph_result["pass"],
            "hashBoundVisualReview": review["status"] == "PASS" and review["expectedText"] == "启用"
                and review["effectiveCjkFontIdentity"] == "UNVERIFIED"
                and visual["nativePngSha256"] == sha(native) and visual["legibleText"] == "启用"
                and visual["completeGlyphs"] is True and visual["clippedText"] is False
                and visual["emptyOrDetached"] is False and visual["selectedDotVisible"] is True,
        }
        rows[platform] = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
                          "fileReference": candidate["fileReference"], "componentId": candidate["componentId"],
                          "instanceId": candidate["instanceId"], "pixelDiagnostics": pixel_result,
                          "glyphDiagnostics": glyph_result,
                          "evidenceSha256": {f: sha(folder / f) for f in FILES},
                          "candidateMetadataSha256": sha(candidate_path)}
    passed = not issues and all(row["status"] == "PASS" for row in rows.values())
    return {"scope": "production", "gateVersion": "0.2.7", "status": "PASS" if passed else "FAIL",
            "logicalComponentId": source["logicalComponentId"], "componentType": "Radio", "variants": ["default"],
            "sourceVersion": source["provenance"]["sourceVersion"],
            "componentIrSha256": sha(SOURCE / "component_ir.json"), "admissionEligible": passed,
            "issues": issues if issues else ([] if passed else ["radio_fidelity_failed"]),
            "platforms": rows, "evidenceSha256": {"sourceScreenshot": sha(reference),
                "visualReview": sha(TASK / "visual-review.json"), "policy": sha(POLICY)},
            "contentScopeProposal": {"kind": "fixed-native-content", "text": "启用", **source["props"],
                                     "width": 48, "height": 21},
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
    print(json.dumps({"status": report["status"], "platforms":
                      {k: v["status"] for k, v in report["platforms"].items()}}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
