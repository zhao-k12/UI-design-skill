"""Validate a token registry and its references in a static UI-IR document."""
from __future__ import annotations

import argparse
from importlib import import_module
import json
from pathlib import Path

from validators.ui_ir import ROOT, load_json, validate_document

tokens = import_module("core.design-rules.tokens")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", type=Path)
    parser.add_argument("--registry", type=Path, default=ROOT / "registries" / "tokens" / "default.json")
    parser.add_argument("--expected-version", default="0.1.0")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    registry = None
    try:
        if args.report and args.report.resolve() in {args.document.resolve(), args.registry.resolve()}:
            parser.error("--report must not overwrite the input document or registry")
        document = load_json(args.document)
        issues = validate_document(document)
        if not issues:
            registry = tokens.TokenRegistry(load_json(args.registry), expected_version=args.expected_version)
            issues = tokens.check_references(document, registry)
    except tokens.RegistryError as exc:
        issues = exc.issues
    except (OSError, ValueError) as exc:
        issues = [{"code": "invalid_input", "path": "/", "message": str(exc)}]
    report = {"scope": "design_tokens", "status": "FAIL" if issues else "PASS", "issues": issues}
    if registry is not None:
        report["registryVersion"] = registry.version
        report["registrySha256"] = registry.fingerprint
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        try:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(output, encoding="utf-8")
        except OSError as exc:
            report["status"] = "FAIL"
            report["issues"].append({"code": "report_write_failed", "path": str(args.report), "message": str(exc)})
            output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    print(output, end="")
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
