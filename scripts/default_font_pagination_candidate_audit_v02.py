"""Audit the fixed official Pagination against its native Figma candidate."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT


SOURCE = ROOT / "artifacts/task-073/pagination-source"
TASK = ROOT / "artifacts/task-074/figma"
ICON_REGISTRY = next((ROOT / "registries/icons/snapshots").glob("*/registry.json"))


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgb(paint):
    return tuple(round(paint["color"][channel] * 255) for channel in ("r", "g", "b"))


def audit(observed):
    source = read(SOURCE / "component_ir.json")["components"][0]
    observation = read(SOURCE / "pagination-observation.json")
    icons = read(ICON_REGISTRY)["icons"]
    nodes = observed["nodes"]
    left, right, main = nodes[:3]
    cells = nodes[3:13:2]
    content = nodes[4:14:2]
    instance = nodes[-1]
    checks = {
        "officialSourceVerified": verify_artifacts(SOURCE, expected_types={"Pagination"}) == []
            and source["logicalComponentId"] == "data.pagination.default.three-pages"
            and source["rootBounds"] == {"width": 400, "height": 32}
            and len(observation["metrics"]["items"]) == 5,
        "targetAndComponentLink": observed["fileReference"] == "0vGWSRoLxBiVPXiZ8xJAX9"
            and observed["pageId"] == "205:2" and main["id"] == "205:16"
            and main["type"] == "COMPONENT" and instance["type"] == "INSTANCE"
            and instance["mainComponentId"] == main["id"],
        "fiveNativeCells": (main["width"], main["height"]) == (400, 32)
            and len(cells) == 5 and all(c["type"] == "FRAME" for c in cells)
            and [(c["x"], c["y"], c["width"], c["height"], c["cornerRadius"])
                 for c in cells] == [(x, 0, 32, 32, 4) for x in (0, 36, 72, 108, 144)],
        "sourceColorsBound": all(rgb(c["fills"][0]) == (255, 255, 255)
            and "boundVariables" in c["fills"][0] and "boundVariables" in c["strokes"][0]
            for c in cells)
            and [rgb(c["strokes"][0]) for c in cells] ==
                [(220,222,226), (45,140,240), (220,222,226), (220,222,226), (220,222,226)],
        "editableDefaultFontDigits": [n["characters"] for n in content[1:4]] == ["1", "2", "3"]
            and all(n["type"] == "TEXT" and n["fontName"]["family"] == "Inter"
                and n["fontName"]["style"] == "Regular" and n["fontSize"] == 14
                and n["lineHeight"] == {"unit": "PIXELS", "value": 30} for n in content[1:4]),
        "officialRemixInstances": left["type"] == right["type"] == "COMPONENT"
            and content[0]["type"] == content[4]["type"] == "INSTANCE"
            and content[0]["mainComponentId"] == left["id"]
            and content[4]["mainComponentId"] == right["id"]
            and all(sha(ROOT / "registries/icons/objects" / (icons[key]["svgSha256"] + ".svg"))
                    == icons[key]["svgSha256"] for key in
                    ("remix.arrow-left-s-line", "remix.arrow-right-s-line")),
        "nativeRepeatStable": sha(TASK / "native.png") == sha(TASK / "native-repeat.png"),
        "nativeSvgSemantics": all(s in (TASK / "native.svg").read_text(encoding="utf-8")
                for s in ('width="400"', 'height="32"', '#2D8CF0', '#DCDEE2')),
    }
    with Image.open(TASK / "native.png") as image:
        checks["nativeRasterSize"] = image.size == (400, 32)
    status = "CANDIDATE_REVIEW" if all(checks.values()) else "FAIL"
    return {"scope": "figma-only-pagination-candidate", "status": status,
            "logicalComponentId": source["logicalComponentId"], "componentType": "Pagination",
            "componentIrSha256": sha(SOURCE / "component_ir.json"),
            "fileReference": observed["fileReference"], "pageReference": observed["pageId"],
            "componentId": main["id"], "instanceId": instance["id"],
            "iconComponentIds": [left["id"], right["id"]], "checks": checks,
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
