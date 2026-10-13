"""Extend the immutable V0.2.1 snapshot with one fixed-value Select."""

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
SELECT = "form.select.default.medium"
REPORT_ID = "form.select.default.medium.default-font-0.2.4"
GATE_PATH = ROOT / "artifacts/task-037/select-native-fidelity.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build():
    base = ROOT / "registries/components/v0.2.1"
    previous = json.loads((base / "catalog.json").read_text(encoding="utf-8"))
    previous_evidence = json.loads((base / "fidelity-reports.json").read_text(encoding="utf-8"))
    old = component.ComponentRegistry(previous, previous_evidence)
    gate = json.loads(GATE_PATH.read_text(encoding="utf-8"))
    if not component.valid_default_font_select_report(gate) or gate["sourceVersion"] != old.source_version:
        raise ValueError("TASK-037 Select native fidelity report is not admissible")
    source = json.loads((ROOT / "artifacts/task-023/replay-final/first/component_ir.json").read_text(encoding="utf-8"))
    source_select = next(item for item in source["components"] if item["logicalComponentId"] == SELECT)
    if (gate["componentIrSha256"] != component.digest(source_select)
            or source_select["props"]["modelValue"] != "enabled"
            or source_select["rootBounds"] != {"width": 240, "height": 32}):
        raise ValueError("Official Select source changed")
    entry = {"componentType": "Select", "tier": "base", "status": "active",
             "variants": ["default"], "defaultVariant": "default", "slots": [],
             "contentScope": gate["contentScopeProposal"],
             "fidelity": {"reportId": REPORT_ID, "reportSha256": component.digest(gate),
                          "componentIrSha256": gate["componentIrSha256"]}}
    catalog = {**previous, "registryVersion": "0.2.2",
               "libraryVersion": "0.2.2-default-font-query-input-select",
               "components": {**previous["components"], SELECT: entry}}
    evidence = {**previous_evidence, REPORT_ID: gate}
    registry = component.ComponentRegistry(catalog, evidence)
    bindings = {}
    for platform in ("figma", "penpot"):
        prior_binding = json.loads((ROOT / f"adapters/{platform}/metadata/component-bindings-0.2.1.json").read_text(encoding="utf-8"))
        metadata_path = ROOT / f"adapters/{platform}/metadata/select-default-font-fidelity-0.2.4.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        candidate_path = ROOT / f"adapters/{platform}/metadata/select-default-font-candidate-0.2.0.json"
        row = gate["platforms"][platform]
        if (metadata["status"] != "PASS" or metadata["fileReference"] != row["fileReference"]
                or metadata["componentId"] != row["componentId"]
                or metadata["evidenceSha256"]["select-native-fidelity.json"] != sha(GATE_PATH)
                or metadata["evidenceSha256"]["candidate-metadata.json"] != sha(candidate_path)
                or row["candidateMetadataSha256"] != sha(candidate_path)):
            raise ValueError("Select native binding evidence changed: " + platform)
        binding = {**prior_binding, "libraryVersion": registry.library_version,
                   "registrySha256": registry.fingerprint,
                   "bindings": {**prior_binding["bindings"], SELECT: {"variants": {"default": {
                       "kind": "component", "fileReference": row["fileReference"],
                       "componentReference": row["componentId"],
                       "fidelityReportSha256": entry["fidelity"]["reportSha256"]}}}}}
        ComponentBindings(binding, registry, platform=platform)
        bindings[platform] = binding
    target = ROOT / "registries/components/v0.2.2"
    write(target / "catalog.json", catalog)
    write(target / "fidelity-reports.json", evidence)
    for platform, binding in bindings.items():
        write(ROOT / f"adapters/{platform}/metadata/component-bindings-0.2.2.json", binding)
    write(target / "admission.json", {"version": "0.2.2", "status": "PASS",
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
