"""Validate the UI-IR contract, not component availability or design quality."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "ui-ir.schema.json"


def load_json(path: Path) -> object:
    def reject_constant(value: str) -> None:
        raise ValueError(f"Non-JSON numeric constant: {value}")

    def unique_object(pairs: list[tuple[str, object]]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(path.read_text(encoding="utf-8-sig"), parse_constant=reject_constant, object_pairs_hook=unique_object)


def pointer(parts) -> str:
    return "/" + "/".join(str(part).replace("~", "~0").replace("/", "~1") for part in parts)


def validate_document(document: object) -> list[dict[str, str]]:
    """Return deterministic diagnostics; an empty list means contract-valid only."""
    issues = []
    def json_types(value: object) -> bool:
        if type(value) in (str, int, float, bool, type(None)):
            return True
        if type(value) is list:
            return all(json_types(child) for child in value)
        if type(value) is dict:
            return all(type(key) is str and json_types(child) for key, child in value.items())
        return False

    if not json_types(document):
        return [{"code": "invalid_json", "path": "/", "message": "Expected JSON types with string object keys"}]
    try:
        json.dumps(document, allow_nan=False)
    except (ValueError, TypeError) as exc:
        return [{"code": "invalid_json", "path": "/", "message": str(exc)}]

    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(document))
    # Node types select their own conditional branch, preserving precise paths.
    for error in errors:
        issues.append({"code": "schema_violation", "path": pointer(error.absolute_path), "message": error.message})

    def platform_keys(value: object, path: tuple = ()) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if isinstance(key, str) and any(platform in key.lower() for platform in ("figma", "penpot")):
                    issues.append({"code": "platform_field", "path": pointer((*path, key)), "message": "Platform metadata must remain outside UI-IR"})
                platform_keys(child, (*path, key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                platform_keys(child, (*path, index))

    platform_keys(document)
    if not errors:
        for index, resource in enumerate(document.get('resourceIssues', [])):
            issues.append({'code': resource['code'], 'path': '/resourceIssues/'+str(index),
                           'message': resource['message']})
        seen: dict[str, str] = {}

        def visit(node: dict, path: tuple) -> None:
            node_id = node["id"]
            location = pointer(path)
            if node_id in seen:
                issues.append({"code": "duplicate_node_id", "path": location + "/id", "message": f"{node_id} already used at {seen[node_id]}"})
            else:
                seen[node_id] = location
            for index, child in enumerate(node.get("children", [])):
                visit(child, (*path, "children", index))
            for slot, children in node.get("slots", {}).items():
                for index, child in enumerate(children):
                    visit(child, (*path, "slots", slot, index))

        for index, page in enumerate(document["pages"]):
            visit(page, ("pages", index))
    return sorted(issues, key=lambda issue: (issue["path"], issue["code"], issue["message"]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", type=Path)
    args = parser.parse_args()
    try:
        issues = validate_document(load_json(args.document))
    except (OSError, ValueError) as exc:
        issues = [{"code": "invalid_input", "path": "/", "message": str(exc)}]
    print(json.dumps({"scope": "ui_ir_contract", "status": "FAIL" if issues else "PASS", "issues": issues}, ensure_ascii=False, indent=2))
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
