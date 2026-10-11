"""Validate production catalog contracts; this does not certify live references."""
import argparse
from importlib import import_module
import json
from pathlib import Path

from jsonschema import ValidationError
from adapters.component_bindings import ComponentBindings
from validators.ui_ir import ROOT, load_json

logical = import_module("core.component-resolver.registry")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=ROOT / "registries/components/catalog.json")
    parser.add_argument("--evidence", type=Path, help="JSON object mapping report IDs to upstream fidelity reports")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--metadata", type=Path, action="append", help="Adapter-owned binding files; defaults to both production metadata files")
    args = parser.parse_args()
    metadata_paths = args.metadata if args.metadata is not None else [ROOT / "adapters" / platform / "metadata/component-bindings.json" for platform in ("figma", "penpot")]
    protected = {args.catalog.resolve(), args.evidence.resolve() if args.evidence else args.catalog.resolve(), *(path.resolve() for path in metadata_paths)}
    protected.add((ROOT/'registries/components/fidelity-reports.json').resolve())
    if args.report and args.report.resolve() in protected:
        parser.error("Report must not overwrite input files")
    try:
        evidence_path=args.evidence
        default_evidence=ROOT/'registries/components/fidelity-reports.json'
        if evidence_path is None and args.catalog.resolve()==(ROOT/'registries/components/catalog.json').resolve() and default_evidence.exists():evidence_path=default_evidence
        registry = logical.ComponentRegistry(load_json(args.catalog), load_json(evidence_path) if evidence_path else {})
        binding_counts = {}
        for path in metadata_paths:
            metadata = load_json(path)
            if not isinstance(metadata, dict):
                raise ValueError("invalid_component_bindings: metadata must be an object")
            ComponentBindings(metadata, registry, platform=metadata.get("platform"))
            platform = metadata["platform"]
            if platform in binding_counts:
                raise ValueError("duplicate_platform_metadata: provide at most one snapshot per platform")
            binding_counts[platform] = len(metadata["bindings"])
        entries = registry.snapshot["components"].values()
        report = {"scope": "component_registry_contract", "status": "PASS", "registrySha256": registry.fingerprint,
                  "activeComponents": sum(entry["status"] == "active" for entry in entries),
                  "plannedComponents": sum(entry["status"] == "planned" for entry in entries),
                  "platformBindingCounts": binding_counts,
                  "liveDualPlatformAcceptance": "DEFERRED", "issues": []}
    except (OSError, ValueError, TypeError, ValidationError) as exc:
        report = {"scope": "component_registry_contract", "status": "FAIL", "liveDualPlatformAcceptance": "DEFERRED", "issues": [{"code": getattr(exc, "code", "invalid_component_registry"), "message": str(exc)}]}
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        try:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(output, encoding="utf-8")
        except OSError as exc:
            report["status"] = "FAIL"
            report["issues"].append({"code": "report_write_failed", "message": str(exc)})
            output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    print(output, end="")
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
