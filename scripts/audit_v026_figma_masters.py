"""Audit the seven admitted Figma component references against an independent native read."""
from pathlib import Path
import argparse
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validators.ui_ir import ROOT, load_json


def expected_texts(component):
    scope = component["contentScope"]
    kind = component["componentType"]
    if kind == "Input":
        return [scope["placeholder"]]
    if kind == "Select":
        return [scope["selectedText"]]
    if kind == "Table":
        return [str(row[column["key"]]) for row in scope["data"] for column in scope["columns"]]
    return [scope["text"]]


def audit(root=ROOT, *, native_path=None):
    root = Path(root)
    native = load_json(native_path or root / "artifacts/task-111/figma-live-masters.json")
    catalog = load_json(root / "registries/components/v0.2.6/catalog.json")
    admission = load_json(root / "registries/components/v0.2.6/admission.json")
    bindings = load_json(root / "adapters/figma/metadata/component-bindings-0.2.6.json")
    issues = []
    components = catalog["components"]
    if admission["status"] != "PASS" or set(admission["components"]) != set(components):
        issues.append("admission does not match seven-component catalog")
    if len(components) != 7 or set(bindings["bindings"]) != set(components):
        issues.append("seven-component Figma bindings are incomplete")
    if bindings["registrySha256"] != admission["registrySha256"]:
        issues.append("Figma binding registry hash differs from admission")
    if native["fileReference"] != "0vGWSRoLxBiVPXiZ8xJAX9" or set(native["components"]) != set(components):
        issues.append("native read is for a different file or component set")
    for logical_id, component in components.items():
        read = native["components"].get(logical_id)
        if not read:
            issues.append(f"{logical_id}: native master missing")
            continue
        binding = bindings["bindings"][logical_id]["variants"]["default"]
        if (binding["kind"] != "component" or binding["fileReference"] != native["fileReference"]
                or read["id"] != binding["componentReference"] or read["type"] != "COMPONENT"
                or not read["found"] or not read["pageId"]):
            issues.append(f"{logical_id}: native identity differs from binding")
        if binding["fidelityReportSha256"] != component["fidelity"]["reportSha256"]:
            issues.append(f"{logical_id}: fidelity report hash differs from catalog")
        scope = component["contentScope"]
        if (read["width"], read["height"]) != (scope["width"], scope["height"]):
            issues.append(f"{logical_id}: native dimensions differ from content scope")
        texts = read["texts"]
        actual = [text["characters"] for text in texts if text["fontFamily"] == "Inter"]
        if actual != expected_texts(component):
            issues.append(f"{logical_id}: fixed text differs from catalog")
        if any(text["width"] <= 0 or text["height"] <= 0 or text["fontSize"] <= 0 for text in texts):
            issues.append(f"{logical_id}: text has invalid geometry or font size")
        other = [text for text in texts if text["fontFamily"] != "Inter"]
        if logical_id == "form.select.default.medium":
            if len(other) != 1 or other[0]["fontFamily"] != "Ionicons" or other[0]["characters"] != "\uf116":
                issues.append(f"{logical_id}: native select arrow differs")
        elif other:
            issues.append(f"{logical_id}: unexpected non-default font")
    return {
        "scope": "v026-seven-component-figma-native-liveness",
        "status": "PASS" if not issues else "FAIL",
        "releaseReady": False,
        "nativeReadMethod": native["readMethod"],
        "componentCount": len(components),
        "checkedLogicalIds": sorted(components),
        "issues": issues,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/task-111/figma-master-liveness.json")
    args = parser.parse_args()
    report = audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
