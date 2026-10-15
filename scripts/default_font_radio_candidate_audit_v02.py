"""Audit and lock native Radio candidates; do not admit them."""
import hashlib
import json
from pathlib import Path

from PIL import Image

from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT


SOURCE = ROOT / "artifacts/task-063/radio-source"
TASK = ROOT / "artifacts/task-064"
FILES = ("native-read.json", "native.png", "native-repeat.png", "native.svg")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def audit():
    issues = verify_artifacts(SOURCE, expected_types={"Radio"})
    source = read(SOURCE / "component_ir.json")["components"][0]
    rows = {}
    for platform in ("figma", "penpot"):
        folder = TASK / platform
        observed = read(folder / "native-read.json")
        with Image.open(folder / "native.png") as image:
            native_size = list(image.size)
        svg = (folder / "native.svg").read_text(encoding="utf-8").lower()
        ring, dot, label, instance = (observed[key] for key in ("ring", "dot", "label", "instance"))
        main = observed["component"] if platform == "figma" else observed["main"]
        if platform == "figma":
            rgb = lambda paint: tuple(round(paint["color"][key] * 255) for key in ("r", "g", "b"))
            component_check = main["type"] == "COMPONENT" and instance["type"] == "INSTANCE" \
                and instance["mainComponentId"] == main["id"]
            geometry = (ring["x"], ring["y"], dot["x"], dot["y"]) == (0, 2, 3, 5)
            colors = rgb(ring["fills"][0]) == (255, 255, 255) and \
                rgb(ring["strokes"][0]) == rgb(dot["fills"][0]) == (45, 140, 240) and \
                rgb(label["fills"][0]) == (81, 90, 110)
            font = label["text"] == "启用" and label["fontName"]["family"] == "Inter" and \
                label["fontName"]["style"] == "Regular" and label["fontSize"] == 14
            svg_check = all(value in svg for value in ('fill="white"', '#2d8cf0', '#515a6e'))
            file_reference, component_id = observed["fileReference"], main["id"]
        else:
            component_check = instance["isCopy"] is True and instance["componentId"] == observed["componentId"] \
                and observed["fileValidation"] == 0
            geometry = (ring["x"] - main["x"], ring["y"] - main["y"],
                        dot["x"] - main["x"], dot["y"] - main["y"]) == (0, 2, 3, 5)
            colors = ring["fills"][0]["fillColor"].upper() == "#FFFFFF" and \
                ring["strokes"][0]["strokeColor"].upper() == dot["fills"][0]["fillColor"].upper() == "#2D8CF0" and \
                label["fills"][0]["fillColor"].upper() == "#515A6E"
            font = label["text"] == "启用" and label["fontId"] == "sourcesanspro" and \
                label["fontVariantId"] == "regular" and label["fontSize"] == "14" and label["lineHeight"] == "1.5"
            svg_check = all(value in svg for value in ("rgb(255, 255, 255)", "rgb(45, 140, 240)",
                                                          "rgb(81, 90, 110)", "sourcesanspro", "启用"))
            file_reference, component_id = observed["fileId"], observed["componentId"]
        checks = {
            "sourceLocked": source["logicalComponentId"] == "form.radio.default.enabled"
                and source["content"]["text"] == "启用" and source["rootBounds"] == {"width": 48, "height": 21},
            "nativeComponentAndInstance": component_check,
            "nativeGeometry": (main["width"], main["height"], ring["width"], ring["height"],
                               dot["width"], dot["height"]) == (48, 21, 16, 16, 10, 10)
                and geometry and native_size == [48, 21],
            "defaultFontAndFixedText": font and label["width"] == 28 and label["height"] == 21,
            "sourceColors": colors,
            "nativeSvgSemantics": svg_check,
            "repeatNativePngStable": sha(folder / "native.png") == sha(folder / "native-repeat.png"),
        }
        metadata = {"scope": "v02-default-font-radio-candidate", "version": "0.2.0",
            "platform": platform, "logicalComponentId": source["logicalComponentId"],
            "sourceVersion": source["provenance"]["sourceVersion"],
            "componentIrSha256": sha(SOURCE / "component_ir.json"),
            "fileReference": file_reference, "pageReference": observed["pageId"],
            "componentId": component_id, "instanceId": instance["id"],
            "contentScope": {"text": "启用", **source["props"], "width": 48, "height": 21},
            "font": "Inter" if platform == "figma" else "sourcesanspro",
            "status": "CANDIDATE_REVIEW" if all(checks.values()) else "FAIL",
            "checks": checks, "evidenceSha256": {name: sha(folder / name) for name in FILES},
            "nativeAdmission": "NOT_RUN", "readyForPageGeneration": False, "releaseReady": False}
        path = ROOT / f"adapters/{platform}/metadata/radio-default-font-candidate-0.2.0.json"
        path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        rows[platform] = metadata
        if not all(checks.values()):
            issues.append({"code": f"{platform}_radio_candidate_check_failed",
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
