"""Derive an independently locked V0.2 input package from approved source evidence."""

from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SOURCE = ROOT / "examples/acceptance-prototype"
TARGET = ROOT / "examples/acceptance-prototype-v02"
ENVELOPE = ROOT / "artifacts/task-050/text-envelope.json"
OLD_CAPTURE = ROOT / "adapters/figma/metadata/list-independent-readback.json"
GEOMETRY = TARGET / "source-geometry.json"
CATALOG = ROOT / "registries/components/v0.2.3/catalog.json"
FIDELITY = ROOT / "registries/components/v0.2.3/fidelity-reports.json"
TOKENS = ROOT / "registries/tokens/v0.2.2/default.json"
ICON_BINDINGS = ROOT / "adapters/penpot/metadata/icon-bindings-0.2.0.json"
INSTANCE_COMPONENTS = {
    "button.query": "action.button.primary.medium",
    "input.name": "form.input.default.medium",
    "select.status": "form.select.default.medium",
    "table.body": "data.table.default",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def compose(rows: dict, recipe: dict, spacing: int) -> tuple[float, float]:
    nodes = [rows[i] for i in recipe["uiIrIds"]]
    if recipe["widthRule"] == "max":
        width = max(n["width"] for n in nodes)
    elif recipe["widthRule"] == "sum-with-spacing.sm":
        width = sum(n["width"] for n in nodes) + spacing
    else:
        raise ValueError("Unknown width composition")
    if recipe["heightRule"] == "max":
        height = max(n["height"] for n in nodes)
    elif recipe["heightRule"] == "sum":
        height = sum(n["height"] for n in nodes)
    else:
        raise ValueError("Unknown height composition")
    return width, height


def main() -> None:
    envelope, old, catalog, tokens, geometry = map(load, (ENVELOPE, OLD_CAPTURE, CATALOG, TOKENS, GEOMETRY))
    if envelope["status"] != "PASS" or len(envelope["rows"]) != 12:
        raise ValueError("Incomplete default-font text envelope")
    for platform, source in envelope["sources"].items():
        path = ROOT / source["path"]
        if digest(path) != source["sha256"]:
            raise ValueError(f"Changed {platform} text capture")
    if geometry["status"] != "PASS" or catalog["libraryVersion"] != "0.2.3-default-font-query-input-select-table":
        raise ValueError("Unaccepted V0.2 component geometry")
    component_bounds = {component["logicalComponentId"]: component["rootBounds"] for component in geometry["components"]}
    old_rows = {row["uiIrId"]: row for row in old["evidence"]}
    text_rows = {row["uiIrId"]: row for row in envelope["rows"]}
    if len(old_rows) != len(old["evidence"]) or not set(text_rows) <= set(old_rows):
        raise ValueError("Changed source node identity")
    rows = []
    for key, old_row in old_rows.items():
        if key in text_rows:
            item = text_rows[key]
            if item["characters"] != old_row["characters"]:
                raise ValueError(f"Source text changed: {key}")
            rows.append({"uiIrId": key, "type": "TEXT", "characters": item["characters"],
                         "width": item["width"], "height": item["height"],
                         "provenance": {"kind": "two-platform-default-font-envelope", "row": key}})
            continue
        if key in INSTANCE_COMPONENTS:
            component = INSTANCE_COMPONENTS[key]
            bounds = component_bounds[component]
            admitted = catalog["components"][component]["contentScope"]
            if any(old_row[axis] != bounds[axis] or bounds[axis] != admitted[axis] for axis in ("width", "height")):
                raise ValueError(f"Component dimensions differ: {key}")
            provenance = {"kind": "admitted-v02-component-ir", "logicalComponentId": component}
        elif key in ("header.settings", "list.export"):
            if (old_row["width"], old_row["height"]) != (24, 24):
                raise ValueError(f"Functional icon dimensions differ: {key}")
            provenance = {"kind": "admitted-remix-icon", "sourceUiIrId": key}
        else:
            provenance = {"kind": "frozen-source-container-geometry", "sourceUiIrId": key}
        rows.append({"uiIrId": key, "type": old_row["type"],
                     "width": old_row["width"], "height": old_row["height"],
                     "provenance": provenance})
    capture = {
        "kind": "v02-derived-runtime-measurement-capture", "status": "PASS",
        "method": "Fixed source container geometry + admitted V0.2 components/icons + two-platform text envelope",
        "sourceLocks": {
            "sourceContainers": {"path": OLD_CAPTURE.relative_to(ROOT).as_posix(), "sha256": digest(OLD_CAPTURE)},
            "sourceGeometry": {"path": GEOMETRY.relative_to(ROOT).as_posix(), "sha256": digest(GEOMETRY)},
            "componentCatalog": {"path": CATALOG.relative_to(ROOT).as_posix(), "sha256": digest(CATALOG)},
            "iconBindings": {"path": ICON_BINDINGS.relative_to(ROOT).as_posix(), "sha256": digest(ICON_BINDINGS)},
            "textEnvelope": {"path": ENVELOPE.relative_to(ROOT).as_posix(), "sha256": digest(ENVELOPE)},
        },
        "evidence": rows,
    }
    TARGET.mkdir(parents=True, exist_ok=True)
    for name in ("prototype.txt", "observations.json", "review.json", "decisions.json"):
        shutil.copyfile(SOURCE / name, TARGET / name)
    capture_path = TARGET / "runtime-capture.json"
    save(capture_path, capture)
    source_metrics = load(SOURCE / "runtime-measurements.json")
    spacing = tokens["tokens"]["spacing.sm"]["value"]
    keyed = {row["uiIrId"]: row for row in rows}
    for recipe in source_metrics["measurements"].values():
        recipe["width"], recipe["height"] = compose(keyed, recipe, spacing)
    source_metrics.update({"version": "0.2.0", "sourceCapture": capture_path.relative_to(ROOT).as_posix(),
                           "sourceCaptureSha256": digest(capture_path)})
    save(TARGET / "runtime-measurements.json", source_metrics)
    plan = load(SOURCE / "layout-plan.json")
    plan["tokenRegistrySha256"] = importlib.import_module("core.design-rules.tokens").TokenRegistry(tokens).fingerprint
    for key, recipe in source_metrics["measurements"].items():
        plan["measurements"][key]["width"] = recipe["width"]
        plan["measurements"][key]["height"] = recipe["height"]
    save(TARGET / "layout-plan.json", plan)
    token_registry = importlib.import_module("core.design-rules.tokens").TokenRegistry(tokens)
    registry = importlib.import_module("core.component-resolver.registry").ComponentRegistry(catalog, load(FIDELITY))
    analysis = load(SOURCE / "prototype_analysis.json")
    page_tree = load(SOURCE / "page_tree.json")
    review = load(TARGET / "review.json")
    layout_builder = importlib.import_module("core.layout.builder")
    tree, layout_report = layout_builder.generate(analysis, page_tree, TARGET, review, plan, token_registry)
    if layout_report["status"] != "PASS":
        raise ValueError("Migrated layout failed")
    decisions = load(SOURCE / "decisions.json")
    decisions["layoutTreeSha256"] = importlib.import_module("validators.structure.gate").builder.fingerprint(tree)
    decisions["registrySha256"] = registry.fingerprint
    save(TARGET / "decisions.json", decisions)
    resolver = importlib.import_module("core.component-resolver.primitive_mapping")
    mapping = resolver.resolve(analysis, page_tree, TARGET, review, plan, decisions, registry,
                               token_registry, allow_text_primitives=True)
    if mapping["status"] != "PASS":
        raise ValueError(f"Migrated component mapping failed: {mapping['status']} {mapping['issues']} "
                         f"{[(r['sourceId'], r['status']) for r in mapping['rows']]}")
    content = load(SOURCE / "content.json")
    content["mappingSha256"] = importlib.import_module("validators.structure.gate").builder.fingerprint(mapping)
    for item in content["items"]:
        if "textSize" in item:
            row = keyed[source_metrics["textMeasurements"][item["sourceId"]]]
            item["textSize"] = {axis: row[axis] for axis in ("width", "height")}
        for children in item.get("cellSlots", {}).values():
            for child in children:
                if child["type"] == "Text":
                    row = keyed[source_metrics["slotMeasurements"][child["id"]]]
                    for axis in ("width", "height"):
                        child["layout"][axis]["value"] = row[axis]
    save(TARGET / "content.json", content)
    versions = load(SOURCE / "versions.json")
    versions["component_library_version"] = catalog["libraryVersion"]
    versions["design_token_version"] = tokens["registryVersion"]
    versions["figma_adapter_version"] = "0.1.0"
    versions["penpot_adapter_version"] = "0.1.0"
    save(TARGET / "versions.json", versions)
    package_files = ("prototype.txt", "observations.json", "review.json", "decisions.json", "source-geometry.json",
                     "runtime-capture.json", "runtime-measurements.json", "layout-plan.json", "content.json", "versions.json")
    save(TARGET / "input-manifest.json", {
        "kind": "v02-independent-input-package", "status": "READY_FOR_PREFLIGHT",
        "sourcePackage": SOURCE.relative_to(ROOT).as_posix(),
        "policy": "fixed-source-containers/admitted-v02-components/max-default-font-text",
        "files": {name: digest(TARGET / name) for name in package_files},
    })
    print("V0.2 input package built; native final-page acceptance has not run")


if __name__ == "__main__":
    main()
