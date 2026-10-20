"""Audit the independently approved compact-search prototype and native Figma page."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.audit_adapter_byte_lock_figma import audit as audit_native
from core.prototype.parser import parse
from validators.structure.gate import builder, check
from validators.ui_ir import load_json


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def audit(root=ROOT, *, native_dir=None):
    root = Path(root)
    source = root / "examples/user-management-compact-search"
    task = root / "artifacts/task-108"
    native_dir = Path(native_dir) if native_dir else task / "figma"
    issues = []
    try:
        observations = load_json(source / "observations.json")
        analysis = parse(observations, source)
        review = load_json(source / "review.json")
        structure = check(analysis, builder.build(analysis), source, review)
        if structure["status"] != "PASS":
            issues.append("semantic_review_or_structure_invalid")
        manifest = load_json(source / "input-manifest.json")
        if (manifest["status"] != "READY_FOR_PREFLIGHT"
                or any(digest(source / name) != expected for name, expected in manifest["files"].items())):
            issues.append("input_package_hash_mismatch")
        old_source = root / "examples/acceptance-prototype-v02/prototype.txt"
        if digest(source / "prototype.txt") == digest(old_source):
            issues.append("prototype_not_independent")
        plan = load_json(source / "layout-plan.json")
        if (plan["sectionConfigs"]["query"].get("buttonAlignment") != "end"
                or plan["sectionConfigs"]["query"].get("inlineGrid") is True):
            issues.append("new_layout_plan_invalid")
        run = task / "run-v5"
        qa = load_json(run / "qa_report.json")
        if (qa["status"] != "PASS" or qa["readyForAdapter"] is not True
                or qa["semanticItemCount"] != 7 or qa["instanceCount"] != 4
                or qa["iconCount"] != 1 or qa["layoutRepeatable"] is not True
                or qa["adapterPreflights"] != {"figma": "PASS", "penpot": "PASS"}):
            issues.append("pipeline_or_preflight_invalid")
        old_qa = load_json(root / "artifacts/task-106/run/qa_report.json")
        if qa["uiIrSha256"] == old_qa["uiIrSha256"]:
            issues.append("ui_ir_not_independent")
        native = audit_native(run, task / "figma-execution", native_dir)
        if native["status"] != "PASS" or native["expectedInstanceCount"] != 5:
            issues.append("figma_native_audit_invalid")
        layout = {row["name"]: row for row in load_json(native_dir / "layout-read.json")}
        fields = layout["layout.group.1.fields"]
        row = layout["layout.group.1.buttons"]
        input_node = layout["layout.item.1.0.instance"]
        select_node = layout["layout.item.1.1.instance"]
        button = layout["layout.item.1.2.instance"]
        if (any(item["id"] is None for item in (fields, row, input_node, select_node, button))
                or input_node["y"] != select_node["y"]
                or not row["y"] >= fields["y"] + fields["height"]
                or button["y"] != row["y"]
                or button["x"] + button["width"] != row["x"] + row["width"]):
            issues.append("native_compact_query_layout_mismatch")
        native_read = load_json(native_dir / "native-read.json")
        visible = [row["characters"] for row in native_read["texts"]]
        if any(text in visible for text in ("范围", "导出", "操作", "查看用户信息")):
            issues.append("removed_content_leaked_into_new_page")
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        native = {}
        issues.append("invalid_or_missing_evidence: " + str(exc))
    return {"scope": "v02-independent-compact-search-figma", "status": "PASS" if not issues else "FAIL",
            "releaseReady": False, "prototypeSha256": digest(source / "prototype.txt"),
            "figmaPageReference": native.get("pageReference"),
            "figmaNativePngSha256": native.get("nativePngSha256"),
            "nativeInstanceCount": native.get("actualInstanceCount"),
            "issues": issues}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        parser.error("Output must stay in artifacts")
    result = audit()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
