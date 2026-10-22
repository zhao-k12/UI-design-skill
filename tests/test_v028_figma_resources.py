"""The new Figma-only table must remain separately admitted and version locked."""
from importlib import import_module
from pathlib import Path

from adapters.component_bindings import ComponentBindings
from scripts.run_figma_pipeline import FIGMA_BATCH_PROFILE_028
from validators.ui_ir import load_json

ROOT = Path(__file__).resolve().parents[1]


def test_v028_registry_and_token_migration():
    paths = FIGMA_BATCH_PROFILE_028
    catalog = load_json(ROOT / paths["components"])
    reports = load_json(ROOT / paths["fidelity"])
    tokens = import_module("core.design-rules.tokens").TokenRegistry(
        load_json(ROOT / paths["tokens"]))
    registry = import_module("core.component-resolver.registry").ComponentRegistry(catalog, reports)
    bindings = ComponentBindings(
        load_json(ROOT / "adapters/figma/metadata" / paths["componentBindings"]),
        registry, platform="figma")
    assert tokens.version == "0.2.3"
    assert tokens.resolve("color.primary") == "#2d8cf0"
    assert tokens.resolve("color.border") == "#dcdee2"
    assert catalog["registryVersion"] == "0.2.8"
    assert catalog["components"]["data.table.default"]["contentScope"]["width"] == 1392
    matches = [(identifier, component) for identifier, component in catalog["components"].items()
               if component["componentType"] == "Table" and
               component["contentScope"].get("width") == 1840]
    assert len(matches) == 1
    identifier, component = matches[0]
    scope = component["contentScope"]
    assert scope["kind"] == "fixed-native-snapshot"
    assert scope["showHeader"] is True and scope["border"] is False and scope["stripe"] is False
    assert (scope["width"], scope["height"]) == (1840, 182.875)
    assert [column["title"] for column in scope["columns"]] == ["姓名", "状态", "角色"]
    assert len(scope["data"]) == 3 and len(scope["visibleText"]) == 12
    report = reports[component["fidelity"]["reportId"]]
    assert report["componentIrSha256"] == component["fidelity"]["componentIrSha256"]
    assert report["evidenceSha256"]["sourceBundleSha256"] != report["componentIrSha256"]
    assert bindings.resolve(identifier, "default")["componentReference"] == "280:3"
