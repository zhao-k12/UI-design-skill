"""Check extracted IR shape, DOM integrity and local evidence hashes; not fidelity."""
import argparse
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from validators.ui_ir import ROOT, load_json, pointer


def validate_bundle(bundle):
    try:
        json.dumps(bundle, allow_nan=False)
    except (TypeError, ValueError) as exc:
        return [{"code": "invalid_component_ir", "path": "/", "message": str(exc)}]
    schema = load_json(ROOT / "schemas/component-ir.schema.json")
    Draft202012Validator.check_schema(schema)
    issues = [{"code": "invalid_component_ir", "path": pointer(error.absolute_path), "message": error.message}
              for error in Draft202012Validator(schema).iter_errors(bundle)]
    if issues:
        return issues
    seen = set()
    for index, component in enumerate(bundle["components"]):
        prefix = f"/components/{index}"
        identity = (component["logicalComponentId"], component["variant"])
        if identity in seen:
            issues.append({"code": "duplicate_component_ir", "path": prefix, "message": "Duplicate logical component and variant"})
        seen.add(identity)
        paths = {node["path"] for node in component["nodes"]}
        if len(paths) != len(component["nodes"]) or component["nodes"][0]["path"] != "0":
            issues.append({"code": "invalid_dom_tree", "path": prefix + "/nodes", "message": "DOM paths must be unique and begin with the root"})
        for node in component["nodes"]:
            expected = None if node["path"] == "0" else node["path"].rsplit(".", 1)[0]
            if node["parentPath"] != expected or (expected is not None and expected not in paths):
                issues.append({"code": "invalid_dom_parent", "path": prefix + "/nodes", "message": "DOM parent must exist and match the path"})
        root = component["nodes"][0]
        if not root["visible"] or any(abs(root["bounds"][axis] - component["rootBounds"][axis]) > 1e-6 for axis in ("width", "height")):
            issues.append({"code": "inconsistent_root_bounds", "path": prefix, "message": "Root visibility and measured dimensions must agree"})
        for icon in component["iconMetrics"]:
            if icon["path"] not in paths:
                issues.append({"code": "invalid_icon_path", "path": prefix + "/iconMetrics", "message": "Icon metrics must reference an extracted DOM node"})
    return sorted(issues, key=lambda item: (item["path"], item["code"]))


def verify_artifacts(directory,*,expected_types=None):
    bundle = load_json(directory / "component_ir.json")
    issues = validate_bundle(bundle)
    if issues:
        return issues
    manifest = load_json(directory / "runtime_manifest.json")
    extraction = load_json(directory / "extraction_report.json")
    def verify(path, expected):
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            issues.append({"code": "evidence_hash_mismatch", "path": str(path), "message": "Evidence file changed"})
    if extraction.get("status") != "PASS" or extraction.get("fidelityGate") != "NOT_RUN":
        issues.append({"code": "invalid_extraction_report", "path": "/", "message": "Expected successful extraction without a fidelity claim"})
    verify(directory / "component_ir.json", extraction["componentIrSha256"])
    verify(directory / "runtime_manifest.json", extraction["runtimeManifestSha256"])
    verify(directory / "official-runtime-gallery.png", manifest["gallerySha256"])
    required_types={"Button", "Input", "Select"} if expected_types is None else set(expected_types)
    if not required_types or {item["componentType"] for item in bundle["components"]} != required_types:
        issues.append({"code": "incomplete_runtime_extraction", "path": "/components", "message": "Required runtime inventory: "+','.join(sorted(required_types))})
    for component in bundle["components"]:
        verify(directory / component["screenshot"]["path"], component["screenshot"]["sha256"])
        if component["provenance"] != manifest["provenance"] or component["environment"] != manifest["environment"]:
            issues.append({"code": "evidence_provenance_mismatch", "path": "/components", "message": "IR must bind the recorded runtime context"})
    css = manifest["provenance"]["officialCssSha256"]
    served_css = [resource for resource in manifest["servedResources"] if resource["path"] == "/vendor/styles/viewuiplus.css"]
    if not served_css or any(resource["sha256"] != css for resource in served_css):
        issues.append({"code": "official_css_not_served", "path": "/servedResources", "message": "Browser must load the locked official CSS"})
    return issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        issues = verify_artifacts(args.directory)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        issues = [{"code": "invalid_runtime_evidence", "path": "/", "message": str(exc)}]
    report = {"scope": "component_ir_evidence", "status": "FAIL" if issues else "PASS", "fidelityGate": "NOT_RUN", "issues": issues}
    (args.directory / "component_ir_qa_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
