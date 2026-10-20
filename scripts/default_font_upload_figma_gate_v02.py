"""Independent Figma-only quality gate for fixed drag Upload empty state."""
import argparse
import json
from pathlib import Path

from PIL import Image

from scripts.default_font_upload_candidate_audit_v02 import ROOT, SOURCE, audit, read, sha


CANDIDATE = ROOT / "artifacts/task-095/figma"
TASK = ROOT / "artifacts/task-096"
POLICY = ROOT / "validators/visual/DEFAULT_FONT_UPLOAD_POLICY.md"
METADATA = ROOT / "adapters/figma/metadata/upload-default-font-candidate-0.2.0.json"
FILES = ("native-read.json", "native.png", "native-repeat.png", "native.svg")
TEXT_ZONE = (120, 25, 205, 60)


def raster_diagnostics(reference, native):
    with Image.open(reference) as image:
        source = image.convert("RGB")
    with Image.open(native) as image:
        rgba = image.convert("RGBA")
    white = Image.new("RGBA", rgba.size, "white")
    white.alpha_composite(rgba)
    figma = white.convert("RGB")
    if source.size != (320, 82) or rgba.size != (320, 82):
        return {"sourceSize": source.size, "nativeSize": rgba.size}
    outside, mismatch, edge_mismatch, interior_mismatch, max_delta = 0, 0, 0, 0, 0
    for y in range(source.height):
        for x in range(source.width):
            if TEXT_ZONE[0] <= x < TEXT_ZONE[2] and TEXT_ZONE[1] <= y < TEXT_ZONE[3]:
                continue
            delta = max(abs(a - b) for a, b in zip(source.getpixel((x, y)), figma.getpixel((x, y))))
            outside += 1
            if delta:
                mismatch += 1
                if x < 5 or x >= 315 or y < 5 or y >= 77:
                    edge_mismatch += 1
                else:
                    interior_mismatch += 1
                max_delta = max(max_delta, delta)
    points = [(x, y) for y in range(TEXT_ZONE[1], TEXT_ZONE[3])
              for x in range(TEXT_ZONE[0], TEXT_ZONE[2])
              if min(figma.getpixel((x, y))) < 210]
    ink = {"pixels": len(points), "bounds":
           [min(x for x, y in points), min(y for x, y in points),
            max(x for x, y in points), max(y for x, y in points)] if points else None}
    return {"sourceSize": source.size, "nativeSize": rgba.size,
            "outsideContentPixels": outside, "outsideContentMismatchPixels": mismatch,
            "edgeMismatchPixels": edge_mismatch, "interiorMismatchPixels": interior_mismatch,
            "outsideContentMaxChannelDelta": max_delta, "ink": ink}


def raster_policy(diag):
    if diag.get("sourceSize") != (320, 82) or diag.get("nativeSize") != (320, 82) \
            or diag.get("interiorMismatchPixels") != 0 \
            or diag.get("edgeMismatchPixels", 999) > 667 \
            or diag.get("outsideContentMaxChannelDelta", 999) > 35 \
            or diag.get("outsideContentMismatchPixels") != diag.get("edgeMismatchPixels"):
        return False
    ink = diag["ink"]
    if ink["pixels"] < 200 or ink["bounds"] is None:
        return False
    x0, y0, x1, y1 = TEXT_ZONE
    a, b, c, d = ink["bounds"]
    return x0 <= a <= c < x1 and y0 <= b <= d < y1


def run():
    observed = read(TASK / "figma/native-read.json")
    candidate = read(ROOT / "artifacts/task-095/upload-candidate-audit.json")
    metadata = read(METADATA)
    visual = read(TASK / "visual-review.json")
    independent = audit(observed)
    diag = raster_diagnostics(SOURCE / "data.upload.drag.empty.png", TASK / "figma/native.png")
    checks = {
        "sourceAndCandidateLocked": candidate["status"] == "CANDIDATE_REVIEW"
            and metadata["candidateAuditSha256"] == sha(ROOT / "artifacts/task-095/upload-candidate-audit.json")
            and metadata["componentIrSha256"] == sha(SOURCE / "component_ir.json"),
        "independentNativeStructure": all(independent["checks"][key] for key in
            ("officialSourceVerified", "targetAndComponentLink", "nativeGeometry",
             "sourceColorsBound", "editableDefaultFontText", "dashedBorder"))
            and sha(TASK / "figma/native-read.json") == sha(CANDIDATE / "native-read.json"),
        "nativeRepeatStable": sha(TASK / "figma/native.png") == sha(TASK / "figma/native-repeat.png")
            == sha(CANDIDATE / "native.png"),
        "nativeSvgStable": sha(TASK / "figma/native.svg") == sha(CANDIDATE / "native.svg"),
        "sourceGeometryAndVisibleContent": raster_policy(diag),
        "hashBoundVisualReview": visual["status"] == "PASS" and visual["scope"] == "figma-only-qa"
            and visual["nativePngSha256"] == sha(TASK / "figma/native.png")
            and visual["visibleText"] == "上传文件"
            and visual["completeText"] is True and visual["clippedOrDetached"] is False
            and visual["dashedBorderVisible"] is True
            and visual["effectiveCjkFontIdentity"] == "UNVERIFIED",
    }
    passed = all(checks.values())
    return {"scope": "figma-only-qa", "gateVersion": "0.2.17-figma-only",
            "status": "PASS" if passed else "FAIL",
            "logicalComponentId": "data.upload.drag.empty", "componentType": "Upload",
            "checks": checks, "rasterDiagnostics": diag,
            "evidenceSha256": {"sourceScreenshot": sha(SOURCE / "data.upload.drag.empty.png"),
                "candidateAudit": sha(ROOT / "artifacts/task-095/upload-candidate-audit.json"),
                "visualReview": sha(TASK / "visual-review.json"), "policy": sha(POLICY),
                **{name: sha(TASK / "figma" / name) for name in FILES}},
            "admissionEligible": False, "dualPlatformFidelity": "DEFERRED",
            "registryAdmission": "DEFERRED_PENPOT", "readyForPageGeneration": False,
            "releaseReady": False, "effectiveCjkFontIdentity": "UNVERIFIED"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        parser.error("Output must stay in artifacts")
    result = run()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": result["checks"],
                      "raster": result["rasterDiagnostics"]}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
