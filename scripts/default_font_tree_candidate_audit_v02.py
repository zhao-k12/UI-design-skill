"""Audit fixed expanded Tree Figma candidate against official runtime source."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT


SOURCE = ROOT / "artifacts/task-079/tree-source"
TASK = ROOT / "artifacts/task-080/figma"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgb(paint):
    return tuple(round(paint["color"][c] * 255) for c in ("r", "g", "b"))


def audit(observed):
    source = read(SOURCE / "component_ir.json")["components"][0]
    metrics = read(SOURCE / "tree-observation.json")["metrics"]
    main, parent, title, child1, label1, child2, label2, arrow, instance, arrow_master = observed["nodes"]
    icon_registry = read(ROOT / "registries/icons/snapshots/550580a4fc9bb3bb7901fe2271e3ade0e73f6da7cb49872249bfc2e091fac11a/registry.json")
    checks = {
        "officialSourceVerified": verify_artifacts(SOURCE, expected_types={"Tree"}) == []
            and source["logicalComponentId"] == "navigation.tree.expanded.departments"
            and source["rootBounds"] == {"width": 240, "height": 79}
            and [x["text"] for x in metrics["titles"]] == ["部门", "研发部", "设计部"],
        "targetAndComponentLink": observed["fileReference"] == "0vGWSRoLxBiVPXiZ8xJAX9"
            and observed["pageId"] == "210:2" and main["id"] == "210:6"
            and main["type"] == "COMPONENT" and instance["type"] == "INSTANCE"
            and instance["mainComponentId"] == main["id"],
        "nativeGeometry": (main["width"], main["height"], main["layoutMode"], main["itemSpacing"])
            == (240, 79, "VERTICAL", 8)
            and [(n["x"], n["y"], n["width"], n["height"]) for n in (parent, child1, child2)]
            == [(0, 0, 240, 21), (0, 29, 240, 21), (0, 58, 240, 21)]
            and [(n["x"], n["y"], n["height"]) for n in (title, label1, label2)]
            == [(16, 0, 21), (34, 0, 21), (34, 0, 21)],
        "editableDefaultFontText": [n["characters"] for n in (title, label1, label2)]
            == ["部门", "研发部", "设计部"]
            and all(n["type"] == "TEXT" and n["fontName"]["family"] == "Inter"
                and n["fontName"]["style"] == "Regular" and n["fontSize"] == 14
                and n["lineHeight"] == {"unit": "PIXELS", "value": 21}
                for n in (title, label1, label2)),
        "sourceColorBound": all(rgb(n["fills"][0]) == (81, 90, 110)
            and n["fills"][0]["boundVariables"]["color"]["id"] == "VariableID:205:9"
            for n in (title, label1, label2)),
        "officialRemixArrowLinked": icon_registry["icons"]["remix.arrow-right-s-line"]["svgSha256"]
            == "2c579a4dbaf25e19a128d71e04f4cf43b19ad2487a0076ff7e7e5a94c9b3e013"
            and arrow["type"] == "INSTANCE" and arrow["mainComponentId"] == arrow_master["id"]
            and (arrow["x"], arrow["y"], arrow["width"], arrow["height"]) == (-3, 1.5, 18, 18),
        "nativeRepeatStable": sha(TASK / "native.png") == sha(TASK / "native-repeat.png"),
        "nativeSvgSemantics": all(s in (TASK / "native.svg").read_text(encoding="utf-8")
            for s in ('width="240"', 'height="79"', '#515A6E')),
    }
    with Image.open(TASK / "native.png") as image:
        checks["nativeRasterSize"] = image.size == (240, 79)
    status = "CANDIDATE_REVIEW" if all(checks.values()) else "FAIL"
    return {"scope": "figma-only-tree-candidate", "status": status,
            "logicalComponentId": source["logicalComponentId"], "componentType": "Tree",
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
