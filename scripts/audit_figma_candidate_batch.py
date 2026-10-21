"""Audit every remaining Figma component candidate in one reproducible batch."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.audit_v02_component_coverage_figma import FIGMA_ONLY_TASKS, audit as audit_coverage


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def audit(root=ROOT, *, source_overrides=None, qa_overrides=None):
    root = Path(root)
    source_overrides = source_overrides or {}
    qa_overrides = qa_overrides or {}
    coverage = audit_coverage(root, qa_overrides=qa_overrides)
    covered = {row["componentType"]: row for row in coverage.get("rows", [])
               if row["state"] == "FIGMA_QA_PASS_ONLY"}
    rows, issues = [], list(coverage.get("issues", []))
    for kind, task_id in FIGMA_ONLY_TASKS.items():
        row_issues = []
        source_dir = root / f"artifacts/task-{task_id - 2:03d}"
        source_paths = list(source_dir.rglob("component_ir.json"))
        qa_paths = list((root / f"artifacts/task-{task_id:03d}").glob("*-figma-qa.json"))
        metadata_paths = list((root / "adapters/figma/metadata").glob(
            kind.lower() + "-default-font-fidelity-*-figma-only.json"))
        if len(source_paths) != 1 or len(qa_paths) != 1 or len(metadata_paths) != 1:
            row_issues.append("source_or_candidate_ambiguous")
        else:
            source_path = Path(source_overrides.get(kind, source_paths[0]))
            qa_path = Path(qa_overrides.get(kind, qa_paths[0]))
            metadata_path = metadata_paths[0]
            try:
                source, qa, metadata = read(source_path), read(qa_path), read(metadata_path)
                components = source.get("components", [])
                if source.get("status") != "PASS" or len(components) != 1:
                    row_issues.append("source_runtime_invalid")
                    component = {}
                else:
                    component = components[0]
                logical_id = qa.get("logicalComponentId")
                if (component.get("logicalComponentId") != logical_id or
                        component.get("componentType") != kind or
                        metadata.get("logicalComponentId") != logical_id or
                        covered.get(kind, {}).get("logicalComponentId") != logical_id):
                    row_issues.append("source_native_identity_mismatch")
                screenshot = component.get("screenshot", {})
                screenshot_path = source_paths[0].parent / screenshot.get("path", "")
                if (not screenshot_path.is_file() or
                        screenshot.get("sha256") != digest(screenshot_path) or
                        qa.get("evidenceSha256", {}).get("sourceScreenshot") != digest(screenshot_path)):
                    row_issues.append("official_screenshot_changed")
                extraction = read(source_paths[0].parent / "extraction_report.json")
                if extraction.get("componentIrSha256") != digest(source_path):
                    row_issues.append("component_ir_changed")
                if qa.get("componentIrSha256") and qa["componentIrSha256"] != digest(source_paths[0]):
                    row_issues.append("component_ir_changed")
                if qa.get("status") != "PASS" or metadata.get("status") not in ("PASS", "FIGMA_QA_PASS"):
                    row_issues.append("native_qa_not_passed")
                bounds = component.get("rootBounds", {})
                scope = metadata.get("contentScope")
                scope_status = "EXPLICIT_FIXED_SCOPE" if scope else "NEEDS_FIXED_SCOPE_REVIEW"
                visible_text = sorted({run["text"] for node in component.get("nodes", [])
                                       if node.get("visible") is True
                                       for run in node.get("textRuns", [])
                                       if isinstance(run.get("text"), str) and run["text"].strip()})
                native_read = read(root / f"artifacts/task-{task_id:03d}/figma/native-read.json")
                native_text = {node.get("characters") for node in native_read.get("nodes", [])
                               if node.get("type") == "TEXT"}
                native_text.add(native_read.get("label", {}).get("text"))
                native_text = sorted(text for text in native_text
                                     if isinstance(text, str) and text.strip()
                                     and not all(0xE000 <= ord(char) <= 0xF8FF for char in text))
                if not native_text:
                    row_issues.append("native_visible_text_missing")
                if scope and (scope.get("width") != bounds.get("width") or
                              scope.get("height") != bounds.get("height")):
                    row_issues.append("fixed_scope_geometry_mismatch")
                rows.append({"componentType": kind, "logicalComponentId": logical_id,
                             "status": "PASS" if not row_issues else "FAIL",
                             "sourceComponentIrSha256": digest(source_paths[0]),
                             "sourceScreenshotSha256": screenshot.get("sha256"),
                             "figmaQaSha256": digest(qa_path),
                             "figmaComponentId": metadata.get("componentId"),
                             "figmaFileReference": metadata.get("fileReference"),
                             "sourceVariant": component.get("variant"),
                             "sourceProps": component.get("props"),
                             "sourceVisibleText": visible_text,
                             "nativeVisibleText": native_text,
                             "sourceSize": bounds,
                             "contentScope": scope,
                             "scopeStatus": scope_status,
                             "issues": row_issues})
            except (OSError, ValueError, TypeError, KeyError) as exc:
                row_issues.append("unreadable_evidence: " + str(exc))
        if row_issues and (not rows or rows[-1].get("componentType") != kind):
            rows.append({"componentType": kind, "status": "FAIL", "issues": row_issues})
        issues.extend({"componentType": kind, "code": code} for code in row_issues)
    scope_review = [row["componentType"] for row in rows
                    if row.get("scopeStatus") == "NEEDS_FIXED_SCOPE_REVIEW"]
    return {"scope": "figma-eleven-candidate-batch",
            "status": "PASS" if not issues and len(rows) == len(FIGMA_ONLY_TASKS) else "FAIL",
            "evidenceValid": not issues and len(rows) == len(FIGMA_ONLY_TASKS),
            "candidateCount": len(rows),
            "fixedScopeReviewCount": len(scope_review),
            "fixedScopeReviewTypes": scope_review,
            "formalRegistryAdmission": "NOT_RUN",
            "rows": rows, "issues": issues}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        parser.error("Output must stay in artifacts")
    result = audit()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in
                      ("status", "candidateCount", "fixedScopeReviewCount", "issues")},
                     ensure_ascii=False))
    return 0 if result["evidenceValid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
