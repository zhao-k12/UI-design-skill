import argparse
import json
from pathlib import Path

from validators.ui_ir import ROOT
from validators.visual.fidelity import run


def main():
    parser = argparse.ArgumentParser(description="Compare locked official runtime with independent native captures")
    parser.add_argument("reference_dir", type=Path)
    parser.add_argument("--candidate-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/task-007")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()) or output == args.reference_dir.resolve() or (args.candidate_dir and output == args.candidate_dir.resolve()):
        parser.error("Output must be a separate artifacts subdirectory")
    try:
        report = run(args.reference_dir, args.candidate_dir)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report = {"scope": "component_fidelity_gate", "status": "FAIL",
                  "issues": [{"code": "invalid_fidelity_input", "detail": str(exc)}], "components": []}
    output.mkdir(parents=True, exist_ok=True)
    (output / "component_fidelity_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "components": len(report["components"]), "report": str(output / "component_fidelity_report.json")}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
