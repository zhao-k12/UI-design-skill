"""Contract tests for observed source -> Core UI-IR admission."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import pytest

from core.pipeline.html_page_v1 import CATALOG, compile_page


def fixture(tmp_path: Path):
    source = tmp_path / "source.png"
    source.write_bytes(b"prototype fixture")
    digest = sha256(source.read_bytes()).hexdigest()
    row = {"key": "router", "name": "路由器", "status": "启用", "creator": "王丽慧",
           "note": "-", "updatedAt": "2025-11-27", "actions": ["修改", "新增", "删除"]}
    content = {"sourceSha256": digest, "brand": "系统", "message": "消息", "account": "账号",
               "sidebar": [{"key": "goods", "label": "商品管理", "children":
                            [{"key": "product-types", "label": "商品类型"}]}],
               "breadcrumb": ["首页", "商品类型"], "pageActions":
               [{"label": x} for x in ("新增", "导出", "刷新")],
               "tabs": ["全部", "启用"], "filters": ["更新日期", "搜索"],
               "listTitle": "类型列表", "columns": ["名称", "状态", "创建人员", "备注", "更新时间", "操作"],
               "rows": [row]}
    items = []
    def add(identifier, region, evidence, traits=None):
        items.append({"id": identifier, "region": region, "sourceEvidence": evidence,
                      "decision": "include", "treeRef": identifier,
                      "traits": traits or {"surface": "plain"}})
    for identifier in ("brand", "message", "account"):
        add(identifier, "header", identifier)
    add("menu-goods", "sidebar", "商品管理 arrow", {"trailing": "chevron-up"})
    add("submenu-product-types", "sidebar", "商品类型")
    add("breadcrumb", "content", "首页 / 商品类型")
    for index in range(3):
        add(f"page-action-{index}", "content", content["pageActions"][index]["label"])
    for identifier in ("tabs", "date-filter", "search-filter"):
        add(identifier, "filters", identifier)
    add("list-header", "list", "类型列表")
    for index, title in enumerate(content["columns"]):
        add(f"column-{index}", "table", title)
    for suffix, evidence in (("name", "路由器"), ("status", "启用"), ("actions", "修改 新增 删除")):
        add(f"row-0-{suffix}", "table", evidence, {"surface": "plain"})
    observation = {"sourceSha256": digest, "items": items}
    scan = {"sourceSha256": digest, "items":
            [{"id": item["id"], "region": item["region"], "traits": item["traits"],
              "visual": item["sourceEvidence"]} for item in items]}
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    return source, content, observation, scan, catalog


def test_compiles_all_observations_to_versioned_ui_ir(tmp_path):
    source, content, observation, scan, catalog = fixture(tmp_path)
    result = compile_page(source, content, observation, scan, catalog)
    assert result["qa"]["status"] == "PASS"
    assert result["qa"]["mappedItemCount"] == len(observation["items"])
    assert result["ui_ir"]["componentPlan"]["status"]["role"] == "status.badge-success"
    assert result["ui_ir"]["componentPlan"]["sidebar"]["openNames"] == ["goods"]


@pytest.mark.parametrize("mutation, failure", [
    ("chevron", "menu_chevron_mismatch"),
    ("status", "status_surface_mismatch"),
    ("missing", "page_tree_source_coverage"),
    ("scan", "independent_scan_disagrees"),
])
def test_rejects_observation_drift(tmp_path, mutation, failure):
    source, content, observation, scan, catalog = fixture(tmp_path)
    observation = deepcopy(observation)
    scan = deepcopy(scan)
    if mutation == "chevron":
        next(x for x in observation["items"] if x["id"] == "menu-goods")["traits"]["trailing"] = "none"
        next(x for x in scan["items"] if x["id"] == "menu-goods")["traits"]["trailing"] = "none"
    elif mutation == "status":
        next(x for x in observation["items"] if x["id"] == "row-0-status")["traits"]["surface"] = "outlined"
        next(x for x in scan["items"] if x["id"] == "row-0-status")["traits"]["surface"] = "outlined"
    elif mutation == "missing":
        observation["items"] = [x for x in observation["items"] if x["id"] != "message"]
        scan["items"] = [x for x in scan["items"] if x["id"] != "message"]
    else:
        next(x for x in scan["items"] if x["id"] == "account")["traits"]["surface"] = "outlined"
    with pytest.raises(ValueError, match=failure):
        compile_page(source, content, observation, scan, catalog)
