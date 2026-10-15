"""Independent Figma-only quality gate for the fixed default-font Card."""
import argparse
import json
from pathlib import Path

from PIL import Image

from scripts.default_font_card_candidate_audit_v02 import ROOT, SOURCE, audit, read, sha


CANDIDATE = ROOT / "artifacts/task-071/figma"
TASK = ROOT / "artifacts/task-072"
POLICY = ROOT / "validators/visual/DEFAULT_FONT_CARD_POLICY.md"
METADATA = ROOT / "adapters/figma/metadata/card-default-font-candidate-0.2.0.json"
FILES = ("native-read.json", "native.png", "native-repeat.png", "native.svg")


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
    zones = ((15, 12, 100, 38), (15, 66, 95, 90))
    outside, exact, maximum = 0, 0, 0
    for y in range(source.height):
        for x in range(source.width):
            if any(x0 <= x < x1 and y0 <= y < y1 for x0, y0, x1, y1 in zones):
                continue
            difference = max(abs(a-b) for a, b in zip(source.getpixel((x,y)), figma.getpixel((x,y))))
            outside += 1
            exact += difference == 0
            maximum = max(maximum, difference)
    def ink(box):
        x0, y0, x1, y1 = box
        points = [(x, y) for y in range(y0, y1) for x in range(x0, x1)
                  if min(figma.getpixel((x, y))) < 180]
        return {"pixels": len(points), "bounds": [min(x for x,y in points), min(y for x,y in points),
                max(x for x,y in points), max(y for x,y in points)]} if points else {"pixels": 0, "bounds": None}
    return {"sourceSize": source.size, "figmaSize": figma.size,
            "outsideTextPixels": outside, "outsideTextExactRatio": round(exact / outside, 6),
            "outsideTextMaxChannelDelta": maximum,
            "titleInk": ink((17,15,90,38)), "bodyInk": ink((17,68,90,89))}


def raster_policy(diag):
    title, body = diag.get("titleInk", {}), diag.get("bodyInk", {})
    return diag.get("sourceSize") == diag.get("figmaSize") == (240, 106) \
        and diag.get("outsideTextExactRatio", 0) >= .998 \
        and diag.get("outsideTextMaxChannelDelta", 999) <= 3 \
        and title.get("pixels", 0) >= 300 and body.get("pixels", 0) >= 200 \
        and title.get("bounds") is not None and body.get("bounds") is not None \
        and 17 < title["bounds"][0] <= title["bounds"][2] < 89 \
        and 15 < title["bounds"][1] <= title["bounds"][3] < 37 \
        and 17 < body["bounds"][0] <= body["bounds"][2] < 89 \
        and 68 < body["bounds"][1] <= body["bounds"][3] < 88


def run():
    observed = read(TASK / "figma/native-read.json")
    candidate_report = read(ROOT / "artifacts/task-071/card-candidate-audit.json")
    metadata = read(METADATA)
    visual = read(TASK / "visual-review.json")
    independent = audit(observed)
    diag = raster_diagnostics(SOURCE / "content.card.default.user-info.png", TASK / "figma/native.png")
    checks = {
        "sourceAndCandidateLocked": candidate_report["status"] == "CANDIDATE_REVIEW"
            and metadata["candidateAuditSha256"] == sha(ROOT / "artifacts/task-071/card-candidate-audit.json")
            and metadata["componentIrSha256"] == sha(SOURCE / "component_ir.json"),
        "independentNativeStructure": all(independent["checks"][key] for key in
            ("officialSourceVerified", "targetAndComponentLink", "nativeGeometry",
             "sourceColorsBound", "defaultFontText"))
            and sha(TASK / "figma/native-read.json") == sha(CANDIDATE / "native-read.json"),
        "nativeRepeatStable": sha(TASK / "figma/native.png") == sha(TASK / "figma/native-repeat.png")
            == sha(CANDIDATE / "native.png"),
        "nativeSvgStable": sha(TASK / "figma/native.svg") == sha(CANDIDATE / "native.svg"),
        "sourceGeometryAndTextRaster": raster_policy(diag),
        "hashBoundVisualReview": visual["status"] == "PASS" and visual["scope"] == "figma-only-qa"
            and visual["nativePngSha256"] == sha(TASK / "figma/native.png")
            and visual["title"] == "用户信息" and visual["body"] == "暂无内容"
            and visual["completeTitle"] is True and visual["completeBody"] is True
            and visual["clippedText"] is False and visual["detachedOrEmpty"] is False
            and visual["borderAndDividerVisible"] is True
            and visual["effectiveCjkFontIdentity"] == "UNVERIFIED",
    }
    passed = all(checks.values())
    return {"scope": "figma-only-qa", "gateVersion": "0.2.9-figma-only",
            "status": "PASS" if passed else "FAIL", "logicalComponentId": "content.card.default.user-info",
            "componentType": "Card", "checks": checks, "rasterDiagnostics": diag,
            "evidenceSha256": {"sourceScreenshot": sha(SOURCE / "content.card.default.user-info.png"),
                "candidateAudit": sha(ROOT / "artifacts/task-071/card-candidate-audit.json"),
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
    print(json.dumps({"status": result["status"], "checks": result["checks"]}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
