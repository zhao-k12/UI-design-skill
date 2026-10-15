"""Audit fixed two-tab Figma candidate against official runtime source."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

from validators.component_ir import verify_artifacts
from validators.ui_ir import ROOT


SOURCE = ROOT / "artifacts/task-076/tabs-source"
TASK = ROOT / "artifacts/task-077/figma"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgb(paint):
    return tuple(round(paint["color"][c] * 255) for c in ("r", "g", "b"))


def audit(observed):
    source = read(SOURCE / "component_ir.json")["components"][0]
    metrics = read(SOURCE / "tabs-observation.json")["metrics"]
    main,bar,divider,row,tab1,label1,tab2,label2,ink,pane,content,instance = observed["nodes"]
    checks = {
        "officialSourceVerified": verify_artifacts(SOURCE, expected_types={"Tabs"}) == []
            and source["logicalComponentId"] == "navigation.tabs.line.overview"
            and source["rootBounds"] == {"width": 320, "height": 73}
            and [x["text"] for x in metrics["tabs"]] == ["概览", "详情"],
        "targetAndComponentLink": observed["fileReference"] == "0vGWSRoLxBiVPXiZ8xJAX9"
            and observed["pageId"] == "207:2" and main["id"] == "207:3"
            and main["type"] == "COMPONENT" and instance["type"] == "INSTANCE"
            and instance["mainComponentId"] == main["id"],
        "nativeGeometry": (main["width"],main["height"]) == (320,73)
            and (bar["x"],bar["y"],bar["width"],bar["height"]) == (0,0,320,36)
            and (divider["x"],divider["y"],divider["width"],divider["height"]) == (0,35,320,1)
            and (tab1["x"],tab1["y"],tab1["width"],tab1["height"]) == (0,0,60,37)
            and (tab2["x"],tab2["y"],tab2["width"],tab2["height"]) == (76,0,60,37)
            and (ink["x"],ink["y"],ink["width"],ink["height"]) == (0,34,60,2)
            and (pane["x"],pane["y"],pane["width"],pane["height"]) == (0,52,320,21),
        "sourceColorsBound": rgb(divider["fills"][0]) == (220,222,226)
            and rgb(ink["fills"][0]) == rgb(label1["fills"][0]) == (45,140,240)
            and rgb(label2["fills"][0]) == rgb(content["fills"][0]) == (81,90,110)
            and all("boundVariables" in n["fills"][0] for n in
                (divider,ink,label1,label2,content)),
        "editableDefaultFontText": [label1["characters"],label2["characters"],content["characters"]]
            == ["概览","详情","概览内容"]
            and all(n["type"] == "TEXT" and n["fontName"]["family"] == "Inter"
                and n["fontName"]["style"] == "Regular" and n["fontSize"] == 14
                and n["lineHeight"] == {"unit":"PIXELS","value":21}
                for n in (label1,label2,content)),
        "selectedPaneOnly": not any(n.get("characters") == "详情内容" for n in observed["nodes"]),
        "nativeRepeatStable": sha(TASK / "native.png") == sha(TASK / "native-repeat.png"),
        "nativeSvgSemantics": all(s in (TASK / "native.svg").read_text(encoding="utf-8")
            for s in ('width="320"','height="73"','#2D8CF0','#DCDEE2','#515A6E')),
    }
    with Image.open(TASK / "native.png") as image:
        checks["nativeRasterSize"] = image.size == (320,73)
    status = "CANDIDATE_REVIEW" if all(checks.values()) else "FAIL"
    return {"scope":"figma-only-tabs-candidate","status":status,
            "logicalComponentId":source["logicalComponentId"],"componentType":"Tabs",
            "componentIrSha256":sha(SOURCE / "component_ir.json"),
            "fileReference":observed["fileReference"],"pageReference":observed["pageId"],
            "componentId":main["id"],"instanceId":instance["id"],"checks":checks,
            "evidenceSha256":{name:sha(TASK / name) for name in
                ("native-read.json","native.png","native-repeat.png","native.svg")},
            "admissionEligible":False,"dualPlatformFidelity":"DEFERRED",
            "registryAdmission":"DEFERRED_PENPOT","releaseReady":False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    output=args.output.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        parser.error("Output must stay in artifacts")
    result=audit(read(TASK / "native-read.json"))
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"checks":result["checks"]},ensure_ascii=False))
    return 0 if result["status"] == "CANDIDATE_REVIEW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
