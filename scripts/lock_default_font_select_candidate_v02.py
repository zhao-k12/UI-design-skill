"""Lock the two Select candidate records to repeat native exports and source evidence."""

import hashlib
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.default_font_select_candidate_audit_v02 import ROOT, TASK, audit


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    report = audit()
    report_path = TASK / "candidate-audit.json"
    if report["status"] != "CANDIDATE_REVIEW" or json.loads(report_path.read_text(encoding="utf-8")) != report:
        raise ValueError("Select candidate audit must be current and pass both platforms")
    for platform, row in report["platforms"].items():
        record = {
            "scope": "v02-default-font-select-candidate",
            "version": "0.2.0",
            "platform": platform,
            "logicalComponentId": report["logicalComponentId"],
            "sourceVersion": report["sourceVersion"],
            "componentIrSha256": report["componentIrSha256"],
            "fileReference": row["fileReference"],
            "pageReference": row["pageReference"],
            "componentId": row["componentId"],
            "instanceId": row["instanceId"],
            "contentScope": {"modelValue": "enabled", "selectedText": "启用", "width": 240, "height": 32},
            "arrowSource": "Official Ionicons U+F116 outline; glyph provenance locked in TASK-036 audit",
            "status": "CANDIDATE_REVIEW",
            "checks": row["checks"],
            "evidenceSha256": {**row["evidenceSha256"], "candidate-audit.json": sha(report_path)},
            "nativeAdmission": "NOT_RUN",
            "readyForPageGeneration": False,
            "releaseReady": False,
        }
        output = ROOT / f"adapters/{platform}/metadata/select-default-font-candidate-0.2.0.json"
        output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "CANDIDATE_REVIEW", "nativeAdmission": "NOT_RUN"}


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False))
