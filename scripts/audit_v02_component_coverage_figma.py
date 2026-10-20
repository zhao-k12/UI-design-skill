"""Read-only audit of the 18-type V0.2 Figma evidence and formal admission boundary."""
import argparse
import hashlib
import json
from pathlib import Path

from scripts.audit_v02_release_readiness import TARGET_TYPES
from validators.ui_ir import ROOT


FIGMA_ONLY_TASKS = {
    "Switch": 69, "Card": 72, "Pagination": 75, "Tabs": 78, "Tree": 81,
    "DatePicker": 84, "Form": 87, "Modal": 90, "Drawer": 93,
    "Upload": 96, "Cascader": 99,
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(root=ROOT, *, qa_overrides=None, native_overrides=None):
    root = Path(root)
    qa_overrides = qa_overrides or {}
    native_overrides = native_overrides or {}
    catalog_path = root / "registries/components/v0.2.6/catalog.json"
    admission_path = root / "registries/components/v0.2.6/admission.json"
    issues, rows = [], []
    try:
        catalog, admission = read(catalog_path), read(admission_path)
    except (OSError, ValueError) as exc:
        return {"status": "INVALID_EVIDENCE", "releaseReady": False,
                "issues": [{"code": "registry_unreadable", "detail": str(exc)}]}
    registered = catalog.get("components", {})
    admitted = admission.get("components", {})
    figma_bindings = admission.get("bindings", {}).get("figma", {})
    penpot_bindings = admission.get("bindings", {}).get("penpot", {})
    if admission.get("status") != "PASS" or set(registered) != set(admitted) \
            or set(admitted) != set(figma_bindings) or set(admitted) != set(penpot_bindings):
        issues.append({"code": "formal_registry_scope_invalid"})
    admitted_types = set()
    for logical_id, item in registered.items():
        kind = item.get("componentType")
        if kind not in TARGET_TYPES or item.get("status") != "active" \
                or admitted.get(logical_id, {}).get("fidelityReportSha256") != item.get("fidelity", {}).get("reportSha256"):
            issues.append({"code": "formal_admission_invalid", "componentType": kind})
            continue
        admitted_types.add(kind)
        rows.append({"componentType": kind, "logicalComponentId": logical_id,
                     "state": "FORMALLY_ADMITTED_FIXED_CONFIG", "figmaComponentId":
                     figma_bindings[logical_id]["componentReference"]})
    if len(admitted_types) != 7:
        issues.append({"code": "admitted_type_count_changed", "actual": len(admitted_types)})
    figma_only_types = set()
    for kind, task_id in FIGMA_ONLY_TASKS.items():
        folder = root / f"artifacts/task-{task_id:03d}"
        qa_paths = list(folder.glob("*-figma-qa.json"))
        metadata_paths = list((root / "adapters/figma/metadata").glob(
            kind.lower() + "-default-font-fidelity-*-figma-only.json"))
        qa_path = Path(qa_overrides.get(kind, qa_paths[0])) if len(qa_paths) == 1 else None
        if qa_path is None or len(metadata_paths) != 1:
            issues.append({"code": "figma_evidence_missing_or_ambiguous", "componentType": kind})
            continue
        metadata_path = metadata_paths[0]
        try:
            qa, metadata = read(qa_path), read(metadata_path)
            native_path = folder / "figma/native.png"
            native_read_path = folder / "figma/native-read.json"
            native = read(native_read_path)
            evidence_hashes = qa.get("platforms", {}).get("figma", {}).get("evidenceSha256") \
                or qa.get("evidenceSha256", {})
            native_files = ("native-read.json", "native.png", "native-repeat.png", "native.svg")
            native_hashes_valid = all(
                evidence_hashes.get(name) == sha(Path(native_overrides.get((kind, name), folder / "figma" / name)))
                for name in native_files
            )
            checks = qa.get("checks") or qa.get("platforms", {}).get("figma", {}).get("checks", {})
            metadata_hashes = metadata.get("evidenceSha256", {})
            metadata_qa_locked = metadata.get("figmaQaSha256") == sha(qa_path) \
                if metadata.get("figmaQaSha256") else \
                metadata_hashes.get(qa_path.name) == sha(qa_path) \
                if metadata_hashes.get(qa_path.name) else \
                metadata_hashes.get("native.png", metadata_hashes.get("native-png")) == sha(native_path)
            native_ids = {node["id"] for node in native["nodes"]} if "nodes" in native \
                else {native["component"]["id"]}
            valid = qa.get("status") == "PASS" and metadata.get("status") in ("PASS", "FIGMA_QA_PASS") \
                and qa.get("componentType") == kind \
                and metadata.get("componentType", kind) == kind \
                and qa.get("logicalComponentId") == metadata.get("logicalComponentId") \
                and metadata_qa_locked \
                and native_hashes_valid \
                and evidence_hashes["native.png"] == evidence_hashes["native-repeat.png"] \
                and native.get("fileReference") == metadata.get("fileReference") \
                and metadata.get("componentId") in native_ids \
                and bool(checks) and all(value is True for value in checks.values()) \
                and qa.get("admissionEligible") is False \
                and qa.get("registryAdmission") == "DEFERRED_PENPOT" \
                and qa.get("readyForPageGeneration") is False \
                and qa.get("dualPlatformFidelity") == "DEFERRED" \
                and metadata.get("admissionEligible") is False \
                and metadata.get("registryAdmission") == "DEFERRED_PENPOT" \
                and metadata.get("readyForPageGeneration") is False \
                and metadata.get("dualPlatformFidelity") == "DEFERRED" \
                and qa.get("releaseReady") is False and metadata.get("releaseReady") is False
        except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
            valid = False
            issues.append({"code": "figma_evidence_unreadable", "componentType": kind, "detail": str(exc)})
        if not valid:
            issues.append({"code": "figma_evidence_invalid", "componentType": kind})
            continue
        figma_only_types.add(kind)
        rows.append({"componentType": kind, "logicalComponentId": qa["logicalComponentId"],
                     "state": "FIGMA_QA_PASS_ONLY", "figmaComponentId": metadata["componentId"],
                     "qaSha256": sha(qa_path)})
    overlaps = admitted_types & figma_only_types
    uncovered = set(TARGET_TYPES) - admitted_types - figma_only_types
    if overlaps:
        issues.append({"code": "coverage_overlap", "componentTypes": sorted(overlaps)})
    if uncovered:
        issues.append({"code": "figma_coverage_missing", "componentTypes": sorted(uncovered)})
    rows.sort(key=lambda row: TARGET_TYPES.index(row["componentType"]))
    return {"scope": "v02-18-type-figma-evidence-audit",
            "status": "FIGMA_EVIDENCE_COMPLETE" if not issues else "INVALID_EVIDENCE",
            "evidenceValid": not issues, "releaseReady": False,
            "targetTypeCount": len(TARGET_TYPES), "formalAdmissionTypeCount": len(admitted_types),
            "figmaOnlyQaTypeCount": len(figma_only_types),
            "figmaEvidenceTypeCount": len(admitted_types | figma_only_types),
            "dualPlatformPendingTypes": sorted(figma_only_types),
            "rows": rows, "issues": issues,
            "remainingReleaseGates": ["dual-platform Fidelity Gate and formal Registry admission for 11 types",
                "Adapter byte lock native receipt and full platform release validation",
                "new independent prototype and full release gates"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        parser.error("Output must stay in artifacts")
    result = audit()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("status", "evidenceValid", "releaseReady",
        "targetTypeCount", "formalAdmissionTypeCount", "figmaOnlyQaTypeCount",
        "figmaEvidenceTypeCount", "issues")}, ensure_ascii=False))
    return 0 if result["evidenceValid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
