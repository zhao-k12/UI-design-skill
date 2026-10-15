import copy
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.default_font_radio_gate_v02 import ROOT, canonical_svg, pixels, read, run, structure


class RadioGateTests(unittest.TestCase):
    def test_locked_dual_platform_gate_passes(self):
        result = run()
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["admissionEligible"])

    def test_missing_center_pixel_fails(self):
        source = ROOT / "artifacts/task-063/radio-source/form.radio.default.enabled.png"
        native = ROOT / "artifacts/task-065/figma/native.png"
        with Image.open(native) as image:
            changed = image.convert("RGBA")
        changed.putpixel((7, 9), (255, 255, 255, 255))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "tampered.png"
            changed.save(path)
            self.assertFalse(pixels(source, path)["pass"])

    def test_changed_native_text_fails_structure(self):
        observed = copy.deepcopy(read(ROOT / "artifacts/task-065/penpot/native-read.json"))
        metadata = read(ROOT / "adapters/penpot/metadata/radio-default-font-candidate-0.2.0.json")
        observed["label"]["text"] = "关闭"
        self.assertFalse(structure("penpot", observed, metadata))

    def test_penpot_svg_normalization_only_ignores_stroke_group_uuid(self):
        source = ROOT / "artifacts/task-064/penpot/native.svg"
        native = ROOT / "artifacts/task-065/penpot/native.svg"
        self.assertEqual(canonical_svg("penpot", source), canonical_svg("penpot", native))
        with tempfile.TemporaryDirectory() as folder:
            changed = Path(folder) / "tampered.svg"
            changed.write_text(native.read_text(encoding="utf-8").replace("45, 140, 240", "45, 140, 241"),
                               encoding="utf-8")
            self.assertNotEqual(canonical_svg("penpot", source), canonical_svg("penpot", changed))


if __name__ == "__main__":
    unittest.main()
