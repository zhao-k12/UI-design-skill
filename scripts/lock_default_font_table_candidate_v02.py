"""Lock both fixed-content Table candidate records to native evidence."""

import hashlib
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.default_font_table_candidate_audit_v02 import ROOT, TASK, audit


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    report = audit()
    report_path = TASK / "candidate-audit.json"
    if report["status"] != "CANDIDATE_REVIEW" or json.loads(report_path.read_text(encoding="utf-8")) != report:
        raise ValueError("Table candidate audit must be current and pass both platforms")
    for platform, row in report["platforms"].items():
        record = {
            "scope": "v02-default-font-table-candidate",
            "version": "0.2.0",
            "platform": platform,
            "logicalComponentId": report["logicalComponentId"],
            "sourceVersion": report["sourceVersion"],
            "componentIrSha256": report["componentIrSha256"],
            "fileReference": row["fileReference"],
            "pageReference": row["pageReference"],
            "componentId": row["componentId"],
            "instanceId": row["instanceId"],
            "contentScope": {
                "showHeader": False, "border": False, "stripe": False,
                "columns": [
                    {"title": "姓名", "key": "name", "width": 464},
                    {"title": "状态", "key": "status", "width": 464},
                    {"title": "角色", "key": "role", "width": 464},
                ],
                "data": [
                    {"name": "张三", "status": "启用", "role": "管理员"},
                    {"name": "李四", "status": "启用", "role": "编辑"},
                    {"name": "王五", "status": "停用", "role": "访客"},
                ],
                "width": 1392, "height": 144,
            },
            "status": "CANDIDATE_REVIEW",
            "checks": row["checks"],
            "evidenceSha256": {**row["evidenceSha256"], "candidate-audit.json": sha(report_path),
                               "visual-review.json": report["visualReviewSha256"]},
            "effectiveCjkFontIdentity": "UNVERIFIED",
            "nativeAdmission": "NOT_RUN",
            "readyForPageGeneration": False,
            "releaseReady": False,
        }
        output = ROOT / f"adapters/{platform}/metadata/table-default-font-candidate-0.2.0.json"
        output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "CANDIDATE_REVIEW", "nativeAdmission": "NOT_RUN"}


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False))
