"""Native fidelity gate for the exact default-font Input placeholder fixture."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from PIL import Image

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.default_font_input_candidate_audit_v02 import ROOT, SOURCE, audit, review_pixels, sha
from validators.visual.fidelity import digest

POLICY = ROOT / "validators/visual/DEFAULT_FONT_INPUT_POLICY.md"
SVG = {"figma": ROOT / "artifacts/task-034/figma/input-outline.svg",
       "penpot": ROOT / "artifacts/task-034/penpot/input-native.svg"}


def palette_residual(color):
    white, border = (255, 255, 255), (220, 222, 226)
    amount = (255 - color[0]) / 35
    return max(abs(color[i] - (white[i] * (1 - amount) + border[i] * amount)) for i in range(3))


def corner_check(reference, native):
    source = Image.open(reference).convert("RGB")
    image = Image.open(native).convert("RGBA")
    white = Image.new("RGBA", image.size, "white")
    white.alpha_composite(image)
    image = white.convert("RGB")
    residual = 0
    for y in range(32):
        for x in range(240):
            if (x < 5 or x >= 235) and (y < 5 or y >= 27):
                residual = max(residual, palette_residual(source.getpixel((x, y))),
                               palette_residual(image.getpixel((x, y))))
    return round(residual, 3)


def svg_check(platform, path):
    root = ET.fromstring(path.read_bytes())
    if root.tag.split("}")[-1] != "svg" or root.attrib.get("width") != "240" or root.attrib.get("height") != "32":
        return False
    if platform == "figma":
        paths = [node for node in root.iter() if node.tag.split("}")[-1] == "path"]
        return bool(paths) and any(node.attrib.get("fill", "").upper() == "#C5C8CE" and node.attrib.get("d")
                                   for node in paths)
    return any(node.tag.split("}")[-1] == "text" and "".join(node.itertext()) == "请输入姓名"
               and "font-family: sourcesanspro" in node.attrib.get("style", "")
               and "font-weight: 400" in node.attrib.get("style", "")
               for node in root.iter())


def run():
    candidate = audit()
    saved = json.loads((ROOT / "artifacts/task-033/candidate-audit.json").read_bytes())
    if candidate != saved or candidate["status"] != "CANDIDATE_REVIEW":
        raise ValueError("Input candidate audit changed or failed")
    bundle = json.loads(SOURCE.read_bytes())
    source = next(item for item in bundle["components"] if item["logicalComponentId"] == "form.input.default.medium")
    reference = SOURCE.parent / source["screenshot"]["path"]
    rows = {}
    for platform, previous in candidate["platforms"].items():
        folder = ROOT / "artifacts/task-033" / platform
        metadata_path = ROOT / f"adapters/{platform}/metadata/input-default-font-candidate-0.2.0.json"
        metadata = json.loads(metadata_path.read_bytes())
        native = folder / "component-native.png"
        metrics = review_pixels(reference, native)
        residual = corner_check(reference, native)
        checks = {
            "candidateEvidenceLocked": (metadata["status"] == "CANDIDATE_REVIEW"
                and metadata["componentId"] == previous["componentId"]
                and metadata["evidenceSha256"]["candidate-audit.json"] == sha(ROOT / "artifacts/task-033/candidate-audit.json")
                and all(metadata["evidenceSha256"][name] == sha(folder / name)
                        for name in previous["evidenceSha256"])),
            "nativeRepeatStable": previous["checks"]["nativeRepeatStable"] is True,
            "geometryAndStyle": previous["checks"]["sourceGeometryAndField"] is True,
            "defaultFontAndText": previous["checks"]["placeholderAndDefaultFont"] is True,
            "hashBoundVisualReview": previous["checks"]["hashBoundVisualReview"] is True,
            "nonTextExact": metrics["nonTextDifferences"] == 0,
            "roundedCornerPalette": residual <= 2,
            "visibleFiveGlyphs": all(count > 2 for count in metrics["visibleInkByCharacter"]),
            "independentNativeSvg": svg_check(platform, SVG[platform]),
        }
        rows[platform] = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
                          "fileReference": previous["fileReference"], "componentId": previous["componentId"],
                          "nativePngSha256": sha(native), "nativeSvgSha256": sha(SVG[platform]),
                          "maxCornerPaletteResidual": residual, "pixelDiagnostics": metrics,
                          "candidateMetadataSha256": sha(metadata_path)}
    passed = all(row["status"] == "PASS" for row in rows.values())
    return {"scope": "production", "gateVersion": "0.2.3", "status": "PASS" if passed else "FAIL",
            "logicalComponentId": source["logicalComponentId"], "componentType": "Input",
            "variants": ["default"], "sourceVersion": source["provenance"]["sourceVersion"],
            "componentIrSha256": digest(source), "candidateEvidenceKind": "native-design-capture",
            "admissionEligible": passed, "issues": [] if passed else ["input_fidelity_failed"],
            "platforms": rows, "evidenceSha256": {"sourceScreenshot": sha(reference),
                "candidateAudit": sha(ROOT / "artifacts/task-033/candidate-audit.json"),
                "visualReview": candidate["visualReviewSha256"], "policy": sha(POLICY)},
            "contentScopeProposal": {"kind": "fixed-native-content", "placeholder": "请输入姓名",
                                     "value": "", "width": 240, "height": 32},
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
