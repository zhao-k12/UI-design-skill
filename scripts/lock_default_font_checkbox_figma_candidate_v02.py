"""Audit and lock the Figma Checkbox native candidate; do not admit it."""
import hashlib
import json
from pathlib import Path

from PIL import Image

from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT


SOURCE = ROOT / "artifacts/task-058/checkbox-source"
FOLDER = ROOT / "artifacts/task-059/figma"
META = ROOT / "adapters/figma/metadata/checkbox-default-font-candidate-0.2.0.json"
FILES = ("independent-read.json", "component-native.png", "repeat-native.png", "component-native.svg")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def audit():
    issues = verify_artifacts(SOURCE, expected_types={"Checkbox"})
    component = read(SOURCE / "component_ir.json")["components"][0]
    observed = read(FOLDER / "independent-read.json")
    box, label, instance = observed["box"], observed["label"], observed["instance"]
    png, repeat, svg = (FOLDER / name for name in FILES[1:])
    with Image.open(png) as image:
        native_size = list(image.size)
    source_size = [component["rootBounds"][key] for key in ("width", "height")]
    svg_text = svg.read_text(encoding="utf-8").lower()
    checks = {
        "sourceLocked": component["logicalComponentId"] == "form.checkbox.default.enabled"
            and component["content"]["text"] == "启用" and source_size == [52, 21],
        "nativeComponentAndInstance": observed["component"]["type"] == "COMPONENT"
            and instance["type"] == "INSTANCE" and instance["mainComponentId"] == observed["component"]["id"],
        "nativeGeometry": [observed["component"][key] for key in ("width", "height")] == [52, 21]
            and [box[key] for key in ("width", "height")] == [16, 16]
            and box["radius"] == 2 and native_size == source_size,
        "defaultFontAndFixedText": label["text"] == "启用" and label["fontName"]["family"] == "Inter"
            and label["fontName"]["style"] == "Regular" and label["fontSize"] == 14,
        "sourceColors": all(color in svg_text for color in ("#2d8cf0", "#515a6e", "white")),
        "editableVectorAndText": len(box["children"]) == 1 and box["children"][0]["type"] == "FRAME"
            and len(observed["component"]["children"]) == 2,
        "repeatNativePngStable": sha(png) == sha(repeat),
    }
    if not all(checks.values()):
        issues.append({"code": "figma_checkbox_candidate_check_failed",
                       "checks": [key for key, value in checks.items() if not value]})
    metadata = {"scope": "v02-default-font-checkbox-candidate", "version": "0.2.0",
        "platform": "figma", "logicalComponentId": component["logicalComponentId"],
        "sourceVersion": component["provenance"]["sourceVersion"],
        "componentIrSha256": sha(SOURCE / "component_ir.json"),
        "fileReference": observed["fileReference"], "pageReference": observed["pageId"],
        "componentId": observed["component"]["id"], "instanceId": instance["id"],
        "contentScope": {"text": "启用", **component["props"], "width": 52, "height": 21},
        "font": "Inter", "status": "CANDIDATE_REVIEW" if not issues else "FAIL",
        "checks": checks, "evidenceSha256": {name: sha(FOLDER / name) for name in FILES},
        "nativeAdmission": "NOT_RUN", "readyForPageGeneration": False, "releaseReady": False}
    META.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata, issues


if __name__ == "__main__":
    report, issues = audit()
    print(json.dumps({"status": report["status"], "checks": report["checks"], "issues": issues}, ensure_ascii=False))
    raise SystemExit(bool(issues))
