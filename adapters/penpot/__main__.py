"""Prepare one Penpot host script per page; never claim native execution."""
import argparse
import hashlib
from importlib import import_module
import json
from pathlib import Path
from jsonschema import ValidationError

from adapters.component_bindings import ComponentBindings
from adapters.penpot.compiler import prepare, script_for_page
from validators.ui_ir import ROOT, load_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", type=Path)
    parser.add_argument("--file-reference")
    parser.add_argument("--font-bindings", type=Path)
    parser.add_argument("--token-library-version", choices=("0.1.0", "0.2.0", "0.2.1", "0.2.2"), default="0.1.0")
    parser.add_argument("--icon-bindings", type=Path)
    parser.add_argument("--native-fidelity", type=Path)
    parser.add_argument("--component-library-version", choices=("0.1.0", "0.2.0", "0.2.1", "0.2.2", "0.2.3", "0.2.4", "0.2.5", "0.2.6"), default="0.1.0")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/task-010/preflight")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()) or output.is_symlink():
        parser.error("Output must stay in project artifacts")
    if output.exists() and any(output.iterdir()):
        parser.error("Choose an empty directory; preserve previous evidence and scripts")
    output.mkdir(parents=True, exist_ok=True)
    read_optional = lambda path: load_json(path) if path else None
    try:
        token_path = (ROOT / "registries/tokens/default.json" if args.token_library_version == "0.1.0"
                      else ROOT / f"registries/tokens/v{args.token_library_version}/default.json")
        tokens = import_module("core.design-rules.tokens").TokenRegistry(
            load_json(token_path), expected_version=args.token_library_version)
        suffix = "/v" + args.component_library_version if args.component_library_version != "0.1.0" else ""
        components = import_module("core.component-resolver.registry").ComponentRegistry(
            load_json(ROOT / f"registries/components{suffix}/catalog.json"),
            load_json(ROOT / f"registries/components{suffix}/fidelity-reports.json"))
        bindings_name = f"component-bindings-{args.component_library_version}.json" if suffix else "component-bindings.json"
        bindings = ComponentBindings(load_json(ROOT / "adapters/penpot/metadata" / bindings_name), components, platform="penpot")
        icons = import_module("core.icon-resolver.registry").IconRegistry(import_module("icon-manager.remix-sync.manager").current())
        report = prepare(load_json(args.document), tokens, components, bindings, icons,
                         read_optional(args.icon_bindings), read_optional(args.font_bindings),
                         file_reference=args.file_reference, native_fidelity=read_optional(args.native_fidelity))
    except (OSError, ValueError, KeyError, TypeError, ValidationError) as exc:
        report = {"status":"FAIL", "nativeExecution":"NOT_RUN", "plan":None,
                  "issues":[{"code":"invalid_adapter_input", "detail":str(exc)}]}
    scripts = {}
    if report["status"] == "PASS":
        for i in range(len(report["plan"]["pages"])):
            name = f"page-{i}.js"
            data = script_for_page(report["plan"], i).encode("utf-8")
            (output / name).write_bytes(data)
            scripts[name] = hashlib.sha256(data).hexdigest()
    for name, value in (("adapter_preflight_report.json", report), ("generated_scripts.json", {"scripts":scripts, "nativeExecution":"NOT_RUN"})):
        (output / name).write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"status":report["status"], "nativeExecution":"NOT_RUN", "issues":len(report["issues"])}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
