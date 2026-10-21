"""Evidence-bound, deliberately narrow View UI Plus page conformance checks.

This gate checks known blocking rules. PASS is not a claim that every View UI
Plus design guideline has been audited.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


def _walk(node):
    yield node
    for child in node.get("children", []):
        yield from _walk(child)


def audit(tree, final_document, tokens, catalog, standard, source_lock):
    issues = []
    source = standard["source"]
    if (source_lock.get("packageVersion") != standard["version"] or
        source_lock.get("gitCommit") != source["commit"] or
        source_lock.get("files", {}).get(source["path"]) != source["sha256"]):
        issues.append({"code": "iview_source_lock_mismatch"})

    values = tokens["tokens"]
    expected_colors = {
        "color.primary": (standard["colors"]["primary"],),
        "color.text": (standard["colors"]["text"],),
        "color.page": (standard["colors"]["body"], standard["colors"]["layoutBody"]),
        "color.surface": (standard["colors"]["surface"],),
        "color.border": (standard["colors"]["border"],),
    }
    for token_id, allowed in expected_colors.items():
        actual = values.get(token_id, {}).get("value")
        if not isinstance(actual, str) or actual.lower() not in {v.lower() for v in allowed}:
            issues.append({"code": "iview_token_mismatch", "token": token_id,
                           "actual": actual, "expected": list(allowed)})

    nodes = [node for page in final_document["pages"] for node in _walk(page)]
    for section in tree["sections"]:
        for item in section["items"]:
            headers = item["sourceContent"].get("props", {}).get("headers", [])
            if not headers or item["component"]["type"] != "Table":
                continue
            source_id = item["id"]
            component_id = item["component"]["id"]
            scope = catalog.get("components", {}).get(component_id, {}).get("contentScope", {})
            native = [node for node in nodes if node["type"] == "ComponentInstance" and
                      node.get("componentId") == component_id and source_id in node.get("sourceIds", [])]
            if len(native) != 1 or scope.get("showHeader") is not True:
                issues.append({"code": "iview_native_table_header_required",
                               "sourceId": source_id, "componentId": component_id})
            if scope.get("showHeader") is True and [c.get("title") for c in scope.get("columns", [])] != [h["text"] for h in headers]:
                issues.append({"code": "iview_table_header_content_mismatch", "sourceId": source_id})
            header_prefix = native[0]["id"].rsplit(".instance", 1)[0] + ".header" if native else None
            if header_prefix and any(node["id"].startswith(header_prefix) for node in nodes):
                issues.append({"code": "iview_synthetic_table_header", "sourceId": source_id})

    return {"status": "PASS" if not issues else "FAIL", "scope": "known-blocking-iview-rules",
            "standard": standard["standard"], "standardVersion": standard["version"],
            "standardSha256": sha256(json.dumps(standard, sort_keys=True, ensure_ascii=False,
                                              separators=(",", ":")).encode("utf-8")).hexdigest(),
            "checked": ["official-source-lock", "page-color-tokens", "native-table-header"],
            "issues": issues}


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", type=Path, required=True)
    parser.add_argument("--ui-ir", type=Path, required=True)
    parser.add_argument("--tokens", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    read = lambda path: json.loads(path.read_text(encoding="utf-8"))
    result = audit(read(args.tree), read(args.ui_ir), read(args.tokens), read(args.catalog),
                   read(root / "registries/design-standards/iview-plus-1.3.24.json"),
                   read(root / "component-builder/source-reader/source-lock.json"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8", newline="\n")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
