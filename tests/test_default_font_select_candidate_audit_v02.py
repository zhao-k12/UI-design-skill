from pathlib import Path
import tempfile
import unittest

from PIL import Image

from scripts import default_font_select_candidate_audit_v02 as candidate
from validators.ui_ir import ROOT, load_json


class DefaultFontSelectCandidateAuditTests(unittest.TestCase):
    def test_two_native_candidates_are_stable_and_scoped(self):
        report = candidate.audit()
        self.assertEqual(report["status"], "CANDIDATE_REVIEW")
        self.assertEqual(report["nativeAdmission"], "NOT_RUN")
        self.assertEqual(report["effectiveCjkFontIdentity"], "UNVERIFIED")
        for platform, row in report["platforms"].items():
            self.assertTrue(all(row["checks"].values()))
            self.assertEqual(row["pixelDiagnostics"]["nonTextDifferences"], 0)
            metadata = load_json(ROOT / f"adapters/{platform}/metadata/select-default-font-candidate-0.2.0.json")
            self.assertEqual(metadata["componentId"], row["componentId"])
            self.assertEqual(metadata["contentScope"]["selectedText"], "启用")
            self.assertFalse(metadata["readyForPageGeneration"])

    def test_source_arrow_and_non_text_region_are_guarded(self):
        svg = (ROOT / "artifacts/task-036/figma/component-native.svg").read_text(encoding="utf-8")
        self.assertTrue(candidate.arrow_outline_preserved(svg))
        self.assertFalse(candidate.arrow_outline_preserved(svg.replace("220.514", "221.514")))
        source = ROOT / "artifacts/task-023/replay-final/first/form.select.default.medium.png"
        native = ROOT / "artifacts/task-036/figma/component-native.png"
        with tempfile.TemporaryDirectory() as folder:
            changed = Path(folder) / "tampered.png"
            image = Image.open(native).convert("RGB")
            image.putpixel((120, 16), (0, 0, 0))
            image.save(changed)
            self.assertGreater(candidate.pixel_review(source, changed)["nonTextDifferences"], 0)


if __name__ == "__main__":
    unittest.main()
