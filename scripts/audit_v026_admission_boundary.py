"""Ensure Figma-only candidate components cannot enter the V0.2.6 production profile."""
import argparse
from importlib import import_module
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.audit_v02_component_coverage_figma import audit as audit_coverage
from validators.ui_ir import load_json

registry_module = import_module("core.component-resolver.registry")


def audit(root=ROOT, *, binding_overrides=None):
    root = Path(root)
    coverage = audit_coverage(root)
    catalog = load_json(root / "registries/components/v0.2.6/catalog.json")
    admission = load_json(root / "registries/components/v0.2.6/admission.json")
    reports = load_json(root / "registries/components/v0.2.6/fidelity-reports.json")
    registry = registry_module.ComponentRegistry(catalog, reports)
    issues = []
    if coverage["status"] != "FIGMA_EVIDENCE_COMPLETE":
        issues.append("Figma coverage evidence is invalid")
    admitted = {row["logicalComponentId"] for row in coverage["rows"]
                if row["state"] == "FORMALLY_ADMITTED_FIXED_CONFIG"}
    candidates = {row["logicalComponentId"] for row in coverage["rows"]
                  if row["state"] == "FIGMA_QA_PASS_ONLY"}
    if len(admitted) != 7 or len(candidates) != 11 or admitted & candidates:
        issues.append("admission and candidate groups are not the expected disjoint 7/11 split")
    if set(catalog["components"]) != admitted or set(admission["components"]) != admitted:
        issues.append("production Registry or admission differs from formally admitted group")
    if registry.fingerprint != admission["registrySha256"]:
        issues.append("production Registry fingerprint differs from admission")
    bindings = {}
    for platform in ("figma", "penpot"):
        binding = (binding_overrides or {}).get(platform) or load_json(
            root / "adapters" / platform / "metadata/component-bindings-0.2.6.json")
        bindings[platform] = set(binding["bindings"])
        if bindings[platform] != admitted or binding["registrySha256"] != registry.fingerprint:
            issues.append(f"{platform} production bindings extend or differ from admitted Registry")
    for logical_id in sorted(admitted):
        try:
            registry.resolve(logical_id)
        except registry_module.ComponentError as exc:
            issues.append(f"admitted component rejected: {logical_id}: {exc.code}")
    for logical_id in sorted(candidates):
        try:
            registry.resolve(logical_id)
        except registry_module.ComponentError as exc:
            if exc.code != "missing_component":
                issues.append(f"Figma-only candidate has unexpected rejection: {logical_id}: {exc.code}")
        else:
            issues.append(f"Figma-only candidate incorrectly resolves: {logical_id}")
    return {
        "scope": "v026-production-admission-boundary",
        "status": "PASS" if not issues else "FAIL",
        "releaseReady": False,
        "admittedCount": len(admitted),
        "figmaOnlyCandidateCount": len(candidates),
        "rejectedCandidateIds": sorted(candidates) if not issues else [],
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/task-113/admission-boundary.json")
    args = parser.parse_args()
    result = audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
