import copy
import unittest

from scripts.audit_v026_admission_boundary import ROOT, audit
from validators.ui_ir import load_json


class V026AdmissionBoundaryTests(unittest.TestCase):
    def test_eleven_figma_only_candidates_are_rejected(self):
        report = audit()
        self.assertEqual(report["status"], "PASS", report["issues"])
        self.assertEqual(report["admittedCount"], 7)
        self.assertEqual(report["figmaOnlyCandidateCount"], 11)
        self.assertEqual(len(report["rejectedCandidateIds"]), 11)
        self.assertFalse(report["releaseReady"])

    def test_candidate_added_to_figma_bindings_fails(self):
        bindings = copy.deepcopy(load_json(
            ROOT / "adapters/figma/metadata/component-bindings-0.2.6.json"))
        bindings["bindings"]["form.switch.default.enabled"] = bindings["bindings"][
            "form.radio.default.enabled"]
        report = audit(binding_overrides={"figma": bindings})
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("figma production bindings" in issue for issue in report["issues"]))


if __name__ == "__main__":
    unittest.main()
