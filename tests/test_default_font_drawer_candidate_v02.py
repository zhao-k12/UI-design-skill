import unittest

from scripts.default_font_drawer_candidate_audit_v02 import TASK, audit, read


class DrawerCandidateTests(unittest.TestCase):
    def test_native_candidate_matches_locked_source(self):
        report = audit(read(TASK / "native-read.json"))
        self.assertEqual(report["status"], "CANDIDATE_REVIEW")
        self.assertTrue(all(report["checks"].values()))
        self.assertFalse(report["admissionEligible"])


if __name__ == "__main__":
    unittest.main()
