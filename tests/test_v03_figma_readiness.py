"""Known component gaps fail before Core or any native page is written."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

from scripts.run_revised_figma_stages import advance
from validators.ui_ir import load_json
from workflow_v03.core import write
from workflow_v03.figma import skeleton_script
from workflow_v03.readiness import table_capability_issues

ROOT = Path(__file__).resolve().parents[1]


def _table_scope():
    catalog = load_json(ROOT / "registries/components/v0.2.8/catalog.json")
    return next(component["contentScope"] for component in catalog["components"].values()
                if component["componentType"] == "Table" and
                component["contentScope"].get("width") == 1840)


def test_admitted_native_table_passes_exact_capability_check():
    scope = _table_scope()
    source_props = {key: scope[key] for key in ("showHeader", "border", "stripe", "columns", "data")}
    assert table_capability_issues(scope, {"width": 1840, "height": 182.875},
                                   [column["title"] for column in scope["columns"]],
                                   scope["data"], source_props) == []


@pytest.mark.parametrize("mutation,expected", [
    ("narrow", "table_native_geometry_unavailable"),
    ("no-header", "native_table_header_unavailable"),
    ("missing-border", "table_content_scope_incomplete"),
    ("wrong-source", "table_source_configuration_mismatch"),
    ("wrong-records", "table_fixed_records_outside_scope"),
])
def test_known_table_mismatches_are_reported_early(mutation, expected):
    scope = deepcopy(_table_scope())
    box = {"width": 1840, "height": 182.875}
    headers = [column["title"] for column in scope["columns"]]
    records = deepcopy(scope["data"])
    source_props = {key: deepcopy(scope[key]) for key in
                    ("showHeader", "border", "stripe", "columns", "data")}
    if mutation == "narrow":
        scope["width"] = 1392
    elif mutation == "no-header":
        scope["showHeader"] = False
    elif mutation == "missing-border":
        del scope["border"]
    elif mutation == "wrong-source":
        source_props["stripe"] = True
    else:
        records[0][next(iter(records[0]))] = "other"
    codes = {issue["code"] for issue in table_capability_issues(
        scope, box, headers, records, source_props)}
    assert expected in codes


def test_skeleton_script_survives_ascii_only_transport():
    script = skeleton_script({"documentId": "测试", "cells": [{"label": "用户管理"}]},
                             "figma-file", "r1")
    assert script.isascii()
    assert "\\u7528\\u6237\\u7ba1\\u7406" in script
    assert "�" not in script


def test_component_compilation_blocks_skeleton_before_native_write():
    with TemporaryDirectory(dir=ROOT / "artifacts") as temp:
        staged = Path(temp)
        write(staged / "iview_conformance_qa.json", {"status": "PASS"})
        write(staged / "layout_quality_qa.json", {"status": "PASS"})
        write(staged / "page_content_tree_review.json",
              {"status": "PASS", "contentTreeSha256": "same"})
        write(staged / "annotated_skeleton_page.json",
              {"contentTreeSha256": "same", "cells": [{"label": "用户管理"}]})
        write(staged / "default_component_page_ui_ir.json", {"documentId": "draft"})
        with patch("scripts.run_revised_figma_stages.component_preflight",
                   side_effect=ValueError("native Table unavailable")):
            with pytest.raises(ValueError, match="native Table unavailable"):
                advance(staged, "skeleton-script", file_reference="file", revision="r1",
                        profile="v0.2.8-figma")
        assert not (staged / "figma-skeleton.js").exists()
        with patch("scripts.run_revised_figma_stages.component_preflight",
                   return_value=("component", {"status": "PASS"})):
            result = advance(staged, "skeleton-script", file_reference="file", revision="r1",
                             profile="v0.2.8-figma")
        assert result["status"] == "PREPARED"
        assert (staged / "figma-default-component-preflight.json").exists()
        assert (staged / "figma-skeleton.js").read_text(encoding="utf-8").isascii()
