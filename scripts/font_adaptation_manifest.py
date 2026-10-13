"""Lock approved V0.2 font-adaptation inputs before new native component measurement."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policies/font-adaptation-0.2.0.json"
AUDIT = ROOT / "artifacts/task-025/source-font-compatibility.json"
PROFILE = {p: ROOT / f"artifacts/task-024/{p}/profile.json" for p in ("figma", "penpot")}
SOURCE_FILES = {
    "artifacts/task-023/replay-final/first/component_ir.json",
    "component-builder/runtime-renderer/metadata/headed-table-source/two-column-typography/component_ir.json",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_manifest(policy, audit, profiles, source_hashes, metadata_hashes):
    if (policy.get("scope") != "v02-platform-default-font-component-adaptation"
            or policy.get("version") != "0.2.0" or policy.get("decisionStatus") != "USER_APPROVED"
            or policy.get("fontSelection") != "platform-native-default"
            or policy.get("componentAdmission") != "NOT_RUN"
            or policy.get("readyForPageGeneration") is not False
            or policy.get("releaseReady") is not False):
        raise ValueError("invalid_adaptation_policy")
    if (audit.get("scope") != "v02-default-font-source-compatibility"
            or audit.get("version") != "0.2.0" or audit.get("status") != "REMEASURE_REQUIRED"
            or audit.get("nativeAcceptance") != "NOT_RUN"
            or audit.get("readyForPageGeneration") is not False
            or audit.get("releaseReady") is not False):
        raise ValueError("invalid_source_audit")
    if set(audit.get("sourceSha256", {})) != SOURCE_FILES or audit["sourceSha256"] != source_hashes:
        raise ValueError("source_evidence_changed")
    if audit.get("targetMetadataSha256") != metadata_hashes:
        raise ValueError("target_metadata_changed")
    if {item.get("componentType") for item in audit.get("components", [])} != {"Button", "Input", "Select", "Table"} or len(audit["components"]) != 4:
        raise ValueError("incomplete_component_coverage")
    targets = {}
    for platform in ("figma", "penpot"):
        profile = profiles.get(platform, {})
        if (profile.get("platform") != platform or profile.get("status") != "PASS"
                or profile.get("fontBindingReady") is not True
                or profile.get("textSampleReview") != "PASS"
                or profile.get("nativeAcceptance") != "NOT_RUN"
                or profile.get("readyForPageGeneration") is not False
                or profile.get("releaseReady") is not False):
            raise ValueError("invalid_native_font_profile:" + platform)
        expected = audit["targetFontMetadata"][platform]
        if (profile.get("defaultFont", {}).get("family") != expected["family"]
                or profile.get("fileReference") != expected["fileReference"]):
            raise ValueError("target_font_identity_changed:" + platform)
        targets[platform] = {"fileReference": profile["fileReference"],
                             "pageReference": profile["pageReference"],
                             "fontFamily": profile["defaultFont"]["family"],
                             "bindings": profile["bindings"],
                             "componentMeasurement": "NOT_RUN",
                             "nativeAdmission": "NOT_RUN"}
    for item in audit["components"]:
        if item.get("measurementReusable") is not False or set(item.get("targets", {})) != set(targets):
            raise ValueError("old_measurement_reuse_forbidden")
        for platform in targets:
            target = item["targets"][platform]
            if target.get("measurement") != "NOT_RUN" or target.get("nativeAdmission") != "NOT_RUN":
                raise ValueError("unsupported_admission_claim")
    return {"scope": "v02-font-adaptation-input-manifest", "version": "0.2.0",
            "status": "INPUTS_LOCKED_MEASUREMENT_PENDING",
            "sourceSha256": dict(source_hashes), "targetMetadataSha256": dict(metadata_hashes),
            "targets": targets,
            "components": [{"type": item["componentType"], "logicalComponentId": item["logicalComponentId"],
                            "measurement": "NOT_RUN", "nativeAdmission": "NOT_RUN"}
                           for item in audit["components"]],
            "effectiveCjkFontIdentity": "UNVERIFIED",
            "readyForPageGeneration": False, "releaseReady": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        parser.error("Output must be inside artifacts")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('{"status":"FAIL","releaseReady":false}\n', encoding="utf-8")
    try:
        policy = json.loads(POLICY.read_bytes())
        audit = json.loads(AUDIT.read_bytes())
        profiles = {p: json.loads(path.read_bytes()) for p, path in PROFILE.items()}
        source_hashes = {relative: sha(ROOT / relative) for relative in SOURCE_FILES}
        metadata_hashes = {relative: sha(ROOT / relative) for relative in audit["targetMetadataSha256"]}
        result = make_manifest(policy, audit, profiles, source_hashes, metadata_hashes)
        result.update(policySha256=sha(POLICY), auditSha256=sha(AUDIT),
                      profileSha256={p: sha(path) for p, path in PROFILE.items()})
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": result["status"], "components": len(result["components"]),
                          "releaseReady": False}))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
