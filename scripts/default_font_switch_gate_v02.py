"""Independent Figma-only quality gate for the fixed selected Switch."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from scripts.default_font_switch_candidate_audit_v02 import SOURCE, sha, read
from scripts.switch_pixel_diagnostics_v02 import compare
from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT


CANDIDATE = ROOT / "artifacts/task-068"
TASK = ROOT / "artifacts/task-069"
POLICY = ROOT / "validators/visual/DEFAULT_FONT_SWITCH_POLICY.md"
FILES = ("native-read.json", "native.png", "native-repeat.png", "native.svg")


def structure(platform, observed, candidate):
    if platform != "figma":
        return False
    main = observed["component"]
    label, knob, instance = (observed[key] for key in ("label", "knob", "instance"))
    ids = observed["fileReference"] == candidate["fileReference"] \
        and observed["pageId"] == candidate["pageReference"] \
        and main["id"] == candidate["componentId"] \
        and instance["id"] == candidate["instanceId"]
    rgb = lambda paint: tuple(round(paint["color"][c] * 255) for c in ("r", "g", "b"))
    offsets = lambda node: (node["x"], node["y"])
    colors = rgb(main["fills"][0]) == (45, 140, 240) and \
        rgb(label["fills"][0]) == rgb(knob["fills"][0]) == (255, 255, 255)
    font = label["fontName"]["family"] == "Inter" and label["fontName"]["style"] == "Regular" \
        and label["fontSize"] == 12 and label["lineHeight"] == {"unit": "PIXELS", "value": 20}
    link = main["type"] == "COMPONENT" and instance["type"] == "INSTANCE" \
        and instance["mainComponentId"] == main["id"]
    child_types = ["TEXT", "ELLIPSE"]
    radius = main["radius"]
    return ids and link and colors and font and radius == 11 and \
        (main["width"], main["height"]) == (44, 22) and \
        [(c["id"], c["type"]) for c in main["children"]] == \
        list(zip((label["id"], knob["id"]), child_types)) and \
        (offsets(label), label["width"], label["height"], label["text"]) == ((8, 1), 12, 20, "开") and \
        (offsets(knob), knob["width"], knob["height"]) == ((24, 2), 18, 18)


def svg_semantics(platform, path):
    svg = path.read_text(encoding="utf-8")
    root = ET.fromstring(svg)
    if root.tag.split("}")[-1] != "svg" or (root.attrib.get("width"), root.attrib.get("height")) != ("44", "22"):
        return False
    lower = svg.lower()
    return platform == "figma" and all(s in lower for s in ('#2d8cf0', 'fill="white"', '<circle'))


def pixel_policy(pixels):
    return pixels.get("sourceBottomBlankRow") is True and pixels.get("exactBlueCore") is True \
        and pixels.get("exactWhiteKnobCore") is True \
        and type(pixels.get("outsideTextMaximumChannelDelta")) is int \
        and pixels["outsideTextMaximumChannelDelta"] <= 30 \
        and pixels.get("largeDifferencesOnSourceAntialias") is True \
        and pixels.get("blueMaskIntersectionOverUnion", 0) >= .98


def glyph_policy(pixels):
    return type(pixels.get("nativeTextInkPixels")) is int and pixels["nativeTextInkPixels"] >= 20 \
        and pixels.get("textOuterEdgeInk") == []


def run():
    issues = verify_artifacts(SOURCE, expected_types={"Switch"})
    source = read(SOURCE / "component_ir.json")["components"][0]
    if source["logicalComponentId"] != "form.switch.default.enabled" or source["content"]["text"] != "开":
        issues.append({"code": "wrong_switch_source"})
    candidate_report = read(CANDIDATE / "candidate-audit.json")
    if candidate_report["status"] != "CANDIDATE_REVIEW":
        issues.append({"code": "candidate_audit_not_passed"})
    review = read(TASK / "visual-review.json")
    reference = SOURCE / source["screenshot"]["path"]
    rows = {}
    for platform in ("figma",):
        folder = TASK / platform
        candidate_path = ROOT / f"adapters/{platform}/metadata/switch-default-font-candidate-0.2.0.json"
        candidate, observed = read(candidate_path), read(folder / "native-read.json")
        native, repeat, svg = (folder / f for f in FILES[1:])
        pixels = compare(reference, native)
        visual = review["platforms"][platform]
        checks = {
            "candidateSourceLocked": candidate["status"] == "CANDIDATE_REVIEW" and all(candidate["checks"].values())
                and candidate["componentIrSha256"] == sha(SOURCE / "component_ir.json")
                and candidate_report["platforms"][platform] == candidate,
            "independentNativeStructure": structure(platform, observed, candidate)
                and sha(folder / "native-read.json") == sha(CANDIDATE / platform / "native-read.json"),
            "nativeRepeatAndCandidateStable": sha(native) == sha(repeat)
                == sha(CANDIDATE / platform / "native.png"),
            "nativeSvgSemantics": svg_semantics(platform, svg)
                and svg.read_text(encoding="utf-8") == (CANDIDATE / platform / "native.svg").read_text(encoding="utf-8"),
            "sourceColorsAndControlRaster": pixel_policy(pixels),
            "visibleUnclippedGlyph": glyph_policy(pixels),
            "hashBoundVisualReview": review["status"] == "PASS" and review["expectedText"] == "开"
                and review["effectiveCjkFontIdentity"] == "UNVERIFIED"
                and visual["nativePngSha256"] == sha(native) and visual["legibleText"] == "开"
                and visual["completeGlyph"] is True and visual["clippedText"] is False
                and visual["emptyOrDetached"] is False and visual["knobVisible"] is True,
        }
        rows[platform] = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
                          "fileReference": candidate["fileReference"], "componentId": candidate["componentId"],
                          "instanceId": candidate["instanceId"], "pixelDiagnostics": pixels,
                          "evidenceSha256": {f: sha(folder / f) for f in FILES},
                          "candidateMetadataSha256": sha(candidate_path)}
    passed = not issues and all(row["status"] == "PASS" for row in rows.values())
    return {"scope": "figma-only-qa", "gateVersion": "0.2.8-figma-only", "status": "PASS" if passed else "FAIL",
            "logicalComponentId": source["logicalComponentId"], "componentType": "Switch", "variants": ["default"],
            "sourceVersion": source["provenance"]["sourceVersion"],
            "componentIrSha256": sha(SOURCE / "component_ir.json"), "admissionEligible": False,
            "issues": issues if issues else ([] if passed else ["switch_fidelity_failed"]),
            "platforms": rows, "evidenceSha256": {"sourceScreenshot": sha(reference),
                "visualReview": sha(TASK / "visual-review.json"), "policy": sha(POLICY)},
            "contentScopeProposal": {"kind": "fixed-native-content", "text": "开", **source["props"],
                                     "width": 44, "height": 22},
            "effectiveCjkFontIdentity": "UNVERIFIED", "dualPlatformFidelity": "DEFERRED",
            "registryAdmission": "DEFERRED_PENPOT",
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
