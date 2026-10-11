"""Compare returned native execution evidence with the exact compiled UI-IR payload."""
import math


def validate_native_evidence(plan, native, icon_bindings):
    issues = []
    def issue(code, node_id, detail):
        issues.append({"code": code, "uiIrId": node_id, "detail": detail})
    if native.get("status") != "PASS":
        issue("native_execution_not_passed", "", "Cannot validate a failed or unexecuted host result")
    for field in ("uiIrSha256", "tokensSha256", "componentsSha256", "iconsSha256", "adapterVersion"):
        if native.get(field) != plan.get(field):
            issue("native_input_hash_mismatch", "", field)
    actual = {entry["uiIrId"]: entry for entry in native.get("evidence", [])}
    expected_ids = set()
    def walk(spec, parent=None):
        node_id = spec["id"]
        expected_ids.add(node_id)
        entry = actual.get(node_id)
        if entry is None:
            issue("missing_native_node", node_id, "No native evidence for this UI-IR node")
            return
        expected_type = "TEXT" if spec["type"] == "Text" else "INSTANCE" if spec["type"] in ("IconInstance", "ComponentInstance") else "FRAME"
        if entry.get("type") != expected_type or entry.get("nodeId") != native.get("nodeMap", {}).get(node_id):
            issue("native_type_or_identity_mismatch", node_id, expected_type)
        for axis in ("width", "height"):
            mode = spec["layout"][axis]["mode"].upper()
            if parent and parent["type"] != "Grid" and parent["layout"]["alignment"]["cross"] == "stretch" and mode == "HUG":
                if (axis == "width" and parent["layout"]["direction"] == "vertical") or (axis == "height" and parent["layout"]["direction"] == "horizontal"):
                    mode = "FILL"
            property_name = "layoutSizingHorizontal" if axis == "width" else "layoutSizingVertical"
            if entry.get(property_name) != mode:
                issue("native_sizing_mode_mismatch", node_id, axis)
            measured = entry.get(axis)
            if not isinstance(measured, (int, float)) or not math.isfinite(measured) or measured <= 0:
                issue("invalid_native_geometry", node_id, axis)
            elif spec["layout"][axis]["mode"] == "fixed" and abs(measured - spec["layout"][axis]["value"]) > 1e-6:
                issue("native_size_mismatch", node_id, axis)
        if expected_type == "FRAME":
            expected_direction = "VERTICAL" if spec["type"] == "Grid" else spec["layout"]["direction"].upper()
            if entry.get("layoutMode") != expected_direction or entry.get("itemSpacing") != spec["layout"]["gap"]:
                issue("native_layout_mismatch", node_id, "Auto Layout mode or gap differs")
            for side, value in spec["layout"]["padding"].items():
                if entry.get("padding" + side.title()) != value:
                    issue("native_padding_mismatch", node_id, side)
            if spec["type"] == "Grid":
                for cell in spec["gridCells"]:
                    child = actual.get(cell["id"])
                    source_child = next(item for item in spec["children"] if item["id"] == cell["id"])
                    if source_child["layout"]["width"]["mode"] == "fill" and (not child or abs(child["width"] - cell["width"]) > 1e-6):
                        issue("native_grid_span_mismatch", cell["id"], "Fill child does not match exact Grid24 cell width")
        if expected_type == "TEXT":
            if entry.get("characters") != spec["text"] or entry.get("fontWeight") != spec["style"]["typographyToken"]["fontWeight"]:
                issue("native_text_mismatch", node_id, "Text or effective font weight differs")
            if entry.get("fontName", {}).get("family") != spec["fontName"]["family"]:
                issue("native_font_mismatch", node_id, "Font family changed")
        if expected_type == "INSTANCE":
            if entry.get("mainComponentReference") != spec.get("componentReference"):
                issue("native_instance_mismatch", node_id, "Instance master differs from admitted binding")
            if spec["type"] == "IconInstance":
                matches = [binding for binding in icon_bindings.get("bindings", {}).values()
                           if binding.get("componentReference") == spec.get("componentReference") and binding.get("svgSha256") == spec.get("svgSha256")]
                if not matches or icon_bindings.get("registrySha256") != plan["iconsSha256"]:
                    issue("native_icon_source_mismatch", node_id, "Native master must retain the locked official SVG binding")
        for child in spec.get("children", []):
            walk(child, spec)
    for page in plan["pages"]:
        walk(page)
    if set(actual) != expected_ids or len(actual) != len(native.get("evidence", [])):
        issue("native_node_inventory_mismatch", "", "Missing, duplicate or extra UI-IR evidence nodes")
    return {"scope": "figma_recorded_native_evidence", "status": "FAIL" if issues else "PASS", "issues": issues,
            "uiIrSha256": plan["uiIrSha256"], "logicalNodes": len(expected_ids),
            "instanceCount": sum(entry.get("type") == "INSTANCE" for entry in actual.values()),
            "fullTaskAcceptance": "PENDING_OFFICIAL_UI_COMPONENTS"}
