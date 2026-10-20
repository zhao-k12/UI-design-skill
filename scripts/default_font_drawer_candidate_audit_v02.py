"""Audit fixed right Drawer Figma candidate against official runtime source."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT


SOURCE = ROOT / "artifacts/task-091/drawer-source"
TASK = ROOT / "artifacts/task-092/figma"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgb(paint):
    return tuple(round(paint["color"][c] * 255) for c in ("r", "g", "b"))


def audit(observed):
    source = read(SOURCE / "component_ir.json")["components"][0]
    metrics = read(SOURCE / "drawer-observation.json")["metrics"]
    main, header, title, body, content, review = observed["nodes"]
    shadow = main["effects"][0]
    checks = {
        "officialSourceVerified": verify_artifacts(SOURCE, expected_types={"Drawer"}) == []
            and source["logicalComponentId"] == "overlay.drawer.detail.open"
            and source["rootBounds"] == {"width": 320, "height": 500}
            and metrics["header"]["text"] == "详情"
            and metrics["body"]["text"] == "抽屉内容"
            and metrics["closeCount"] == 0 and metrics["maskCount"] == 1,
        "targetAndComponentLink": observed["fileReference"] == "0vGWSRoLxBiVPXiZ8xJAX9"
            and observed["pageId"] == "226:2" and main["id"] == "226:8"
            and main["type"] == "COMPONENT" and review["type"] == "INSTANCE"
            and review["mainComponentId"] == main["id"],
        "nativeGeometry": (main["width"], main["height"], main["layoutMode"], main["cornerRadius"])
            == (320, 500, "VERTICAL", 0)
            and (header["x"], header["y"], header["width"], header["height"])
            == (0, 0, 320, 51)
            and (body["x"], body["y"], body["width"], body["height"])
            == (0, 51, 320, 449)
            and (title["x"], title["y"], title["height"]) == (16, 14, 20)
            and (content["x"], content["y"], content["height"]) == (16, 16, 21),
        "sourceColorsBound": rgb(main["fills"][0]) == (255, 255, 255)
            and rgb(header["strokes"][0]) == (232, 234, 236)
            and rgb(title["fills"][0]) == (23, 35, 61)
            and rgb(content["fills"][0]) == (81, 90, 110)
            and [main["fills"][0]["boundVariables"]["color"]["id"],
                 header["strokes"][0]["boundVariables"]["color"]["id"],
                 title["fills"][0]["boundVariables"]["color"]["id"],
                 content["fills"][0]["boundVariables"]["color"]["id"]]
            == ["VariableID:226:4", "VariableID:226:7", "VariableID:226:5", "VariableID:226:6"],
        "editableDefaultFontText": title["characters"] == "详情"
            and title["fontName"]["family"] == "Inter"
            and title["fontName"]["style"] == "Medium" and title["fontSize"] == 16
            and title["lineHeight"] == {"unit": "PIXELS", "value": 20}
            and content["characters"] == "抽屉内容"
            and content["fontName"]["family"] == "Inter"
            and content["fontName"]["style"] == "Regular" and content["fontSize"] == 14
            and content["lineHeight"] == {"unit": "PIXELS", "value": 21},
        "sourceShadow": shadow["type"] == "DROP_SHADOW"
            and shadow["radius"] == 12 and shadow["offset"] == {"x": 0, "y": 4}
            and abs(shadow["color"]["a"] - 0.15) < 0.001,
        "nativeRepeatStable": sha(TASK / "native.png") == sha(TASK / "native-repeat.png"),
        "nativeSvgSemantics": all(s in (TASK / "native.svg").read_text(encoding="utf-8")
            for s in ('width="344"', 'height="524"', '#17233D', '#515A6E')),
    }
    with Image.open(TASK / "native.png") as image:
        checks["nativeRasterSize"] = image.size == (344, 524)
    status = "CANDIDATE_REVIEW" if all(checks.values()) else "FAIL"
    return {"scope": "figma-only-drawer-candidate", "status": status,
            "logicalComponentId": source["logicalComponentId"], "componentType": "Drawer",
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
