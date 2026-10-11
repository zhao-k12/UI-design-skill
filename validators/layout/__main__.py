"""Calculate and persist a validated Layout Skeleton; failures return no skeleton."""
import argparse
from importlib import import_module
import json
from pathlib import Path

from validators.ui_ir import ROOT, load_json

tokens = import_module("core.design-rules.tokens")
engine = import_module("core.layout.engine")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tree", type=Path)
    parser.add_argument("--registry", type=Path, default=ROOT / "registries/tokens/default.json")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    outputs = {name: args.output_dir / name for name in ("layout_skeleton.json", "layout_qa_report.json")}
    inputs = {args.tree.resolve(), args.registry.resolve()}
    if any(path.resolve() in inputs for path in outputs.values()):
        parser.error("Outputs must not overwrite the input tree or registry")
    try:
        registry = tokens.TokenRegistry(load_json(args.registry), expected_version="0.1.0")
        result = engine.LayoutEngine(registry).run(load_json(args.tree))
    except tokens.RegistryError as exc:
        result = {"scope": "layout", "status": "FAIL", "skeleton": None, "issues": exc.issues}
    except (OSError, ValueError) as exc:
        result = {"scope": "layout", "status": "FAIL", "skeleton": None, "issues": [{"code": "invalid_input", "path": "/", "message": str(exc)}]}
    report = {key: value for key, value in result.items() if key != "skeleton"}
    skeleton = {key: value for key, value in result.items() if key != "issues"}
    try:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        # Even on FAIL replace the old success output with an explicitly null skeleton.
        for path, data in ((outputs["layout_skeleton.json"], skeleton), (outputs["layout_qa_report.json"], report)):
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        report["status"] = "FAIL"
        report["issues"].append({"code": "artifact_write_failed", "path": str(args.output_dir), "message": str(exc)})
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
