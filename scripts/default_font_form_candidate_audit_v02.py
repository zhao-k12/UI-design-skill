"""Audit fixed one-field Figma Form candidate against official runtime source."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT


SOURCE = ROOT / "artifacts/task-085/form-source"
TASK = ROOT / "artifacts/task-086/figma"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgb(paint):
    return tuple(round(paint["color"][c] * 255) for c in ("r", "g", "b"))


def audit(observed):
    source = read(SOURCE / "component_ir.json")["components"][0]
    metrics = read(SOURCE / "form-observation.json")["metrics"]
    main, label_box, label, input_instance, review = observed["nodes"]
    binding = read(ROOT / "adapters/figma/metadata/component-bindings-0.2.6.json")
    checks = {
        "officialSourceVerified": verify_artifacts(SOURCE, expected_types={"Form"}) == []
            and source["logicalComponentId"] == "form.single.name.empty"
            and source["rootBounds"] == {"width": 320, "height": 34}
            and metrics["label"]["text"] == "姓名"
            and metrics["input"]["placeholder"] == "请输入姓名",
        "targetAndComponentLink": observed["fileReference"] == "0vGWSRoLxBiVPXiZ8xJAX9"
            and observed["pageId"] == "220:2" and main["id"] == "220:9"
            and main["type"] == "COMPONENT" and review["type"] == "INSTANCE"
            and review["mainComponentId"] == main["id"],
        "nativeGeometry": (main["width"], main["height"], main["layoutMode"])
            == (320, 34, "HORIZONTAL")
            and (label_box["x"], label_box["y"], label_box["width"], label_box["height"])
            == (0, 0, 80, 34)
            and (label["x"], label["y"], label["width"], label["height"])
            == (40, 10, 28, 14)
            and (input_instance["x"], input_instance["y"], input_instance["width"], input_instance["height"])
            == (80, 1, 240, 32),
        "editableDefaultFontLabel": label["type"] == "TEXT" and label["characters"] == "姓名"
            and label["fontName"]["family"] == "Inter"
            and label["fontName"]["style"] == "Regular" and label["fontSize"] == 14
            and label["lineHeight"] == {"unit": "PIXELS", "value": 14}
            and rgb(label["fills"][0]) == (81, 90, 110)
            and label["fills"][0]["boundVariables"]["color"]["id"] == "VariableID:205:9",
        "admittedInputInstance": input_instance["type"] == "INSTANCE"
            and input_instance["mainComponentId"] == "141:3"
            and binding["bindings"]["form.input.default.medium"]["variants"]["default"]["componentReference"]
            == "141:3",
        "nativeRepeatStable": sha(TASK / "native.png") == sha(TASK / "native-repeat.png"),
        "nativeSvgSemantics": all(s in (TASK / "native.svg").read_text(encoding="utf-8")
            for s in ('width="320"', 'height="34"', '#515A6E', '#DCDEE2')),
    }
    with Image.open(TASK / "native.png") as image:
        checks["nativeRasterSize"] = image.size == (320, 34)
    status = "CANDIDATE_REVIEW" if all(checks.values()) else "FAIL"
    return {"scope": "figma-only-form-candidate", "status": status,
            "logicalComponentId": source["logicalComponentId"], "componentType": "Form",
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
