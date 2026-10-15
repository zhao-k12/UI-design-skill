"""Audit the fixed official Card against its native Figma candidate."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT


SOURCE = ROOT / "artifacts/task-070/card-source"
TASK = ROOT / "artifacts/task-071/figma"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgb(paint):
    return tuple(round(paint["color"][channel] * 255) for channel in ("r", "g", "b"))


def audit(observed):
    source = read(SOURCE / "component_ir.json")["components"][0]
    main, head, title, divider, body, body_text, instance = observed["nodes"]
    checks = {
        "officialSourceVerified": verify_artifacts(SOURCE, expected_types={"Card"}) == []
            and source["logicalComponentId"] == "content.card.default.user-info"
            and source["rootBounds"] == {"width": 240, "height": 106},
        "targetAndComponentLink": observed["fileReference"] == "0vGWSRoLxBiVPXiZ8xJAX9"
            and observed["pageId"] == "198:2" and main["id"] == "198:8"
            and main["type"] == "COMPONENT" and instance["type"] == "INSTANCE"
            and instance["mainComponentId"] == main["id"],
        "nativeGeometry": (main["width"], main["height"], main["cornerRadius"]) == (240, 106, 4)
            and (head["x"], head["y"], head["width"], head["height"]) == (1, 1, 238, 51)
            and (body["x"], body["y"], body["width"], body["height"]) == (1, 52, 238, 53)
            and (divider["x"], divider["y"], divider["width"], divider["height"]) == (0, 50, 238, 1),
        "sourceColorsBound": rgb(main["fills"][0]) == (255, 255, 255)
            and rgb(main["strokes"][0]) == rgb(divider["fills"][0]) == (232, 234, 236)
            and rgb(title["fills"][0]) == (23, 35, 61)
            and rgb(body_text["fills"][0]) == (81, 90, 110)
            and all("boundVariables" in paint for paint in (main["fills"][0], main["strokes"][0],
                divider["fills"][0], title["fills"][0], body_text["fills"][0])),
        "defaultFontText": title["characters"] == "用户信息" and body_text["characters"] == "暂无内容"
            and (title["fontName"]["family"], title["fontName"]["style"], title["fontSize"],
                 title["lineHeight"]) == ("Inter", "Medium", 16, {"unit": "PIXELS", "value": 22})
            and (body_text["fontName"]["family"], body_text["fontName"]["style"], body_text["fontSize"],
                 body_text["lineHeight"]) == ("Inter", "Regular", 14, {"unit": "PIXELS", "value": 21}),
        "nativeRepeatStable": sha(TASK / "native.png") == sha(TASK / "native-repeat.png"),
        "nativeSvgSourceColors": all(s in (TASK / "native.svg").read_text(encoding="utf-8")
                                     for s in ('width="240"', 'height="106"', '#E8EAEC', '#17233D', '#515A6E')),
    }
    with Image.open(TASK / "native.png") as image:
        checks["nativeRasterSize"] = image.size == (240, 106)
    status = "CANDIDATE_REVIEW" if all(checks.values()) else "FAIL"
    return {"scope": "figma-only-card-candidate", "status": status,
            "logicalComponentId": source["logicalComponentId"], "componentType": "Card",
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
