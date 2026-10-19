"""Audit fixed selected-date Figma candidate against official DatePicker runtime."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT


SOURCE = ROOT / "artifacts/task-082/datepicker-source"
TASK = ROOT / "artifacts/task-083/figma"
ICON_SHA = "97a1307f5f723435587f185da18a0046c29907843bad0e66e42a75a45b53e8dc"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgb(paint):
    return tuple(round(paint["color"][c] * 255) for c in ("r", "g", "b"))


def audit(observed):
    source = read(SOURCE / "component_ir.json")["components"][0]
    metrics = read(SOURCE / "datepicker-observation.json")["metrics"]
    main, label, spacer, icon, icon_master, vector, instance = observed["nodes"]
    icon_registry = read(ROOT / "registries/icons/snapshots/550580a4fc9bb3bb7901fe2271e3ade0e73f6da7cb49872249bfc2e091fac11a/registry.json")
    checks = {
        "officialSourceVerified": verify_artifacts(SOURCE, expected_types={"DatePicker"}) == []
            and source["logicalComponentId"] == "form.datepicker.date.selected"
            and source["rootBounds"] == {"width": 211, "height": 32}
            and metrics["input"]["value"] == "2024-01-01"
            and metrics["icon"]["classes"] == ["ivu-icon", "ivu-icon-ios-calendar-outline"],
        "targetAndComponentLink": observed["fileReference"] == "0vGWSRoLxBiVPXiZ8xJAX9"
            and observed["pageId"] == "218:2" and main["id"] == "218:16"
            and main["type"] == "COMPONENT" and instance["type"] == "INSTANCE"
            and instance["mainComponentId"] == main["id"],
        "nativeGeometry": (main["width"], main["height"], main["layoutMode"], main["cornerRadius"])
            == (211, 32, "HORIZONTAL", 4)
            and (label["x"], label["y"], label["height"]) == (8, 5.5, 21)
            and (spacer["x"], spacer["width"]) == (88, 99)
            and (icon["x"], icon["y"], icon["width"], icon["height"]) == (187, 8, 16, 16),
        "sourceColorsBound": rgb(main["fills"][0]) == (255, 255, 255)
            and rgb(main["strokes"][0]) == (220, 222, 226)
            and rgb(label["fills"][0]) == (81, 90, 110)
            and rgb(vector["fills"][0]) == (128, 134, 149)
            and [main["fills"][0]["boundVariables"]["color"]["id"],
                 main["strokes"][0]["boundVariables"]["color"]["id"],
                 label["fills"][0]["boundVariables"]["color"]["id"],
                 vector["fills"][0]["boundVariables"]["color"]["id"]]
            == ["VariableID:218:4", "VariableID:218:5", "VariableID:218:6", "VariableID:218:7"],
        "editableDefaultFontText": label["type"] == "TEXT" and label["characters"] == "2024-01-01"
            and label["fontName"]["family"] == "Inter"
            and label["fontName"]["style"] == "Regular" and label["fontSize"] == 14
            and label["lineHeight"] == {"unit": "PIXELS", "value": 21},
        "officialRemixCalendarLinked": icon_registry["icons"]["remix.calendar-line"]["svgSha256"] == ICON_SHA
            and sha(ROOT / "registries/icons/objects" / (ICON_SHA + ".svg")) == ICON_SHA
            and icon["type"] == "INSTANCE" and icon["mainComponentId"] == icon_master["id"]
            and vector["type"] == "VECTOR",
        "nativeRepeatStable": sha(TASK / "native.png") == sha(TASK / "native-repeat.png"),
        "nativeSvgSemantics": all(s in (TASK / "native.svg").read_text(encoding="utf-8")
            for s in ('width="211"', 'height="32"', '#DCDEE2', '#515A6E', '#808695')),
    }
    with Image.open(TASK / "native.png") as image:
        checks["nativeRasterSize"] = image.size == (211, 32)
    status = "CANDIDATE_REVIEW" if all(checks.values()) else "FAIL"
    return {"scope": "figma-only-datepicker-candidate", "status": status,
            "logicalComponentId": source["logicalComponentId"], "componentType": "DatePicker",
            "componentIrSha256": sha(SOURCE / "component_ir.json"),
            "fileReference": observed["fileReference"], "pageReference": observed["pageId"],
            "componentId": main["id"], "instanceId": instance["id"], "checks": checks,
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
