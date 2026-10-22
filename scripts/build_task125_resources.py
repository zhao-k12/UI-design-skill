"""Version the independently verified iView list-page resources for TASK-125."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from adapters.component_bindings import ComponentBindings
from validators.ui_ir import load_json
from workflow_v03.core import write

SOURCE = ROOT / "artifacts/task-125"
VERSION = "0.2.8"


def _sha(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def build():
    qa = load_json(SOURCE / "table-candidate-qa.json")
    request = load_json(SOURCE / "table-source-request-1840.json")
    native = load_json(SOURCE / "figma-1840-readback.json")
    source = load_json(SOURCE / "headed-table-source-1840/table-source-report.json")
    if qa["status"] != "PASS" or not all(qa["checks"].values()):
        raise ValueError("Table candidate fidelity review is not PASS")
    expected = {
        "sourceComponentIr": source["componentIrSha256"],
        "sourceScreenshot": source["screenshot"]["sha256"],
        "nativeRead": _sha(SOURCE / "figma-1840-readback.json"),
        "nativePng": _sha(SOURCE / "figma-1840-linked.png"),
        "nativeSvg": _sha(SOURCE / "figma-1840-linked.svg"),
    }
    if _sha(SOURCE / "headed-table-source-1840/component_ir.json") != source["componentIrSha256"]:
        raise ValueError("Official component IR changed")
    if _sha(next((SOURCE / "headed-table-source-1840").glob("data.table.headed.*.png"))) != source["screenshot"]["sha256"]:
        raise ValueError("Official screenshot changed")
    if any(qa["evidenceSha256"][key] != value for key, value in expected.items()):
        raise ValueError("Table candidate evidence changed")
    if native["instance"]["mainComponentReference"] != qa["componentReference"]:
        raise ValueError("Table main component is no longer the tested instance source")
    if qa["logicalComponentId"] != source["componentId"]:
        raise ValueError("Official source component ID differs")

    catalog_schema = load_json(ROOT / "schemas/component-registry-0.2.7.schema.json")
    catalog_schema["$id"] = "urn:ui-design-skill:component-registry:0.2.8"
    catalog_schema["title"] = "Logical Component Registry V0.2.8 Figma iView list page"
    catalog_schema["properties"]["registryVersion"]["const"] = VERSION
    scopes = catalog_schema["properties"]["components"]["additionalProperties"]["properties"]["contentScope"]["oneOf"]
    snapshot = scopes[1]
    snapshot["properties"]["height"] = {"type": "number", "exclusiveMinimum": 0}
    snapshot["properties"]["showHeader"] = {"type": "boolean"}
    snapshot["properties"]["border"] = {"type": "boolean"}
    snapshot["properties"]["stripe"] = {"type": "boolean"}
    snapshot["properties"]["columns"] = {"type": "array"}
    snapshot["properties"]["data"] = {"type": "array"}

    token_schema = load_json(ROOT / "schemas/token-registry-0.2.2.schema.json")
    token_schema["$id"] = "urn:ui-design-skill:token-registry:0.2.3"
    token_schema["properties"]["registryVersion"]["const"] = "0.2.3"
    token_schema["properties"]["provenance"]["properties"]["kind"]["const"] = "project-iview-migration"
    tokens = load_json(ROOT / "registries/tokens/v0.2.2/default.json")
    tokens["registryVersion"] = "0.2.3"
    tokens["name"] = "v0.2.3-figma-iview-list-page-default-font"
    tokens["provenance"] = {"kind": "project-iview-migration",
                            "description": "View UI Plus 1.3.24 page palette with approved Figma default font."}
    for token, value in {"color.primary": "#2d8cf0", "color.text": "#515a6e",
                         "color.page": "#f5f7f9", "color.border": "#dcdee2"}.items():
        tokens["tokens"][token]["value"] = value

    catalog = load_json(ROOT / "registries/components/v0.2.7/catalog.json")
    reports = load_json(ROOT / "registries/components/v0.2.7/fidelity-reports.json")
    binding = load_json(ROOT / "adapters/figma/metadata/component-bindings-0.2.7-figma.json")
    catalog["registryVersion"] = VERSION
    catalog["libraryVersion"] = "0.2.8-figma-iview-list-page"
    binding["libraryVersion"] = catalog["libraryVersion"]
    visible = [col["title"] for col in request["columns"]] + [
        row[col["key"]] for row in request["records"] for col in request["columns"]]
    content_scope = {"kind": "fixed-native-snapshot",
                     "props": {"showHeader": True, "border": False, "stripe": False,
                               "columns": request["columns"], "data": request["records"]},
                     "visibleText": visible, "showHeader": True,
                     "border": False, "stripe": False,
                     "columns": request["columns"], "data": request["records"],
                     "width": 1840, "height": 182.875}
    report_id = qa["logicalComponentId"] + ".figma-iview-0.2.8"
    registry_module = __import__("importlib").import_module("core.component-resolver.registry")
    source_component = load_json(SOURCE / "headed-table-source-1840/component_ir.json")["components"][0]
    component_digest = registry_module.digest(source_component)
    report = {"scope": "production", "gateVersion": "0.2.8-figma-batch",
              "status": "PASS", "logicalComponentId": qa["logicalComponentId"],
              "componentType": "Table", "variants": ["default"],
              "sourceVersion": catalog["sourceVersion"],
              "componentIrSha256": component_digest,
              "contentScopeProposal": content_scope,
              "admissionEligible": True, "issues": [],
              "platforms": {"figma": {"status": "PASS", "fileReference": native["fileReference"],
                                      "componentId": qa["componentReference"]}},
              "evidenceSha256": {"sourceComponentIr": component_digest,
                                 "sourceBundleSha256": source["componentIrSha256"],
                                 "sourceScreenshot": source["screenshot"]["sha256"],
                                 "figmaQa": _sha(SOURCE / "table-candidate-qa.json"),
                                 "nativeRead": expected["nativeRead"],
                                 "nativePng": expected["nativePng"],
                                 "nativeSvg": expected["nativeSvg"]}}
    report_sha = registry_module.digest(report)
    reports[report_id] = report
    catalog["components"][qa["logicalComponentId"]] = {
        "componentType": "Table", "tier": "base", "status": "active",
        "variants": ["default"], "defaultVariant": "default", "slots": [],
        "contentScope": content_scope,
        "fidelity": {"reportId": report_id, "reportSha256": report_sha,
                     "componentIrSha256": component_digest}}
    binding["bindings"][qa["logicalComponentId"]] = {"variants": {"default": {
        "kind": "component", "fileReference": native["fileReference"],
        "componentReference": qa["componentReference"],
        "fidelityReportSha256": report_sha}}}

    (ROOT / "registries/tokens/v0.2.3").mkdir(parents=True, exist_ok=True)
    (ROOT / "registries/components/v0.2.8").mkdir(parents=True, exist_ok=True)
    write(ROOT / "schemas/component-registry-0.2.8.schema.json", catalog_schema)
    write(ROOT / "schemas/token-registry-0.2.3.schema.json", token_schema)
    write(ROOT / "registries/tokens/v0.2.3/default.json", tokens)
    write(ROOT / "registries/components/v0.2.8/catalog.json", catalog)
    write(ROOT / "registries/components/v0.2.8/fidelity-reports.json", reports)
    registry = registry_module.ComponentRegistry(catalog, reports)
    binding["registrySha256"] = registry.fingerprint
    ComponentBindings(binding, registry, platform="figma")
    write(ROOT / "adapters/figma/metadata/component-bindings-0.2.8-figma.json", binding)
    return {"status": "PASS", "registryVersion": VERSION,
            "componentCount": len(catalog["components"]),
            "newComponentId": qa["logicalComponentId"],
            "registrySha256": registry.fingerprint}


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False))
