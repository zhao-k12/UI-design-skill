import json
from pathlib import Path
import tempfile
import unittest

from scripts.audit_v02_figma_release_gates import ROOT, audit


class V02FigmaReleaseGateTests(unittest.TestCase):
    def test_scoped_figma_gates_pass_without_claiming_full_release(self):
        result = audit()
        self.assertEqual(result["status"], "FIGMA_SCOPED_PASS", result["issues"])
        self.assertTrue(result["figmaScopedReady"])
        self.assertFalse(result["releaseReady"])
        self.assertEqual(len(result["gates"]), 9)

    def test_wrong_native_font_fails_gate(self):
        source = ROOT / "artifacts/task-110/figma/native-geometry-read.json"
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "geometry.json"
            value = json.loads(source.read_text(encoding="utf-8"))
            next(row for row in value["texts"] if row["fontFamily"] == "Inter")["fontFamily"] = "Arial"
            target.write_text(json.dumps(value), encoding="utf-8")
            result = audit(geometry_path=target)
        self.assertEqual(result["status"], "INVALID_EVIDENCE")
        self.assertIn("defaultFontsAndNoTextClipping", result["issues"])

    def test_mismatched_visual_image_fails_gate(self):
        source = ROOT / "artifacts/task-110/visual-review.json"
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "visual.json"
            value = json.loads(source.read_text(encoding="utf-8"))
            value["sourceImageSha256"] = "0" * 64
            target.write_text(json.dumps(value), encoding="utf-8")
            result = audit(visual_path=target)
        self.assertEqual(result["status"], "INVALID_EVIDENCE")
        self.assertIn("actualVisualReview", result["issues"])


if __name__ == "__main__":
    unittest.main()
