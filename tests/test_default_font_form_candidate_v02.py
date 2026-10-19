import copy
import unittest

from scripts.default_font_form_candidate_audit_v02 import ROOT, TASK, audit, read, sha


class FormCandidateTests(unittest.TestCase):
    def test_locked_figma_candidate_passes_without_admission(self):
        report = audit(read(TASK / "native-read.json"))
        self.assertEqual(report["status"], "CANDIDATE_REVIEW")
        self.assertTrue(all(report["checks"].values()))
        self.assertFalse(report["admissionEligible"])
        metadata = read(ROOT / "adapters/figma/metadata/form-default-font-candidate-0.2.0.json")
        self.assertEqual(metadata["candidateAuditSha256"],
                         sha(ROOT / "artifacts/task-086/form-candidate-audit.json"))

    def test_wrong_input_component_fails(self):
        observed = copy.deepcopy(read(TASK / "native-read.json"))
        observed["nodes"][3]["mainComponentId"] = "missing"
        self.assertFalse(audit(observed)["checks"]["admittedInputInstance"])


if __name__ == "__main__":
    unittest.main()
