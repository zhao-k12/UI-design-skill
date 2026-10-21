"""The new scoped release verdict is tied to actual native Figma evidence."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.audit_v027_figma_release import audit
from validators.ui_ir import ROOT, load_json


class V027FigmaReleaseTests(unittest.TestCase):
    def test_current_evidence_passes_all_scoped_gates(self):
        result = audit()
        self.assertEqual(result["status"], "FIGMA_SCOPED_PASS", result["issues"])
        self.assertEqual(len(result["gates"]), 10)
        self.assertTrue(all(value == "PASS" for value in result["gates"].values()))
        self.assertFalse(result["historicalDualPlatformReleaseReady"])

    def test_visual_hash_or_text_clipping_drift_is_rejected(self):
        visual = deepcopy(load_json(ROOT / "artifacts/task-118/visual-review.json"))
        geometry = deepcopy(load_json(ROOT / "artifacts/task-118/figma/native-geometry-read.json"))
        with tempfile.TemporaryDirectory() as directory:
            visual["sourceImageSha256"] = "0" * 64
            visual_path = Path(directory) / "visual.json"
            visual_path.write_text(json.dumps(visual), encoding="utf-8")
            invalid = audit(visual_path=visual_path)
            self.assertEqual(invalid["gates"]["actualVisualReview"], "FAIL")
            geometry["texts"][0]["box"]["x"] = -100
            geometry_path = Path(directory) / "geometry.json"
            geometry_path.write_text(json.dumps(geometry), encoding="utf-8")
            invalid = audit(geometry_path=geometry_path)
            self.assertEqual(invalid["gates"]["defaultFontsAndNoTextClipping"], "FAIL")


if __name__ == "__main__":
    unittest.main()
