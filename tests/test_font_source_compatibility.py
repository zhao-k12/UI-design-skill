import unittest
from copy import deepcopy

from scripts.font_source_compatibility import SOURCES, TARGETS, audit, family_tokens


def fixture():
    documents = {}
    for kind in SOURCES:
        documents[kind] = {"status": "PASS", "components": [{
            "componentType": kind, "logicalComponentId": kind.lower(),
            "rootBounds": {"width": 40, "height": 32},
            "nodes": [{"path": "0", "visible": True, "attributes": {},
                       "textRuns": [{"text": "查询"}],
                       "computedStyle": {"font-family": '"Helvetica Neue", "PingFang SC", Arial',
                                         "font-weight": "400"}}],
        }]}
    targets = {}
    for platform, family in (("figma", "Inter"), ("penpot", "sourcesanspro")):
        targets[platform] = {"platform": platform, "status": "PASS",
                             "defaultFont": {"family": family},
                             "fileReference": platform + "-file",
                             "nativeAcceptance": "NOT_RUN",
                             "readyForPageGeneration": False, "releaseReady": False}
    return documents, targets


class FontSourceCompatibilityTests(unittest.TestCase):
    def test_all_four_components_need_new_measurement(self):
        sources, targets = fixture()
        before = deepcopy(sources)
        result = audit(sources, targets)
        self.assertEqual(len(result["components"]), 4)
        self.assertEqual(result["status"], "REMEASURE_REQUIRED")
        self.assertFalse(result["readyForPageGeneration"])
        for item in result["components"]:
            self.assertFalse(item["measurementReusable"])
            self.assertTrue(all(not target["declaredSourceFamilyMatch"] for target in item["targets"].values()))
        self.assertEqual(sources, before)

    def test_matching_stack_still_does_not_reuse_geometry(self):
        sources, targets = fixture()
        targets["figma"]["defaultFont"]["family"] = "PingFang SC"
        result = audit(sources, targets)
        self.assertTrue(result["components"][0]["targets"]["figma"]["declaredSourceFamilyMatch"])
        self.assertFalse(result["components"][0]["measurementReusable"])

    def test_invalid_target_claim_rejected(self):
        for key, value in (("status", "FAIL"), ("nativeAcceptance", "PASS"),
                           ("releaseReady", True), ("readyForPageGeneration", True)):
            sources, targets = fixture()
            targets["figma"][key] = value
            with self.assertRaisesRegex(ValueError, "target_font_metadata"):
                audit(sources, targets)

    def test_missing_source_text_or_style_rejected(self):
        for changed in ({"textRuns": []}, {"computedStyle": {}}, {"visible": False}):
            sources, targets = fixture()
            sources["Button"]["components"][0]["nodes"][0].update(changed)
            with self.assertRaisesRegex(ValueError, "source_text"):
                audit(sources, targets)

    def test_missing_or_duplicate_source_rejected(self):
        sources, targets = fixture()
        sources["Table"]["components"] = []
        with self.assertRaisesRegex(ValueError, "source_component"):
            audit(sources, targets)
        sources, targets = fixture()
        sources["Table"]["components"].append(deepcopy(sources["Table"]["components"][0]))
        with self.assertRaisesRegex(ValueError, "source_component"):
            audit(sources, targets)

    def test_css_stack_parser(self):
        self.assertEqual(family_tokens(' "Helvetica Neue" , Arial, sans-serif '),
                         ("helvetica neue", "arial", "sans-serif"))


if __name__ == "__main__":
    unittest.main()
