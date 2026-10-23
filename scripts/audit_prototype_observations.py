"""Check independent prototype observations against the reviewed HTML stages.

This validates recorded evidence; it cannot discover pixels an observer omitted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

TRAITS = ("leading", "trailing", "surface", "shape", "role")
STAGES = ("tree", "skeleton", "component", "delivery")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def indexed(rows: object, label: str, issues: list[str]) -> dict[str, dict]:
    if not isinstance(rows, list):
        issues.append(f"{label}_items_missing")
        return {}
    found = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]:
            issues.append(f"{label}_item_invalid")
            continue
        if row["id"] in found:
            issues.append(f"{label}_duplicate:{row['id']}")
        found[row["id"]] = row
    return found


def traits_of(row: dict, label: str, issues: list[str]) -> dict:
    traits = row.get("traits")
    if not isinstance(traits, dict) or any(not isinstance(traits.get(key), str) or not traits[key] for key in TRAITS):
        issues.append(f"{label}_traits_incomplete:{row.get('id', '?')}")
        return {}
    return {key: traits[key] for key in TRAITS}


def audit(source: Path, observation: dict, independent_scan: dict,
          review: dict, screenshots: dict[str, Path]) -> dict:
    issues: list[str] = []
    source_hash = digest(source)
    for label, artifact in (("observation", observation), ("scan", independent_scan), ("review", review)):
        if artifact.get("sourceSha256") != source_hash:
            issues.append(f"{label}_source_mismatch")

    observed = indexed(observation.get("items"), "observation", issues)
    scanned = indexed(independent_scan.get("items"), "scan", issues)
    reviewed = indexed(review.get("items"), "review", issues)
    if not observed:
        issues.append("source_observations_empty")
    if set(observed) != set(scanned):
        issues.append("independent_scan_coverage_mismatch")
    if set(observed) != set(reviewed):
        issues.append("review_coverage_mismatch")
    batched = review.get("reviewMode") == "batched-v2"
    if batched and any(review.get("stageChecks", {}).get(stage) != "PASS" for stage in STAGES):
        issues.append("stage_review_incomplete")
    variant_rules = indexed(review.get("variantRules"), "variant_rule", issues) if batched else {}

    for identifier, item in observed.items():
        source_traits = traits_of(item, "source", issues)
        second = scanned.get(identifier, {})
        if second:
            second_traits = traits_of(second, "scan", issues)
            if second.get("region") != item.get("region") or second_traits != source_traits:
                issues.append(f"independent_scan_disagrees:{identifier}")
        if not item.get("region") or not item.get("sourceEvidence"):
            issues.append(f"source_location_or_evidence_missing:{identifier}")
        decision = item.get("decision")
        result = reviewed.get(identifier, {})
        if decision == "include":
            if not item.get("treeRef"):
                issues.append(f"tree_binding_missing:{identifier}")
            variant = variant_rules.get(result.get("variantRef"), {}) if batched else result
            if not variant.get("component") or not variant.get("variantReason") or not variant.get("officialEvidence"):
                issues.append(f"component_variant_reason_missing:{identifier}")
            rendered = result.get("renderedTraits")
            if not isinstance(rendered, dict) or any(rendered.get(key) != source_traits.get(key) for key in TRAITS):
                issues.append(f"rendered_variant_mismatch:{identifier}")
            if not batched:
                checks = result.get("checks")
                if not isinstance(checks, dict) or any(checks.get(stage) != "PASS" for stage in STAGES):
                    issues.append(f"stage_review_incomplete:{identifier}")
        elif decision == "exclude":
            if not item.get("reason") or result.get("exclusionStatus") != "PASS":
                issues.append(f"exclusion_unreviewed:{identifier}")
        elif decision == "Review":
            issues.append(f"source_unresolved:{identifier}")
        else:
            issues.append(f"decision_invalid:{identifier}")

    if batched:
        relations = indexed(observation.get("relations"), "relation", issues)
        rescanned = indexed(independent_scan.get("relations"), "relation_scan", issues)
        checked = indexed(review.get("relationChecks"), "relation_review", issues)
        if set(relations) != set(rescanned) or set(relations) != set(checked):
            issues.append("relation_coverage_mismatch")
        for identifier, relation in relations.items():
            ids = relation.get("sourceIds")
            second = rescanned.get(identifier, {})
            result = checked.get(identifier, {})
            if (not isinstance(ids, list) or not ids or any(item not in observed for item in ids)
                or not relation.get("kind") or not relation.get("sourceEvidence")):
                issues.append(f"relation_source_invalid:{identifier}")
            if (second.get("sourceIds") != ids or second.get("kind") != relation.get("kind")
                or not second.get("visual")):
                issues.append(f"relation_scan_disagrees:{identifier}")
            if (result.get("status") != "PASS" or not result.get("officialEvidence")
                or not result.get("renderedEvidence")):
                issues.append(f"relation_unreviewed:{identifier}")

    recorded_hashes = review.get("screenshotSha256")
    if not isinstance(recorded_hashes, dict):
        issues.append("screenshot_hashes_missing")
    else:
        for stage in ("skeleton", "component", "delivery"):
            path = screenshots[stage]
            if not path.is_file() or recorded_hashes.get(stage) != digest(path):
                issues.append(f"screenshot_mismatch:{stage}")
    return {"status": "PASS" if not issues else "FAIL", "issues": issues,
            "sourceSha256": source_hash, "observationCount": len(observed)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--observation", required=True, type=Path)
    parser.add_argument("--independent-scan", required=True, type=Path)
    parser.add_argument("--review", required=True, type=Path)
    for stage in ("skeleton", "component", "delivery"):
        parser.add_argument(f"--{stage}", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.source, load(args.observation), load(args.independent_scan),
                       load(args.review), {stage: getattr(args, stage) for stage in ("skeleton", "component", "delivery")})
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.exit(2, f"{error}\n")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
