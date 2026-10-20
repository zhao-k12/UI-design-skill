"""Build a new, source-bound compact user-management input from reviewed semantics."""
from copy import deepcopy
from hashlib import sha256
from importlib import import_module
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.prototype.parser import parse
from validators.structure.gate import builder, check
from validators.ui_ir import load_json

BASE = ROOT / "examples/acceptance-prototype-v02"
TARGET = ROOT / "examples/user-management-compact-search"
ARTIFACT = ROOT / "artifacts/task-108"
KEEP = ("header-title", "field-name", "field-status", "query-action",
        "list-title", "user-table", "list-summary")
EVIDENCE = {"e1": "e1", "e3": "e2", "e4": "e2", "e6": "e2",
            "e8": "e3", "e10": "e3", "e11": "e3", "e12": "e3"}


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def remap_evidence(value):
    if isinstance(value, dict):
        return {key: list(dict.fromkeys(EVIDENCE[ref] for ref in item)) if key == "evidence" else remap_evidence(item)
                for key, item in value.items()}
    if isinstance(value, list):
        return [remap_evidence(item) for item in value]
    return value


def build():
    prior_manifest = load_json(BASE / "input-manifest.json")
    for name in ("runtime-capture.json", "runtime-measurements.json", "source-geometry.json",
                 "layout-plan.json", "content.json", "versions.json"):
        if digest(BASE / name) != prior_manifest["files"][name]:
            raise ValueError("Reused source evidence changed: " + name)
    analysis = parse(load_json(TARGET / "observations.json"), TARGET)
    review = load_json(TARGET / "review.json")
    tree = builder.build(analysis)
    structure = check(analysis, tree, TARGET, review)
    if structure["status"] != "PASS":
        raise ValueError("Semantic structure lacks a human approval receipt: " + str(structure))
    save(ARTIFACT / "prototype-analysis.json", analysis)
    save(ARTIFACT / "structure/page_tree.json", tree)
    save(ARTIFACT / "structure/structure_qa_report.json", structure)

    catalog = load_json(ROOT / "registries/components/v0.2.3/catalog.json")
    fidelity = load_json(ROOT / "registries/components/v0.2.3/fidelity-reports.json")
    tokens_data = load_json(ROOT / "registries/tokens/v0.2.2/default.json")
    tokens = import_module("core.design-rules.tokens").TokenRegistry(tokens_data)
    components = import_module("core.component-resolver.registry").ComponentRegistry(catalog, fidelity)

    geometry = load_json(BASE / "source-geometry.json")
    save(TARGET / "source-geometry.json", geometry)
    old_capture = load_json(BASE / "runtime-capture.json")
    old_metrics = load_json(BASE / "runtime-measurements.json")
    needed = {uid for key in KEEP for uid in old_metrics["measurements"][key]["uiIrIds"]}
    needed.update(old_metrics["textMeasurements"][key] for key in KEEP
                  if key in old_metrics["textMeasurements"])
    slots = ("field-name.label", "field-status.label")
    needed.update(old_metrics["slotMeasurements"][key] for key in slots)
    needed.add("button.query")
    capture = {
        "kind": "v02-reused-native-metrics-for-new-prototype", "status": "PASS",
        "method": "Reuse identical fixed component and text measurements; calculate a new layout from reviewed semantics",
        "sourceLocks": {
            "prototype": {"path": TARGET.relative_to(ROOT).as_posix() + "/prototype.txt",
                          "sha256": digest(TARGET / "prototype.txt")},
            "priorCapture": {"path": (BASE / "runtime-capture.json").relative_to(ROOT).as_posix(),
                             "sha256": digest(BASE / "runtime-capture.json")},
            "componentCatalog": {"path": "registries/components/v0.2.3/catalog.json",
                                 "sha256": digest(ROOT / "registries/components/v0.2.3/catalog.json")},
        },
        "evidence": [deepcopy(row) for row in old_capture["evidence"] if row["uiIrId"] in needed],
    }
    source_text = (TARGET / "prototype.txt").read_text(encoding="utf-8")
    for row in capture["evidence"]:
        if row["type"] == "TEXT" and row["characters"] not in source_text:
            raise ValueError("Reused text is absent from the new prototype: " + row["uiIrId"])
    save(TARGET / "runtime-capture.json", capture)
    metrics = deepcopy(old_metrics)
    metrics["sourceCapture"] = (TARGET / "runtime-capture.json").relative_to(ROOT).as_posix()
    metrics["sourceCaptureSha256"] = digest(TARGET / "runtime-capture.json")
    metrics["measurements"] = {key: value for key, value in metrics["measurements"].items() if key in KEEP}
    button = next(row for row in capture["evidence"] if row["uiIrId"] == "button.query")
    metrics["measurements"]["query-action"] = {
        "uiIrIds": ["button.query"], "width": button["width"], "height": button["height"],
        "widthRule": "max", "heightRule": "max",
    }
    metrics["textMeasurements"] = {key: value for key, value in metrics["textMeasurements"].items() if key in KEEP}
    metrics["slotMeasurements"] = {key: value for key, value in metrics["slotMeasurements"].items()
                                   if key in slots and key != "query-action.label"}
    save(TARGET / "runtime-measurements.json", metrics)

    plan = load_json(BASE / "layout-plan.json")
    plan["pageTreeSha256"] = builder.fingerprint(tree)
    plan["measurements"] = {key: value for key, value in plan["measurements"].items() if key in KEEP}
    plan["measurements"]["query-action"].update(width=button["width"], height=button["height"])
    query = plan["sectionConfigs"]["query"]
    query.pop("inlineGrid")
    query.pop("inlineOrder")
    query["buttonAlignment"] = "end"
    plan["sectionConfigs"]["list"] = {"contentOrder": ["list-title", "user-table", "list-summary"]}
    save(TARGET / "layout-plan.json", plan)

    layout_builder = import_module("core.layout.builder")
    layout, report = layout_builder.generate(analysis, tree, TARGET, review, plan, tokens)
    if report["status"] != "PASS":
        raise ValueError("New compact layout failed: " + str(report["issues"]))
    save(ARTIFACT / "layout_tree.json", layout)
    save(ARTIFACT / "layout_qa_report.json", report)

    decisions = load_json(BASE / "decisions.json")
    decisions["layoutTreeSha256"] = builder.fingerprint(layout)
    decisions["registrySha256"] = components.fingerprint
    decisions["items"] = [remap_evidence(row) for row in decisions["items"] if row["sourceId"] in KEEP]
    save(TARGET / "decisions.json", decisions)
    mapping = import_module("core.component-resolver.primitive_mapping").resolve(
        analysis, tree, TARGET, review, plan, decisions, components, tokens, allow_text_primitives=True)
    if mapping["status"] != "PASS":
        raise ValueError("New compact mapping failed: " + str(mapping["issues"]))
    save(ARTIFACT / "component_mapping.json", mapping)

    content = load_json(BASE / "content.json")
    content["mappingSha256"] = builder.fingerprint(mapping)
    content["items"] = [remap_evidence(row) for row in content["items"] if row["sourceId"] in KEEP]
    query_content = next(row for row in content["items"] if row["sourceId"] == "query-action")
    query_content.pop("cellSlots", None)
    query_content.pop("cellDirection", None)
    save(TARGET / "content.json", content)
    save(TARGET / "versions.json", load_json(BASE / "versions.json"))
    files = ("prototype.txt", "observations.json", "review.json", "decisions.json",
             "source-geometry.json", "runtime-capture.json", "runtime-measurements.json",
             "layout-plan.json", "content.json", "versions.json")
    save(TARGET / "input-manifest.json", {
        "kind": "v02-independent-input-package", "status": "READY_FOR_PREFLIGHT",
        "sourcePackage": TARGET.relative_to(ROOT).as_posix(),
        "policy": "new-human-reviewed-compact-structure/reused-identical-native-metrics/fixed-components",
        "files": {name: digest(TARGET / name) for name in files},
    })
    return {"status": "PASS", "semanticItems": len(KEEP), "layoutSha256": builder.fingerprint(layout),
            "sourceSha256": digest(TARGET / "prototype.txt")}


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False))
