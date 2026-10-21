"""Batch evidence review is deterministic and fails closed on changed sources."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.audit_figma_candidate_batch import audit
from validators.ui_ir import ROOT


class FigmaCandidateBatchTests(unittest.TestCase):
    def test_all_eleven_are_checked_together_without_promotion(self):
        result = audit()
        self.assertEqual(result["status"], "PASS", result["issues"])
        self.assertEqual(result["candidateCount"], 11)
        self.assertEqual(result["fixedScopeReviewCount"], 7)
        self.assertEqual(result["formalRegistryAdmission"], "NOT_RUN")
        self.assertTrue(all(row["status"] == "PASS" for row in result["rows"]))

    def test_changed_official_identity_blocks_the_batch(self):
        source = ROOT / "artifacts/task-079/tree-source/component_ir.json"
        with tempfile.TemporaryDirectory() as directory:
            changed = json.loads(source.read_text(encoding="utf-8"))
            changed["components"][0]["logicalComponentId"] = "changed.tree"
            path = Path(directory) / "component_ir.json"
            path.write_text(json.dumps(changed), encoding="utf-8")
            result = audit(source_overrides={"Tree": path})
        self.assertEqual(result["status"], "FAIL")
        self.assertIn({"componentType": "Tree", "code": "source_native_identity_mismatch"},
                      result["issues"])


if __name__ == "__main__":
    unittest.main()
