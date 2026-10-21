"""Compare one live Figma batch read with all 18 locked native component bindings."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validators.ui_ir import ROOT, load_json

FILE_KEY = "0vGWSRoLxBiVPXiZ8xJAX9"


def expected_texts(component):
    scope = component["contentScope"]
    if scope["kind"] == "fixed-native-snapshot":
        return sorted(set(scope["visibleText"]))
    kind = component["componentType"]
    if kind == "Input":
        return [scope["placeholder"]]
    if kind == "Select":
        return [scope["selectedText"]]
    if kind == "Table":
        return sorted({str(row[column["key"]]) for row in scope["data"]
                       for column in scope["columns"]})
    return [scope["text"]]


def audit(native, *, root=ROOT):
    root = Path(root)
    catalog = load_json(root / "registries/components/v0.2.7/catalog.json")
    admission = load_json(root / "registries/components/v0.2.7/admission.json")
    bindings = load_json(root / "adapters/figma/metadata/component-bindings-0.2.7-figma.json")
    components = catalog["components"]
    issues, rows = [], []
    if (len(components) != 18 or set(components) != set(admission["components"])
            or set(components) != set(bindings["bindings"])
            or admission["registrySha256"] != bindings["registrySha256"]):
        issues.append({"code": "admission_or_binding_scope_changed"})
    if native.get("scope") != "figma-batch-master-native-read" \
            or native.get("fileReference") != FILE_KEY \
            or set(native.get("components", {})) != set(components):
        issues.append({"code": "native_batch_identity_changed"})
    for logical_id, component in components.items():
        read = native.get("components", {}).get(logical_id, {})
        variant = component["defaultVariant"]
        binding = bindings["bindings"][logical_id]["variants"][variant]
        row_issues = []
        if (not read.get("found") or read.get("type") != "COMPONENT"
                or read.get("id") != binding["componentReference"]
                or not read.get("pageId") or binding["fileReference"] != FILE_KEY
                or binding["fidelityReportSha256"] != component["fidelity"]["reportSha256"]):
            row_issues.append("native_identity_mismatch")
        scope = component["contentScope"]
        if (read.get("width"), read.get("height")) != (scope["width"], scope["height"]):
            row_issues.append("native_size_mismatch")
        texts = read.get("texts", [])
        visible = sorted({text.get("characters") for text in texts
                          if isinstance(text.get("characters"), str)
                          and text["characters"].strip()
                          and not all(0xE000 <= ord(char) <= 0xF8FF
                                      for char in text["characters"])})
        if visible != expected_texts(component):
            row_issues.append("native_text_mismatch")
        if any(text.get("width", 0) <= 0 or text.get("height", 0) <= 0
               or not isinstance(text.get("fontSize"), (int, float))
               or text["fontSize"] <= 0 for text in texts):
            row_issues.append("native_text_geometry_invalid")
        if any(text.get("fontFamily") != "Inter" for text in texts
               if text.get("characters") in visible):
            row_issues.append("native_default_font_mismatch")
        rows.append({"logicalComponentId": logical_id,
                     "status": "PASS" if not row_issues else "FAIL", "issues": row_issues})
        issues.extend({"logicalComponentId": logical_id, "code": code} for code in row_issues)
    return {"scope": "v027-figma-batch-master-audit", "status": "PASS" if not issues else "FAIL",
            "componentCount": len(rows), "rows": rows, "issues": issues}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        parser.error("Output must stay in artifacts")
    result = audit(load_json(args.native))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "componentCount": result["componentCount"],
                      "issues": result["issues"]}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
