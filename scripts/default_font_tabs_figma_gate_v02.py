"""Independent Figma-only quality gate for fixed two-tab default-font Tabs."""
import argparse
import json
from pathlib import Path

from PIL import Image

from scripts.default_font_tabs_candidate_audit_v02 import ROOT, SOURCE, audit, read, sha


CANDIDATE = ROOT / "artifacts/task-077/figma"
TASK = ROOT / "artifacts/task-078"
POLICY = ROOT / "validators/visual/DEFAULT_FONT_TABS_POLICY.md"
METADATA = ROOT / "adapters/figma/metadata/tabs-default-font-candidate-0.2.0.json"
FILES = ("native-read.json", "native.png", "native-repeat.png", "native.svg")
ZONES = {"active": (15,7,46,31), "inactive": (91,7,122,31),
         "content": (0,51,70,73)}


def raster_diagnostics(reference, native):
    with Image.open(reference) as image:
        source = image.convert("RGB")
    with Image.open(native) as image:
        rgba = image.convert("RGBA")
    white = Image.new("RGBA", rgba.size, "white")
    white.alpha_composite(rgba)
    figma = white.convert("RGB")
    if source.size != figma.size:
        return {"sourceSize":source.size,"figmaSize":figma.size}
    outside, exact, maximum = 0, 0, 0
    for y in range(source.height):
        for x in range(source.width):
            if any(x0<=x<x1 and y0<=y<y1 for x0,y0,x1,y1 in ZONES.values()):
                continue
            delta=max(abs(a-b) for a,b in zip(source.getpixel((x,y)),figma.getpixel((x,y))))
            outside+=1;exact+=delta==0;maximum=max(maximum,delta)
    ink={}
    for name,(x0,y0,x1,y1) in ZONES.items():
        points=[(x,y) for y in range(y0,y1) for x in range(x0,x1)
                if min(figma.getpixel((x,y)))<200]
        ink[name]={"pixels":len(points),"bounds":
            [min(x for x,y in points),min(y for x,y in points),
             max(x for x,y in points),max(y for x,y in points)] if points else None}
    return {"sourceSize":source.size,"figmaSize":figma.size,
            "outsideTextPixels":outside,"outsideTextExactRatio":round(exact/outside,6),
            "outsideTextMaxChannelDelta":maximum,"ink":ink}


def raster_policy(diag):
    if diag.get("sourceSize") != diag.get("figmaSize") or diag.get("sourceSize") != (320,73) \
            or diag.get("outsideTextExactRatio") != 1.0 \
            or diag.get("outsideTextMaxChannelDelta") != 0:
        return False
    minima={"active":100,"inactive":100,"content":250}
    for name,zone in ZONES.items():
        item=diag["ink"][name]
        if item["pixels"]<minima[name] or item["bounds"] is None:
            return False
        x0,y0,x1,y1=zone;a,b,c,d=item["bounds"]
        if not (x0<=a<=c<x1 and y0<b<=d<y1-1):
            return False
    return True


def run():
    observed=read(TASK / "figma/native-read.json")
    candidate=read(ROOT / "artifacts/task-077/tabs-candidate-audit.json")
    metadata=read(METADATA)
    visual=read(TASK / "visual-review.json")
    independent=audit(observed)
    diag=raster_diagnostics(SOURCE / "navigation.tabs.line.overview.png",TASK / "figma/native.png")
    checks={
        "sourceAndCandidateLocked":candidate["status"]=="CANDIDATE_REVIEW"
            and metadata["candidateAuditSha256"]==sha(ROOT / "artifacts/task-077/tabs-candidate-audit.json")
            and metadata["componentIrSha256"]==sha(SOURCE / "component_ir.json"),
        "independentNativeStructure":all(independent["checks"][key] for key in
            ("officialSourceVerified","targetAndComponentLink","nativeGeometry",
             "sourceColorsBound","editableDefaultFontText","selectedPaneOnly"))
            and sha(TASK / "figma/native-read.json")==sha(CANDIDATE / "native-read.json"),
        "nativeRepeatStable":sha(TASK / "figma/native.png")==sha(TASK / "figma/native-repeat.png")
            ==sha(CANDIDATE / "native.png"),
        "nativeSvgStable":sha(TASK / "figma/native.svg")==sha(CANDIDATE / "native.svg"),
        "sourceGeometryAndVisibleText":raster_policy(diag),
        "hashBoundVisualReview":visual["status"]=="PASS" and visual["scope"]=="figma-only-qa"
            and visual["nativePngSha256"]==sha(TASK / "figma/native.png")
            and visual["visibleLabels"]==["概览","详情"]
            and visual["activeLabel"]=="概览" and visual["visibleContent"]=="概览内容"
            and visual["activeInkVisible"] is True and visual["inactiveContentHidden"] is True
            and visual["completeText"] is True and visual["clippedOrDetached"] is False
            and visual["effectiveCjkFontIdentity"]=="UNVERIFIED",
    }
    passed=all(checks.values())
    return {"scope":"figma-only-qa","gateVersion":"0.2.11-figma-only",
            "status":"PASS" if passed else "FAIL",
            "logicalComponentId":"navigation.tabs.line.overview","componentType":"Tabs",
            "checks":checks,"rasterDiagnostics":diag,
            "evidenceSha256":{"sourceScreenshot":sha(SOURCE / "navigation.tabs.line.overview.png"),
                "candidateAudit":sha(ROOT / "artifacts/task-077/tabs-candidate-audit.json"),
                "visualReview":sha(TASK / "visual-review.json"),"policy":sha(POLICY),
                **{name:sha(TASK / "figma" / name) for name in FILES}},
            "admissionEligible":False,"dualPlatformFidelity":"DEFERRED",
            "registryAdmission":"DEFERRED_PENPOT","readyForPageGeneration":False,
            "releaseReady":False,"effectiveCjkFontIdentity":"UNVERIFIED"}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();output=args.output.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        parser.error("Output must stay in artifacts")
    result=run();output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"checks":result["checks"]},ensure_ascii=False))
    return 0 if result["status"]=="PASS" else 2


if __name__=="__main__":
    raise SystemExit(main())
