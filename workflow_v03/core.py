"""Versioned, platform-neutral stages for the prototype-to-page workflow.

This module prepares three distinct, immutable design stages. Native execution
and independent readback are separate gates; preparing a stage never marks it
as delivered.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re

from validators.ui_ir import load_json, validate_document

COLORS = {
    "Input": "#DBEAFE", "Select": "#DCFCE7", "Button": "#FEF3C7",
    "Table": "#EDE9FE", "Text": "#F1F5F9", "Icon": "#FCE7F3",
    "Card": "#FFE4E6", "Cascader": "#CCFBF1", "Checkbox": "#E0E7FF",
    "DatePicker": "#FAE8FF", "Drawer": "#FEE2E2", "Form": "#D1FAE5",
    "Modal": "#FFEDD5", "Pagination": "#E2E8F0", "Radio": "#EDE9FE",
    "Switch": "#DCFCE7", "Tabs": "#FDE68A", "Tag": "#CFFAFE",
    "Tree": "#DDD6FE", "Upload": "#FBCFE8",
}


def fingerprint(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode("utf-8")).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8", newline="\n")


def _walk(node):
    yield node
    for child in node.get("children", []):
        yield from _walk(child)


def _claims(value):
    if isinstance(value, dict):
        if isinstance(value.get("text"), str) and isinstance(value.get("evidence"), list):
            yield {"text": value["text"], "evidence": value["evidence"]}
        else:
            for child in value.values():
                yield from _claims(child)
    elif isinstance(value, list):
        for child in value:
            yield from _claims(child)


def prepare(run_dir, source_dir):
    """Build a new staged contract from a fully verified Core run.

    The source package and Core outputs remain untouched. A new output directory
    is required so old version locks and completed pages retain their meaning.
    """
    run_dir, source_dir = Path(run_dir), Path(source_dir)
    qa = load_json(run_dir / "qa_report.json")
    structure = load_json(run_dir / "structure_qa_report.json")
    layout = load_json(run_dir / "layout_qa_report.json")
    mapping = load_json(run_dir / "component_mapping.json")
    if any(report.get("status") != "PASS" for report in (qa, structure, layout, mapping)):
        raise ValueError("Core Tree, structure, layout and mapping must all PASS")
    page_tree = load_json(run_dir / "page_tree.json")
    layout_tree = load_json(run_dir / "layout_tree.json")
    observations = load_json(source_dir / "observations.json")
    version = load_json(source_dir / "versions.json")["component_library_version"]
    match = re.match(r"^(\d+\.\d+\.\d+)", version)
    if not match:
        raise ValueError("A versioned component catalog is required for complete default content")
    catalog_path = Path(__file__).resolve().parents[1] / "registries/components" / ("v" + match.group(1)) / "catalog.json"
    catalog = load_json(catalog_path)
    content = load_json(source_dir / "content.json")
    final = load_json(run_dir / "final_ui_ir.json")
    if validate_document(final):
        raise ValueError("Final UI-IR is invalid")
    semantic = [item for section in page_tree["page"]["children"] for item in section["children"]]
    source_ids = [item["id"] for item in semantic]
    content_by_id = {item["sourceId"]: item for item in content["items"]}
    if len(content_by_id) != len(content["items"]) or set(content_by_id) != set(source_ids):
        raise ValueError("Content Tree requires exactly one content record per source item")
    layout_paths = {}
    def index_layout(node, path=()):
        for source_id in node.get("sourceIds", []):
            if source_id in content_by_id and node["type"] == "Cell":
                if source_id in layout_paths:
                    raise ValueError("Ambiguous Cell for source item: " + source_id)
                layout_paths[source_id] = list(path + (node["id"],))
        for child in node.get("children", []):
            index_layout(child, path + (node["id"],))
    index_layout(layout_tree["page"])
    if set(layout_paths) != set(source_ids):
        raise ValueError("Content Tree lacks a layout Cell for each source item")
    mapping_by_id = {row["sourceId"]: row for row in mapping["rows"]}
    if set(mapping_by_id) != set(source_ids):
        raise ValueError("Content Tree lacks a component decision for each source item")
    def component(item_id):
        row = mapping_by_id[item_id]
        logical_id = row["componentId"]
        descriptor = catalog["components"][logical_id] if logical_id else None
        return {"type": row["componentType"], "id": logical_id,
                "defaultContent": deepcopy(descriptor.get("contentScope")) if descriptor else None}
    sections = []
    for section in page_tree["page"]["children"]:
        sections.append({"id": section["id"], "purpose": section["purpose"],
                         "items": [{"id": item["id"], "kind": item["kind"],
                                    "description": item["description"],
                                    "layoutPath": layout_paths[item["id"]],
                                    "component": component(item["id"]),
                                    "sourceContent": deepcopy(content_by_id[item["id"]])}
                                   for item in section["children"]]})
    tree = {"version": "0.3.0", "stage": "page-content-tree",
            "documentId": page_tree["documentId"],
            "sourceFiles": [{"path": source["path"],
                             "sha256": sha256((source_dir / source["path"]).read_bytes()).hexdigest()}
                            for source in observations["sources"]],
            "identity": page_tree["page"]["identity"],
            "primaryTask": page_tree["page"]["primaryTask"],
            "sections": sections,
            "sourcePageTreeSha256": fingerprint(page_tree),
            "sourceLayoutTreeSha256": fingerprint(layout_tree),
            "sourceContentSha256": fingerprint(content)}
    claims = list(_claims(content["items"]))
    if not claims or any(not claim["evidence"] for claim in claims):
        raise ValueError("Every prototype content claim needs source evidence")
    tree_qa = {"status": "NOT_RUN", "scope": "source-bound-content-and-hierarchy",
               "sourceItemCount": len(source_ids), "claimCount": len(claims),
               "sourceReviewStatus": structure["status"], "structuralChecks": "PASS",
               "limitation": "Original-image omissions still require human review against the prototype."}

    skeleton = mapping["layoutReport"]["engineReport"]["skeleton"]
    boxes = {node["id"]: node["box"] for node in _walk(skeleton)}
    rows = mapping["rows"]
    if len(rows) != len(source_ids) or {row["sourceId"] for row in rows} != set(source_ids):
        raise ValueError("Colored skeleton must annotate every source item exactly once")
    cells = []
    for row in rows:
        if row["status"] != "Resolved" or row["cellId"] not in boxes:
            raise ValueError("Unresolved or missing skeleton Cell")
        kind = row["componentType"]
        if kind not in COLORS:
            raise ValueError("No declared annotation color for " + str(kind))
        cells.append({"cellId": row["cellId"], "sourceId": row["sourceId"],
                      "componentType": kind, "componentId": row["componentId"],
                      "label": row["label"], "color": COLORS[kind],
                      "box": deepcopy(boxes[row["cellId"]])})
    skeleton_page = {"version": "0.3.0", "stage": "annotated-skeleton-page",
                     "documentId": tree["documentId"], "contentTreeSha256": fingerprint(tree),
                     "layoutSkeletonSha256": fingerprint(skeleton),
                     "box": deepcopy(skeleton["box"]), "cells": cells}
    skeleton_qa = {"status": "PASS", "scope": "planned-component-selection-placement-spacing",
                   "annotatedCellCount": len(cells), "layoutStatus": layout["status"],
                   "nativePageStatus": "NOT_RUN"}

    default_page = deepcopy(final)
    target_text = {node["id"]: node["text"] for page in final["pages"]
                   for node in _walk(page) if node["type"] == "Text"}
    if len(target_text) != sum(1 for page in final["pages"] for node in _walk(page)
                               if node["type"] == "Text"):
        raise ValueError("Text node IDs are not unique")
    for page in default_page["pages"]:
        for node in _walk(page):
            if node["type"] == "Text":
                node["text"] = "文本"
    if validate_document(default_page):
        raise ValueError("Default-content page is invalid")
    fill = {"version": "0.3.0", "stage": "prototype-content-fill",
            "documentId": tree["documentId"],
            "defaultPageSha256": fingerprint(default_page),
            "finalPageSha256": fingerprint(final),
            "targets": [{"uiIrId": node_id, "expectedDefault": "文本", "text": value}
                        for node_id, value in target_text.items()]}
    workflow = {"version": "0.3.0", "status": "AWAITING_NATIVE_STAGES",
                "contentTree": tree_qa, "annotatedSkeleton": skeleton_qa,
                "defaultComponentPage": {"status": "NOT_RUN", "distinctPageRequired": True},
                "filledContent": {"status": "NOT_RUN"},
                "prototypeProofread": {"status": "NOT_RUN"},
                "deliverable": False}
    return {"page_content_tree.json": tree, "page_content_tree_qa.json": tree_qa,
            "annotated_skeleton_page.json": skeleton_page,
            "annotated_skeleton_qa.json": skeleton_qa,
            "default_component_page_ui_ir.json": default_page,
            "prototype_content_fill.json": fill,
            "workflow_qa.json": workflow}


def save(bundle, output_dir):
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("Use a new empty staged-workflow directory")
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, value in bundle.items():
        write(output_dir / name, value)
