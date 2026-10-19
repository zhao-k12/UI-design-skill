import copy
import unittest

from scripts.default_font_datepicker_candidate_audit_v02 import ROOT, TASK, audit, read, sha


class DatePickerCandidateTests(unittest.TestCase):
    def test_locked_figma_candidate_passes_without_admission(self):
        report = audit(read(TASK / "native-read.json"))
        self.assertEqual(report["status"], "CANDIDATE_REVIEW")
        self.assertTrue(all(report["checks"].values()))
        self.assertFalse(report["admissionEligible"])
        metadata = read(ROOT / "adapters/figma/metadata/datepicker-default-font-candidate-0.2.0.json")
        self.assertEqual(metadata["candidateAuditSha256"],
                         sha(ROOT / "artifacts/task-083/datepicker-candidate-audit.json"))

    def test_wrong_date_fails(self):
        observed = copy.deepcopy(read(TASK / "native-read.json"))
        observed["nodes"][1]["characters"] = "2024-01-02"
        self.assertFalse(audit(observed)["checks"]["editableDefaultFontText"])


if __name__ == "__main__":
    unittest.main()
