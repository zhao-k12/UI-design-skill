"""Cheap source/resource checks before the full Core run or any Figma write.

This is an early diagnostic, not a substitute for Core, iView or native QA.
"""
from __future__ import annotations

from importlib import import_module
from pathlib import Path

from validators.ui_ir import load_json

ROOT = Path(__file__).resolve().parents[1]


def table_capability_issues(scope, box, headers, records, source_props, sizing=None,
                            source_height=None):
    """Check the exact native Table configuration needed by one source item."""
    issues = []
    sizing = sizing or {}
    flexible = sizing.get("width") == "fill-cell" and sizing.get("height") == "intrinsic"
    height = source_height if flexible else scope.get("height")
    if (box is None or not isinstance(box.get("width"), (int, float)) or box["width"] <= 0 or
            (not flexible and scope.get("width") != box["width"]) or
            not isinstance(height, (int, float)) or height <= 0 or height > box["height"]):
        issues.append({"code": "table_native_geometry_unavailable",
                       "admittedWidth": scope.get("width"),
                       "requiredWidth": box["width"] if box else None})
    if headers and (scope.get("showHeader") is not True or
                    headers != [column.get("title") for column in scope.get("columns", [])]):
        issues.append({"code": "native_table_header_unavailable"})
    required = ("showHeader", "border", "stripe", "columns", "data")
    missing = [key for key in required if key not in scope]
    if missing:
        issues.append({"code": "table_content_scope_incomplete", "missing": missing})
    else:
        expected_props = {key: scope[key] for key in required}
        source_props = {key: source_props.get(key) for key in required}
        if flexible:
            for config in (expected_props, source_props):
                config["columns"] = [{key: value for key, value in column.items() if key != "width"}
                                     for column in config["columns"]]
        if source_props != expected_props:
            issues.append({"code": "table_source_configuration_mismatch"})
    if records != scope.get("data"):
        issues.append({"code": "table_fixed_records_outside_scope"})
    return issues


def audit(source_root, tokens, components, geometry, bindings, file_reference):
    source_root = Path(source_root)
    issues = []

    def issue(code, source_id=None, **details):
        issues.append({"code": code, **({"sourceId": source_id} if source_id else {}), **details})

    standard = load_json(ROOT / "registries/design-standards/iview-plus-1.3.24.json")
    lock = load_json(ROOT / "component-builder/source-reader/source-lock.json")
    origin = standard["source"]
    if (lock.get("packageVersion") != standard["version"] or
        lock.get("gitCommit") != origin["commit"] or
        lock.get("files", {}).get(origin["path"]) != origin["sha256"]):
        issue("iview_source_lock_mismatch")
    palette = {"color.primary": (standard["colors"]["primary"],),
               "color.text": (standard["colors"]["text"],),
               "color.page": (standard["colors"]["body"], standard["colors"]["layoutBody"]),
               "color.surface": (standard["colors"]["surface"],),
               "color.border": (standard["colors"]["border"],)}
    for token_id, allowed in palette.items():
        actual = tokens.snapshot["tokens"].get(token_id, {}).get("value")
        if not isinstance(actual, str) or actual.lower() not in {value.lower() for value in allowed}:
            issue("iview_token_mismatch", token=token_id, actual=actual)

    observations = load_json(source_root / "observations.json")
    review = load_json(source_root / "review.json")
    plan = load_json(source_root / "layout-plan.json")
    decisions = load_json(source_root / "decisions.json")
    content = load_json(source_root / "content.json")
    parser = import_module("core.prototype.parser")
    structure = import_module("validators.structure.gate")
    builder = import_module("core.layout.builder")
    analysis = parser.parse(observations, source_root)
    page_tree = structure.builder.build(analysis)
    layout_tree, layout_report = builder.generate(analysis, page_tree, source_root,
                                                  review, plan, tokens)
    if layout_report["status"] != "PASS" or not layout_report["readyForMapping"]:
        issue("layout_input_not_ready", detail=layout_report.get("issues", []))
        return {"status": "REVISE_INPUT", "issues": issues,
                "checked": ["source-lock", "palette", "structure", "layout"]}
    mapping = import_module("core.component-resolver.primitive_mapping").resolve(
        analysis, page_tree, source_root, review, plan, decisions, components, tokens,
        allow_text_primitives=True)
    if mapping["status"] != "PASS":
        issue("component_mapping_not_ready", detail=[{"sourceId": row["sourceId"],
             "status": row["status"]} for row in mapping["rows"] if row["status"] != "Resolved"])
    by_content = {item["sourceId"]: item for item in content["items"]}
    cells = {}
    def walk(node):
        if node["type"] == "Cell":
            for identifier in node.get("sourceIds", []):
                cells[identifier] = node["box"]
        for child in node.get("children", []):
            walk(child)
    walk(layout_report["engineReport"]["skeleton"])
    for row in mapping["rows"]:
        if row["status"] != "Resolved" or not row["componentId"]:
            continue
        identifier, component_id = row["sourceId"], row["componentId"]
        try:
            reference = bindings.resolve(component_id, row["variant"])
            if reference["fileReference"] != file_reference:
                issue("figma_component_file_mismatch", identifier, componentId=component_id)
        except (ValueError, KeyError) as exc:
            issue("figma_component_binding_missing", identifier, componentId=component_id,
                  detail=str(exc))
        if row["componentType"] != "Table":
            continue
        descriptor = components.inspect(component_id)
        scope = descriptor.get("contentScope") or {}
        item = by_content.get(identifier, {})
        box = cells.get(identifier)
        headers = [claim["text"] for claim in item.get("props", {}).get("headers", [])]
        source = geometry.source_component(component_id, row["variant"])
        records = [{key: claim["text"] for key, claim in record.items()}
                   for record in item.get("tableRecords", [])]
        for problem in table_capability_issues(scope, box, headers, records, source["props"],
                                               descriptor.get("sizingPolicy"),
                                               source["rootBounds"]["height"]):
            issue(problem.pop("code"), identifier, **problem)
    return {"status": "READY" if not issues else "NEEDS_RESOURCE", "issues": issues,
            "checked": ["source-lock", "palette", "structure", "layout", "mapping",
                        "figma-bindings", "table-width", "native-table-header",
                        "table-source-configuration", "fixed-records"]}
