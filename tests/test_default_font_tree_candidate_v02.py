import copy
import unittest

from scripts.default_font_tree_candidate_audit_v02 import ROOT, TASK, audit, read, sha


class TreeCandidateTests(unittest.TestCase):
    def test_locked_figma_candidate_passes_without_admission(self):
        report = audit(read(TASK / "native-read.json"))
        self.assertEqual(report["status"], "CANDIDATE_REVIEW")
        self.assertTrue(all(report["checks"].values()))
        self.assertFalse(report["admissionEligible"])
        metadata = read(ROOT / "adapters/figma/metadata/tree-default-font-candidate-0.2.0.json")
        self.assertEqual(metadata["candidateAuditSha256"],
                         sha(ROOT / "artifacts/task-080/tree-candidate-audit.json"))

    def test_changed_child_label_fails(self):
        observed = copy.deepcopy(read(TASK / "native-read.json"))
        observed["nodes"][4]["characters"] = "市场部"
        self.assertFalse(audit(observed)["checks"]["editableDefaultFontText"])


if __name__ == "__main__":
    unittest.main()
