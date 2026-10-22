"""Build the Figma-only size-policy registry without changing historical files."""
from copy import deepcopy
from hashlib import sha256
from importlib import import_module
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
digest = import_module("core.component-resolver.registry").digest
TABLE = "data.table.headed.b334d80b864ecaf53198737bffec5c2bc8d59d337667effacb16ea74dcd024b4"
NEW_MASTER = "299:3"


def content_without_sample_dimensions(scope):
    result = deepcopy(scope)
    result.pop("width", None)
    result.pop("height", None)
    for columns in (result.get("columns"), result.get("props", {}).get("columns")):
        if columns:
            for column in columns:
                column.pop("width", None)
    return result


def build():
    read = lambda path: json.loads((ROOT / path).read_text(encoding="utf-8"))
    catalog = read("registries/components/v0.2.8/catalog.json")
    reports = read("registries/components/v0.2.8/fidelity-reports.json")
    bindings = read("adapters/figma/metadata/component-bindings-0.2.8-figma.json")
    schema = read("schemas/component-registry-0.2.8.schema.json")
    catalog["registryVersion"] = "0.2.9"
    catalog["libraryVersion"] = "0.2.9-figma-adaptive-size"
    schema["$id"] = "urn:ui-design-skill:component-registry:0.2.9"
    schema["title"] = "Logical Component Registry V0.2.9 Figma adaptive sizing"
    schema["properties"]["registryVersion"]["const"] = "0.2.9"
    entry_schema = schema["properties"]["components"]["additionalProperties"]
    entry_schema["properties"]["contentScope"] = {
        "type": "object", "required": ["kind"],
        "properties": {"kind": {"enum": ["fixed-native-content", "fixed-native-snapshot"]}},
        "not": {"anyOf": [{"required": ["width"]}, {"required": ["height"]}]}}
    entry_schema["properties"]["sizingPolicy"] = {
        "type": "object", "required": ["width", "height"], "additionalProperties": False,
        "properties": {"width": {"enum": ["intrinsic", "fill-cell"]},
                       "height": {"const": "intrinsic"}}}
    for logical_id, entry in catalog["components"].items():
        report_id = entry["fidelity"]["reportId"]
        report = reports[report_id]
        original_sha = digest(report)
        original_gate = report["gateVersion"]
        entry["contentScope"] = content_without_sample_dimensions(entry["contentScope"])
        entry["sizingPolicy"] = {"width": "fill-cell" if logical_id == TABLE else "intrinsic",
                                 "height": "intrinsic"}
        report["contentScopeProposal"] = deepcopy(entry["contentScope"])
        report["gateVersion"] = "0.2.9-figma-size-policy"
        report["sizingMigration"] = {"baseReportSha256": original_sha,
                                     "baseGateVersion": original_gate,
                                     "policy": deepcopy(entry["sizingPolicy"])}
        if logical_id == TABLE:
            report["platforms"]["figma"]["componentId"] = NEW_MASTER
            report["sizingMigration"]["nativeResponsiveEvidenceSha256"] = sha256(
                (ROOT / ".dev/TASK-127_ADAPTIVE_TABLE_READBACK.json").read_bytes()).hexdigest()
            evidence_dir = ROOT / ".dev/task-127-evidence"
            report["sizingMigration"]["nativePngSha256"] = {
                name: sha256((evidence_dir / name).read_bytes()).hexdigest() for name in
                ("table-source-1840-native.png", "table-adaptive-1840-native.png",
                 "table-1660-native.png")}
            report["sizingMigration"]["sourceSizeComparison"] = {
                "changedPixels": 1926, "changedXBuckets100px": [6, 12],
                "unchangedOutsideShiftedColumnText": True}
            report["sizingMigration"]["nativeResponsiveEvidence"] = {
                "fileReference": "0vGWSRoLxBiVPXiZ8xJAX9", "masterId": NEW_MASTER,
                "instanceId": "299:36", "testedWidth": 1660, "height": 182.875,
                "rows": 4, "columns": 3, "rowWidths": [1660] * 4,
                "borderWidths": [1660] * 4}
        entry["fidelity"]["reportSha256"] = digest(report)
        for reference in bindings["bindings"][logical_id]["variants"].values():
            reference["fidelityReportSha256"] = digest(report)
    bindings["libraryVersion"] = catalog["libraryVersion"]
    bindings["registrySha256"] = digest(catalog)
    for reference in bindings["bindings"][TABLE]["variants"].values():
        reference["componentReference"] = NEW_MASTER
    output = {
        "registries/components/v0.2.9/catalog.json": catalog,
        "registries/components/v0.2.9/fidelity-reports.json": reports,
        "adapters/figma/metadata/component-bindings-0.2.9-figma.json": bindings,
        "schemas/component-registry-0.2.9.schema.json": schema}
    for path, data in output.items():
        target = ROOT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        if target.exists() and target.read_text(encoding="utf-8") != encoded:
            raise ValueError("Refusing to overwrite changed migration output: " + path)
        target.write_text(encoded, encoding="utf-8", newline="\n")
    return {path: digest(data) for path, data in output.items()}


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
