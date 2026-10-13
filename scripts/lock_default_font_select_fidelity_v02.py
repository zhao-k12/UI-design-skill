"""Record the passed Select native gate without admitting it to a Registry."""

import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.default_font_select_gate_v02 import ROOT, TASK, run, sha


def build():
    path = ROOT / "artifacts/task-037/select-native-fidelity.json"
    report = run()
    if report["status"] != "PASS" or json.loads(path.read_text(encoding="utf-8")) != report:
        raise ValueError("Select native gate must be current and PASS")
    for platform, row in report["platforms"].items():
        candidate_path = ROOT / f"adapters/{platform}/metadata/select-default-font-candidate-0.2.0.json"
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        if (candidate["componentId"] != row["componentId"]
                or candidate["fileReference"] != row["fileReference"]
                or row["candidateMetadataSha256"] != sha(candidate_path)):
            raise ValueError("Candidate native binding changed: " + platform)
        metadata = {
            "scope": "v02-default-font-select-native-fidelity",
            "gateVersion": "0.2.4",
            "platform": platform,
            "logicalComponentId": report["logicalComponentId"],
            "fileReference": row["fileReference"],
            "componentId": row["componentId"],
            "instanceId": candidate["instanceId"],
            "contentScope": report["contentScopeProposal"],
            "status": "PASS",
            "evidenceSha256": {
                "select-native-fidelity.json": sha(path),
                "candidate-metadata.json": sha(candidate_path),
                "native-svg": row["nativeSvgSha256"],
                "native-png": row["nativePngSha256"],
                "visual-review.json": report["evidenceSha256"]["visualReview"],
            },
            "effectiveCjkFontIdentity": "UNVERIFIED",
            "registryAdmission": "NOT_RUN",
            "readyForPageGeneration": False,
            "releaseReady": False,
        }
        destination = ROOT / f"adapters/{platform}/metadata/select-default-font-fidelity-0.2.4.json"
        destination.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "PASS", "platforms": list(report["platforms"]), "registryAdmission": "NOT_RUN"}


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False))
