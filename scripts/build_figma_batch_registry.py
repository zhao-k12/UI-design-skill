"""Build an immutable 18-component Figma profile from the audited 11-type batch."""
from copy import deepcopy
from importlib import import_module
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapters.component_bindings import ComponentBindings
from scripts.audit_figma_candidate_batch import audit as audit_batch
from scripts.audit_v02_component_coverage_figma import FIGMA_ONLY_TASKS
from validators.ui_ir import load_json

registry_module = import_module("core.component-resolver.registry")
VERSION = "0.2.7"
LIBRARY = "0.2.7-figma-fixed-eighteen"


def build(root=ROOT):
    root = Path(root)
    batch = audit_batch(root)
    if batch.get("status") != "PASS" or batch.get("candidateCount") != 11:
        raise ValueError("All eleven Figma candidate evidence rows must PASS")
    catalog = deepcopy(load_json(root / "registries/components/v0.2.6/catalog.json"))
    reports = deepcopy(load_json(root / "registries/components/v0.2.6/fidelity-reports.json"))
    old_binding = load_json(root / "adapters/figma/metadata/component-bindings-0.2.6.json")
    binding = deepcopy(old_binding)
    catalog.update(registryVersion=VERSION, libraryVersion=LIBRARY)
    binding["libraryVersion"] = LIBRARY
    for row in batch["rows"]:
        if row.get("status") != "PASS":
            raise ValueError("Candidate failed: " + str(row.get("componentType")))
        kind = row["componentType"]
        task = FIGMA_ONLY_TASKS[kind]
        qa_paths = list((root / f"artifacts/task-{task:03d}").glob("*-figma-qa.json"))
        if len(qa_paths) != 1:
            raise ValueError("Candidate QA ambiguous: " + kind)
        qa = load_json(qa_paths[0])
        native = qa.get("platforms", {}).get("figma", {}).get("evidenceSha256") or qa.get("evidenceSha256", {})
        scope = {"kind": "fixed-native-snapshot", "props": row["sourceProps"],
                 "visibleText": row["nativeVisibleText"],
                 "width": row["sourceSize"]["width"],
                 "height": row["sourceSize"]["height"]}
        report_id = row["logicalComponentId"] + ".figma-batch-0.2.8"
        report = {
            "scope": "production", "gateVersion": "0.2.8-figma-batch",
            "status": "PASS", "logicalComponentId": row["logicalComponentId"],
            "componentType": kind, "variants": [row["sourceVariant"]],
            "sourceVersion": catalog["sourceVersion"],
            "componentIrSha256": row["sourceComponentIrSha256"],
            "contentScopeProposal": scope, "admissionEligible": True, "issues": [],
            "platforms": {"figma": {"status": "PASS",
                                    "fileReference": row["figmaFileReference"],
                                    "componentId": row["figmaComponentId"]}},
            "evidenceSha256": {"sourceComponentIr": row["sourceComponentIrSha256"],
                               "sourceScreenshot": row["sourceScreenshotSha256"],
                               "figmaQa": row["figmaQaSha256"],
                               "nativeRead": native["native-read.json"],
                               "nativePng": native["native.png"],
                               "nativeSvg": native["native.svg"]},
        }
        report_sha = registry_module.digest(report)
        reports[report_id] = report
        logical_id = row["logicalComponentId"]
        catalog["components"][logical_id] = {
            "componentType": kind,
            "tier": "base", "status": "active",
            "variants": [row["sourceVariant"]],
            "defaultVariant": row["sourceVariant"], "slots": [],
            "contentScope": scope,
            "fidelity": {"reportId": report_id, "reportSha256": report_sha,
                         "componentIrSha256": row["sourceComponentIrSha256"]},
        }
        binding["bindings"][logical_id] = {"variants": {row["sourceVariant"]: {
            "kind": "component", "fileReference": row["figmaFileReference"],
            "componentReference": row["figmaComponentId"],
            "fidelityReportSha256": report_sha}}}
    registry = registry_module.ComponentRegistry(catalog, reports)
    binding["registrySha256"] = registry.fingerprint
    ComponentBindings(binding, registry, platform="figma")
    if len(catalog["components"]) != 18 or len(binding["bindings"]) != 18:
        raise ValueError("Figma Registry/binding must include exactly 18 components")
    admission = {"version": VERSION, "scope": "figma-only-production",
                 "status": "PASS", "registryAdmission": "PASS",
                 "registrySha256": registry.fingerprint,
                 "components": {logical_id: {
                     "contentScope": entry["contentScope"],
                     "fidelityReportSha256": entry["fidelity"]["reportSha256"]}
                     for logical_id, entry in catalog["components"].items()},
                 "bindings": {"figma": {logical_id: {
                     "fileReference": reference["variants"][catalog["components"][logical_id]["defaultVariant"]]["fileReference"],
                     "componentReference": reference["variants"][catalog["components"][logical_id]["defaultVariant"]]["componentReference"]}
                     for logical_id, reference in binding["bindings"].items()}},
                 "scopedPageGenerationReady": True,
                 "releaseReady": False}
    return {"catalog.json": catalog, "fidelity-reports.json": reports,
            "admission.json": admission,
            "component-bindings-0.2.7-figma.json": binding}


def write(outputs, root=ROOT):
    root = Path(root)
    destinations = {name: root / ("adapters/figma/metadata" if name.startswith("component-bindings")
                                else "registries/components/v0.2.7") / name
                    for name in outputs}
    encoded = {name: (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
               for name, value in outputs.items()}
    for name, path in destinations.items():
        if path.exists() and path.read_bytes() != encoded[name]:
            raise ValueError("Existing Registry snapshot differs: " + str(path))
    for name, path in destinations.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(encoded[name])
    return destinations


if __name__ == "__main__":
    result = write(build())
    print(json.dumps({"status": "PASS", "componentCount": 18,
                      "paths": [str(path) for path in result.values()]}, ensure_ascii=False))
