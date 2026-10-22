"""Bind HTML export inputs to the reviewed prototype and staged artifacts."""
from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validators.ui_ir import load_json, validate_document
from workflow_v03.core import fingerprint


def validate(core: Path, staged: Path, source: Path) -> None:
    tree = load_json(staged / "page_content_tree.json")
    skeleton = load_json(staged / "annotated_skeleton_page.json")
    default = load_json(staged / "default_component_page_ui_ir.json")
    final = load_json(core / "final_ui_ir.json")
    fill = load_json(staged / "prototype_content_fill.json")
    tree_qa = load_json(staged / "page_content_tree_qa.json")
    if tree_qa.get("status") != "PASS" or tree_qa.get("contentTreeSha256") != fingerprint(tree):
        raise ValueError("Reviewed content Tree has changed")
    if skeleton.get("contentTreeSha256") != fingerprint(tree):
        raise ValueError("Skeleton belongs to another content Tree")
    if fill.get("defaultPageSha256") != fingerprint(default) or fill.get("finalPageSha256") != fingerprint(final):
        raise ValueError("Default/final page differs from staged content-fill contract")
    if validate_document(default) or validate_document(final):
        raise ValueError("Invalid UI-IR document")
    for item in tree["sourceFiles"]:
        path = (source / item["path"]).resolve()
        if not path.is_relative_to(source.resolve()) or sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("Prototype source changed: " + item["path"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-dir", type=Path, required=True)
    parser.add_argument("--staged-dir", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    args = parser.parse_args()
    validate(args.core_dir, args.staged_dir, args.source_dir)
    print("HTML_INPUTS_VALID")


if __name__ == "__main__":
    main()
