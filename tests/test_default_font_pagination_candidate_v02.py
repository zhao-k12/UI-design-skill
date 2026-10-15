import copy
import unittest

from scripts.default_font_pagination_candidate_audit_v02 import ROOT, TASK, audit, read, sha


class PaginationCandidateTests(unittest.TestCase):
    def test_locked_figma_candidate_passes_without_admission(self):
        result = audit(read(TASK / "native-read.json"))
        self.assertEqual(result["status"], "CANDIDATE_REVIEW")
        self.assertTrue(all(result["checks"].values()))
        self.assertFalse(result["admissionEligible"])
        self.assertEqual(result["registryAdmission"], "DEFERRED_PENPOT")
        metadata = read(ROOT / "adapters/figma/metadata/pagination-default-font-candidate-0.2.0.json")
        self.assertEqual(metadata["candidateAuditSha256"],
                         sha(ROOT / "artifacts/task-074/pagination-candidate-audit.json"))

    def test_wrong_active_page_fails(self):
        observed = copy.deepcopy(read(TASK / "native-read.json"))
        observed["nodes"][6]["characters"] = "2"
        self.assertFalse(audit(observed)["checks"]["editableDefaultFontDigits"])


if __name__ == "__main__":
    unittest.main()
