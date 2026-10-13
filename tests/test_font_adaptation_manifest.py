import unittest
from copy import deepcopy

from scripts.font_adaptation_manifest import make_manifest, SOURCE_FILES


def fixture():
    policy = {"scope": "v02-platform-default-font-component-adaptation", "version": "0.2.0",
              "decisionStatus": "USER_APPROVED", "fontSelection": "platform-native-default",
              "componentAdmission": "NOT_RUN", "readyForPageGeneration": False, "releaseReady": False}
    sources = {path: path + "-hash" for path in SOURCE_FILES}
    metadata = {"adapters/figma/metadata/default-font-target-0.2.0.json": "figma-hash",
                "adapters/penpot/metadata/default-font-target-0.2.0.json": "penpot-hash"}
    profiles = {}
    targets = {}
    for platform, family in (("figma", "Inter"), ("penpot", "sourcesanspro")):
        profiles[platform] = {"platform": platform, "status": "PASS", "fontBindingReady": True,
                              "textSampleReview": "PASS", "nativeAcceptance": "NOT_RUN",
                              "readyForPageGeneration": False, "releaseReady": False,
                              "fileReference": platform + "-file", "pageReference": platform + "-page",
                              "defaultFont": {"family": family}, "bindings": {family + ":400": {"family": family}}}
        targets[platform] = {"family": family, "fileReference": platform + "-file"}
    audit = {"scope": "v02-default-font-source-compatibility", "version": "0.2.0",
             "status": "REMEASURE_REQUIRED", "nativeAcceptance": "NOT_RUN",
             "readyForPageGeneration": False, "releaseReady": False,
             "sourceSha256": dict(sources), "targetMetadataSha256": dict(metadata),
             "targetFontMetadata": targets,
             "components": [{"componentType": kind, "logicalComponentId": kind.lower(),
                             "measurementReusable": False,
                             "targets": {p: {"measurement": "NOT_RUN", "nativeAdmission": "NOT_RUN"}
                                         for p in profiles}}
                            for kind in ("Button", "Input", "Select", "Table")]}
    return policy, audit, profiles, sources, metadata


class AdaptationManifestTests(unittest.TestCase):
    def test_approved_inputs_lock_without_admission(self):
        inputs = fixture()
        before = deepcopy(inputs)
        result = make_manifest(*inputs)
        self.assertEqual(result["status"], "INPUTS_LOCKED_MEASUREMENT_PENDING")
        self.assertEqual(len(result["components"]), 4)
        self.assertFalse(result["readyForPageGeneration"])
        self.assertFalse(result["releaseReady"])
        self.assertEqual(inputs, before)

    def test_unapproved_policy_rejected(self):
        inputs = list(fixture())
        inputs[0]["decisionStatus"] = "DRAFT"
        with self.assertRaisesRegex(ValueError, "policy"):
            make_manifest(*inputs)

    def test_source_and_metadata_drift_rejected(self):
        for index, message in ((3, "source_evidence_changed"), (4, "target_metadata_changed")):
            inputs = list(fixture())
            key = next(iter(inputs[index]))
            inputs[index][key] = "changed"
            with self.assertRaisesRegex(ValueError, message):
                make_manifest(*inputs)

    def test_failed_profile_and_changed_font_rejected(self):
        for key, value, message in (("textSampleReview", "FAIL", "invalid_native_font_profile"),
                                    ("releaseReady", True, "invalid_native_font_profile"),
                                    ("defaultFont", {"family": "Other"}, "target_font_identity_changed")):
            inputs = list(fixture())
            inputs[2]["figma"][key] = value
            with self.assertRaisesRegex(ValueError, message):
                make_manifest(*inputs)

    def test_old_measurements_or_admission_rejected(self):
        for key, value, message in (("measurementReusable", True, "old_measurement_reuse_forbidden"),
                                    ("nativeAdmission", "PASS", "unsupported_admission_claim")):
            inputs = list(fixture())
            item = inputs[1]["components"][0]
            if key == "nativeAdmission":
                item["targets"]["figma"][key] = value
            else:
                item[key] = value
            with self.assertRaisesRegex(ValueError, message):
                make_manifest(*inputs)


if __name__ == "__main__":
    unittest.main()
