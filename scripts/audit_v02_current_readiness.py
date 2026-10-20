"""Aggregate current V0.2 evidence without rewriting historical release audits."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.audit_adapter_byte_lock_figma import audit as audit_figma_lock
from scripts.audit_v02_compact_search_figma import audit as audit_independent_figma
from scripts.audit_v02_component_coverage_figma import audit as audit_coverage
from scripts.audit_v02_figma_release_gates import audit as audit_figma_release_gates


def audit(root=ROOT, *, native_dir=None):
    root = Path(root)
    coverage = audit_coverage(root)
    task = root / "artifacts/task-106"
    native_dir = Path(native_dir) if native_dir else task / "figma"
    try:
        figma_lock = audit_figma_lock(task / "run", task / "figma-execution", native_dir)
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        figma_lock = {"status": "FAIL", "issues": ["figma_lock_evidence_invalid: " + str(exc)]}
    independent = audit_independent_figma(root)
    figma_gates = audit_figma_release_gates(root)
    evidence_valid = (coverage.get("status") == "FIGMA_EVIDENCE_COMPLETE"
                      and coverage.get("evidenceValid") is True
                      and figma_lock.get("status") == "PASS"
                      and figma_lock.get("executionReceiptPersisted") is True
                      and independent.get("status") == "PASS"
                      and figma_gates.get("status") == "FIGMA_SCOPED_PASS")
    return {
        "scope": "v02-current-release-readiness",
        "status": "NOT_READY" if evidence_valid else "INVALID_EVIDENCE",
        "releaseReady": False,
        "evidenceValid": evidence_valid,
        "componentCoverage": {
            "targetTypeCount": coverage.get("targetTypeCount"),
            "formallyAdmittedTypeCount": coverage.get("formalAdmissionTypeCount"),
            "figmaOnlyQaTypeCount": coverage.get("figmaOnlyQaTypeCount"),
            "dualPlatformPendingTypes": coverage.get("dualPlatformPendingTypes", []),
        },
        "gates": {
            "figmaComponentEvidence": "PASS" if coverage.get("status") == "FIGMA_EVIDENCE_COMPLETE" else "INVALID",
            "figmaAdapterByteLockNativeReceipt": "PASS" if figma_lock.get("status") == "PASS" and figma_lock.get("executionReceiptPersisted") else "INVALID",
            "penpotAdapterByteLockNativeReceipt": "DEFERRED",
            "dualPlatformAdmissionForRemainingTypes": "DEFERRED",
            "newIndependentPrototypeFigmaE2E": "PASS" if independent.get("status") == "PASS" else "INVALID",
            "newIndependentPrototypePenpotE2E": "DEFERRED",
            "newIndependentPrototypeE2E": "FIGMA_PASS_PENPOT_DEFERRED" if independent.get("status") == "PASS" else "INVALID",
            "figmaScopedReleaseGates": "PASS" if figma_gates.get("status") == "FIGMA_SCOPED_PASS" else "INVALID",
            "allReleaseGates": "NOT_RUN",
        },
        "currentFigmaSample": {
            "pageReference": figma_lock.get("pageReference"),
            "rootReference": figma_lock.get("rootReference"),
            "nativePngSha256": figma_lock.get("nativePngSha256"),
        },
        "independentFigmaSample": {"pageReference": independent.get("figmaPageReference"),
                                    "nativePngSha256": independent.get("figmaNativePngSha256")},
        "issues": (list(coverage.get("issues", [])) + list(figma_lock.get("issues", []))
                   + list(independent.get("issues", [])) + list(figma_gates.get("issues", []))),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        parser.error("Output must stay in artifacts")
    result = audit()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["evidenceValid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
