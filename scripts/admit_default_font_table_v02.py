"""Extend the immutable V0.2.2 snapshot with one fixed 3x3 Table."""

import hashlib
import json
from pathlib import Path
import sys
from importlib import import_module

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adapters.component_bindings import ComponentBindings


component = import_module("core.component-resolver.registry")
ROOT = Path(__file__).resolve().parents[1]
TABLE = "data.table.default"
REPORT_ID = "data.table.default.default-font-0.2.5"
GATE_PATH = ROOT / "artifacts/task-040/table-native-fidelity.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build():
    base = ROOT / "registries/components/v0.2.2"
    previous = json.loads((base / "catalog.json").read_text(encoding="utf-8"))
    previous_evidence = json.loads((base / "fidelity-reports.json").read_text(encoding="utf-8"))
    old = component.ComponentRegistry(previous, previous_evidence)
    gate = json.loads(GATE_PATH.read_text(encoding="utf-8"))
    if not component.valid_default_font_table_report(gate) or gate["sourceVersion"] != old.source_version:
        raise ValueError("TASK-040 Table native fidelity report is not admissible")
    source = json.loads((ROOT / "examples/acceptance-prototype/source-geometry.json").read_text(encoding="utf-8"))
    source_table = next(item for item in source["components"] if item["logicalComponentId"] == TABLE)
    source_scope = {key: gate["contentScopeProposal"][key]
                    for key in ("showHeader", "border", "stripe", "columns", "data")}
    if (gate["componentIrSha256"] != component.digest(source_table)
            or source_table["props"] != source_scope
            or source_table["rootBounds"] != {"width": 1392, "height": 144}):
        raise ValueError("Official Table source changed")
    entry = {"componentType": "Table", "tier": "base", "status": "active",
             "variants": ["default"], "defaultVariant": "default", "slots": [],
             "contentScope": gate["contentScopeProposal"],
             "fidelity": {"reportId": REPORT_ID, "reportSha256": component.digest(gate),
                          "componentIrSha256": gate["componentIrSha256"]}}
    catalog = {**previous, "registryVersion": "0.2.3",
               "libraryVersion": "0.2.3-default-font-query-input-select-table",
               "components": {**previous["components"], TABLE: entry}}
    evidence = {**previous_evidence, REPORT_ID: gate}
    registry = component.ComponentRegistry(catalog, evidence)
    bindings = {}
    for platform in ("figma", "penpot"):
        prior = json.loads((ROOT / f"adapters/{platform}/metadata/component-bindings-0.2.2.json").read_text(encoding="utf-8"))
        metadata_path = ROOT / f"adapters/{platform}/metadata/table-default-font-fidelity-0.2.5.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        candidate_path = ROOT / f"adapters/{platform}/metadata/table-default-font-candidate-0.2.0.json"
        row = gate["platforms"][platform]
        if (metadata["status"] != "PASS" or metadata["fileReference"] != row["fileReference"]
                or metadata["componentId"] != row["componentId"]
                or metadata["evidenceSha256"]["table-native-fidelity.json"] != sha(GATE_PATH)
                or metadata["evidenceSha256"]["candidate-metadata.json"] != sha(candidate_path)
                or row["candidateMetadataSha256"] != sha(candidate_path)):
            raise ValueError("Table native binding evidence changed: " + platform)
        binding = {**prior, "libraryVersion": registry.library_version,
                   "registrySha256": registry.fingerprint,
                   "bindings": {**prior["bindings"], TABLE: {"variants": {"default": {
                       "kind": "component", "fileReference": row["fileReference"],
                       "componentReference": row["componentId"],
                       "fidelityReportSha256": entry["fidelity"]["reportSha256"]}}}}}
        ComponentBindings(binding, registry, platform=platform)
        bindings[platform] = binding
    target = ROOT / "registries/components/v0.2.3"
    write(target / "catalog.json", catalog)
    write(target / "fidelity-reports.json", evidence)
    for platform, binding in bindings.items():
        write(ROOT / f"adapters/{platform}/metadata/component-bindings-0.2.3.json", binding)
    write(target / "admission.json", {"version": "0.2.3", "status": "PASS",
        "registryAdmission": "PASS", "registrySha256": registry.fingerprint,
        "components": {logical_id: {"contentScope": row["contentScope"],
                         "fidelityReportSha256": row["fidelity"]["reportSha256"]}
                       for logical_id, row in catalog["components"].items()},
        "bindings": {platform: {logical_id: {"fileReference": item["variants"]["default"]["fileReference"],
                                              "componentReference": item["variants"]["default"]["componentReference"]}
                                for logical_id, item in binding["bindings"].items()}
                     for platform, binding in bindings.items()},
        "scopedPageGenerationReady": True, "releaseReady": False})
    return {"status": "PASS", "registrySha256": registry.fingerprint,
            "activeComponents": list(catalog["components"])}


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False))
