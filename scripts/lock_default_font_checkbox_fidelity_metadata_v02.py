"""Lock both native Checkbox fidelity records after the independent gate passes."""
import hashlib
import json

from validators.ui_ir import ROOT


TASK = ROOT / "artifacts/task-061"
REPORT = TASK / "checkbox-native-fidelity.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    if report["status"] != "PASS" or not report["admissionEligible"]:
        raise ValueError("checkbox_native_gate_not_passed")
    rows = {}
    for platform in ("figma", "penpot"):
        row = report["platforms"][platform]
        if row["status"] != "PASS":
            raise ValueError(f"{platform}_checkbox_native_gate_not_passed")
        folder = TASK / platform
        candidate = ROOT / f"adapters/{platform}/metadata/checkbox-default-font-candidate-0.2.0.json"
        metadata = {"scope": "v02-default-font-checkbox-native-fidelity", "gateVersion": report["gateVersion"],
                    "platform": platform, "logicalComponentId": report["logicalComponentId"],
                    "fileReference": row["fileReference"], "componentId": row["componentId"],
                    "instanceId": row["instanceId"], "contentScope": report["contentScopeProposal"],
                    "status": "PASS", "evidenceSha256": {
                        "checkbox-native-fidelity.json": sha(REPORT), "candidate-metadata.json": sha(candidate),
                        "native-svg": sha(folder / "native.svg"), "native-png": sha(folder / "native.png"),
                        "native-read.json": sha(folder / "native-read.json"),
                        "visual-review.json": sha(TASK / "visual-review.json")},
                    "effectiveCjkFontIdentity": "UNVERIFIED", "registryAdmission": "NOT_RUN",
                    "readyForPageGeneration": False, "releaseReady": False}
        path = ROOT / f"adapters/{platform}/metadata/checkbox-default-font-fidelity-{report['gateVersion']}.json"
        path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        rows[platform] = str(path.relative_to(ROOT))
    return rows


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False))
