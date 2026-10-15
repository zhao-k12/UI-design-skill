import copy
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.default_font_checkbox_gate_v02 import ROOT, pixels, read, run, structure


class CheckboxGateTests(unittest.TestCase):
    def test_locked_dual_platform_gate_passes(self):
        result = run()
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["admissionEligible"])

    def test_missing_source_checkmark_pixel_fails(self):
        source = ROOT / "artifacts/task-058/checkbox-source/form.checkbox.default.enabled.png"
        native = ROOT / "artifacts/task-061/figma/native.png"
        with Image.open(native) as image:
            changed = image.convert("RGBA")
        with Image.open(source) as image:
            reference = image.convert("RGB")
        mark = next((x, y) for y in range(5, 15) for x in range(3, 14)
                    if min(reference.getpixel((x, y))) >= 220)
        changed.putpixel(mark, (45, 140, 240, 255))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "tampered.png"
            changed.save(path)
            self.assertFalse(pixels(source, path)["pass"])

    def test_changed_native_text_fails_structure(self):
        folder = ROOT / "artifacts/task-061/figma"
        metadata = read(ROOT / "adapters/figma/metadata/checkbox-default-font-candidate-0.2.0.json")
        observed = read(folder / "native-read.json")
        observed = copy.deepcopy(observed)
        observed["label"]["text"] = "关闭"
        self.assertFalse(structure("figma", observed, metadata))


if __name__ == "__main__":
    unittest.main()
