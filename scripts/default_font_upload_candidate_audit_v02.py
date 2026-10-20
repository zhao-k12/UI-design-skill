"""Audit fixed drag Upload Figma candidate against official runtime source."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT


SOURCE = ROOT / "artifacts/task-094/upload-source"
TASK = ROOT / "artifacts/task-095/figma"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgb(paint):
    return tuple(round(paint["color"][c] * 255) for c in ("r", "g", "b"))


def audit(observed):
    source = read(SOURCE / "component_ir.json")["components"][0]
    metrics = read(SOURCE / "upload-observation.json")["metrics"]
    main, label, review = observed["nodes"]
    checks = {
        "officialSourceVerified": verify_artifacts(SOURCE, expected_types={"Upload"}) == []
            and source["logicalComponentId"] == "data.upload.drag.empty"
            and source["rootBounds"] == {"width": 320, "height": 82}
            and metrics["drag"]["style"]["border"] == "1px dashed rgb(220, 222, 226)"
            and metrics["content"]["text"] == "上传文件"
            and metrics["fileInputPresent"] is True and metrics["uploadListCount"] == 0,
        "targetAndComponentLink": observed["fileReference"] == "0vGWSRoLxBiVPXiZ8xJAX9"
            and observed["pageId"] == "229:2" and main["id"] == "229:7"
            and main["type"] == "COMPONENT" and review["type"] == "INSTANCE"
            and review["mainComponentId"] == main["id"],
        "nativeGeometry": (main["width"], main["height"], main["layoutMode"], main["cornerRadius"])
            == (320, 82, "HORIZONTAL", 4)
            and (label["x"], label["y"], label["width"], label["height"])
            == (110, 30.5, 100, 21),
        "sourceColorsBound": rgb(main["fills"][0]) == (255, 255, 255)
            and rgb(main["strokes"][0]) == (220, 222, 226)
            and rgb(label["fills"][0]) == (81, 90, 110)
            and [main["fills"][0]["boundVariables"]["color"]["id"],
                 main["strokes"][0]["boundVariables"]["color"]["id"],
                 label["fills"][0]["boundVariables"]["color"]["id"]]
            == ["VariableID:229:4", "VariableID:229:5", "VariableID:229:6"],
        "editableDefaultFontText": label["characters"] == "上传文件"
            and label["fontName"]["family"] == "Inter"
            and label["fontName"]["style"] == "Regular" and label["fontSize"] == 14
            and label["lineHeight"] == {"unit": "PIXELS", "value": 21}
            and label["textAlignHorizontal"] == "CENTER",
        "dashedBorder": main["strokeWeight"] == 1 and main["strokeAlign"] == "INSIDE"
            and main["dashPattern"] == [3, 2],
        "nativeRepeatStable": sha(TASK / "native.png") == sha(TASK / "native-repeat.png"),
        "nativeSvgSemantics": all(s in (TASK / "native.svg").read_text(encoding="utf-8")
            for s in ('width="320"', 'height="82"', '#DCDEE2', '#515A6E')),
    }
    with Image.open(TASK / "native.png") as image:
        checks["nativeRasterSize"] = image.size == (320, 82)
    status = "CANDIDATE_REVIEW" if all(checks.values()) else "FAIL"
    return {"scope": "figma-only-upload-candidate", "status": status,
            "logicalComponentId": source["logicalComponentId"], "componentType": "Upload",
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
