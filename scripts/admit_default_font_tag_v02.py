"""Extend the immutable V0.2.3 snapshot with the fixed enabled Tag."""

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
TAG = "data.tag.default.enabled"
REPORT_ID = TAG + ".default-font-0.2.5"
GATE_PATH = ROOT / "artifacts/task-056/tag-native-fidelity.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build():
    base = ROOT / "registries/components/v0.2.3"
    previous, previous_evidence = read(base / "catalog.json"), read(base / "fidelity-reports.json")
    old = component.ComponentRegistry(previous, previous_evidence)
    gate = read(GATE_PATH)
    if not component.valid_default_font_tag_report(gate) or gate["sourceVersion"] != old.source_version:
        raise ValueError("TASK-056 Tag native fidelity report is not admissible")
    source = read(ROOT / "artifacts/task-054/tag-source/component_ir.json")
    source_tag = next(item for item in source["components"] if item["logicalComponentId"] == TAG)
    scope = gate["contentScopeProposal"]
    if (gate["componentIrSha256"] != component.digest(source_tag)
            or source_tag["props"] != {key: scope[key] for key in
                                       ("size", "color", "closable", "checkable", "checked")}
            or source_tag["content"]["text"] != scope["text"]
            or source_tag["rootBounds"] != {"width": scope["width"], "height": scope["height"]}):
        raise ValueError("Official Tag source changed")
    entry = {"componentType": "Tag", "tier": "base", "status": "active",
             "variants": ["default"], "defaultVariant": "default", "slots": ["label"],
             "contentScope": scope,
             "fidelity": {"reportId": REPORT_ID, "reportSha256": component.digest(gate),
                          "componentIrSha256": gate["componentIrSha256"]}}
    catalog = {**previous, "registryVersion": "0.2.4",
               "libraryVersion": "0.2.4-default-font-query-input-select-table-tag",
               "components": {**previous["components"], TAG: entry}}
    evidence = {**previous_evidence, REPORT_ID: gate}
    registry = component.ComponentRegistry(catalog, evidence)
    bindings = {}
    for platform in ("figma", "penpot"):
        prior = read(ROOT / f"adapters/{platform}/metadata/component-bindings-0.2.3.json")
        metadata = read(ROOT / f"adapters/{platform}/metadata/tag-default-font-fidelity-0.2.5.json")
        candidate_path = ROOT / f"adapters/{platform}/metadata/tag-default-font-candidate-0.2.0.json"
        row = gate["platforms"][platform]
        if (metadata["status"] != "PASS" or metadata["fileReference"] != row["fileReference"]
                or metadata["componentId"] != row["componentId"]
                or metadata["contentScope"] != scope
                or metadata["evidenceSha256"]["tag-native-fidelity.json"] != sha(GATE_PATH)
                or metadata["evidenceSha256"]["candidate-metadata.json"] != sha(candidate_path)
                or row["candidateMetadataSha256"] != sha(candidate_path)):
            raise ValueError("Tag native binding evidence changed: " + platform)
        binding = {**prior, "libraryVersion": registry.library_version,
                   "registrySha256": registry.fingerprint,
                   "bindings": {**prior["bindings"], TAG: {"variants": {"default": {
                       "kind": "component", "fileReference": row["fileReference"],
                       "componentReference": row["componentId"],
                       "fidelityReportSha256": entry["fidelity"]["reportSha256"]}}}}}
        ComponentBindings(binding, registry, platform=platform)
        bindings[platform] = binding
    target = ROOT / "registries/components/v0.2.4"
    write(target / "catalog.json", catalog)
    write(target / "fidelity-reports.json", evidence)
    for platform, binding in bindings.items():
        write(ROOT / f"adapters/{platform}/metadata/component-bindings-0.2.4.json", binding)
    write(target / "admission.json", {"version": "0.2.4", "status": "PASS",
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
