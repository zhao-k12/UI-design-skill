"""A visual substitution must have explicit, honest evidence on both sides."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest

from scripts.audit_prototype_observations import audit
from scripts.html_compact import delta_review


SOURCE_TRAITS = {"leading": "logo", "trailing": "none", "surface": "plain", "shape": "square", "role": "brand"}
ACTUAL_TRAITS = {"leading": "icon", "trailing": "none", "surface": "plain", "shape": "circle", "role": "brand"}


@pytest.fixture
def example(tmp_path):
    source = tmp_path / "source.png"
    source.write_bytes(b"source")
    shots = {}
    for stage in ("skeleton", "component", "delivery"):
        shots[stage] = tmp_path / (stage + ".png")
        shots[stage].write_bytes(stage.encode())
    source_hash = sha256(source.read_bytes()).hexdigest()
    source_item = {
        "id": "brand", "region": "header", "sourceEvidence": "原图为方形品牌图案",
        "decision": "include", "treeRef": "brand-node", "traits": deepcopy(SOURCE_TRAITS),
        "substitution": {"status": "resolved", "importance": "noncritical", "businessCritical": False,
                         "exactRequired": False, "description": "圆形图标加品牌文字",
                         "reason": "本次页面任务不要求精确品牌图形"},
    }
    observation = {"sourceSha256": source_hash, "items": [source_item], "relations": []}
    scan = {"sourceSha256": source_hash,
            "items": [{"id": "brand", "region": "header", "traits": deepcopy(SOURCE_TRAITS)}],
            "relations": []}
    rule = {"id": "rule:brand", "component": "Avatar", "variantReason": "替代图标",
            "officialEvidence": "官方 Avatar"}
    plan = {"groups": {"item:brand": {"items": [source_item], "rules": {"brand": rule}}},
            "reusableGroups": []}
    review = {"reviewMode": "delta-v1", "sourceSha256": source_hash,
              "checkedStages": ["tree", "skeleton", "component", "delivery"],
              "confirmedGroups": ["item:brand"], "issues": [], "relationChecks": [],
              "substitutions": {"brand": {"renderedTraits": deepcopy(ACTUAL_TRAITS),
                  "description": "圆形图标加品牌文字", "reason": "图形不影响本次业务识别",
                  "renderedEvidence": "已查看交付截图中的圆形图标与文字"}}}
    return source, shots, observation, scan, plan, review


def run_audit(example):
    source, shots, observation, scan, plan, review = example
    expanded = delta_review(review, plan)
    expanded["screenshotSha256"] = {k: sha256(v.read_bytes()).hexdigest() for k, v in shots.items()}
    return audit(source, observation, scan, expanded, shots)


def test_reviewed_noncritical_substitution_preserves_source_and_reports_actual(example):
    source, shots, observation, scan, plan, review = example
    expanded = delta_review(review, plan)
    assert observation["items"][0]["traits"] == SOURCE_TRAITS
    assert expanded["items"][0]["renderedTraits"] == ACTUAL_TRAITS
    assert run_audit(example)["status"] == "PASS"


@pytest.mark.parametrize("field", ["renderedTraits", "description", "reason", "renderedEvidence"])
def test_substitution_requires_explicit_reviewer_evidence(example, field):
    review = example[-1]
    del review["substitutions"]["brand"][field]
    with pytest.raises(ValueError, match="substitution_review"):
        delta_review(review, example[-2])


@pytest.mark.parametrize(("field", "value"), [
    ("businessCritical", True), ("exactRequired", True),
    ("importance", "critical"), ("status", "pending"), ("reason", ""),
])
def test_critical_unresolved_or_unjustified_substitution_cannot_pass(example, field, value):
    source_item = example[2]["items"][0]
    source_item["substitution"][field] = value
    assert "substitution_unverified:brand" in run_audit(example)["issues"]


def test_undeclared_or_mismatched_substitution_cannot_pass(example):
    source_item = example[2]["items"][0]
    review = example[-1]
    review["substitutions"]["brand"]["description"] = "不同的替代"
    assert "substitution_unverified:brand" in run_audit(example)["issues"]
    del source_item["substitution"]
    with pytest.raises(ValueError, match="substitution_source_not_declared"):
        delta_review(review, example[-2])


@pytest.mark.parametrize("field", ["businessCritical", "exactRequired"])
def test_conflicting_source_level_critical_flag_cannot_be_downgraded(example, field):
    example[2]["items"][0][field] = True
    assert "substitution_unverified:brand" in run_audit(example)["issues"]


def test_old_strict_matching_rejects_unexplained_visual_difference(example):
    source_item = example[2]["items"][0]
    del source_item["substitution"]
    review = example[-1]
    review["substitutions"] = {}
    expanded = delta_review(review, example[-2])
    expanded["items"][0]["renderedTraits"] = deepcopy(ACTUAL_TRAITS)
    expanded["screenshotSha256"] = {
        k: sha256(v.read_bytes()).hexdigest() for k, v in example[1].items()
    }
    result = audit(example[0], example[2], example[3], expanded, example[1])
    assert "rendered_variant_mismatch:brand" in result["issues"]
