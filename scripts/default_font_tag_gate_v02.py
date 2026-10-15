"""Native fidelity gate for the exact default-font static Tag fixture."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from PIL import Image

from scripts.default_font_tag_candidate_audit_v02 import audit, pixel_review
from validators.ui_ir import ROOT
from validators.visual.fidelity import digest


SOURCE = ROOT / "artifacts/task-054/tag-source"
CANDIDATE = ROOT / "artifacts/task-055"
TASK = ROOT / "artifacts/task-056"
POLICY = ROOT / "validators/visual/DEFAULT_FONT_TAG_POLICY.md"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def visible_glyphs(path):
    with Image.open(path) as image:
        native = image.convert("RGBA")
    canvas = Image.new("RGBA", native.size, "white")
    canvas.alpha_composite(native)
    counts = [sum(min(canvas.getpixel((x, y))[:3]) < 200
                  for y in range(3, 19) for x in range(start, end))
              for start, end in ((9, 21), (21, 33))]
    edge_ink = sum(min(canvas.getpixel((x, y))[:3]) < 200
                   for y in range(22) for x in range(42)
                   if x in (0, 41) or y in (0, 21))
    return {"perCharacter": counts, "outerEdgeInkPixels": edge_ink}


def svg_check(platform, path):
    root = ET.fromstring(path.read_bytes())
    if root.tag.split("}")[-1] != "svg" or root.attrib.get("width") != "42" or root.attrib.get("height") != "22":
        return False
    svg = path.read_text(encoding="utf-8").lower()
    colors = (("#f7f7f7", "rgb(247, 247, 247)"),
              ("#e8eaec", "rgb(232, 234, 236)"),
              ("#515a6e", "rgb(81, 90, 110)"))
    if not all(any(color in svg for color in choices) for choices in colors):
        return False
    if platform == "figma":
        return any(node.tag.split("}")[-1] == "path" and node.attrib.get("d")
                   and node.attrib.get("fill", "").upper() == "#515A6E"
                   for node in root.iter())
    return any(node.tag.split("}")[-1] == "text" and "".join(node.itertext()) == "启用"
               and "font-family: sourcesanspro" in node.attrib.get("style", "")
               and "font-weight: 400" in node.attrib.get("style", "")
               for node in root.iter())


def canonical_penpot_svg(path, main_id):
    """Ignore only Penpot's per-export stroke-group UUID, not rendered structure."""
    root = ET.fromstring(path.read_bytes())
    pattern = re.compile(r"^strokes-[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}-" + re.escape(main_id) + r"$")
    normalized = 0
    for node in root.iter():
        if pattern.fullmatch(node.attrib.get("id", "")):
            node.attrib["id"] = "strokes-EXPORT-ID-" + main_id
            normalized += 1
    if normalized != 1:
        raise ValueError("unexpected_penpot_svg_stroke_identity")
    return ET.tostring(root, encoding="unicode")


def native_structure(platform, observed, candidate):
    if platform == "figma":
        frame, label, instance = observed["component"], observed["label"], observed["instance"]
        rgb = lambda paint: tuple(round(paint["color"][key] * 255) for key in ("r", "g", "b"))
        return (observed["pageId"] == candidate["pageReference"] and
                frame["id"] == candidate["componentId"] and frame["type"] == "COMPONENT" and
                frame["width"] == 42 and frame["height"] == 22 and
                frame["paddingLeft"] == frame["paddingRight"] == 9 and
                frame["paddingTop"] == frame["paddingBottom"] == 0 and
                frame["cornerRadius"] == 3 and frame["strokeWeight"] == 1 and frame["strokeAlign"] == "INSIDE" and
                rgb(frame["fills"][0]) == (247, 247, 247) and rgb(frame["strokes"][0]) == (232, 234, 236) and
                rgb(label["fills"][0]) == (81, 90, 110) and
                frame["children"] == [{"id": label["id"], "type": "TEXT", "name": "label"}] and
                label["characters"] == "启用" and label["fontName"]["family"] == "Inter" and
                label["fontName"]["style"] == "Regular" and label["fontSize"] == 12 and
                label["width"] == 24 and label["height"] == 14 and
                bool(label["textStyleId"]) and bool(label["boundVariables"]) and
                instance["id"] == candidate["instanceId"] and instance["mainComponentId"] == frame["id"] and
                instance["width"] == 42 and instance["height"] == 22)
    frame, label, instance = observed["main"], observed["label"], observed["instance"]
    bounds = label["textBounds"]
    return (observed["fileId"] == candidate["fileReference"] and
            observed["componentId"] == candidate["componentId"] and observed["fileValidation"] == 0 and
            frame["id"] == "f1153c87-a7fc-80d8-8008-c9a7f325f8b1" and
            frame["width"] == 42 and frame["height"] == 22 and frame["borderRadius"] == 3 and
            frame["fills"][0]["fillColor"].upper() == "#F7F7F7" and
            frame["strokes"][0]["strokeColor"].upper() == "#E8EAEC" and
            frame["strokes"][0]["strokeWidth"] == 1 and frame["strokes"][0]["strokeAlignment"] == "inner" and
            frame["flex"]["leftPadding"] == frame["flex"]["rightPadding"] == 9 and
            frame["children"] == [{"id": label["id"], "name": "label", "type": "text"}] and
            label["characters"] == "启用" and label["fontId"] == "sourcesanspro" and
            label["fontVariantId"] == "regular" and label["fontWeight"] == "400" and
            label["fontSize"] == "12" and label["fills"][0]["fillColor"].upper() == "#515A6E" and
            bounds["x"] >= frame["bounds"]["x"] and bounds["y"] >= frame["bounds"]["y"] and
            bounds["x"] + bounds["width"] <= frame["bounds"]["x"] + 42 and
            bounds["y"] + bounds["height"] <= frame["bounds"]["y"] + 22 and
            instance["id"] == candidate["instanceId"] and instance["componentId"] == candidate["componentId"] and
            instance["width"] == 42 and instance["height"] == 22)


def run():
    saved_bytes = (CANDIDATE / "candidate-audit.json").read_bytes()
    saved_candidate = json.loads(saved_bytes)
    regenerated = audit()
    if saved_candidate != regenerated or sha(CANDIDATE / "candidate-audit.json") != hashlib.sha256(saved_bytes).hexdigest():
        raise ValueError("tag_candidate_audit_changed")
    if regenerated["status"] != "CANDIDATE_REVIEW" or regenerated["issues"]:
        raise ValueError("tag_candidate_not_ready_for_gate")
    source = read_json(SOURCE / "component_ir.json")["components"][0]
    if source["logicalComponentId"] != "data.tag.default.enabled":
        raise ValueError("wrong_tag_source")
    reference = SOURCE / source["screenshot"]["path"]
    review = read_json(TASK / "visual-review.json")
    rows = {}
    for platform, candidate in regenerated["platforms"].items():
        folder = TASK / platform
        observed = read_json(folder / "native-read.json")
        first = folder / ("native-gate.png" if platform == "figma" else "native-gate-a.png")
        second = folder / ("native-gate-repeat.png" if platform == "figma" else "native-gate-b.png")
        svg = folder / "native-gate.svg"
        old = CANDIDATE / platform
        old_svg = old / "component-native.svg"
        pixels = pixel_review(reference, first)
        glyphs = visible_glyphs(first)
        visual = review["platforms"][platform]
        svg_stable = (sha(svg) == sha(old_svg) if platform == "figma" else
                      canonical_penpot_svg(svg, observed["main"]["id"]) ==
                      canonical_penpot_svg(old_svg, observed["main"]["id"]))
        checks = {
            "candidateEvidenceLocked": all(candidate["checks"].values()) and
                candidate["candidateMetadataSha256"] == sha(ROOT / f"adapters/{platform}/metadata/tag-default-font-candidate-0.2.0.json"),
            "independentNativeStructure": native_structure(platform, observed, candidate),
            "nativeRepeatStable": sha(first) == sha(second) == sha(old / "component-native.png"),
            "nativeSvgSemanticallyStable": svg_stable and svg_check(platform, svg),
            "nonTextExactExceptCorners": pixels["nonTextChangesOutsideFourCorners"] == 0,
            "cornerAntialiasWithinPolicy": pixels["nonTextMaximumChannelDelta"] <= 3,
            "twoVisibleUnclippedGlyphs": min(glyphs["perCharacter"]) >= 20 and glyphs["outerEdgeInkPixels"] == 0,
            "hashBoundVisualReview": review["status"] == "PASS" and review["expectedText"] == "启用" and
                review["effectiveCjkFontIdentity"] == "UNVERIFIED" and
                visual["nativePngSha256"] == sha(first) and visual["legibleText"] == "启用" and
                visual["completeGlyphs"] is True and visual["clippedText"] is False and
                visual["emptyOrDetached"] is False,
        }
        rows[platform] = {"status": "PASS" if all(checks.values()) else "FAIL",
                          "checks": checks, "fileReference": candidate["fileReference"],
                          "componentId": candidate["componentId"], "instanceId": candidate["instanceId"],
                          "nativePngSha256": sha(first), "nativeSvgSha256": sha(svg),
                          "candidateNativeSvgSha256": sha(old_svg),
                          "nativeReadSha256": sha(folder / "native-read.json"),
                          "pixelDiagnostics": pixels, "glyphDiagnostics": glyphs,
                          "candidateMetadataSha256": candidate["candidateMetadataSha256"]}
    passed = all(row["status"] == "PASS" for row in rows.values())
    return {"scope": "production", "gateVersion": "0.2.5", "status": "PASS" if passed else "FAIL",
            "logicalComponentId": source["logicalComponentId"], "componentType": "Tag", "variants": ["default"],
            "sourceVersion": source["provenance"]["sourceVersion"],
            "componentIrSha256": digest(source), "candidateEvidenceKind": "native-design-capture",
            "admissionEligible": passed, "issues": [] if passed else ["tag_fidelity_failed"],
            "platforms": rows, "evidenceSha256": {"sourceScreenshot": sha(reference),
                "candidateAudit": sha(CANDIDATE / "candidate-audit.json"),
                "visualReview": sha(TASK / "visual-review.json"), "policy": sha(POLICY)},
            "contentScopeProposal": {"kind": "fixed-native-content", "text": "启用",
                                     "size": "default", "color": "default", "closable": False,
                                     "checkable": False, "checked": True, "width": 42, "height": 22},
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
