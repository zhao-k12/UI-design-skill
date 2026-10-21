"""Advance the staged Figma workflow only after each independent native QA."""
import argparse
from hashlib import sha256
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from workflow_v03.figma import component_script, fill_script, skeleton_script
from workflow_v03.core import write
from workflow_v03.iview_conformance import audit as audit_iview
from workflow_v03.layout_quality import audit as audit_layout_quality
from workflow_v03.qa import (audit_content_tree, audit_skeleton, audit_default_page,
                                      audit_filled_content, audit_prototype_proofread)
from validators.ui_ir import load_json


def _save_once(path, data):
    encoded = data if isinstance(data, str) else None
    if path.exists():
        if (path.read_text(encoding="utf-8") if encoded is not None else load_json(path)) != data:
            raise ValueError("Stage artifact changed; use a new revision: " + str(path))
        return
    if encoded is None:
        write(path, data)
    else:
        path.write_text(data, encoding="utf-8", newline="\n")


def advance(directory, stage, *, file_reference=None, revision=None,
            execution=None, readback=None, review=None, native_png=None,
            tokens=None, catalog=None, intent=None, plan=None,
            layout_tree=None, layout_report=None):
    directory = Path(directory).resolve()
    if not directory.is_relative_to((ROOT / "artifacts").resolve()) or not directory.is_dir():
        raise ValueError("Use a prepared workflow directory under artifacts")
    get = lambda name: load_json(directory / name)
    if stage in {"skeleton-script", "skeleton-qa", "component-script", "component-qa",
                 "fill-script", "fill-qa", "proofread"}:
        gate = directory / "iview_conformance_qa.json"
        if not gate.is_file() or load_json(gate).get("status") != "PASS":
            raise ValueError("iView design conformance must pass before native construction")
        gate = directory / "layout_quality_qa.json"
        if not gate.is_file() or load_json(gate).get("status") != "PASS":
            raise ValueError("Normative layout intent and computed geometry must pass before native construction")
    if stage == "tree-qa":
        result = audit_content_tree(get("page_content_tree.json"), load_json(review))
        _save_once(directory / "page_content_tree_review.json", result)
        return result
    if stage == "layout-qa":
        if get("page_content_tree_review.json").get("status") != "PASS":
            raise ValueError("Reviewed content Tree is required before layout quality audit")
        if any(path is None for path in (intent, plan, layout_tree, layout_report, tokens, catalog)):
            raise ValueError("Model layout intent, Core layout evidence, tokens and catalog are required")
        decision = load_json(intent)
        result = audit_layout_quality(get("page_content_tree.json"), load_json(plan),
            load_json(layout_tree), load_json(layout_report), load_json(catalog),
            load_json(tokens),
            load_json(ROOT / "registries/design-standards/list-page-layout-v0.3.2.json"),
            decision)
        _save_once(directory / "layout_intent.json", decision)
        _save_once(directory / "layout_quality_qa.json", result)
        return result
    if stage == "iview-qa":
        if get("page_content_tree_review.json").get("status") != "PASS":
            raise ValueError("Reviewed content Tree is required before iView audit")
        if tokens is None or catalog is None:
            raise ValueError("Explicit token registry and component catalog are required")
        result = audit_iview(get("page_content_tree.json"),
            get("default_component_page_ui_ir.json"), load_json(tokens), load_json(catalog),
            load_json(ROOT / "registries/design-standards/iview-plus-1.3.24.json"),
            load_json(ROOT / "component-builder/source-reader/source-lock.json"))
        _save_once(directory / "iview_conformance_qa.json", result)
        return result
    if stage == "skeleton-script":
        tree_qa = get("page_content_tree_review.json")
        if (tree_qa.get("status") != "PASS" or
            tree_qa.get("contentTreeSha256") != get("annotated_skeleton_page.json")["contentTreeSha256"]):
            raise ValueError("Reviewed complete content Tree is required before skeleton construction")
        script = skeleton_script(get("annotated_skeleton_page.json"), file_reference, revision)
        _save_once(directory / "figma-skeleton.js", script)
        return {"status": "PREPARED", "scriptSha256": sha256(script.encode("utf-8")).hexdigest()}
    if stage == "skeleton-qa":
        result = audit_skeleton(get("annotated_skeleton_page.json"), load_json(execution),
                                load_json(readback), load_json(review))
        _save_once(directory / "annotated_skeleton_native_qa.json", result)
        return result
    if stage == "component-script":
        script, preflight = component_script(get("default_component_page_ui_ir.json"),
            get("annotated_skeleton_page.json"), file_reference, revision,
            get("annotated_skeleton_native_qa.json"))
        _save_once(directory / "figma-default-component-preflight.json", preflight)
        _save_once(directory / "figma-default-component.js", script)
        return {"status": "PREPARED", "scriptSha256": sha256(script.encode("utf-8")).hexdigest()}
    if stage == "component-qa":
        result = audit_default_page(get("default_component_page_ui_ir.json"),
            get("annotated_skeleton_native_qa.json"), load_json(execution), load_json(readback))
        _save_once(directory / "default_component_native_qa.json", result)
        return result
    if stage == "fill-script":
        script = fill_script(get("prototype_content_fill.json"), file_reference,
                             get("default_component_native_qa.json"))
        _save_once(directory / "figma-prototype-content-fill.js", script)
        return {"status": "PREPARED", "scriptSha256": sha256(script.encode("utf-8")).hexdigest()}
    if stage == "fill-qa":
        result = audit_filled_content(get("prototype_content_fill.json"),
            get("default_component_native_qa.json"), load_json(execution), load_json(readback))
        _save_once(directory / "filled_content_native_qa.json", result)
        return result
    if stage == "proofread":
        iview = get("iview_conformance_qa.json")
        layout = get("layout_quality_qa.json")
        if iview.get("status") != "PASS":
            raise ValueError("iView design conformance must pass before delivery")
        if layout.get("status") != "PASS":
            raise ValueError("Normative layout quality must pass before delivery")
        result = audit_prototype_proofread(get("page_content_tree.json"),
            get("filled_content_native_qa.json"), load_json(review), native_png)
        _save_once(directory / "final_prototype_proofread.json", result)
        stages = {"contentTree": get("page_content_tree_review.json")["status"],
                  "normativeLayout": layout["status"],
                  "iviewConformance": iview["status"],
                  "annotatedSkeleton": get("annotated_skeleton_native_qa.json")["status"],
                  "defaultComponentPage": get("default_component_native_qa.json")["status"],
                  "filledContent": get("filled_content_native_qa.json")["status"],
                  "prototypeProofread": result["status"]}
        _save_once(directory / "workflow_final_qa.json",
                   {"version": "0.3.2", "stages": stages,
                    "status": "PASS" if all(value == "PASS" for value in stages.values()) else "FAIL",
                    "deliverable": all(value == "PASS" for value in stages.values()),
                    "pageReference": result["pageReference"]})
        return result
    raise ValueError("Unknown stage")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("stage", choices=("tree-qa", "layout-qa", "iview-qa", "skeleton-script", "skeleton-qa", "component-script",
                                          "component-qa", "fill-script", "fill-qa", "proofread"))
    parser.add_argument("--file-reference")
    parser.add_argument("--revision")
    parser.add_argument("--execution", type=Path)
    parser.add_argument("--readback", type=Path)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--native-png", type=Path)
    parser.add_argument("--tokens", type=Path)
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--intent", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--layout-tree", type=Path)
    parser.add_argument("--layout-report", type=Path)
    args = parser.parse_args()
    try:
        result = advance(args.directory, args.stage, file_reference=args.file_reference,
                         revision=args.revision, execution=args.execution, readback=args.readback,
                         review=args.review, native_png=args.native_png,
                         tokens=args.tokens, catalog=args.catalog,
                         intent=args.intent, plan=args.plan,
                         layout_tree=args.layout_tree, layout_report=args.layout_report)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print(result)
    return 0 if result["status"] in ("PASS", "PREPARED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
