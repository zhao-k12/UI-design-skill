"""Independent Figma-only quality gate for fixed expanded default-font Tree."""
import argparse
import json
from pathlib import Path

from PIL import Image

from scripts.default_font_tree_candidate_audit_v02 import ROOT, SOURCE, audit, read, sha


CANDIDATE = ROOT / "artifacts/task-080/figma"
TASK = ROOT / "artifacts/task-081"
POLICY = ROOT / "validators/visual/DEFAULT_FONT_TREE_POLICY.md"
METADATA = ROOT / "adapters/figma/metadata/tree-default-font-candidate-0.2.0.json"
FILES = ("native-read.json", "native.png", "native-repeat.png", "native.svg")
ZONES = {"arrow": (0, 0, 16, 21), "parent": (16, 0, 110, 21),
         "child1": (30, 29, 144, 50), "child2": (30, 58, 144, 79)}


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
            if any(x0 <= x < x1 and y0 <= y < y1 for x0,y0,x1,y1 in ZONES.values()):
                continue
            delta = max(abs(a-b) for a,b in zip(source.getpixel((x,y)), figma.getpixel((x,y))))
            outside += 1
            exact += delta == 0
            maximum = max(maximum, delta)
    ink = {}
    for name,(x0,y0,x1,y1) in ZONES.items():
        points = [(x,y) for y in range(y0,y1) for x in range(x0,x1)
                  if min(figma.getpixel((x,y))) < 200]
        ink[name] = {"pixels": len(points), "bounds":
            [min(x for x,y in points), min(y for x,y in points),
             max(x for x,y in points), max(y for x,y in points)] if points else None}
    return {"sourceSize": source.size, "figmaSize": figma.size,
            "outsideContentPixels": outside, "outsideContentExactRatio": round(exact/outside, 6),
            "outsideContentMaxChannelDelta": maximum, "ink": ink}


def raster_policy(diag):
    if diag.get("sourceSize") != diag.get("figmaSize") or diag.get("sourceSize") != (240, 79) \
            or diag.get("outsideContentExactRatio") != 1.0 \
            or diag.get("outsideContentMaxChannelDelta") != 0:
        return False
    minima = {"arrow": 3, "parent": 50, "child1": 75, "child2": 75}
    for name,zone in ZONES.items():
        item = diag["ink"][name]
        if item["pixels"] < minima[name] or item["bounds"] is None:
            return False
        x0,y0,x1,y1 = zone
        a,b,c,d = item["bounds"]
        if not (x0 <= a <= c < x1 and y0 <= b <= d < y1):
            return False
    return True


def run():
    observed = read(TASK / "figma/native-read.json")
    candidate = read(ROOT / "artifacts/task-080/tree-candidate-audit.json")
    metadata = read(METADATA)
    visual = read(TASK / "visual-review.json")
    independent = audit(observed)
    diag = raster_diagnostics(SOURCE / "navigation.tree.expanded.departments.png",
                              TASK / "figma/native.png")
    checks = {
        "sourceAndCandidateLocked": candidate["status"] == "CANDIDATE_REVIEW"
            and metadata["candidateAuditSha256"] == sha(ROOT / "artifacts/task-080/tree-candidate-audit.json")
            and metadata["componentIrSha256"] == sha(SOURCE / "component_ir.json"),
        "independentNativeStructure": all(independent["checks"][key] for key in
            ("officialSourceVerified", "targetAndComponentLink", "nativeGeometry",
             "editableDefaultFontText", "sourceColorBound", "officialRemixArrowLinked"))
            and sha(TASK / "figma/native-read.json") == sha(CANDIDATE / "native-read.json"),
        "nativeRepeatStable": sha(TASK / "figma/native.png") == sha(TASK / "figma/native-repeat.png")
            == sha(CANDIDATE / "native.png"),
        "nativeSvgStable": sha(TASK / "figma/native.svg") == sha(CANDIDATE / "native.svg"),
        "sourceGeometryAndVisibleContent": raster_policy(diag),
        "hashBoundVisualReview": visual["status"] == "PASS" and visual["scope"] == "figma-only-qa"
            and visual["nativePngSha256"] == sha(TASK / "figma/native.png")
            and visual["visibleLabels"] == ["部门", "研发部", "设计部"]
            and visual["expandedArrowVisible"] is True and visual["extraChildIcons"] is False
            and visual["completeText"] is True and visual["clippedOrDetached"] is False
            and visual["effectiveCjkFontIdentity"] == "UNVERIFIED",
    }
    passed = all(checks.values())
    return {"scope": "figma-only-qa", "gateVersion": "0.2.12-figma-only",
            "status": "PASS" if passed else "FAIL",
            "logicalComponentId": "navigation.tree.expanded.departments", "componentType": "Tree",
            "checks": checks, "rasterDiagnostics": diag,
            "evidenceSha256": {"sourceScreenshot": sha(SOURCE / "navigation.tree.expanded.departments.png"),
                "candidateAudit": sha(ROOT / "artifacts/task-080/tree-candidate-audit.json"),
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
