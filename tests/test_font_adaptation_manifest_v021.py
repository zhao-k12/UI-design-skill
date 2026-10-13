from copy import deepcopy
import unittest

from scripts.font_adaptation_manifest_v021 import rebind


def fixture():
    base = {"scope": "v02-font-adaptation-input-manifest", "version": "0.2.0",
            "status": "INPUTS_LOCKED_MEASUREMENT_PENDING", "readyForPageGeneration": False,
            "releaseReady": False, "sourceSha256": {"source": "hash"},
            "targets": {"figma": {"fileReference": "figma-file", "fontFamily": "Inter",
                                   "componentMeasurement": "NOT_RUN", "nativeAdmission": "NOT_RUN"},
                        "penpot": {"fileReference": "deleted-file", "fontFamily": "sourcesanspro",
                                   "componentMeasurement": "NOT_RUN", "nativeAdmission": "NOT_RUN"}},
            "components": [{"type": name, "logicalComponentId": name.lower(),
                            "measurement": "NOT_RUN", "nativeAdmission": "NOT_RUN"}
                           for name in ("Button", "Input", "Select", "Table")]}
    target = {"platform": "penpot", "status": "OBSERVED_IN_REPLACEMENT_FILE",
              "replacementAuthorizedByUser": True, "replacesDeletedTarget": "deleted-file",
              "fileReference": "new-file", "pageReference": "new-page",
              "defaultFont": {"family": "sourcesanspro"}, "nativeAcceptance": "NOT_RUN",
              "readyForPageGeneration": False, "releaseReady": False}
    candidates = {platform: {"platform": platform, "status": "CANDIDATE_REVIEW",
                             "fileReference": file, "pageReference": platform + "-page",
                             "fontBinding": {"family": family},
                             "sourceLogicalComponentId": "button", "componentId": platform + "-component",
                             "nativeAdmission": "NOT_RUN", "readyForPageGeneration": False,
                             "releaseReady": False}
                  for platform, file, family in (("figma", "figma-file", "Inter"),
                                                  ("penpot", "new-file", "sourcesanspro"))}
    return base, target, candidates, {"figma": True, "penpot": True}


class ReplacementManifestTests(unittest.TestCase):
    def test_replacement_preserves_history_and_pending_gate(self):
        inputs = fixture()
        before = deepcopy(inputs)
        result = rebind(*inputs)
        self.assertEqual(result["version"], "0.2.1")
        self.assertEqual(result["historicalPenpotFileReference"], "deleted-file")
        self.assertEqual(result["targets"]["penpot"]["fileReference"], "new-file")
        self.assertEqual(result["components"][0]["measurement"], "CANDIDATE_REVIEW")
        self.assertTrue(all(item["nativeAdmission"] == "NOT_RUN" for item in result["components"]))
        self.assertFalse(result["releaseReady"])
        self.assertEqual(inputs, before)

    def test_deleted_file_cannot_remain_active(self):
        inputs = list(fixture())
        inputs[1]["fileReference"] = "deleted-file"
        with self.assertRaisesRegex(ValueError, "replacement_target"):
            rebind(*inputs)

    def test_missing_evidence_or_wrong_candidate_rejected(self):
        inputs = list(fixture())
        inputs[3]["penpot"] = False
        with self.assertRaisesRegex(ValueError, "candidate_binding"):
            rebind(*inputs)
        inputs = list(fixture())
        inputs[2]["penpot"]["fileReference"] = "deleted-file"
        with self.assertRaisesRegex(ValueError, "candidate_binding"):
            rebind(*inputs)

    def test_fake_admission_rejected(self):
        inputs = list(fixture())
        inputs[2]["figma"]["nativeAdmission"] = "PASS"
        with self.assertRaisesRegex(ValueError, "candidate_binding"):
            rebind(*inputs)


if __name__ == "__main__":
    unittest.main()
