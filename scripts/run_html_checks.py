"""Run the source Tree, layout and iView checks required before HTML export."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from validators.ui_ir import load_json
from workflow_v03.core import write
from workflow_v03.iview_conformance import audit as audit_iview
from workflow_v03.layout_quality import audit as audit_layout
from workflow_v03.qa import audit_content_tree


def save_once(path: Path, value: dict) -> None:
    if path.exists():
        if load_json(path) != value:
            raise ValueError("Check artifact changed; use a new revision: " + str(path))
    else:
        write(path, value)


def run(staged: Path, review: Path, intent: Path, plan: Path,
        layout_tree: Path, layout_report: Path) -> dict:
    staged = staged.resolve()
    if not staged.is_dir() or not staged.is_relative_to((ROOT / "artifacts").resolve()):
        raise ValueError("Use a prepared artifact directory")
    tree = load_json(staged / "page_content_tree.json")
    tree_result = audit_content_tree(tree, load_json(review))
    save_once(staged / "page_content_tree_review.json", tree_result)
    status = {"tree": tree_result["status"]}
    if tree_result["status"] != "PASS":
        return {"status": "FAIL", "checks": status, "issues": tree_result["issues"]}

    tokens = load_json(ROOT / "registries/tokens/v0.2.3/default.json")
    catalog = load_json(ROOT / "registries/components/v0.2.9/catalog.json")
    decision = load_json(intent)
    layout_result = audit_layout(tree, load_json(plan), load_json(layout_tree),
        load_json(layout_report), catalog, tokens,
        load_json(ROOT / "registries/design-standards/list-page-layout-v0.3.2.json"),
        decision)
    save_once(staged / "layout_intent.json", decision)
    save_once(staged / "layout_quality_qa.json", layout_result)
    status["layout"] = layout_result["status"]
    if layout_result["status"] != "PASS":
        return {"status": "FAIL", "checks": status, "issues": layout_result["issues"]}

    iview_result = audit_iview(tree, load_json(staged / "default_component_page_ui_ir.json"),
        tokens, catalog,
        load_json(ROOT / "registries/design-standards/iview-plus-1.3.24.json"),
        load_json(ROOT / "component-builder/source-reader/source-lock.json"),
        delivery_mode="html-official-runtime")
    save_once(staged / "iview_conformance_qa.json", iview_result)
    status["iview"] = iview_result["status"]
    return {"status": "PASS" if iview_result["status"] == "PASS" else "FAIL",
            "checks": status, "issues": iview_result["issues"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged-dir", required=True, type=Path)
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--intent", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--layout-tree", required=True, type=Path)
    parser.add_argument("--layout-report", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = run(args.staged_dir, args.review, args.intent, args.plan,
                     args.layout_tree, args.layout_report)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, str(exc) + "\n")
    print(result)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
