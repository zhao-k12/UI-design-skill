"""New Figma tasks separate source samples from component size admission."""
from copy import deepcopy
from hashlib import sha256
from importlib import import_module
from pathlib import Path

import pytest
from PIL import Image, ImageChops

from adapters.component_bindings import ComponentBindings, validate_instance_scope
from scripts.migrate_adaptive_sizing import TABLE
from validators.ui_ir import load_json
from workflow_v03.readiness import table_capability_issues

ROOT = Path(__file__).resolve().parents[1]
registry_module = import_module("core.component-resolver.registry")


def resources():
    catalog = load_json(ROOT / "registries/components/v0.2.9/catalog.json")
    reports = load_json(ROOT / "registries/components/v0.2.9/fidelity-reports.json")
    registry = registry_module.ComponentRegistry(catalog, reports)
    bindings = ComponentBindings(
        load_json(ROOT / "adapters/figma/metadata/component-bindings-0.2.9-figma.json"),
        registry, platform="figma")
    return catalog, reports, registry, bindings


def test_every_admitted_component_has_content_without_pixel_size_gate():
    catalog, _, registry, bindings = resources()
    assert catalog["registryVersion"] == "0.2.9"
    assert len(catalog["components"]) == 19
    for entry in catalog["components"].values():
        scope = entry["contentScope"]
        assert "width" not in scope and "height" not in scope
        assert entry["sizingPolicy"]["height"] == "intrinsic"
        for columns in (scope.get("columns", []), scope.get("props", {}).get("columns", [])):
            assert all("width" not in column for column in columns)
    assert catalog["components"][TABLE]["sizingPolicy"]["width"] == "fill-cell"
    assert bindings.resolve(TABLE, "default")["componentReference"] == "299:3"
    assert registry.library_version == "0.2.9-figma-adaptive-size"


def test_adaptive_table_accepts_1660_without_losing_source_content():
    catalog, _, _, _ = resources()
    scope = catalog["components"][TABLE]["contentScope"]
    source = deepcopy(scope["props"])
    for column in source["columns"]:
        column["width"] = 614
    headers = [column["title"] for column in scope["columns"]]
    assert table_capability_issues(scope, {"width": 1660, "height": 182.875},
                                   headers, scope["data"], source,
                                   catalog["components"][TABLE]["sizingPolicy"],
                                   source_height=182.875) == []
    descriptor = catalog["components"][TABLE]
    validate_instance_scope({"props": {}, "slots": {}, "style": {}}, descriptor,
                            {"mode": "fixed", "value": 1660},
                            {"mode": "fixed", "value": 182.875})


def test_adaptive_report_rejects_made_up_dimension_policy():
    catalog, reports, _, _ = resources()
    broken = deepcopy(catalog)
    broken["components"][TABLE]["sizingPolicy"]["width"] = "intrinsic"
    with pytest.raises(registry_module.ComponentError):
        registry_module.ComponentRegistry(broken, reports)


def test_source_geometry_uses_cell_width_only_when_policy_is_fill():
    bundle = load_json(ROOT / "examples/workflow-v03-smoke-figma/source-geometry.json")
    source = next(component for component in bundle["components"]
                  if component["componentType"] == "Table")
    class Registry:
        fingerprint = "test-registry"
        def resolve(self, logical_id, variant):
            assert (logical_id, variant) == (source["logicalComponentId"], source["variant"])
            return {"descriptor": {"componentType": "Table",
                                   "fidelity": {"componentIrSha256": registry_module.digest(source)},
                                   "sizingPolicy": {"width": "fill-cell", "height": "intrinsic"}}}
    geometry = import_module("core.component-resolver.placement").SourceGeometry(
        {**bundle, "components": [source]}, Registry())
    box = {"x": 10, "y": 20, "width": 1660, "height": source["rootBounds"]["height"]}
    placed = geometry.place({"componentId": source["logicalComponentId"],
                             "variant": source["variant"]}, box)
    assert placed["instanceBox"]["width"] == 1660
    assert placed["instanceBox"]["height"] == source["rootBounds"]["height"]
    assert placed["instance"]["layout"]["width"] == {"mode": "fixed", "value": 1660}


def test_native_responsive_pngs_preserve_source_style_outside_column_reflow():
    _, reports, _, _ = resources()
    report = reports["data.table.headed.b334d80b864ecaf53198737bffec5c2bc8d59d337667effacb16ea74dcd024b4.figma-iview-0.2.8"]
    proof = report["sizingMigration"]
    folder = ROOT / ".dev/task-127-evidence"
    for name, expected in proof["nativePngSha256"].items():
        assert sha256((folder / name).read_bytes()).hexdigest() == expected
    original = Image.open(folder / "table-source-1840-native.png").convert("RGB")
    adaptive = Image.open(folder / "table-adaptive-1840-native.png").convert("RGB")
    narrow = Image.open(folder / "table-1660-native.png")
    assert original.size == adaptive.size == (1840, 183)
    assert narrow.size == (1660, 183)
    changed = [(index % 1840, index // 1840)
               for index, pixel in enumerate(ImageChops.difference(original, adaptive).getdata())
               if pixel != (0, 0, 0)]
    assert len(changed) == proof["sourceSizeComparison"]["changedPixels"]
    assert {x // 100 for x, _ in changed} == set(
        proof["sourceSizeComparison"]["changedXBuckets100px"])


def test_page_width_is_a_layout_input_without_a_new_token_or_component():
    source = ROOT / "examples/workflow-v03-smoke-figma"
    analysis = import_module("core.prototype.parser").parse(
        load_json(source / "observations.json"), source)
    tree = import_module("validators.structure.gate").builder.build(analysis)
    plan = load_json(source / "layout-plan.json")
    plan["canvasWidth"] = 1740
    tokens = import_module("core.design-rules.tokens").TokenRegistry(
        load_json(ROOT / "registries/tokens/v0.2.2/default.json"))
    result, report = import_module("core.layout.builder").generate(
        analysis, tree, source, load_json(source / "review.json"), plan, tokens)
    assert report["status"] == "PASS", report["issues"]
    assert result["page"]["layout"]["width"] == {"mode": "fixed", "value": 1740}
