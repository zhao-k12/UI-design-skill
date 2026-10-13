"""Extend the immutable V0.2.0 Button snapshot with one fixed-placeholder Input."""
import hashlib
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from importlib import import_module
from adapters.component_bindings import ComponentBindings

component = import_module("core.component-resolver.registry")
ROOT = Path(__file__).resolve().parents[1]
BUTTON = "action.button.primary.medium"
INPUT = "form.input.default.medium"
REPORT_ID = "form.input.default.medium.default-font-0.2.3"
GATE_PATH = ROOT / "artifacts/task-034/input-native-fidelity.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build():
    base = ROOT / "registries/components/v0.2.0"
    previous = json.loads((base / "catalog.json").read_bytes())
    previous_evidence = json.loads((base / "fidelity-reports.json").read_bytes())
    old = component.ComponentRegistry(previous, previous_evidence)
    gate = json.loads(GATE_PATH.read_bytes())
    if not component.valid_default_font_input_report(gate) or gate["sourceVersion"] != old.source_version:
        raise ValueError("TASK-034 Input native fidelity report is not admissible")
    source = json.loads((ROOT / "artifacts/task-023/replay-final/first/component_ir.json").read_bytes())
    source_input = next(item for item in source["components"] if item["logicalComponentId"] == INPUT)
    if (gate["componentIrSha256"] != component.digest(source_input)
            or source_input["props"]["modelValue"] != ""
            or source_input["props"]["placeholder"] != "请输入姓名"):
        raise ValueError("Official Input source changed")
    entry = {"componentType": "Input", "tier": "base", "status": "active",
             "variants": ["default"], "defaultVariant": "default", "slots": [],
             "contentScope": gate["contentScopeProposal"],
             "fidelity": {"reportId": REPORT_ID, "reportSha256": component.digest(gate),
                          "componentIrSha256": gate["componentIrSha256"]}}
    catalog = {**previous, "registryVersion": "0.2.1",
               "libraryVersion": "0.2.1-default-font-query-input",
               "components": {**previous["components"], INPUT: entry}}
    evidence = {**previous_evidence, REPORT_ID: gate}
    registry = component.ComponentRegistry(catalog, evidence)
    bindings = {}
    for platform in ("figma", "penpot"):
        prior_path = ROOT / f"adapters/{platform}/metadata/component-bindings-0.2.0.json"
        prior_binding = json.loads(prior_path.read_bytes())
        metadata_path = ROOT / f"adapters/{platform}/metadata/input-default-font-fidelity-0.2.3.json"
        metadata = json.loads(metadata_path.read_bytes())
        candidate_path = ROOT / f"adapters/{platform}/metadata/input-default-font-candidate-0.2.0.json"
        row = gate["platforms"][platform]
        if (metadata["status"] != "PASS" or metadata["fileReference"] != row["fileReference"]
                or metadata["componentId"] != row["componentId"]
                or metadata["evidenceSha256"]["input-native-fidelity.json"] != sha(GATE_PATH)
                or metadata["evidenceSha256"]["candidate-metadata.json"] != sha(candidate_path)
                or row["candidateMetadataSha256"] != sha(candidate_path)):
            raise ValueError("Input native binding evidence changed: " + platform)
        binding = {**prior_binding, "libraryVersion": registry.library_version,
                   "registrySha256": registry.fingerprint,
                   "bindings": {**prior_binding["bindings"], INPUT: {"variants": {"default": {
                       "kind": "component", "fileReference": row["fileReference"],
                       "componentReference": row["componentId"],
                       "fidelityReportSha256": entry["fidelity"]["reportSha256"]}}}}}
        ComponentBindings(binding, registry, platform=platform)
        bindings[platform] = binding
    target = ROOT / "registries/components/v0.2.1"
    write(target / "catalog.json", catalog)
    write(target / "fidelity-reports.json", evidence)
    for platform, binding in bindings.items():
        write(ROOT / f"adapters/{platform}/metadata/component-bindings-0.2.1.json", binding)
    write(target / "admission.json", {"version": "0.2.1", "status": "PASS",
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
