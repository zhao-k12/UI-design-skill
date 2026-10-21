"""Advance the staged Figma workflow only after each independent native QA."""
import argparse
from hashlib import sha256
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from workflow_v03.figma import component_script, fill_script, skeleton_script
from workflow_v03.core import write
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
            execution=None, readback=None, review=None, native_png=None):
    directory = Path(directory).resolve()
    if not directory.is_relative_to((ROOT / "artifacts").resolve()) or not directory.is_dir():
        raise ValueError("Use a prepared workflow directory under artifacts")
    get = lambda name: load_json(directory / name)
    if stage == "tree-qa":
        result = audit_content_tree(get("page_content_tree.json"), load_json(review))
        _save_once(directory / "page_content_tree_review.json", result)
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
        result = audit_prototype_proofread(get("page_content_tree.json"),
            get("filled_content_native_qa.json"), load_json(review), native_png)
        _save_once(directory / "final_prototype_proofread.json", result)
        stages = {"contentTree": get("page_content_tree_review.json")["status"],
                  "annotatedSkeleton": get("annotated_skeleton_native_qa.json")["status"],
                  "defaultComponentPage": get("default_component_native_qa.json")["status"],
                  "filledContent": get("filled_content_native_qa.json")["status"],
                  "prototypeProofread": result["status"]}
        _save_once(directory / "workflow_final_qa.json",
                   {"version": "0.3.0", "stages": stages,
                    "status": "PASS" if all(value == "PASS" for value in stages.values()) else "FAIL",
                    "deliverable": all(value == "PASS" for value in stages.values()),
                    "pageReference": result["pageReference"]})
        return result
    raise ValueError("Unknown stage")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("stage", choices=("tree-qa", "skeleton-script", "skeleton-qa", "component-script",
                                          "component-qa", "fill-script", "fill-qa", "proofread"))
    parser.add_argument("--file-reference")
    parser.add_argument("--revision")
    parser.add_argument("--execution", type=Path)
    parser.add_argument("--readback", type=Path)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--native-png", type=Path)
    args = parser.parse_args()
    try:
        result = advance(args.directory, args.stage, file_reference=args.file_reference,
                         revision=args.revision, execution=args.execution, readback=args.readback,
                         review=args.review, native_png=args.native_png)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print(result)
    return 0 if result["status"] in ("PASS", "PREPARED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
