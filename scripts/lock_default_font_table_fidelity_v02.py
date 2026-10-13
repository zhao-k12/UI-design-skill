"""Record the passed Table native gate without admitting it to a Registry."""

import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.default_font_table_candidate_audit_v02 import ROOT, TASK, read, sha
from scripts.default_font_table_gate_v02 import run


def build():
    path = ROOT / "artifacts/task-040/table-native-fidelity.json"
    report = run()
    if report["status"] != "PASS" or read(path) != report:
        raise ValueError("Table native gate must be current and PASS")
    for platform, row in report["platforms"].items():
        candidate_path = ROOT / f"adapters/{platform}/metadata/table-default-font-candidate-0.2.0.json"
        candidate = read(candidate_path)
        if (candidate["componentId"] != row["componentId"]
                or candidate["fileReference"] != row["fileReference"]
                or row["candidateMetadataSha256"] != sha(candidate_path)):
            raise ValueError("Candidate native binding changed: " + platform)
        metadata = {
            "scope": "v02-default-font-table-native-fidelity", "gateVersion": "0.2.5",
            "platform": platform, "logicalComponentId": report["logicalComponentId"],
            "fileReference": row["fileReference"], "componentId": row["componentId"],
            "instanceId": candidate["instanceId"], "contentScope": report["contentScopeProposal"],
            "status": "PASS", "evidenceSha256": {
                "table-native-fidelity.json": sha(path),
                "candidate-metadata.json": sha(candidate_path),
                "native-svg": row["nativeSvgSha256"],
                "native-png": row["nativePngSha256"],
                "visual-review.json": report["evidenceSha256"]["visualReview"],
            },
            "effectiveCjkFontIdentity": "UNVERIFIED", "registryAdmission": "NOT_RUN",
            "readyForPageGeneration": False, "releaseReady": False,
        }
        destination = ROOT / f"adapters/{platform}/metadata/table-default-font-fidelity-0.2.5.json"
        destination.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "PASS", "platforms": list(report["platforms"]), "registryAdmission": "NOT_RUN"}


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False))
