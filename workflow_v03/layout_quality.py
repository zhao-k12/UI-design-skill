"""Check model-authored layout intent against project rules and computed geometry.

This gate does not generate coordinates or admit new source components. It rejects
plans that merely fit a component inside a Cell while leaving unjustified space.
"""
from __future__ import annotations

from workflow_v03.core import fingerprint

EDGES = ("top", "right", "bottom", "left")
EPSILON = 0.5


def _walk(node):
    yield node
    for child in node.get("children", []):
        yield from _walk(child)


def _token_value(tokens, reference):
    value = tokens["tokens"][reference]["value"]
    return _token_value(tokens, value["token"]) if isinstance(value, dict) else value


def audit(tree, plan, layout_tree, layout_report, catalog, tokens, rule, intent):
    """Return evidence-bound issues for a single versioned page pattern."""
    issues = []

    def issue(code, **details):
        issues.append({"code": code, **details})

    if rule.get("pattern") != "list-page" or plan.get("pattern") != rule.get("pattern"):
        issue("layout_rule_unavailable", pattern=plan.get("pattern"))
        return {"status": "Review", "issues": issues, "scope": "project-list-page-layout"}
    if (intent.get("version") != rule.get("version") or
            intent.get("sourcePageTreeSha256") != tree.get("sourcePageTreeSha256") or
            plan.get("pageTreeSha256") != tree.get("sourcePageTreeSha256") or
            intent.get("ruleSha256") != fingerprint(rule) or
            intent.get("pattern") != plan.get("pattern") or
            intent.get("geometryPolicy") != "prototype-geometry-nonbinding"):
        issue("layout_intent_source_or_rule_mismatch")
    if (plan.get("tokenRegistrySha256") != fingerprint(tokens) or
            layout_report.get("tokenRegistrySha256") != fingerprint(tokens) or
            layout_report.get("planSha256") != fingerprint(plan) or
            layout_report.get("layoutTreeSha256") != fingerprint(layout_tree)):
        issue("layout_core_evidence_mismatch")
    section_roles = plan.get("sectionRegions", {})
    expected_sections = {section["id"] for section in tree["sections"]}
    if set(section_roles) != expected_sections:
        issue("layout_section_mapping_incomplete")
    declared = intent.get("sections", {})
    if set(declared) != expected_sections:
        issue("layout_intent_section_coverage")
    required_tables = {item["id"] for section in tree["sections"]
                       for item in section["items"] if item["component"]["type"] == "Table"}
    for section in tree["sections"]:
        for item in section["items"]:
            component = item["component"]
            component_id = component["id"]
            if component_id and component.get("defaultContent") != catalog.get("components", {}).get(component_id, {}).get("contentScope"):
                issue("component_catalog_not_bound_to_tree", sourceId=item["id"],
                      componentId=component_id)
    declared_tables = intent.get("tableSizing", {})
    if set(declared_tables) != required_tables:
        issue("layout_intent_table_coverage")
    for source_id in required_tables:
        decision = declared_tables.get(source_id, {})
        if (decision.get("policy") != rule["tableWidthPolicy"] or
                decision.get("basis") != "project-page-rule" or
                not decision.get("rationale")):
            issue("table_width_policy_missing", sourceId=source_id)

    if layout_report.get("status") != "PASS" or layout_report.get("engineReport", {}).get("status") != "PASS":
        issue("computed_layout_not_passed")
        skeleton = None
    else:
        skeleton = layout_report["engineReport"].get("skeleton")
    if layout_tree.get("pattern") != rule["pattern"] or not skeleton:
        issue("computed_layout_missing_or_wrong_pattern")
        return {"status": "FAIL", "issues": issues, "scope": "project-list-page-layout"}
    page_padding = layout_tree["page"].get("layout", {}).get("padding", {})
    expected_page = {"token": rule["pagePaddingToken"]}
    if any(page_padding.get(edge) != expected_page for edge in EDGES):
        issue("page_padding_rule_mismatch")

    layout_by_role = {node.get("role"): node for node in layout_tree["page"]["children"]}
    geometry_by_role = {node.get("role"): node for node in skeleton["children"]}
    by_source = {}
    for node in _walk(skeleton):
        if node["type"] == "Cell":
            for source_id in node.get("sourceIds", []):
                by_source.setdefault(source_id, []).append(node["box"])

    for section in tree["sections"]:
        section_id = section["id"]
        role = section_roles.get(section_id)
        required_token = rule["sectionPaddingToken"].get(role)
        if required_token is None:
            issue("section_rule_unavailable", sectionId=section_id, role=role)
            continue
        decision = declared.get(section_id, {})
        if (decision.get("paddingToken") != required_token or
                decision.get("basis") != "project-page-rule" or
                not decision.get("rationale")):
            issue("section_layout_intent_missing", sectionId=section_id)
        layout_section = layout_by_role.get(role, {})
        geometry_section = geometry_by_role.get(role, {})
        padding = layout_section.get("layout", {}).get("padding", {})
        expected_padding = {"token": required_token}
        if any(padding.get(edge) != expected_padding for edge in EDGES):
            issue("section_padding_rule_mismatch", sectionId=section_id, role=role)
        box = geometry_section.get("box")
        if not box:
            issue("section_geometry_missing", sectionId=section_id)
            continue
        inset = _token_value(tokens, required_token)
        inner_left = box["x"] + inset
        inner_width = box["width"] - 2 * inset
        if inner_width <= 0:
            issue("section_content_width_invalid", sectionId=section_id)
            continue
        for item in section["items"]:
            source_id = item["id"]
            cells = by_source.get(source_id, [])
            if len(cells) != 1:
                issue("layout_cell_coverage", sourceId=source_id)
                continue
            cell = cells[0]
            component_type = item["component"]["type"]
            if (role in rule["startAlignedContentRoles"] and
                    component_type in rule["startAlignedComponentTypes"] and
                    abs(cell["x"] - inner_left) > EPSILON):
                issue("content_start_inset_mismatch", sourceId=source_id,
                      actual=cell["x"] - box["x"], expected=inset)
            if component_type != "Table":
                continue
            if abs(cell["width"] - inner_width) > EPSILON:
                issue("table_cell_not_fill_content", sourceId=source_id,
                      actual=cell["width"], expected=inner_width)
            component_id = item["component"]["id"]
            scope = catalog.get("components", {}).get(component_id, {}).get("contentScope", {})
            sizing = catalog.get("components", {}).get(component_id, {}).get("sizingPolicy", {})
            if sizing.get("width") == "fill-cell":
                continue
            if abs(scope.get("width", -1) - inner_width) > EPSILON:
                issue("table_component_width_capability_mismatch", sourceId=source_id,
                      componentId=component_id, admittedWidth=scope.get("width"),
                      requiredWidth=inner_width)

    return {"status": "PASS" if not issues else "FAIL", "issues": issues,
            "scope": "project-list-page-layout", "ruleSha256": fingerprint(rule),
            "intentSha256": fingerprint(intent),
            "checked": ["decision-provenance", "page-and-section-insets",
                        "start-alignment", "table-content-width",
                        "native-sizing-policy" if catalog.get("registryVersion") == "0.2.9"
                        else "admitted-component-width"]}
