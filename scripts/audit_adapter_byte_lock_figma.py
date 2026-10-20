"""Read-only Figma native readback audit for a versioned Adapter execution intent."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from adapters.byte_lock import verify_execution_script
from validators.ui_ir import load_json


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def walk(node):
    yield node
    for child in node.get("children", []):
        yield from walk(child)


def png_size(path):
    header = Path(path).read_bytes()[:24]
    if len(header) != 24 or header[:16] != b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR":
        raise ValueError("Invalid native PNG")
    return struct.unpack(">II", header[16:24])


def audit(run_dir, execution_dir, native_dir):
    run_dir, execution_dir, native_dir = map(Path, (run_dir, execution_dir, native_dir))
    issues = []
    lock = load_json(run_dir / "adapter-execution-lock.json")
    plans = {"figma": load_json(run_dir / "figma_preflight.json")["plan"]}
    intent = load_json(execution_dir / "execution-intent.json")
    script = (execution_dir / "execution.js").read_text(encoding="utf-8")
    page_index = intent["pageIndex"]
    try:
        receipt = verify_execution_script(lock, plans, "figma", script, page_index,
                                          page_reference=intent["pageReference"])
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        receipt = None
        issues.append("adapter_execution_lock_invalid: " + str(exc))
    if receipt and (any(intent.get(key) != value for key, value in receipt.items())
                    or intent.get("lockSha256") != digest(run_dir / "adapter-execution-lock.json")
                    or intent.get("fileReference") != plans["figma"]["fileReference"]
                    or intent.get("uiIrSha256") != plans["figma"]["uiIrSha256"]):
        issues.append("execution_intent_mismatch")
    plan = plans["figma"]
    page = plan["pages"][page_index]
    native = load_json(native_dir / "native-read.json")
    root = native["root"]
    result_path = execution_dir / "execution-result.json"
    if result_path.is_file():
        result = load_json(result_path)
        expected_ids = {node["id"] for node in walk(page)}
        evidence = result.get("evidence", [])
        node_map = result.get("nodeMap", {})
        if (result.get("status") != "PASS" or result.get("scope") != "figma_native_translation"
                or result.get("adapterVersion") != plan["adapterVersion"]
                or result.get("uiIrSha256") != plan["uiIrSha256"]
                or result.get("tokensSha256") != plan["tokensSha256"]
                or result.get("componentsSha256") != plan["componentsSha256"]
                or result.get("iconsSha256") != plan["iconsSha256"]
                or result.get("pageReference") != intent["pageReference"]
                or result.get("rootReference") != root["id"]
                or node_map.get(page["id"]) != root["id"]
                or set(node_map) != expected_ids
                or len(evidence) != len(expected_ids)
                or {row.get("uiIrId") for row in evidence} != expected_ids
                or any(node_map.get(row.get("uiIrId")) != row.get("nodeId") for row in evidence)
                or root["id"] not in result.get("createdNodeIds", [])):
            issues.append("native_execution_receipt_mismatch")
    if native["fileReference"] != plan["fileReference"] or native["page"]["id"] != intent["pageReference"]:
        issues.append("native_target_mismatch")
    if (root["name"] != f"UI-IR/{plan['documentId']}/{page['id']}"
            or root["width"] != page["layout"]["width"]["value"]
            or root["height"] != page["layout"]["height"]["value"]):
        issues.append("native_root_mismatch")
    expected_instances = {node["id"]: node for node in walk(page)
                          if node["type"] in ("ComponentInstance", "IconInstance")}
    actual_instances = {row["name"]: row for row in native["instances"]}
    if set(expected_instances) != set(actual_instances) or len(actual_instances) != len(native["instances"]):
        issues.append("native_instance_inventory_mismatch")
    else:
        for name, expected in expected_instances.items():
            actual = actual_instances[name]
            if (actual["mainComponentId"] != expected["componentReference"]
                    or actual["width"] != expected["layout"]["width"]["value"]
                    or actual["height"] != expected["layout"]["height"]["value"]):
                issues.append("native_instance_binding_mismatch: " + name)
    actual_texts = {row["name"]: row for row in native["texts"]}
    for expected in (node for node in walk(page) if node["type"] == "Text"):
        actual = actual_texts.get(expected["id"])
        if not actual or actual["characters"] != expected["text"] or \
                actual["fontFamily"] != expected["fontName"]["family"]:
            issues.append("native_text_mismatch: " + expected["id"])
    png = native_dir / "native.png"
    repeat = native_dir / "native-repeat.png"
    if digest(png) != digest(repeat) or png_size(png) != (root["width"], root["height"]):
        issues.append("native_png_mismatch")
    return {"scope": "v02-figma-adapter-byte-lock-native-readback",
            "status": "PASS" if not issues else "FAIL", "releaseReady": False,
            "nativeExecution": "OBSERVED_FROM_FIGMA_TOOL",
            "fileReference": plan["fileReference"], "pageReference": native["page"]["id"],
            "rootReference": root["id"], "rootSize": [root["width"], root["height"]],
            "expectedInstanceCount": len(expected_instances),
            "actualInstanceCount": len(native["instances"]),
            "textNodeCount": len(native["texts"]),
            "executionScriptSha256": digest(execution_dir / "execution.js"),
            "executionReceiptPersisted": result_path.is_file(),
            "executionResultSha256": digest(result_path) if result_path.is_file() else None,
            "nativeReadSha256": digest(native_dir / "native-read.json"),
            "nativePngSha256": digest(png), "nativeRepeatSha256": digest(repeat),
            "issues": issues}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("run-dir", "execution-dir", "native-dir", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        parser.error("Output must stay in artifacts")
    result = audit(args.run_dir, args.execution_dir, args.native_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "releaseReady", "expectedInstanceCount",
                                                "actualInstanceCount", "textNodeCount", "issues")},
                     ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
