import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.default_font_upload_figma_gate_v02 import ROOT, raster_diagnostics, raster_policy, run


class UploadFigmaGateTests(unittest.TestCase):
    def test_locked_figma_quality_passes_without_admission(self):
        report = run()
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(all(report["checks"].values()))
        self.assertFalse(report["admissionEligible"])
        self.assertEqual(report["registryAdmission"], "DEFERRED_PENPOT")

    def test_changed_interior_fails(self):
        native = ROOT / "artifacts/task-096/figma/native.png"
        source = ROOT / "artifacts/task-094/upload-source/data.upload.drag.empty.png"
        with Image.open(native) as image:
            changed = image.convert("RGBA")
        changed.putpixel((250, 40), (0, 0, 0, 255))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "tampered.png"
            changed.save(path)
            self.assertFalse(raster_policy(raster_diagnostics(source, path)))


if __name__ == "__main__":
    unittest.main()
