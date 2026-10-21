"""The live batch read must fail when a master drifts from its admitted snapshot."""
from copy import deepcopy
import unittest

from scripts.audit_v027_figma_batch_masters import audit
from scripts.prepare_figma_batch_master_read import prepare
from validators.ui_ir import ROOT, load_json


class BatchMasterReadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native = load_json(ROOT / "tests/fixtures/figma-v027-batch-master-read.json")

    def test_preparation_covers_eighteen_bound_masters(self):
        script, report = prepare()
        self.assertEqual(report["componentCount"], 18)
        self.assertNotIn("__SPECS__", script)

    def test_real_native_batch_passes(self):
        result = audit(self.native)
        self.assertEqual(result["status"], "PASS", result["issues"])
        self.assertEqual(result["componentCount"], 18)

    def test_changed_native_text_fails_only_affected_row(self):
        changed = deepcopy(self.native)
        changed["components"]["action.button.primary.medium"]["texts"][0]["characters"] = "保存"
        result = audit(changed)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn({"logicalComponentId": "action.button.primary.medium",
                       "code": "native_text_mismatch"}, result["issues"])
        self.assertEqual(sum(row["status"] == "FAIL" for row in result["rows"]), 1)

    def test_changed_native_reference_and_size_fail(self):
        changed = deepcopy(self.native)
        changed["components"]["form.input.default.medium"].update(id="wrong", width=200)
        result = audit(changed)
        self.assertEqual(result["status"], "FAIL")
        codes = {issue["code"] for issue in result["issues"]}
        self.assertIn("native_identity_mismatch", codes)
        self.assertIn("native_size_mismatch", codes)


if __name__ == "__main__":
    unittest.main()
