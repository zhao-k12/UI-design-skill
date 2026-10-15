import copy
import json
import unittest

from scripts.default_font_card_candidate_audit_v02 import ROOT, TASK, audit, read, sha


class CardCandidateTests(unittest.TestCase):
    def test_locked_figma_candidate_passes_without_admission(self):
        report = audit(read(TASK / "native-read.json"))
        self.assertEqual(report["status"], "CANDIDATE_REVIEW")
        self.assertTrue(all(report["checks"].values()))
        self.assertFalse(report["admissionEligible"])
        self.assertEqual(report["registryAdmission"], "DEFERRED_PENPOT")
        metadata = read(ROOT / "adapters/figma/metadata/card-default-font-candidate-0.2.0.json")
        self.assertEqual(metadata["candidateAuditSha256"], sha(ROOT / "artifacts/task-071/card-candidate-audit.json"))

    def test_changed_title_fails(self):
        observed = copy.deepcopy(read(TASK / "native-read.json"))
        observed["nodes"][2]["characters"] = "其他标题"
        self.assertFalse(audit(observed)["checks"]["defaultFontText"])


if __name__ == "__main__":
    unittest.main()
