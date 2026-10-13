import hashlib
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from scripts import default_font_input_candidate_audit_v02 as candidate
from validators.ui_ir import ROOT, load_json


class DefaultFontInputCandidateAuditTests(unittest.TestCase):
    def test_both_native_candidates_stable_and_scoped(self):
        report = candidate.audit()
        self.assertEqual(report["status"], "CANDIDATE_REVIEW")
        self.assertEqual(report["nativeAdmission"], "NOT_RUN")
        self.assertEqual(report["effectiveCjkFontIdentity"], "UNVERIFIED")
        for platform, row in report["platforms"].items():
            self.assertEqual(row["status"], "CANDIDATE_REVIEW")
            self.assertTrue(all(row["checks"].values()))
            self.assertEqual(row["pixelDiagnostics"]["nonTextDifferences"], 0)
            self.assertTrue(all(value > 2 for value in row["pixelDiagnostics"]["visibleInkByCharacter"]))
            metadata = load_json(ROOT / f"adapters/{platform}/metadata/input-default-font-candidate-0.2.0.json")
            self.assertEqual(metadata["componentId"], row["componentId"])
            self.assertEqual(metadata["status"], "CANDIDATE_REVIEW")
            self.assertFalse(metadata["readyForPageGeneration"])
            for name, expected in row["evidenceSha256"].items():
                actual = hashlib.sha256((ROOT / f"artifacts/task-033/{platform}" / name).read_bytes()).hexdigest()
                self.assertEqual(actual, expected)

    def test_pixel_partition_rejects_non_text_change_and_missing_character(self):
        source = ROOT / "artifacts/task-023/replay-final/first/form.input.default.medium.png"
        native = ROOT / "artifacts/task-033/figma/component-native.png"
        with tempfile.TemporaryDirectory() as folder:
            changed = Path(folder) / "modified.png"
            image = Image.open(native).convert("RGBA")
            image.putpixel((120, 16), (0, 0, 0, 255))
            image.save(changed)
            self.assertGreater(candidate.review_pixels(source, changed)["nonTextDifferences"], 0)
            image = Image.open(native).convert("RGBA")
            for y in range(7, 26):
                for x in range(7, 21):
                    image.putpixel((x, y), (255, 255, 255, 255))
            image.save(changed)
            self.assertEqual(candidate.review_pixels(source, changed)["visibleInkByCharacter"][0], 0)


if __name__ == "__main__":
    unittest.main()
