"""Fail-closed, read-only audit of the current V0.2 release evidence."""
import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET_TYPES = (
    "Button", "Input", "Select", "DatePicker", "Checkbox", "Radio", "Switch", "Tag",
    "Table", "Pagination", "Card", "Tabs", "Form", "Modal", "Drawer", "Upload", "Tree", "Cascader",
)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _audit(root=ROOT, *, native_qa_path=None, admission_path=None):
    root = Path(root)
    pre = root / "artifacts/task-051/pipeline-v02-ready"
    native = root / "artifacts/task-052"
    catalog_path = root / "registries/components/v0.2.3/catalog.json"
    admission_path = Path(admission_path) if admission_path else root / "registries/components/v0.2.3/admission.json"
    native_qa_path = Path(native_qa_path) if native_qa_path else native / "native-qa.json"
    paths = {
        "catalog": catalog_path, "admission": admission_path,
        "manifest": pre / "manifest.json", "coreQa": pre / "qa_report.json",
        "figmaPreflight": pre / "figma_preflight.json", "penpotPreflight": pre / "penpot_preflight.json",
        "nativeQa": native_qa_path, "figmaPng": native / "figma/native-page.png",
        "penpotPng": native / "penpot/native-page.png",
        "penpotExecution": native / "penpot/native-execution.json",
    }
    issues = []

    def check(ok, code, detail=""):
        if not ok:
            issues.append({"code": code, "detail": detail})

    try:
        catalog, admission, manifest, core, figma_pre, penpot_pre, native_qa, execution = (
            read(paths[key]) for key in ("catalog", "admission", "manifest", "coreQa", "figmaPreflight", "penpotPreflight", "nativeQa", "penpotExecution")
        )
        snapshot = {name: sha(path) for name, path in paths.items()}
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"status": "INVALID_EVIDENCE", "releaseReady": False, "evidenceValid": False,
                "issues": [{"code": "missing_or_invalid_evidence", "detail": str(exc)}]}

    components = catalog.get("components", {})
    admitted = admission.get("components", {})
    admitted_types = sorted({entry.get("componentType") for key, entry in components.items() if key in admitted and entry.get("status") == "active"})
    missing_types = [kind for kind in TARGET_TYPES if kind not in admitted_types]
    check(admission.get("status") == admission.get("registryAdmission") == "PASS", "registry_admission_missing")
    check(set(components) == set(admitted) and len(components) == 4, "registry_scope_changed")
    check(manifest["registries"]["components"] == admission.get("registrySha256") == figma_pre["plan"]["componentsSha256"] == penpot_pre["plan"]["componentsSha256"], "component_lock_mismatch")
    check(core.get("status") == "PASS" and core.get("readyForAdapter") is True and core.get("issues") == [], "core_pipeline_failed")
    check(figma_pre.get("status") == penpot_pre.get("status") == "PASS", "adapter_preflight_failed")
    check(core.get("uiIrSha256") == native_qa.get("uiIrSha256") == figma_pre["plan"]["uiIrSha256"] == penpot_pre["plan"]["uiIrSha256"], "ui_ir_lock_mismatch")
    check(native_qa.get("status") == "PASS" and native_qa.get("issues") == [] and native_qa.get("releaseReady") is False, "native_readback_missing")
    check(execution.get("status") == "EXECUTED" and execution.get("rootReference"), "penpot_execution_missing")
    check(execution.get("uiIrSha256") == core.get("uiIrSha256"), "penpot_execution_input_mismatch")
    for platform in ("figma", "penpot"):
        check(native_qa.get("counts", {}).get(platform, {}).get("nativePngSha256") == snapshot[platform + "Png"], "native_png_hash_mismatch", platform)
    check(native_qa.get("counts", {}).get("figma", {}).get("nativeInstances") == native_qa.get("counts", {}).get("penpot", {}).get("nativeInstances") == 6, "native_instance_count_mismatch")

    # The V0.1-style manifest locks Core code and Adapter version strings, but no
    # Adapter runtime/compiler/script digests. Audit this absence explicitly.
    adapter_byte_lock = all(key in manifest for key in ("figmaAdapterSha256", "penpotAdapterSha256"))
    gates = {
        "scopedRegistry": "PASS" if not issues and len(admitted_types) == 4 else "INVALID",
        "targetComponentCoverage": "PASS" if not missing_types else "PARTIAL",
        "frozenListCorePipeline": "PASS" if not issues else "INVALID",
        "frozenListDualNativeOutput": "PASS" if not issues else "INVALID",
        "adapterRuntimeByteLock": "PASS" if adapter_byte_lock else "NOT_IMPLEMENTED",
        "newIndependentPrototypeE2E": "NOT_RUN",
        "allReleaseGates": "NOT_RUN",
    }
    return {
        "scope": "v02-release-readiness-audit", "status": "INVALID_EVIDENCE" if issues else "NOT_READY",
        "releaseReady": False, "evidenceValid": not issues, "snapshots": snapshot,
        "componentCoverage": {"targetCount": len(TARGET_TYPES), "admittedTypeCount": len(admitted_types), "admittedTypes": admitted_types, "missingTypes": missing_types,
                              "admittedConfigurationCount": len(admitted), "contentScope": "fixed-native-content only"},
        "gates": gates,
        "nextAction": "Decide a bounded component coverage increment and versioned Adapter byte-lock migration before claiming V0.2 release readiness.",
        "issues": issues,
    }


def audit(root=ROOT, *, native_qa_path=None, admission_path=None):
    try:
        return _audit(root, native_qa_path=native_qa_path, admission_path=admission_path)
    except (KeyError, TypeError, AttributeError) as exc:
        return {"status": "INVALID_EVIDENCE", "releaseReady": False, "evidenceValid": False,
                "issues": [{"code": "malformed_evidence", "detail": str(exc)}]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("status", "releaseReady", "evidenceValid", "componentCoverage", "gates", "issues") if k in report}, ensure_ascii=True, indent=2))
    return 0 if report["evidenceValid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
