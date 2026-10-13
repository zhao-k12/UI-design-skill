from pathlib import Path
import tempfile
import unittest

from PIL import Image

from scripts import default_font_table_candidate_audit_v02 as candidate
from validators.ui_ir import ROOT, load_json


class DefaultFontTableCandidateAuditTests(unittest.TestCase):
    def test_both_native_candidates_are_stable_and_fixed_content(self):
        report = candidate.audit()
        self.assertEqual(report["status"], "CANDIDATE_REVIEW")
        self.assertEqual(report["nativeAdmission"], "NOT_RUN")
        self.assertEqual(report["effectiveCjkFontIdentity"], "UNVERIFIED")
        for platform, row in report["platforms"].items():
            self.assertTrue(all(row["checks"].values()), platform)
            self.assertEqual(row["pixelDiagnostics"]["nonTextDifferences"], 0)
            metadata = load_json(ROOT / f"adapters/{platform}/metadata/table-default-font-candidate-0.2.0.json")
            self.assertEqual(metadata["componentId"], row["componentId"])
            self.assertEqual(metadata["contentScope"]["data"][2]["role"], "访客")
            self.assertFalse(metadata["readyForPageGeneration"])

    def test_non_text_pixel_change_fails_partition(self):
        native = ROOT / "artifacts/task-039/penpot/component-native.png"
        with tempfile.TemporaryDirectory() as folder:
            changed = Path(folder) / "tampered.png"
            image = Image.open(native).convert("RGB")
            image.putpixel((700, 46), (0, 0, 0))
            image.save(changed)
            metrics = candidate.pixel_review(candidate.REFERENCE, changed)
            self.assertGreater(metrics["nonTextDifferences"], 0)


if __name__ == "__main__":
    unittest.main()
