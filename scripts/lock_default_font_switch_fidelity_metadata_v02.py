"""Lock Figma-only Switch QA evidence without production admission."""
import hashlib
import json

from validators.ui_ir import ROOT


TASK = ROOT / "artifacts/task-069"
REPORT = TASK / "switch-figma-qa.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    if report["status"] != "PASS" or report["scope"] != "figma-only-qa" \
            or report["admissionEligible"] or report["registryAdmission"] != "DEFERRED_PENPOT":
        raise ValueError("switch_native_gate_not_passed")
    rows = {}
    for platform in ("figma",):
        row = report["platforms"][platform]
        if row["status"] != "PASS":
            raise ValueError(f"{platform}_switch_native_gate_not_passed")
        folder = TASK / platform
        candidate = ROOT / f"adapters/{platform}/metadata/switch-default-font-candidate-0.2.0.json"
        metadata = {"scope": "v02-default-font-switch-figma-qa", "gateVersion": report["gateVersion"],
                    "platform": platform, "logicalComponentId": report["logicalComponentId"],
                    "fileReference": row["fileReference"], "componentId": row["componentId"],
                    "instanceId": row["instanceId"], "contentScope": report["contentScopeProposal"],
                    "status": "PASS", "evidenceSha256": {
                        "switch-figma-qa.json": sha(REPORT), "candidate-metadata.json": sha(candidate),
                        "native-svg": sha(folder / "native.svg"), "native-png": sha(folder / "native.png"),
                        "native-read.json": sha(folder / "native-read.json"),
                        "visual-review.json": sha(TASK / "visual-review.json")},
                    "effectiveCjkFontIdentity": "UNVERIFIED", "admissionEligible": False,
                    "dualPlatformFidelity": "DEFERRED", "registryAdmission": "DEFERRED_PENPOT",
                    "readyForPageGeneration": False, "releaseReady": False}
        path = ROOT / f"adapters/{platform}/metadata/switch-default-font-fidelity-{report['gateVersion']}.json"
        path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        rows[platform] = str(path.relative_to(ROOT))
    return rows


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False))
