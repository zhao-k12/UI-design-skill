import argparse
from importlib import import_module
import json
from pathlib import Path
import hashlib
import re
from jsonschema import ValidationError

from adapters.component_bindings import ComponentBindings
from adapters.figma.compiler import prepare, script_for_page
from validators.ui_ir import ROOT, load_json


def main():
    parser = argparse.ArgumentParser(description="Preflight UI-IR and emit one verified-input Figma host script per page")
    parser.add_argument("document", type=Path)
    parser.add_argument("--file-reference")
    parser.add_argument("--font-bindings", type=Path)
    parser.add_argument("--token-library-version", choices=("0.1.0", "0.2.0", "0.2.1"), default="0.1.0")
    parser.add_argument("--icon-bindings", type=Path)
    parser.add_argument("--component-library-version", choices=("0.1.0", "0.2.0", "0.2.1", "0.2.2", "0.2.3"), default="0.1.0")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/task-009")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        parser.error("Output must stay in project artifacts")
    output.mkdir(parents=True, exist_ok=True)
    ledger_path = output / "generated_scripts.json"
    scripts = {}
    try:
        # Only invalidate exact, unchanged files recorded by this adapter's previous run.
        if ledger_path.exists():
            ledger = load_json(ledger_path)
            stale = []
            for name, expected in ledger.get("scripts", {}).items():
                if not re.fullmatch(r"page-[0-9]+\.js", name):
                    raise ValueError("Invalid generated-script ledger path")
                old = output / name
                if old.exists():
                    if hashlib.sha256(old.read_bytes()).hexdigest() != expected:
                        raise ValueError("Generated script was modified; preserved for review: " + name)
                    stale.append(old)
            for old in stale:
                old.unlink()
        token_path = (ROOT / "registries/tokens/default.json" if args.token_library_version == "0.1.0"
                      else ROOT / f"registries/tokens/v{args.token_library_version}/default.json")
        tokens = import_module("core.design-rules.tokens").TokenRegistry(
            load_json(token_path), expected_version=args.token_library_version)
        suffix = "/v" + args.component_library_version if args.component_library_version != "0.1.0" else ""
        evidence_path = ROOT / f"registries/components{suffix}/fidelity-reports.json"
        components = import_module("core.component-resolver.registry").ComponentRegistry(
            load_json(ROOT / f"registries/components{suffix}/catalog.json"), load_json(evidence_path))
        bindings_name = f"component-bindings-{args.component_library_version}.json" if suffix else "component-bindings.json"
        bindings = ComponentBindings(load_json(ROOT / "adapters/figma/metadata" / bindings_name), components, platform="figma")
        icons_module = import_module("icon-manager.remix-sync.manager")
        icons = icons_module.logical.IconRegistry(icons_module.current())
        report = prepare(load_json(args.document), tokens, components, bindings, icons,
                         load_json(args.icon_bindings) if args.icon_bindings else None,
                         load_json(args.font_bindings) if args.font_bindings else None, file_reference=args.file_reference)
        if report["status"] == "PASS":
            generated = {f"page-{index}.js": script_for_page(report["plan"], index) for index in range(len(report["plan"]["pages"]))}
            for name in generated:
                if (output / name).exists():
                    raise ValueError("Unowned script preserved; choose an empty output directory: " + name)
            for name, code in generated.items():
                target = output / name
                target.write_text(code, encoding="utf-8")
                scripts[name] = hashlib.sha256(target.read_bytes()).hexdigest()
    except (OSError, ValueError, KeyError, TypeError, ValidationError) as exc:
        report = {"scope": "figma_adapter_preflight", "status": "FAIL", "nativeExecution": "NOT_RUN", "plan": None,
                  "issues": [{"code": "invalid_adapter_input", "detail": str(exc)}]}
    (output / "adapter_preflight_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ledger_path.write_text(json.dumps({"status": report["status"], "scripts": scripts}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "nativeExecution": "NOT_RUN", "issues": len(report["issues"])}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
