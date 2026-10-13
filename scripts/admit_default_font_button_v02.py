"""Build the isolated, fixed-content V0.2 Button registry from TASK-031 evidence."""
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
REPORT = ROOT / "artifacts/task-031/button-native-fidelity.json"
REPORT_ID = "action.button.primary.medium.default-font-0.2.2"
LOGICAL_ID = "action.button.primary.medium"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build():
    report = json.loads(REPORT.read_bytes())
    if not component.valid_default_font_button_report(report) or report.get("status") != "PASS":
        raise ValueError("TASK-031 native fidelity evidence is not admissible")
    prior = json.loads((ROOT / "registries/components/catalog.json").read_bytes())
    if report["sourceVersion"] != prior["sourceVersion"]:
        raise ValueError("Source version mismatch")
    source = json.loads((ROOT / "artifacts/task-023/replay-final/first/component_ir.json").read_bytes())
    button = next(item for item in source["components"] if item["logicalComponentId"] == LOGICAL_ID)
    if report["componentIrSha256"] != component.digest(button) or button["content"]["text"] != "查询":
        raise ValueError("Source Button changed")
    entry = {"componentType": "Button", "tier": "base", "status": "active",
             "variants": ["default"], "defaultVariant": "default", "slots": ["label"],
             "contentScope": {"kind": "fixed-native-content", "text": "查询", "width": 60, "height": 32},
             "fidelity": {"reportId": REPORT_ID, "reportSha256": component.digest(report),
                          "componentIrSha256": report["componentIrSha256"]}}
    catalog = {"registryVersion": "0.2.0", "libraryVersion": "0.2.0-default-font-query",
               "sourceVersion": report["sourceVersion"], "scope": "production",
               "components": {LOGICAL_ID: entry}}
    registry = component.ComponentRegistry(catalog, {REPORT_ID: report})
    bindings = {}
    for platform in ("figma", "penpot"):
        row = report["platforms"][platform]
        metadata = ROOT / f"adapters/{platform}/metadata/button-default-font-fidelity-0.2.2.json"
        declared = json.loads(metadata.read_bytes())
        candidate = ROOT / f"adapters/{platform}/metadata/button-default-font-candidate-0.2.0.json"
        if (declared["status"] != "PASS" or declared["fileReference"] != row["fileReference"]
                or declared["componentId"] != row["componentId"]
                or declared["evidenceSha256"]["button-native-fidelity.json"] != sha(REPORT)
                or report["evidenceSha256"][platform]["candidateMetadataSha256"] != sha(candidate)):
            raise ValueError("Platform native evidence mismatch: " + platform)
        binding = {"metadataVersion": "0.1.0", "platform": platform, "scope": "production",
                   "libraryVersion": registry.library_version, "sourceVersion": registry.source_version,
                   "registrySha256": registry.fingerprint,
                   "bindings": {LOGICAL_ID: {"variants": {"default": {
                       "kind": "component", "fileReference": row["fileReference"],
                       "componentReference": row["componentId"],
                       "fidelityReportSha256": entry["fidelity"]["reportSha256"]}}}}}
        ComponentBindings(binding, registry, platform=platform)
        bindings[platform] = binding
    base = ROOT / "registries/components/v0.2.0"
    write(base / "catalog.json", catalog)
    write(base / "fidelity-reports.json", {REPORT_ID: report})
    for platform, binding in bindings.items():
        write(ROOT / f"adapters/{platform}/metadata/component-bindings-0.2.0.json", binding)
    write(base / "admission.json", {
        "version": "0.2.0", "status": "PASS", "registryAdmission": "PASS",
        "logicalComponentId": LOGICAL_ID, "variant": "default",
        "contentScope": entry["contentScope"], "registrySha256": registry.fingerprint,
        "fidelityReportSha256": entry["fidelity"]["reportSha256"],
        "bindings": {platform: {"fileReference": report["platforms"][platform]["fileReference"],
                                "componentReference": report["platforms"][platform]["componentId"]}
                     for platform in bindings},
        "scopedPageGenerationReady": True, "releaseReady": False})
    return {"status": "PASS", "registrySha256": registry.fingerprint,
            "contentScope": entry["contentScope"], "platforms": {
                platform: value["bindings"][LOGICAL_ID]["variants"]["default"]["componentReference"]
                for platform, value in bindings.items()}}


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False))
