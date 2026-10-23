"""Versioned, platform-neutral compiler for an observed static admin tree list.

The HTML adapter consumes only the resulting UI-IR. This compiler never calls a
browser or imports a platform adapter.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "registries/components/html-v1/catalog.json"


def fingerprint(value: object) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json_object_required:{path}")
    return value


def flatten(rows: list[dict]) -> list[dict]:
    result = []
    for row in rows:
        result.append(row)
        result.extend(flatten(row.get("children", [])))
    return result


def compile_page(source: Path, content: dict, observation: dict, second: dict, catalog: dict) -> dict:
    source_hash = sha256(source.read_bytes()).hexdigest()
    if any(data.get("sourceSha256") != source_hash for data in (content, observation, second)):
        raise ValueError("source_hash_mismatch")
    if catalog.get("registryVersion") != "html-v1.0" or catalog.get("sourceVersion") != "view-ui-plus@1.3.24":
        raise ValueError("html_registry_version_mismatch")
    installed = read(ROOT / "node_modules/view-ui-plus/package.json")
    if f"view-ui-plus@{installed.get('version')}" != catalog["sourceVersion"]:
        raise ValueError("official_package_version_mismatch")
    source_hashes = {}
    for role, component in catalog["components"].items():
        path = ROOT / "node_modules/view-ui-plus" / component["source"]
        if not path.is_file():
            raise ValueError(f"official_source_missing:{role}")
        source_hashes[role] = sha256(path.read_bytes()).hexdigest()
    first = {item["id"]: item for item in observation["items"]}
    scan = {item["id"]: item for item in second["items"]}
    if len(first) != len(observation["items"]) or len(scan) != len(second["items"]) or set(first) != set(scan):
        raise ValueError("independent_scan_coverage_mismatch")
    for identifier, item in first.items():
        other = scan[identifier]
        if item.get("region") != other.get("region") or item.get("traits") != other.get("traits"):
            raise ValueError(f"independent_scan_disagrees:{identifier}")
        if item.get("decision") not in ("include", "exclude") or not item.get("sourceEvidence"):
            raise ValueError(f"observation_unresolved:{identifier}")
        if item["decision"] == "include" and not item.get("treeRef"):
            raise ValueError(f"tree_binding_missing:{identifier}")
        if item["decision"] == "exclude" and not item.get("reason"):
            raise ValueError(f"exclusion_reason_missing:{identifier}")

    page_tree = {
        "version": "html-v1.0", "sourceSha256": source_hash,
        "regions": [
            {"id": "header", "sourceIds": ["brand", "message", "account"]},
            {"id": "sidebar", "sourceIds": [f"menu-{item['key']}" for item in content["sidebar"]] +
             [f"submenu-{item['key']}" for parent in content["sidebar"] for item in parent.get("children", [])]},
            {"id": "heading", "sourceIds": ["breadcrumb"] + [f"page-action-{i}" for i in range(len(content["pageActions"]))]},
            {"id": "filters", "sourceIds": ["tabs", "date-filter", "search-filter"]},
            {"id": "list", "sourceIds": ["list-header"] + [f"column-{i}" for i in range(len(content["columns"]))] +
             [f"row-{i}-{part}" for i, _ in enumerate(flatten(content["rows"])) for part in ("name", "status", "actions")]}
        ]
    }
    required = {identifier for region in page_tree["regions"] for identifier in region["sourceIds"]}
    included = {identifier for identifier, item in first.items() if item["decision"] == "include"}
    if required != included:
        raise ValueError(f"page_tree_source_coverage:{sorted(required ^ included)}")
    rows = flatten(content["rows"])
    if len(content["columns"]) != 6:
        raise ValueError("tree_table_six_columns_required")
    if len({row["key"] for row in rows}) != len(rows):
        raise ValueError("duplicate_tree_row_key")
    if len({item["key"] for item in content["sidebar"]}) != len(content["sidebar"]):
        raise ValueError("duplicate_menu_key")
    expanded = [item["key"] for item in content["sidebar"] if item.get("children")]
    selected = [child["key"] for item in content["sidebar"] for child in item.get("children", []) if child["label"] == content["breadcrumb"][-1]]
    if len(expanded) != 1 or len(selected) != 1:
        raise ValueError("menu_open_or_selected_ambiguous")
    for index, item in enumerate(content["sidebar"]):
        identifier = f"menu-{item['key']}"
        if item["label"] not in first[identifier]["sourceEvidence"] or item["label"] not in scan[identifier]["visual"]:
            raise ValueError(f"menu_text_not_source_bound:{identifier}")
        expected = "chevron-up" if item.get("children") else "chevron-down"
        if first[identifier]["traits"].get("trailing") != expected:
            raise ValueError(f"menu_chevron_mismatch:{identifier}")
    for index, row in enumerate(rows):
        if row["actions"] != ["修改", "新增", "删除"]:
            raise ValueError(f"unmapped_row_actions:{row['key']}")
        for suffix, claim in (("name", row["name"]), ("status", row["status"]), ("actions", row["actions"][0])):
            identifier = f"row-{index}-{suffix}"
            if claim not in first[identifier]["sourceEvidence"] or claim not in scan[identifier]["visual"]:
                raise ValueError(f"table_cell_not_source_bound:{identifier}")
        if row.get("children") and row.get("_showChildren") is not True:
            raise ValueError(f"tree_children_not_expanded:{row['key']}")
        if first[f"row-{index}-status"]["traits"].get("surface") != "plain":
            raise ValueError(f"status_surface_mismatch:{row['key']}")

    layout_tree = {
        "version": "html-v1.0", "gridColumns": 24,
        "shell": {"header": {"span": 24, "height": "official-menu-natural"},
                  "body": {"direction": "horizontal", "sidebar": "official-sider-hug", "main": "fill"}},
        "mainFlow": ["heading", "filters", "list"],
        "filterFlow": {"left": "status-tabs", "right": ["date-filter", "search-filter"], "wrap": True},
        "table": {"width": "fill-card", "rows": "content-intrinsic"}
    }
    mapping: dict[str, list[str]] = {}
    for identifier in required:
        if identifier == "brand": roles = ["identity.avatar"]
        elif identifier == "message": roles = ["notification.badge-count", "action.button-text"]
        elif identifier == "account": roles = ["identity.avatar", "identity.dropdown"]
        elif identifier.startswith("menu-"): roles = ["navigation.parent"]
        elif identifier.startswith("submenu-"): roles = ["navigation.child"]
        elif identifier == "breadcrumb": roles = ["navigation.breadcrumb", "navigation.breadcrumb-item"]
        elif identifier.startswith("page-action-"): roles = ["action.button-primary" if identifier == "page-action-0" else "action.button-default"]
        elif identifier == "tabs": roles = ["filter.radio-group", "filter.radio"]
        elif identifier == "date-filter": roles = ["filter.date-picker"]
        elif identifier == "search-filter": roles = ["filter.search-input"]
        elif identifier == "list-header": roles = ["content.card", "content.divider", "action.button-default"]
        elif identifier.startswith("column-"): roles = ["data.tree-table"]
        elif identifier.endswith("-name"): roles = ["data.tree-table", "data.tree-icon"]
        elif identifier.endswith("-status"): roles = ["status.badge-success"]
        elif identifier.endswith("-actions"): roles = ["action.button-text"]
        else: raise ValueError(f"unmapped_source:{identifier}")
        if any(role not in catalog["components"] for role in roles):
            raise ValueError(f"unregistered_component:{identifier}")
        mapping[identifier] = roles
    component_mapping = {"version": "html-v1.0", "sourceSha256": source_hash,
                         "registryVersion": catalog["registryVersion"], "sourceRoles": mapping,
                         "officialSourceSha256": source_hashes}
    plan = {
        "header": {"role": "navigation.header", "mode": "horizontal", "theme": "light"},
        "sidebar": {"role": "navigation.sidebar", "theme": "dark", "openNames": expanded, "activeName": selected[0]},
        "pageActions": [{"role": "action.button-primary" if i == 0 else "action.button-default",
                         "type": "primary" if i == 0 else "default"} for i in range(len(content["pageActions"]))],
        "tabs": {"role": "filter.radio-group", "type": "button", "buttonStyle": "solid"},
        "date": {"role": "filter.date-picker", "type": "date"},
        "search": {"role": "filter.search-input", "search": True},
        "table": {"role": "data.tree-table", "stripe": True, "rowKey": "key", "treeColumn": "name",
                  "columns": [{"title": title, "key": ["name", "status", "creator", "note", "updatedAt", "actions"][i],
                               "minWidth": [240, 120, 120, 120, 195, 260][i]}
                              for i, title in enumerate(content["columns"])]},
        "status": {"role": "status.badge-success", "status": "success"},
        "rowActions": {"role": "action.button-text", "type": "text", "size": "small",
                       "icons": {"修改": "edit-line", "新增": "add-box-line", "删除": "close-line"}}
    }
    if len(plan["table"]["columns"]) != 6:
        raise ValueError("tree_table_six_columns_required")
    ui_ir = {"schemaVersion": "html-v1.0", "sourceSha256": source_hash,
             "registryVersion": catalog["registryVersion"], "registrySha256": fingerprint(catalog),
             "layout": layout_tree, "componentPlan": plan,
             "componentMappingSha256": fingerprint(component_mapping), "content": content}
    return {"page_tree": page_tree, "layout_tree": layout_tree,
            "component_mapping": component_mapping, "ui_ir": ui_ir,
            "qa": {"status": "PASS", "sourceSha256": source_hash, "observationCount": len(first),
                   "semanticItemCount": len(required), "rowCount": len(rows),
                   "mappedItemCount": len(mapping), "gridColumns": 24,
                   "uiIrSha256": fingerprint(ui_ir)}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--content", required=True, type=Path)
    parser.add_argument("--observation", required=True, type=Path)
    parser.add_argument("--independent-scan", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        parser.error("output_must_be_in_artifacts")
    try:
        result = compile_page(args.source, read(args.content), read(args.observation),
                              read(args.independent_scan), read(CATALOG))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"{error}\n")
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"schemaVersion": "html-v1.0", "sourceSha256": result["qa"]["sourceSha256"],
                "registrySha256": fingerprint(read(CATALOG)),
                "compilerSha256": sha256(Path(__file__).read_bytes()).hexdigest()}
    if (output / "manifest.json").exists() and read(output / "manifest.json") != manifest:
        parser.exit(2, "html_core_manifest_mismatch_use_new_revision\n")
    save(output / "manifest.json", manifest)
    for key in ("page_tree", "layout_tree", "component_mapping", "ui_ir"):
        save(output / f"{key}.json", result[key])
    save(output / "qa_report.json", result["qa"])
    print(json.dumps(result["qa"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
