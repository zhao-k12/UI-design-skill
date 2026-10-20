"""Fail-closed Figma-only release-gate audit for the independent V0.2 prototype."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.audit_v02_compact_search_figma import audit as audit_independent
from validators.ui_ir import load_json, validate_document


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def inside(inner, outer):
    epsilon = 0.5
    return (inner["x"] >= outer["x"] - epsilon
            and inner["y"] >= outer["y"] - epsilon
            and inner["x"] + inner["width"] <= outer["x"] + outer["width"] + epsilon
            and inner["y"] + inner["height"] <= outer["y"] + outer["height"] + epsilon)


def walk(node):
    yield node
    for child in node.get("children", []):
        yield from walk(child)
    for children in node.get("slots", {}).values():
        for child in children:
            yield from walk(child)


def audit(root=ROOT, *, geometry_path=None, visual_path=None):
    root = Path(root)
    source = root / "examples/user-management-compact-search-v026"
    task = root / "artifacts/task-110"
    run = task / "run"
    gates = {}
    issues = []

    def gate(name, condition):
        gates[name] = "PASS" if condition else "FAIL"
        if not condition:
            issues.append(name)

    try:
        independent = audit_independent(root)
        gate("approvedIndependentPrototype", independent["status"] == "PASS")
        qa = load_json(run / "qa_report.json")
        structure = load_json(run / "structure_qa_report.json")
        layout = load_json(run / "layout_qa_report.json")
        rules = load_json(run / "design_rule_report.json")
        document = load_json(run / "final_ui_ir.json")
        checkpoint = load_json(run / "checkpoint.json")
        manifest = load_json(run / "manifest.json")
        preflight = load_json(run / "figma_preflight.json")
        native = load_json(task / "figma/native-read.json")
        geometry = load_json(geometry_path or task / "figma/native-geometry-read.json")
        visual = load_json(visual_path or task / "visual-review.json")
        admission = load_json(root / "registries/components/v0.2.6/admission.json")

        gate("completePageTreeAndHumanReview", structure["status"] == "PASS"
             and structure["readyForLayout"] is True and structure["issues"] == [])
        gate("deterministicRuleLayout", layout["status"] == "PASS"
             and qa["layoutRepeatable"] is True and rules["status"] == "PASS"
             and not any(key in load_json(source / "layout-plan.json") for key in ("x", "y")))
        gate("platformNeutralUiIr", not validate_document(document)
             and document["documentId"] == "user-management-compact-search"
             and preflight["plan"]["uiIrSha256"] == qa["uiIrSha256"])
        nodes = [node for page in document["pages"] for node in walk(page)]
        components = [node["componentId"] for node in nodes if node["type"] == "ComponentInstance"]
        icons = [node["iconId"] for node in nodes if node["type"] == "IconInstance"]
        gate("admittedComponentsAndRemixIcon", admission["status"] == "PASS"
             and len(admission["components"]) == 7
             and len(components) == 4 and set(components) <= set(admission["components"])
             and icons == ["remix.settings-3-line"]
             and manifest["registries"]["components"] == admission["registrySha256"])
        stages = checkpoint["stages"]
        gate("savedStagesAndCheckpointRecovery", len(stages) == 9
             and all((run / row["artifact"]).is_file()
                     and digest(run / row["artifact"]) == row["artifactSha256"] for row in stages.values())
             and qa["executedStages"] == [] and set(qa["reusedStages"]) == set(stages))
        gate("lockedFigmaNativeExecution", preflight["status"] == "PASS"
             and independent["status"] == "PASS"
             and native["root"]["type"] == "FRAME"
             and len(native["instances"]) == 5
             and all(row["mainComponentId"] for row in native["instances"])
             and digest(task / "figma/native.png") == digest(task / "figma/native-repeat.png"))

        texts = geometry["texts"]
        root_box = geometry["root"]["box"]
        gate("defaultFontsAndNoTextClipping", geometry["root"]["id"] == native["root"]["id"]
             and len(texts) == len(native["texts"]) == 21
             and all(row["visible"] and row["box"] and inside(row["box"], root_box)
                     and all(inside(row["box"], ancestor["box"]) for ancestor in row["clippingAncestors"])
                     and row["fontFamily"] == ("Ionicons" if row["name"] == "source/ionicons-arrow" else "Inter")
                     for row in texts))
        gate("actualVisualReview", visual["status"] == "PASS"
             and visual["sourceImageSha256"] == digest(task / "figma/native.png")
             and len(visual["checks"]) >= 6
             and all(value == "PASS" for value in visual["checks"].values()))
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        issues.append("invalid_or_missing_gate_evidence: " + str(exc))

    return {"scope": "v02-independent-prototype-figma-release-gates",
            "status": "FIGMA_SCOPED_PASS" if not issues else "INVALID_EVIDENCE",
            "releaseReady": False, "figmaScopedReady": not issues,
            "gates": gates,
            "deferredGates": ["penpot_native_execution", "remaining_11_dual_platform_component_admissions",
                              "cross_platform_visual_comparison", "full_v02_release"],
            "issues": issues}


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
    return 0 if result["figmaScopedReady"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
