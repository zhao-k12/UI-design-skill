import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.default_font_datepicker_figma_gate_v02 import ROOT, raster_diagnostics, raster_policy, run


class DatePickerFigmaGateTests(unittest.TestCase):
    def test_locked_figma_quality_passes_without_admission(self):
        report = run()
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(all(report["checks"].values()))
        self.assertFalse(report["admissionEligible"])
        self.assertEqual(report["registryAdmission"], "DEFERRED_PENPOT")

    def test_changed_border_pixel_fails(self):
        native = ROOT / "artifacts/task-084/figma/native.png"
        source = ROOT / "artifacts/task-082/datepicker-source/form.datepicker.date.selected.png"
        with Image.open(native) as image:
            changed = image.convert("RGBA")
        changed.putpixel((100, 0), (0, 0, 0, 255))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "tampered.png"
            changed.save(path)
            self.assertFalse(raster_policy(raster_diagnostics(source, path)))


if __name__ == "__main__":
    unittest.main()
