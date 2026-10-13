"""Run the native fidelity gate for the fixed default-font Select fixture."""

import argparse
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from PIL import Image

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.default_font_select_candidate_audit_v02 import ROOT, SOURCE, TASK, audit, arrow_outline_preserved, pixel_review, sha
from validators.visual.fidelity import digest


POLICY = ROOT / "validators/visual/DEFAULT_FONT_SELECT_POLICY.md"


def corner_palette_residual(path):
    native = Image.open(path).convert("RGBA")
    white_canvas = Image.new("RGBA", native.size, "white")
    white_canvas.alpha_composite(native)
    image = white_canvas.convert("RGB")
    white, border = (255, 255, 255), (220, 222, 226)
    residual = 0.0
    for y in range(32):
        for x in range(240):
            if (x < 5 or x >= 235) and (y < 5 or y >= 27):
                color = image.getpixel((x, y))
                blend = (255 - color[0]) / 35
                residual = max(residual, *(abs(color[i] - (white[i] * (1 - blend) + border[i] * blend)) for i in range(3)))
    return round(residual, 3)


def visible_glyphs(path):
    image = Image.open(path).convert("RGB")
    counts = []
    for offset in (0, 14):
        count = 0
        for y in range(5, 27):
            for x in range(9 + offset, 23 + offset):
                color = image.getpixel((x, y))
                count += max(abs(color[i] - (81, 90, 110)[i]) for i in range(3)) < 40
        counts.append(count)
    return counts


def svg_check(platform, path):
    svg = path.read_text(encoding="utf-8")
    root = ET.fromstring(svg)
    if (root.tag.split("}")[-1] != "svg" or root.attrib.get("width") != "240"
            or root.attrib.get("height") != "32" or not arrow_outline_preserved(svg)):
        return False
    if platform == "figma":
        paths = [n for n in root.iter() if n.tag.split("}")[-1] == "path"]
        return any(n.attrib.get("fill", "").upper() == "#515A6E" and n.attrib.get("d") for n in paths)
    return any(n.tag.split("}")[-1] == "text" and "".join(n.itertext()) == "启用"
               and "font-family: sourcesanspro" in n.attrib.get("style", "")
               and "font-weight: 400" in n.attrib.get("style", "")
               for n in root.iter())


def run():
    candidate = audit()
    saved = json.loads((TASK / "candidate-audit.json").read_text(encoding="utf-8"))
    if candidate != saved or candidate["status"] != "CANDIDATE_REVIEW":
        raise ValueError("Select candidate audit changed or failed")
    review = json.loads((TASK / "visual-review.json").read_text(encoding="utf-8"))
    bundle = json.loads(SOURCE.read_text(encoding="utf-8"))
    source = next(c for c in bundle["components"] if c["logicalComponentId"] == "form.select.default.medium")
    reference = SOURCE.parent / source["screenshot"]["path"]
    rows = {}
    for platform, previous in candidate["platforms"].items():
        folder = TASK / platform
        native = folder / "component-native.png"
        svg = folder / "component-native.svg"
        metadata_path = ROOT / f"adapters/{platform}/metadata/select-default-font-candidate-0.2.0.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metrics = pixel_review(reference, native)
        residual = max(corner_palette_residual(reference), corner_palette_residual(native))
        ink = visible_glyphs(native)
        observed = review["platforms"][platform]
        checks = {
            "candidateEvidenceLocked": (metadata["status"] == "CANDIDATE_REVIEW"
                                        and metadata["componentId"] == previous["componentId"]
                                        and metadata["evidenceSha256"]["candidate-audit.json"] == sha(TASK / "candidate-audit.json")
                                        and all(metadata["evidenceSha256"][name] == sha(folder / name)
                                                for name in previous["evidenceSha256"])),
            "sameNativeMainAndInstance": previous["checks"]["sameNativeMainAndInstance"],
            "nativeRepeatStable": previous["checks"]["nativeRepeatStable"],
            "fixedSelectedValueAndDefaultFont": previous["checks"]["fixedSelectedValueAndDefaultFont"],
            "sourceArrowOutline": previous["checks"]["officialArrowPreserved"] and svg_check(platform, svg),
            "nonTextExact": metrics["nonTextDifferences"] == 0,
            "roundedCornerPalette": residual <= 2,
            "arrowRasterWithinPolicy": metrics["arrowAbsoluteError"] <= 1500,
            "twoVisibleGlyphs": all(count > 10 for count in ink),
            "hashBoundVisualReview": (review["status"] == "PASS"
                                      and review["expectedSelectedText"] == "启用"
                                      and review["effectiveCjkFontIdentity"] == "UNVERIFIED"
                                      and observed["nativePngSha256"] == sha(native)
                                      and observed["legibleSelectedText"] == "启用"
                                      and observed["glyphsComplete"] is True
                                      and observed["clippedText"] is False
                                      and observed["tofuOrMissingGlyph"] is False
                                      and observed["arrowVisible"] is True),
        }
        rows[platform] = {"status": "PASS" if all(checks.values()) else "FAIL",
                          "checks": checks, "fileReference": previous["fileReference"],
                          "componentId": previous["componentId"],
                          "nativePngSha256": sha(native), "nativeSvgSha256": sha(svg),
                          "maxCornerPaletteResidual": residual, "visibleInkByCharacter": ink,
                          "pixelDiagnostics": metrics, "candidateMetadataSha256": sha(metadata_path)}
    passed = all(row["status"] == "PASS" for row in rows.values())
    return {"scope": "production", "gateVersion": "0.2.4",
            "status": "PASS" if passed else "FAIL", "logicalComponentId": source["logicalComponentId"],
            "componentType": "Select", "variants": ["default"],
            "sourceVersion": source["provenance"]["sourceVersion"],
            "componentIrSha256": digest(source), "candidateEvidenceKind": "native-design-capture",
            "admissionEligible": passed, "issues": [] if passed else ["select_fidelity_failed"],
            "platforms": rows, "evidenceSha256": {
                "sourceScreenshot": sha(reference), "candidateAudit": sha(TASK / "candidate-audit.json"),
                "visualReview": sha(TASK / "visual-review.json"), "policy": sha(POLICY)},
            "contentScopeProposal": {"kind": "fixed-native-content", "modelValue": "enabled",
                                     "selectedText": "启用", "width": 240, "height": 32},
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
                      "platforms": {k: v["status"] for k, v in report["platforms"].items()}}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
