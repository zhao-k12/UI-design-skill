"""Batch planning must reuse identical admissions and isolate changed configurations."""
import unittest

from scripts.plan_figma_variant_batch import plan
from validators.ui_ir import ROOT, load_json


class BatchPlanTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_json(ROOT / "registries/components/v0.2.7/catalog.json")
        self.logical_id, self.entry = next(iter(self.catalog["components"].items()))

    def request(self, logical_id=None, scope=None):
        return {"components": [{"logicalComponentId": logical_id or self.logical_id,
                                "componentType": self.entry["componentType"],
                                "variant": self.entry["defaultVariant"],
                                "contentScope": scope or self.entry["contentScope"]}]}

    def test_identical_configuration_reuses_admission(self):
        result = plan(self.request())
        self.assertEqual(result["counts"]["REUSE_ADMITTED"], 1)
        self.assertEqual(result["captureQueue"], [])

    def test_all_eighteen_admitted_configurations_reuse_in_one_batch(self):
        entries = [{"logicalComponentId": logical_id,
                    "componentType": component["componentType"],
                    "variant": component["defaultVariant"],
                    "contentScope": component["contentScope"]}
                   for logical_id, component in self.catalog["components"].items()]
        result = plan({"components": entries})
        self.assertEqual(result["counts"]["REUSE_ADMITTED"], 18)
        self.assertEqual(result["captureQueue"], [])

    def test_new_identity_enters_single_capture_queue(self):
        result = plan(self.request(logical_id="action.button.secondary.medium"))
        self.assertEqual(result["captureQueue"], ["action.button.secondary.medium"])
        self.assertTrue(result["readyForCapture"])

    def test_changed_existing_identity_requires_migration(self):
        scope = {**self.entry["contentScope"], "text": "保存"}
        result = plan(self.request(scope=scope))
        self.assertEqual(result["counts"]["MIGRATION_REQUIRED"], 1)
        self.assertFalse(result["readyForCapture"])

    def test_duplicate_identity_is_rejected(self):
        entry = self.request()["components"][0]
        with self.assertRaises(ValueError):
            plan({"components": [entry, entry]})

    def test_unknown_type_is_rejected(self):
        entry = self.request()["components"][0]
        entry["componentType"] = "Unknown"
        with self.assertRaises(ValueError):
            plan({"components": [entry]})


if __name__ == "__main__":
    unittest.main()
