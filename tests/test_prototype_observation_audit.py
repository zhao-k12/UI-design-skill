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


if __name__ == "__main__":
    unittest.main()
