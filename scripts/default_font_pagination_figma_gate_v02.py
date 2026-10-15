"""Independent Figma-only quality gate for the fixed three-page Pagination."""
import argparse
import json
from pathlib import Path

from PIL import Image

from scripts.default_font_pagination_candidate_audit_v02 import ROOT, SOURCE, audit, read, sha


CANDIDATE = ROOT / "artifacts/task-074/figma"
TASK = ROOT / "artifacts/task-075"
POLICY = ROOT / "validators/visual/DEFAULT_FONT_PAGINATION_POLICY.md"
METADATA = ROOT / "adapters/figma/metadata/pagination-default-font-candidate-0.2.0.json"
FILES = ("native-read.json", "native.png", "native-repeat.png", "native.svg")
ZONES = {"previous": (8, 6, 24, 27), "page1": (44, 6, 60, 27),
         "page2": (80, 6, 96, 27), "page3": (116, 6, 132, 27),
         "next": (152, 6, 168, 27)}


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
    outside, exact, maximum = 0, 0, 0
    for y in range(source.height):
        for x in range(source.width):
            if any(x0 <= x < x1 and y0 <= y < y1 for x0, y0, x1, y1 in ZONES.values()):
                continue
            delta = max(abs(a-b) for a,b in zip(source.getpixel((x,y)), figma.getpixel((x,y))))
            outside += 1
            exact += delta == 0
            maximum = max(maximum, delta)
    ink = {}
    for name, (x0,y0,x1,y1) in ZONES.items():
        points = [(x,y) for y in range(y0,y1) for x in range(x0,x1)
                  if min(figma.getpixel((x,y))) < 200]
        ink[name] = {"pixels": len(points), "bounds":
            [min(x for x,y in points),min(y for x,y in points),
             max(x for x,y in points),max(y for x,y in points)] if points else None}
    return {"sourceSize": source.size, "figmaSize": figma.size,
            "outsideContentPixels": outside, "outsideContentExactRatio": round(exact/outside,6),
            "outsideContentMaxChannelDelta": maximum, "ink": ink}


def raster_policy(diag):
    if diag.get("sourceSize") != diag.get("figmaSize") or diag.get("sourceSize") != (400,32) \
            or diag.get("outsideContentExactRatio",0) < .98 \
            or diag.get("outsideContentMaxChannelDelta",999) > 20:
        return False
    minima = {"previous": 7, "page1": 12, "page2": 20, "page3": 20, "next": 20}
    for name, zone in ZONES.items():
        item = diag["ink"][name]
        if item["pixels"] < minima[name] or item["bounds"] is None:
            return False
        x0,y0,x1,y1 = zone
        a,b,c,d = item["bounds"]
        if not (x0 < a <= c < x1-1 and y0 < b <= d < y1-1):
            return False
    return True


def run():
    observed = read(TASK / "figma/native-read.json")
    candidate = read(ROOT / "artifacts/task-074/pagination-candidate-audit.json")
    metadata = read(METADATA)
    visual = read(TASK / "visual-review.json")
    independent = audit(observed)
    diag = raster_diagnostics(SOURCE / "data.pagination.default.three-pages.png",
                              TASK / "figma/native.png")
    checks = {
        "sourceAndCandidateLocked": candidate["status"] == "CANDIDATE_REVIEW"
            and metadata["candidateAuditSha256"] == sha(ROOT / "artifacts/task-074/pagination-candidate-audit.json")
            and metadata["componentIrSha256"] == sha(SOURCE / "component_ir.json"),
        "independentNativeStructure": all(independent["checks"][key] for key in
            ("officialSourceVerified", "targetAndComponentLink", "fiveNativeCells",
             "sourceColorsBound", "editableDefaultFontDigits", "officialRemixInstances"))
            and sha(TASK / "figma/native-read.json") == sha(CANDIDATE / "native-read.json"),
        "nativeRepeatStable": sha(TASK / "figma/native.png") == sha(TASK / "figma/native-repeat.png")
            == sha(CANDIDATE / "native.png"),
        "nativeSvgStable": sha(TASK / "figma/native.svg") == sha(CANDIDATE / "native.svg"),
        "sourceGeometryAndVisibleContent": raster_policy(diag),
        "hashBoundVisualReview": visual["status"] == "PASS" and visual["scope"] == "figma-only-qa"
            and visual["nativePngSha256"] == sha(TASK / "figma/native.png")
            and visual["visiblePages"] == "1 2 3" and visual["activePage"] == 1
            and visual["previousDisabledVisible"] is True and visual["nextVisible"] is True
            and visual["remixIconsComplete"] is True and visual["digitsComplete"] is True
            and visual["clippedOrDetached"] is False,
    }
    passed = all(checks.values())
    return {"scope": "figma-only-qa", "gateVersion": "0.2.10-figma-only",
            "status": "PASS" if passed else "FAIL",
            "logicalComponentId": "data.pagination.default.three-pages", "componentType": "Pagination",
            "checks": checks, "rasterDiagnostics": diag,
            "evidenceSha256": {"sourceScreenshot": sha(SOURCE / "data.pagination.default.three-pages.png"),
                "candidateAudit": sha(ROOT / "artifacts/task-074/pagination-candidate-audit.json"),
                "visualReview": sha(TASK / "visual-review.json"), "policy": sha(POLICY),
                **{name: sha(TASK / "figma" / name) for name in FILES}},
            "admissionEligible": False, "dualPlatformFidelity": "DEFERRED",
            "registryAdmission": "DEFERRED_PENPOT", "readyForPageGeneration": False,
            "releaseReady": False, "iconAdaptation": "View UI Plus icon font to hash-locked Remix Icon 4.9.1"}


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
    print(json.dumps({"status": result["status"], "checks": result["checks"]}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
