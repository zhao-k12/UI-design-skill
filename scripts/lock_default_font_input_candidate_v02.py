"""Lock both Input candidate records to the repeat native reads and source audit."""
import hashlib
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.default_font_input_candidate_audit_v02 import ROOT, audit


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    report = audit()
    path = ROOT / "artifacts/task-033/candidate-audit.json"
    if report["status"] != "CANDIDATE_REVIEW" or json.loads(path.read_bytes()) != report:
        raise ValueError("Input candidate audit must be current and pass both platforms")
    for platform, row in report["platforms"].items():
        capture = json.loads((ROOT / f"artifacts/task-033/{platform}/independent-capture.json").read_bytes())
        record = {"scope": "v02-default-font-input-candidate", "version": "0.2.0",
                  "platform": platform, "logicalComponentId": report["logicalComponentId"],
                  "sourceVersion": report["sourceVersion"], "componentIrSha256": report["componentIrSha256"],
                  "fileReference": row["fileReference"], "pageReference": capture["pageReference"],
                  "componentId": row["componentId"], "instanceId": capture["instanceId"],
                  "status": "CANDIDATE_REVIEW", "checks": row["checks"],
                  "evidenceSha256": {**row["evidenceSha256"],
                                     "candidate-audit.json": sha(path),
                                     "visual-review.json": report["visualReviewSha256"]},
                  "nativeAdmission": "NOT_RUN", "readyForPageGeneration": False,
                  "releaseReady": False}
        destination = ROOT / f"adapters/{platform}/metadata/input-default-font-candidate-0.2.0.json"
        destination.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "CANDIDATE_REVIEW", "platforms": list(report["platforms"]),
            "nativeAdmission": "NOT_RUN"}


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False))
