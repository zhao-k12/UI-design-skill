"""Audit fixed selected Cascader Figma candidate against official runtime source."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT


SOURCE = ROOT / "artifacts/task-097/cascader-source"
TASK = ROOT / "artifacts/task-098/figma"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgb(paint):
    return tuple(round(paint["color"][c] * 255) for c in ("r", "g", "b"))


def audit(observed):
    source = read(SOURCE / "component_ir.json")["components"][0]
    metrics = read(SOURCE / "cascader-observation.json")["metrics"]
    main, frame, label, arrow, review = observed["nodes"]
    checks = {
        "officialSourceVerified": verify_artifacts(SOURCE, expected_types={"Cascader"}) == []
            and source["logicalComponentId"] == "form.cascader.region.selected"
            and source["rootBounds"] == {"width": 240, "height": 32}
            and metrics["input"]["value"] == "浙江 / 杭州"
            and metrics["input"]["style"]["border"] == "1px solid rgb(220, 222, 226)"
            and metrics["visibleDropdownCount"] == 0,
        "targetAndComponentLink": observed["fileReference"] == "0vGWSRoLxBiVPXiZ8xJAX9"
            and observed["pageId"] == "231:7" and main["id"] == "231:13"
            and main["type"] == "COMPONENT" and review["type"] == "INSTANCE"
            and review["mainComponentId"] == main["id"],
        "nativeGeometry": (main["width"], main["height"], frame["width"], frame["height"],
                            frame["cornerRadius"], main["layoutMode"])
            == (240, 32, 240, 32, 4, "HORIZONTAL")
            and (label["x"], label["y"], label["width"], label["height"])
            == (8, 0, 120, 30)
            and (arrow["x"], arrow["y"], arrow["width"], arrow["height"])
            == (216, 8, 14, 14),
        "sourceColorsBound": rgb(frame["fills"][0]) == (255, 255, 255)
            and rgb(frame["strokes"][0]) == (220, 222, 226)
            and rgb(label["fills"][0]) == (81, 90, 110)
            and rgb(arrow["fills"][0]) == (128, 134, 149)
            and [frame["fills"][0]["boundVariables"]["color"]["id"],
                 frame["strokes"][0]["boundVariables"]["color"]["id"],
                 label["fills"][0]["boundVariables"]["color"]["id"],
                 arrow["fills"][0]["boundVariables"]["color"]["id"]]
            == ["VariableID:231:9", "VariableID:231:10", "VariableID:231:11", "VariableID:231:12"],
        "editableDefaultFontText": label["characters"] == "浙江 / 杭州"
            and label["fontName"]["family"] == "Inter"
            and label["fontName"]["style"] == "Regular" and label["fontSize"] == 14
            and label["lineHeight"] == {"unit": "PIXELS", "value": 30},
        "nativeOfficialArrow": arrow["fontName"]["family"] == "Ionicons"
            and arrow["fontSize"] == 14 and len(arrow["characters"]) == 1,
        "nativeRepeatStable": sha(TASK / "native.png") == sha(TASK / "native-repeat.png"),
        "nativeSvgSemantics": all(s in (TASK / "native.svg").read_text(encoding="utf-8")
            for s in ('width="240"', 'height="32"', '#DCDEE2', '#515A6E', '#808695')),
    }
    with Image.open(TASK / "native.png") as image:
        checks["nativeRasterSize"] = image.size == (240, 32)
    status = "CANDIDATE_REVIEW" if all(checks.values()) else "FAIL"
    return {"scope": "figma-only-cascader-candidate", "status": status,
            "logicalComponentId": source["logicalComponentId"], "componentType": "Cascader",
            "componentIrSha256": sha(SOURCE / "component_ir.json"),
            "fileReference": observed["fileReference"], "pageReference": observed["pageId"],
            "componentId": main["id"], "instanceId": review["id"], "checks": checks,
            "evidenceSha256": {name: sha(TASK / name) for name in
                ("native-read.json", "native.png", "native-repeat.png", "native.svg")},
            "admissionEligible": False, "dualPlatformFidelity": "DEFERRED",
            "registryAdmission": "DEFERRED_PENPOT", "releaseReady": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        parser.error("Output must stay in artifacts")
    result = audit(read(TASK / "native-read.json"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": result["checks"]}, ensure_ascii=False))
    return 0 if result["status"] == "CANDIDATE_REVIEW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
