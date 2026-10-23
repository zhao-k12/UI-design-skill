"""Regression cases for omitted menu affordances and wrong status variants."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.audit_prototype_observations import audit


class PrototypeObservationAuditTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        folder = Path(self.temp.name)
        self.source = folder / "source.png"
        self.source.write_bytes(b"prototype")
        self.screenshots = {}
        for name in ("skeleton", "component", "delivery"):
            path = folder / f"{name}.png"
            path.write_bytes(name.encode())
            self.screenshots[name] = path
        source_hash = sha256(self.source.read_bytes()).hexdigest()
        menu = {"leading": "icon", "trailing": "chevron", "surface": "plain", "shape": "rect", "role": "menu-parent"}
        status = {"leading": "dot", "trailing": "none", "surface": "filled", "shape": "pill", "role": "status-label"}
        self.observation = {"sourceSha256": source_hash, "items": [
            {"id": "menu-home", "region": "sidebar", "sourceEvidence": "一级菜单右侧可见箭头", "decision": "include", "treeRef": "sidebar[0]", "traits": menu},
            {"id": "row-1-status", "region": "table", "sourceEvidence": "状态为带圆点的填充胶囊", "decision": "include", "treeRef": "rows[0].status", "traits": status},
        ]}
        self.scan = {"sourceSha256": source_hash, "items": [
            {"id": item["id"], "region": item["region"], "traits": deepcopy(item["traits"])}
            for item in self.observation["items"]
        ]}
        self.review = {"sourceSha256": source_hash, "items": [
            {"id": item["id"], "component": "Submenu" if item["id"] == "menu-home" else "Tag",
             "variantReason": "选择与来源呈现类别对应的官方变体",
             "officialEvidence": "node_modules/view-ui-plus/src/components",
             "renderedTraits": deepcopy(item["traits"]),
             "checks": {stage: "PASS" for stage in ("tree", "skeleton", "component", "delivery")}}
            for item in self.observation["items"]
        ], "screenshotSha256": {name: sha256(path.read_bytes()).hexdigest()
                                for name, path in self.screenshots.items()}}

    def check(self):
        return audit(self.source, self.observation, self.scan, self.review, self.screenshots)

    def test_complete_review_passes(self):
        self.assertEqual(self.check()["status"], "PASS")

    def test_second_scan_catches_missing_menu_arrow(self):
        self.scan["items"][0]["traits"]["trailing"] = "none"
        result = self.check()
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("independent_scan_disagrees:menu-home", result["issues"])

    def test_render_review_catches_outlined_instead_of_filled_tag(self):
        self.review["items"][1]["renderedTraits"]["surface"] = "outlined"
        result = self.check()
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("rendered_variant_mismatch:row-1-status", result["issues"])

    def test_review_cannot_skip_a_source_item(self):
        self.review["items"].pop()
        self.assertIn("review_coverage_mismatch", self.check()["issues"])

    def make_batched_review(self):
        self.review["reviewMode"] = "batched-v2"
        self.review["stageChecks"] = {stage: "PASS" for stage in ("tree", "skeleton", "component", "delivery")}
        self.review["variantRules"] = [
            {"id": "menu-parent", "component": "Submenu", "variantReason": "官方子菜单含箭头",
             "officialEvidence": "node_modules/view-ui-plus/src/components/menu/submenu.vue"},
            {"id": "status-label", "component": "Tag", "variantReason": "官方填充状态类别",
             "officialEvidence": "node_modules/view-ui-plus/src/components/tag/tag.vue"},
        ]
        for item in self.review["items"]:
            item.pop("checks")
            item.pop("component")
            item.pop("variantReason")
            item.pop("officialEvidence")
            item["variantRef"] = "menu-parent" if item["id"] == "menu-home" else "status-label"
        relation = {"id": "menu-icon-label", "sourceIds": ["menu-home"],
                    "kind": "icon-label-spacing", "sourceEvidence": "图标与菜单文字间有可见间隔"}
        self.observation["relations"] = [relation]
        self.scan["relations"] = [{**{key: relation[key] for key in ("id", "sourceIds", "kind")},
                                    "visual": "菜单图标和文字留有间隔"}]
        self.review["relationChecks"] = [{"id": relation["id"], "status": "PASS",
                                          "officialEvidence": "官方 Menu 组合源码",
                                          "renderedEvidence": "默认组件与交付截图均有间隔"}]

    def test_batched_review_checks_stage_once_and_relation_once(self):
        self.make_batched_review()
        self.assertEqual(self.check()["status"], "PASS")
        self.review["relationChecks"][0]["status"] = "FAIL"
        self.assertIn("relation_unreviewed:menu-icon-label", self.check()["issues"])

    def test_batched_review_rejects_missing_stage_and_relation_scan(self):
        self.make_batched_review()
        self.review["stageChecks"]["component"] = "FAIL"
        self.scan["relations"] = []
        issues = self.check()["issues"]
        self.assertIn("stage_review_incomplete", issues)
        self.assertIn("relation_coverage_mismatch", issues)

    def test_batched_review_rejects_unknown_shared_variant(self):
        self.make_batched_review()
        self.review["items"][0]["variantRef"] = "missing"
        self.assertIn("component_variant_reason_missing:menu-home", self.check()["issues"])


if __name__ == "__main__":
    unittest.main()
