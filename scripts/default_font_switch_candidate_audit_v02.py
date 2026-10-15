"""Audit and lock native Switch candidates; do not admit them."""
import hashlib
import json

from PIL import Image

from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT


SOURCE = ROOT / "artifacts/task-067/switch-source"
TASK = ROOT / "artifacts/task-068"
FILES = ("native-read.json", "native.png", "native-repeat.png", "native.svg")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def audit():
    issues = verify_artifacts(SOURCE, expected_types={"Switch"})
    source = read(SOURCE / "component_ir.json")["components"][0]
    rows = {}
    for platform in ("figma", "penpot"):
        folder = TASK / platform
        observed = read(folder / "native-read.json")
        with Image.open(folder / "native.png") as image:
            native_size = list(image.size)
        svg = (folder / "native.svg").read_text(encoding="utf-8").lower()
        main = observed["component"] if platform == "figma" else observed["main"]
        label, knob, instance = (observed[key] for key in ("label", "knob", "instance"))
        if platform == "figma":
            rgb = lambda paint: tuple(round(paint["color"][key] * 255) for key in ("r", "g", "b"))
            component_check = main["type"] == "COMPONENT" and instance["type"] == "INSTANCE" \
                and instance["mainComponentId"] == main["id"]
            geometry = (label["x"], label["y"], knob["x"], knob["y"]) == (8, 1, 24, 2)
            colors = rgb(main["fills"][0]) == (45, 140, 240) and \
                rgb(label["fills"][0]) == rgb(knob["fills"][0]) == (255, 255, 255)
            font = label["text"] == "开" and label["fontName"]["family"] == "Inter" and \
                label["fontName"]["style"] == "Regular" and label["fontSize"] == 12 \
                and label["lineHeight"] == {"unit": "PIXELS", "value": 20}
            svg_check = all(value in svg for value in ('#2d8cf0', 'fill="white"', '<circle'))
            file_reference, component_id = observed["fileReference"], main["id"]
        else:
            component_check = instance["isCopy"] is True and instance["componentId"] == observed["componentId"] \
                and observed["fileValidation"] == 0
            geometry = (label["x"] - main["x"], label["y"] - main["y"],
                        knob["x"] - main["x"], knob["y"] - main["y"]) == (8, 1, 24, 2)
            colors = main["fills"][0]["fillColor"].upper() == "#2D8CF0" and \
                label["fills"][0]["fillColor"].upper() == knob["fills"][0]["fillColor"].upper() == "#FFFFFF"
            font = label["text"] == "开" and label["fontId"] == "sourcesanspro" and \
                label["fontVariantId"] == "regular" and label["fontSize"] == "12" and \
                label["lineHeight"] == "1.6666667"
            svg_check = all(value in svg for value in ("rgb(45, 140, 240)", "rgb(255, 255, 255)",
                                                          "sourcesanspro", "开", "<ellipse"))
            file_reference, component_id = observed["fileId"], observed["componentId"]
        checks = {
            "sourceLocked": source["logicalComponentId"] == "form.switch.default.enabled"
                and source["content"]["text"] == "开" and source["rootBounds"] == {"width": 44, "height": 22},
            "nativeComponentAndInstance": component_check,
            "nativeGeometry": (main["width"], main["height"], main["borderRadius"] if platform == "penpot" else main["radius"],
                               label["width"], label["height"], knob["width"], knob["height"]) ==
                (44, 22, 11, 12, 20, 18, 18) and geometry and native_size == [44, 22],
            "defaultFontAndFixedText": font,
            "sourceColors": colors,
            "nativeSvgSemantics": svg_check,
            "repeatNativePngStable": sha(folder / "native.png") == sha(folder / "native-repeat.png"),
        }
        metadata = {"scope": "v02-default-font-switch-candidate", "version": "0.2.0",
            "platform": platform, "logicalComponentId": source["logicalComponentId"],
            "sourceVersion": source["provenance"]["sourceVersion"],
            "componentIrSha256": sha(SOURCE / "component_ir.json"),
            "fileReference": file_reference, "pageReference": observed["pageId"],
            "componentId": component_id, "instanceId": instance["id"],
            "contentScope": {"text": "开", **source["props"], "width": 44, "height": 22},
            "font": "Inter" if platform == "figma" else "sourcesanspro",
            "status": "CANDIDATE_REVIEW" if all(checks.values()) else "FAIL",
            "checks": checks, "evidenceSha256": {name: sha(folder / name) for name in FILES},
            "nativeAdmission": "NOT_RUN", "readyForPageGeneration": False, "releaseReady": False}
        path = ROOT / f"adapters/{platform}/metadata/switch-default-font-candidate-0.2.0.json"
        path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        rows[platform] = metadata
        if not all(checks.values()):
            issues.append({"code": f"{platform}_switch_candidate_check_failed",
                           "checks": [key for key, value in checks.items() if not value]})
    result = {"status": "CANDIDATE_REVIEW" if not issues else "FAIL", "issues": issues,
              "logicalComponentId": source["logicalComponentId"], "platforms": rows,
              "sourceComponentIrSha256": sha(SOURCE / "component_ir.json")}
    (TASK / "candidate-audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    report = audit()
    print(json.dumps({"status": report["status"], "issues": report["issues"],
                      "platforms": {key: value["checks"] for key, value in report["platforms"].items()}}, ensure_ascii=False))
    raise SystemExit(report["status"] != "CANDIDATE_REVIEW")
