"""Rebind the locked V0.2 font adaptation to the user-approved Penpot replacement file."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "artifacts/task-026/font-adaptation-manifest.json"
NEW_TARGET = ROOT / "adapters/penpot/metadata/default-font-target-0.2.1.json"
CANDIDATES = {platform: ROOT / f"adapters/{platform}/metadata/button-default-font-candidate-0.2.0.json"
              for platform in ("figma", "penpot")}
EVIDENCE_ROOT = {"figma": ROOT / "artifacts/task-027/figma",
                 "penpot": ROOT / "artifacts/task-028/penpot"}
POLICY = ROOT / "policies/font-adaptation-0.2.0.json"
AUDIT = ROOT / "artifacts/task-025/source-font-compatibility.json"
PROFILES = {p: ROOT / f"artifacts/task-024/{p}/profile.json" for p in ("figma", "penpot")}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rebind(base, target, candidates, evidence_valid):
    if (base.get("scope") != "v02-font-adaptation-input-manifest" or base.get("version") != "0.2.0"
            or base.get("status") != "INPUTS_LOCKED_MEASUREMENT_PENDING"
            or base.get("readyForPageGeneration") is not False or base.get("releaseReady") is not False):
        raise ValueError("invalid_historical_input_lock")
    old = base["targets"]["penpot"]
    if (target.get("platform") != "penpot" or target.get("status") != "OBSERVED_IN_REPLACEMENT_FILE"
            or target.get("replacementAuthorizedByUser") is not True
            or target.get("replacesDeletedTarget") != old["fileReference"]
            or target.get("fileReference") == old["fileReference"]
            or target.get("nativeAcceptance") != "NOT_RUN"
            or target.get("readyForPageGeneration") is not False
            or target.get("releaseReady") is not False):
        raise ValueError("invalid_replacement_target")
    if set(candidates) != {"figma", "penpot"} or set(evidence_valid) != set(candidates):
        raise ValueError("incomplete_candidate_evidence")
    button = next((item for item in base["components"] if item["type"] == "Button"), None)
    if button is None:
        raise ValueError("missing_historical_button")
    for platform, candidate in candidates.items():
        expected_file = (target if platform == "penpot" else base["targets"]["figma"])["fileReference"]
        expected_font = (target["defaultFont"]["family"] if platform == "penpot"
                         else base["targets"]["figma"]["fontFamily"])
        if (candidate.get("platform") != platform or candidate.get("status") != "CANDIDATE_REVIEW"
                or candidate.get("fileReference") != expected_file
                or candidate.get("fontBinding", {}).get("family") != expected_font
                or candidate.get("sourceLogicalComponentId") != button["logicalComponentId"]
                or candidate.get("nativeAdmission") != "NOT_RUN"
                or candidate.get("readyForPageGeneration") is not False
                or candidate.get("releaseReady") is not False
                or evidence_valid[platform] is not True):
            raise ValueError("invalid_candidate_binding:" + platform)
    if ({item["type"] for item in base["components"]} != {"Button", "Input", "Select", "Table"}
            or any(item["measurement"] != "NOT_RUN" or item["nativeAdmission"] != "NOT_RUN"
                   for item in base["components"])):
        raise ValueError("unexpected_historical_measurement")
    targets = {
        "figma": {**base["targets"]["figma"], "candidatePageReference": candidates["figma"]["pageReference"],
                  "componentMeasurement": "CANDIDATE_REVIEW", "nativeAdmission": "NOT_RUN"},
        "penpot": {"fileReference": target["fileReference"], "pageReference": target["pageReference"],
                   "fontFamily": target["defaultFont"]["family"],
                   "fontBinding": target["defaultFont"], "componentMeasurement": "CANDIDATE_REVIEW",
                   "nativeAdmission": "NOT_RUN"},
    }
    components = [{**item, "measurement": "CANDIDATE_REVIEW" if item["type"] == "Button" else "NOT_RUN"}
                  for item in base["components"]]
    return {"scope": "v02-font-adaptation-input-manifest", "version": "0.2.1",
            "status": "TARGET_REPLACED_BUTTON_CANDIDATES_PENDING_ADMISSION",
            "historicalPenpotFileReference": old["fileReference"],
            "sourceSha256": base["sourceSha256"], "targets": targets,
            "candidateComponentIds": {p: c["componentId"] for p, c in candidates.items()},
            "components": components, "effectiveCjkFontIdentity": "UNVERIFIED",
            "readyForPageGeneration": False, "releaseReady": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if not out.is_relative_to((ROOT / "artifacts").resolve()):
        parser.error("Output must be inside artifacts")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('{"status":"FAIL","releaseReady":false}\n', encoding="utf-8")
    try:
        base = json.loads(BASE.read_bytes())
        target = json.loads(NEW_TARGET.read_bytes())
        candidates = {p: json.loads(path.read_bytes()) for p, path in CANDIDATES.items()}
        if (base.get("policySha256") != sha(POLICY) or base.get("auditSha256") != sha(AUDIT)
                or any(base.get("profileSha256", {}).get(p) != sha(path) for p, path in PROFILES.items())
                or any(sha(ROOT / relative) != expected
                       for relative, expected in base.get("targetMetadataSha256", {}).items())):
            raise ValueError("historical_input_lock_changed")
        evidence_valid = {}
        for platform, candidate in candidates.items():
            checksums = candidate["evidenceSha256"]
            report = json.loads((EVIDENCE_ROOT[platform] / "audit.json").read_bytes())
            evidence_valid[platform] = (bool(checksums) and all(
                sha(EVIDENCE_ROOT[platform] / name) == expected for name, expected in checksums.items())
                and report.get("status") == "CANDIDATE_REVIEW"
                and report.get("nativeComponentId") == candidate.get("componentId")
                and report.get("nativeAdmission") == "NOT_RUN" and report.get("releaseReady") is False)
        if target.get("candidateCaptureSha256") != sha(EVIDENCE_ROOT["penpot"] / "independent-capture.json"):
            raise ValueError("replacement_font_observation_changed")
        if any(sha(ROOT / relative) != expected for relative, expected in base["sourceSha256"].items()):
            raise ValueError("source_evidence_changed")
        result = rebind(base, target, candidates, evidence_valid)
        result["inputSha256"] = {str(path.relative_to(ROOT)).replace("\\", "/"): sha(path)
                                 for path in (BASE, NEW_TARGET, *CANDIDATES.values())}
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": result["status"], "penpotFile": result["targets"]["penpot"]["fileReference"],
                          "releaseReady": False}))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
