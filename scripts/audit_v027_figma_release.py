"""Audit the new 18-component Figma-only profile and its native page evidence."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.audit_adapter_byte_lock_figma import audit as audit_native
from scripts.audit_figma_candidate_batch import audit as audit_batch
from scripts.audit_v02_figma_release_gates import inside, walk
from scripts.build_figma_batch_registry import build
from validators.ui_ir import load_json, validate_document


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def audit(root=ROOT, *, visual_path=None, geometry_path=None, native_dir=None):
    root = Path(root)
    task = root / "artifacts/task-118"
    run = task / "figma-v027-run-final"
    native_dir = Path(native_dir) if native_dir else task / "figma"
    gates, issues = {}, []

    def gate(name, ok):
        gates[name] = "PASS" if ok else "FAIL"
        if not ok:
            issues.append(name)

    try:
        source = root / "examples/user-management-compact-search-v027-figma"
        manifest = load_json(source / "input-manifest.json")
        batch = audit_batch(root)
        outputs = build(root)
        catalog = load_json(root / "registries/components/v0.2.7/catalog.json")
        admission = load_json(root / "registries/components/v0.2.7/admission.json")
        binding = load_json(root / "adapters/figma/metadata/component-bindings-0.2.7-figma.json")
        gate("approvedIndependentPrototype", manifest["status"] == "READY_FOR_PREFLIGHT"
             and manifest["sourcePackage"] == "examples/user-management-compact-search-v026"
             and all(digest(source / name) == expected for name, expected in manifest["files"].items()))
        gate("eighteenFixedFigmaComponents", batch["status"] == "PASS"
             and len(catalog["components"]) == len(admission["components"]) == len(binding["bindings"]) == 18
             and catalog == outputs["catalog.json"] and admission == outputs["admission.json"]
             and binding == outputs["component-bindings-0.2.7-figma.json"])

        qa = load_json(run / "qa_report.json")
        structure = load_json(run / "structure_qa_report.json")
        layout = load_json(run / "layout_qa_report.json")
        rules = load_json(run / "design_rule_report.json")
        document = load_json(run / "final_ui_ir.json")
        checkpoint = load_json(run / "checkpoint.json")
        pipeline_manifest = load_json(run / "manifest.json")
        preflight = load_json(run / "figma_preflight.json")
        gate("completePageTreeAndHumanReview", structure["status"] == "PASS"
             and structure["readyForLayout"] is True and structure["issues"] == [])
        gate("deterministicRuleLayout", layout["status"] == "PASS"
             and qa["layoutRepeatable"] is True and rules["status"] == "PASS"
             and not any(key in load_json(source / "layout-plan.json") for key in ("x", "y")))
        gate("platformNeutralUiIr", not validate_document(document)
             and preflight["plan"]["uiIrSha256"] == qa["uiIrSha256"])
        nodes = [node for page in document["pages"] for node in walk(page)]
        components = [node["componentId"] for node in nodes if node["type"] == "ComponentInstance"]
        icons = [node["iconId"] for node in nodes if node["type"] == "IconInstance"]
        gate("admittedComponentsAndRemixIcon", len(components) == 4
             and set(components) <= set(admission["components"])
             and icons == ["remix.settings-3-line"]
             and pipeline_manifest["registries"]["components"] == admission["registrySha256"])
        stages = checkpoint["stages"]
        gate("savedStagesAndCheckpointRecovery", len(stages) == 9
             and all((run / row["artifact"]).is_file()
                     and digest(run / row["artifact"]) == row["artifactSha256"]
                     for row in stages.values())
             and qa["executedStages"] == [] and set(qa["reusedStages"]) == set(stages))

        native = audit_native(run, task / "figma-execution", native_dir)
        gate("lockedFigmaNativeExecution", native["status"] == "PASS"
             and native["executionReceiptPersisted"] is True
             and native["actualInstanceCount"] == 5 and native["textNodeCount"] == 21)
        geometry = load_json(geometry_path or native_dir / "native-geometry-read.json")
        native_read = load_json(native_dir / "native-read.json")
        root_box = geometry["root"]["box"]
        gate("defaultFontsAndNoTextClipping", geometry["root"]["id"] == native_read["root"]["id"]
             and len(geometry["texts"]) == len(native_read["texts"]) == 21
             and all(row["visible"] and row["box"] and inside(row["box"], root_box)
                     and all(inside(row["box"], ancestor["box"])
                             for ancestor in row["clippingAncestors"])
                     and row["fontFamily"] == ("Ionicons" if row["name"] == "source/ionicons-arrow" else "Inter")
                     for row in geometry["texts"]))
        visual = load_json(visual_path or task / "visual-review.json")
        gate("actualVisualReview", visual["status"] == "PASS"
             and visual["sourceImageSha256"] == digest(native_dir / "native.png")
             and len(visual["checks"]) >= 6
             and all(value == "PASS" for value in visual["checks"].values()))
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        issues.append("invalid_or_missing_evidence: " + str(exc))
    return {"scope": "v027-figma-only-release-gates",
            "status": "FIGMA_SCOPED_PASS" if not issues else "INVALID_EVIDENCE",
            "figmaScopedReady": not issues, "historicalDualPlatformReleaseReady": False,
            "gates": gates, "issues": issues}


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
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["figmaScopedReady"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
