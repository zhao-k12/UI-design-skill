"""Admit source-exact Remix icon masters in the replacement Penpot file."""
import base64
import hashlib
import io
import json
from pathlib import Path

from PIL import Image

from adapters.penpot.icon_precision import validate_approved_icon_encoding
from adapters.penpot.icon_raster_diagnostic import observe_pixels
from adapters.penpot.icons import prepare_icons
from validators.ui_ir import ROOT

BASE = ROOT / "adapters/penpot/metadata/icons-native-v02"
OLD = ROOT / "adapters/penpot/metadata/icons-native-v1"
FILE = "57949053-620f-8001-8008-c804c8d61529"
PAGE = "11686d7e-2c06-8039-8008-c9829eb3f7c3"
MASTER_IDS = {
    "remix.settings-3-line": ("11686d7e-2c06-8039-8008-c982c49f20aa", "11686d7e-2c06-8039-8008-c982c49e16bd"),
    "remix.download-line": ("11686d7e-2c06-8039-8008-c982c4af394f", "11686d7e-2c06-8039-8008-c982c4aea0db"),
}
INSTANCE_IDS = {
    "remix.settings-3-line": "11686d7e-2c06-8039-8008-c98599071f24",
    "remix.download-line": "11686d7e-2c06-8039-8008-c985a829f30a",
}
REPORT = BASE / "gate-report.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_instance_qa():
    capture_path, repeat_path = BASE / "instance-capture.json", BASE / "instance-repeat.json"
    capture, repeat = load(capture_path), load(repeat_path)
    if (capture != repeat or capture["status"] != "CAPTURED" or capture["fileId"] != FILE
            or capture["pageId"] != PAGE or {row["iconId"] for row in capture["instances"]} != set(INSTANCE_IDS)):
        raise ValueError("Penpot V0.2 icon instances are not repeatably captured")
    rows = []
    for item in capture["instances"]:
        icon_id = item["iconId"]
        if item["instanceId"] != INSTANCE_IDS[icon_id] or item["componentId"] != MASTER_IDS[icon_id][0]:
            raise ValueError("Penpot V0.2 icon instance lost its master reference")
        png = base64.b64decode(item["pngBase64"], validate=True)
        with Image.open(OLD / f"{icon_id}.source.png") as source_png, Image.open(io.BytesIO(png)) as native, Image.open(OLD / f"{icon_id}.native.png") as vector:
            raster = observe_pixels(source_png, native, vector)
        if not raster["proposedEvidenceConditionsMet"]:
            raise ValueError("Penpot V0.2 icon instance raster gate failed")
        rows.append({"iconId": icon_id, "instanceReference": item["instanceId"],
                     "componentReference": item["componentId"], "nativePngSha256": hashlib.sha256(png).hexdigest(),
                     "changedPixels": raster["changedPixels"],
                     "changedPixelsOutsideVerifiedEdgeBand": raster["changedPixelsOutsideVerifiedEdgeBand"],
                     "inkRegionBoundsExact": raster["inkRegionBoundsExact"], "status": "PASS"})
    return {"status": "PASS", "fileReference": FILE, "pageReference": PAGE,
            "repeatExportBytesExact": True, "results": rows}


def build_gate():
    capture_path, repeat_path = BASE / "native-capture.json", BASE / "native-repeat.json"
    capture, repeat = load(capture_path), load(repeat_path)
    if capture != repeat or capture["status"] != "CAPTURED" or capture["fileReference"] != FILE or capture["pageReference"] != PAGE:
        raise ValueError("Penpot V0.2 independent icon capture mismatch")
    source = prepare_icons(FILE, PAGE)
    old = load(OLD / "gate-report.json")
    if old["status"] != "PASS" or old["registrySha256"] != source["registrySha256"] or old["sourceVersion"] != source["sourceVersion"]:
        raise ValueError("Approved Remix source baseline changed")
    if {item["iconId"] for item in capture["icons"]} != set(MASTER_IDS):
        raise ValueError("Penpot V0.2 icon inventory mismatch")
    rows = []
    for source_icon in source["icons"]:
        icon_id = source_icon["iconId"]
        item = next(item for item in capture["icons"] if item["iconId"] == icon_id)
        old_row = next(item for item in old["results"] if item["iconId"] == icon_id)
        component_id, main_id = MASTER_IDS[icon_id]
        if (item["componentId"], item["mainId"]) != (component_id, main_id):
            raise ValueError("Penpot V0.2 icon identity mismatch")
        nodes = item["nodes"]
        if ([node["type"] for node in nodes] != ["board", "group", "rectangle", "path"]
                or nodes[0]["id"] != main_id or any(node["width"] != 24 or node["height"] != 24 for node in nodes[:3])
                or any(node["fills"] or node["strokes"] for node in nodes[:3])
                or len(nodes[3]["fills"]) != 1
                or nodes[3]["fills"][0]["fillColor"] != "#000000" or nodes[3]["fills"][0]["fillOpacity"] != 1
                or nodes[3]["strokes"]):
            raise ValueError("Penpot V0.2 icon master structure changed")
        encoding = validate_approved_icon_encoding(icon_id, source_icon["svg"].encode("utf-8"), nodes[3]["d"])
        native_png = base64.b64decode(item["nativePngBase64"], validate=True)
        native_svg = base64.b64decode(item["nativeSvgBase64"], validate=True)
        png_sha = hashlib.sha256(native_png).hexdigest()
        if png_sha != old_row["nativePngSha256"] or not native_svg.startswith(b"<svg"):
            raise ValueError("Penpot V0.2 native export differs from approved master")
        with Image.open(OLD / f"{icon_id}.source.png") as source_png, Image.open(io.BytesIO(native_png)) as native, Image.open(OLD / f"{icon_id}.native.png") as vector:
            raster = observe_pixels(source_png, native, vector)
        if not raster["proposedEvidenceConditionsMet"]:
            raise ValueError("Penpot V0.2 icon raster gate failed")
        rows.append({"iconId": icon_id, "componentReference": component_id, "mainReference": main_id,
                     "sourceSvgSha256": source_icon["svgSha256"], "nativePngSha256": png_sha,
                     "sourceFloat32EncodingExact": encoding["sourceFloat32EncodingExact"],
                     "changedPixels": raster["changedPixels"],
                     "changedPixelsOutsideVerifiedEdgeBand": raster["changedPixelsOutsideVerifiedEdgeBand"],
                     "inkRegionBoundsExact": raster["inkRegionBoundsExact"],
                     "inkAndVoidRegionCountsExact": raster["inkAndVoidRegionCountsExact"],
                     "independentNativePngBytesExact": True, "status": "PASS"})
    instance_qa = build_instance_qa()
    return {"status": "PASS", "scope": "v02-penpot-native-icon-master-admission",
            "platform": "penpot", "fileReference": FILE, "pageReference": PAGE,
            "registrySha256": source["registrySha256"], "sourceVersion": source["sourceVersion"],
            "fileRevision": capture["fileRevision"], "nativeExecution": "PASS",
            "actualInstanceAcceptance": instance_qa["status"], "instanceResults": instance_qa["results"],
            "results": rows,
            "proofFiles": [{"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path)}
                           for path in (capture_path, repeat_path, BASE / "instance-capture.json",
                                        BASE / "instance-repeat.json", OLD / "gate-report.json")]}


def verify_binding(icon_id, binding, file_reference, registry_sha):
    if (binding.get("fidelityReportPath") != REPORT.relative_to(ROOT).as_posix()
            or binding.get("fidelityReportSha256") != sha(REPORT)):
        raise ValueError("Penpot V0.2 icon binding is not tied to its gate")
    report = load(REPORT)
    if report != build_gate() or report["fileReference"] != file_reference or report["registrySha256"] != registry_sha:
        raise ValueError("Penpot V0.2 icon gate changed")
    row = next((row for row in report["results"] if row["iconId"] == icon_id), None)
    if not row or row["componentReference"] != binding.get("componentReference") or row["sourceSvgSha256"] != binding.get("svgSha256"):
        raise ValueError("Penpot V0.2 icon binding identity mismatch")
    return row
