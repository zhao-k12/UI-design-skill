"""Independent Figma-only quality gate for one-field default-font Form."""
import argparse
import json
from pathlib import Path

from PIL import Image

from scripts.default_font_form_candidate_audit_v02 import ROOT, SOURCE, audit, read, sha


CANDIDATE = ROOT / "artifacts/task-086/figma"
TASK = ROOT / "artifacts/task-087"
POLICY = ROOT / "validators/visual/DEFAULT_FONT_FORM_POLICY.md"
METADATA = ROOT / "adapters/figma/metadata/form-default-font-candidate-0.2.0.json"
FILES = ("native-read.json", "native.png", "native-repeat.png", "native.svg")
ZONES = {"label": (38, 4, 72, 30), "placeholder": (86, 3, 180, 30)}


def raster_diagnostics(reference, native):
    with Image.open(reference) as image:
        source = image.convert("RGB")
    with Image.open(native) as image:
        rgba = image.convert("RGBA")
    white = Image.new("RGBA", rgba.size, "white")
    white.alpha_composite(rgba)
    figma = white.convert("RGB")
    if source.size != figma.size:
        return {"sourceSize": source.size, "figmaSize": figma.size}
    outside, mismatch, maximum, out_of_corner = 0, 0, 0, 0
    for y in range(source.height):
        for x in range(source.width):
            if any(x0 <= x < x1 and y0 <= y < y1 for x0,y0,x1,y1 in ZONES.values()):
                continue
            delta = max(abs(a-b) for a,b in zip(source.getpixel((x,y)), figma.getpixel((x,y))))
            outside += 1
            if delta:
                mismatch += 1
                out_of_corner += not ((80 <= x < 85 or 315 <= x < 320)
                                      and (y < 6 or y >= 28))
            maximum = max(maximum, delta)
    ink = {}
    for name,(x0,y0,x1,y1) in ZONES.items():
        threshold = 200 if name == "label" else 220
        points = [(x,y) for y in range(y0,y1) for x in range(x0,x1)
                  if min(figma.getpixel((x,y))) < threshold]
        ink[name] = {"pixels": len(points), "bounds":
            [min(x for x,y in points), min(y for x,y in points),
             max(x for x,y in points), max(y for x,y in points)] if points else None}
    return {"sourceSize": source.size, "figmaSize": figma.size,
            "outsideContentPixels": outside, "outsideContentMismatchPixels": mismatch,
            "outsideContentMaxChannelDelta": maximum,
            "outOfCornerMismatchPixels": out_of_corner, "ink": ink}


def raster_policy(diag):
    if diag.get("sourceSize") != diag.get("figmaSize") or diag.get("sourceSize") != (320, 34) \
            or diag.get("outsideContentMismatchPixels", 999) > 41 \
            or diag.get("outsideContentMaxChannelDelta", 999) > 4 \
            or diag.get("outOfCornerMismatchPixels", 999) != 0:
        return False
    for name,minimum in (("label", 100), ("placeholder", 150)):
        item = diag["ink"][name]
        if item["pixels"] < minimum or item["bounds"] is None:
            return False
        x0,y0,x1,y1 = ZONES[name]
        a,b,c,d = item["bounds"]
        if not (x0 <= a <= c < x1 and y0 <= b <= d < y1):
            return False
    return True


def run():
    observed = read(TASK / "figma/native-read.json")
    candidate = read(ROOT / "artifacts/task-086/form-candidate-audit.json")
    metadata = read(METADATA)
    visual = read(TASK / "visual-review.json")
    independent = audit(observed)
    diag = raster_diagnostics(SOURCE / "form.single.name.empty.png", TASK / "figma/native.png")
    checks = {
        "sourceAndCandidateLocked": candidate["status"] == "CANDIDATE_REVIEW"
            and metadata["candidateAuditSha256"] == sha(ROOT / "artifacts/task-086/form-candidate-audit.json")
            and metadata["componentIrSha256"] == sha(SOURCE / "component_ir.json"),
        "independentNativeStructure": all(independent["checks"][key] for key in
            ("officialSourceVerified", "targetAndComponentLink", "nativeGeometry",
             "editableDefaultFontLabel", "admittedInputInstance"))
            and sha(TASK / "figma/native-read.json") == sha(CANDIDATE / "native-read.json"),
        "nativeRepeatStable": sha(TASK / "figma/native.png") == sha(TASK / "figma/native-repeat.png")
            == sha(CANDIDATE / "native.png"),
        "nativeSvgStable": sha(TASK / "figma/native.svg") == sha(CANDIDATE / "native.svg"),
        "sourceGeometryAndVisibleContent": raster_policy(diag),
        "hashBoundVisualReview": visual["status"] == "PASS" and visual["scope"] == "figma-only-qa"
            and visual["nativePngSha256"] == sha(TASK / "figma/native.png")
            and visual["visibleLabel"] == "姓名"
            and visual["visiblePlaceholder"] == "请输入姓名"
            and visual["admittedInputInstanceVisible"] is True
            and visual["completeText"] is True and visual["clippedOrDetached"] is False
            and visual["effectiveCjkFontIdentity"] == "UNVERIFIED",
    }
    passed = all(checks.values())
    return {"scope": "figma-only-qa", "gateVersion": "0.2.14-figma-only",
            "status": "PASS" if passed else "FAIL",
            "logicalComponentId": "form.single.name.empty", "componentType": "Form",
            "checks": checks, "rasterDiagnostics": diag,
            "evidenceSha256": {"sourceScreenshot": sha(SOURCE / "form.single.name.empty.png"),
                "candidateAudit": sha(ROOT / "artifacts/task-086/form-candidate-audit.json"),
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
