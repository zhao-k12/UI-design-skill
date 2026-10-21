"""Independent stage gates for the retained two-page Figma workflow."""
from hashlib import sha256
from pathlib import Path
from workflow_v03.core import fingerprint


def audit_content_tree(tree, review):
    """Require a separate direct prototype review of the assembled content Tree."""
    expected_items = {item["id"] for section in tree["sections"] for item in section["items"]}
    reviewed = review.get("items", [])
    issues = []
    if review.get("contentTreeSha256") != fingerprint(tree):
        issues.append("content_tree_changed")
    if review.get("sourceFiles") != tree["sourceFiles"]:
        issues.append("prototype_source_changed")
    if review.get("sectionOrder") != [section["id"] for section in tree["sections"]]:
        issues.append("section_order_not_reviewed")
    if (len(reviewed) != len(expected_items) or
        {item.get("sourceId") for item in reviewed} != expected_items or
        any(item.get("contentAccuracy") != "PASS" or item.get("contentCompleteness") != "PASS"
            for item in reviewed)):
        issues.append("tree_content_review_incomplete")
    if review.get("layoutRelationsStatus") != "PASS":
        issues.append("tree_layout_relations_not_reviewed")
    return {"status": "PASS" if not issues else "FAIL", "issues": issues,
            "stage": "page-content-tree", "contentTreeSha256": fingerprint(tree)}


def audit_skeleton(spec, execution, readback, review):
    """Readback must come from a separate native inspection, not the write receipt."""
    issues = []
    if execution.get("status") != "EXECUTED" or execution.get("stage") != "annotated-skeleton-page":
        issues.append("skeleton_execution_missing")
    if (not readback.get("independent") or
        readback.get("pageReference") != execution.get("pageReference") or
        readback.get("rootReference") != execution.get("rootReference")):
        issues.append("independent_skeleton_readback_missing")
    expected = {cell["cellId"]: cell for cell in spec["cells"]}
    actual = {cell["cellId"]: cell for cell in readback.get("cells", [])}
    if len(actual) != len(readback.get("cells", [])) or set(actual) != set(expected):
        issues.append("skeleton_cell_coverage")
    for cell_id, wanted in expected.items():
        got = actual.get(cell_id, {})
        if any(got.get(key) != wanted[key] for key in
               ("sourceId", "componentType", "componentId", "color", "box", "label")):
            issues.append("skeleton_cell_mismatch:" + cell_id)
    reviewed = review.get("cells", [])
    if (review.get("skeletonSha256") != fingerprint(spec) or
        len(reviewed) != len(expected) or
        {row.get("cellId") for row in reviewed} != set(expected) or
        any(any(row.get(key) != "PASS" for key in
                ("componentChoice", "placement", "spacing", "completeness")) for row in reviewed)):
        issues.append("skeleton_selection_and_spacing_review_incomplete")
    return {"status": "PASS" if not issues else "FAIL", "issues": issues,
            "stage": "annotated-skeleton-page", "independentReadback": bool(readback.get("independent")),
            "pageReference": execution.get("pageReference"),
            "skeletonSha256": fingerprint(spec)}


def audit_default_page(default_document, skeleton_qa, execution, readback):
    issues = []
    if skeleton_qa.get("status") != "PASS":
        issues.append("skeleton_not_approved")
    if execution.get("status") != "PASS" or not execution.get("pageReference"):
        issues.append("default_page_execution_missing")
    if execution.get("pageReference") == skeleton_qa.get("pageReference"):
        issues.append("skeleton_page_was_overwritten")
    if (not readback.get("independent") or
        readback.get("pageReference") != execution.get("pageReference")):
        issues.append("independent_default_readback_missing")
    if readback.get("skeletonPageReference") != skeleton_qa.get("pageReference"):
        issues.append("retained_skeleton_page_missing")
    node_map = execution.get("nodeMap", {})
    expected = {}
    def walk(node):
        if node["type"] == "Text":
            expected[node["id"]] = ("TEXT", node["text"])
        elif node["type"] in ("ComponentInstance", "IconInstance"):
            expected[node["id"]] = ("INSTANCE", None)
        for child in node.get("children", []):
            walk(child)
    for page in default_document["pages"]:
        walk(page)
    actual = {entry["uiIrId"]: entry for entry in readback.get("nodes", [])}
    if len(actual) != len(readback.get("nodes", [])) or set(expected) - set(actual):
        issues.append("default_node_coverage")
    for node_id, (kind, text) in expected.items():
        got = actual.get(node_id, {})
        if got.get("nodeId") != node_map.get(node_id) or got.get("type") != kind:
            issues.append("default_node_mismatch:" + node_id)
        if kind == "TEXT" and got.get("characters") != text:
            issues.append("default_text_mismatch:" + node_id)
        if kind == "INSTANCE" and not got.get("mainComponentReference"):
            issues.append("detached_component:" + node_id)
    return {"status": "PASS" if not issues else "FAIL", "issues": issues,
            "stage": "default-component-page", "independentReadback": bool(readback.get("independent")),
            "pageReference": execution.get("pageReference"), "nodeMap": node_map,
            "defaultPageSha256": fingerprint(default_document)}


def audit_filled_content(fill, default_qa, execution, readback):
    issues = []
    if default_qa.get("status") != "PASS":
        issues.append("default_page_not_approved")
    if execution.get("status") != "EXECUTED" or execution.get("stage") != "prototype-content-fill":
        issues.append("content_fill_execution_missing")
    if (not readback.get("independent") or
        readback.get("pageReference") != default_qa.get("pageReference")):
        issues.append("independent_content_readback_missing")
    if readback.get("instancesIntact") is not True:
        issues.append("native_components_changed_during_fill")
    expected = {row["uiIrId"]: row["text"] for row in fill["targets"]}
    actual = {row["uiIrId"]: row for row in readback.get("texts", [])}
    if len(actual) != len(readback.get("texts", [])) or set(actual) != set(expected):
        issues.append("content_target_coverage")
    for node_id, value in expected.items():
        got = actual.get(node_id, {})
        if got.get("nodeId") != default_qa.get("nodeMap", {}).get(node_id) or got.get("characters") != value:
            issues.append("content_mismatch:" + node_id)
    return {"status": "PASS" if not issues else "FAIL", "issues": issues,
            "stage": "prototype-content-fill", "independentReadback": bool(readback.get("independent")),
            "pageReference": default_qa.get("pageReference"), "finalPageSha256": fill["finalPageSha256"]}


def audit_prototype_proofread(content_tree, content_qa, review, native_png_path):
    """Final QA explicitly covers each original item and the final native PNG."""
    expected = {item["id"] for section in content_tree["sections"] for item in section["items"]}
    rows = review.get("items", [])
    actual = {row.get("sourceId") for row in rows}
    issues = []
    if content_qa.get("status") != "PASS":
        issues.append("content_not_approved")
    if len(rows) != len(actual) or actual != expected or any(row.get("status") != "PASS" for row in rows):
        issues.append("prototype_item_proofread_incomplete")
    png = Path(native_png_path)
    if (review.get("originalPrototypeSha256") not in
            {source["sha256"] for source in content_tree["sourceFiles"]} or
        not png.is_file() or
        review.get("nativePngSha256") != (sha256(png.read_bytes()).hexdigest() if png.is_file() else None) or
        review.get("pageReference") != content_qa.get("pageReference") or
        review.get("fullPageVisualStatus") != "PASS"):
        issues.append("final_visual_evidence_incomplete")
    return {"status": "PASS" if not issues else "FAIL", "issues": issues,
            "stage": "prototype-proofread", "deliverable": not issues,
            "contentTreeSha256": fingerprint(content_tree),
            "pageReference": content_qa.get("pageReference")}
