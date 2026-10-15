import copy
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.default_font_switch_gate_v02 import ROOT, pixel_policy, read, run, structure
from scripts.switch_pixel_diagnostics_v02 import SOURCE, compare


class SwitchGateTests(unittest.TestCase):
    def test_figma_only_gate_passes_without_registry_eligibility(self):
        result = run()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["scope"], "figma-only-qa")
        self.assertEqual(set(result["platforms"]), {"figma"})
        self.assertFalse(result["admissionEligible"])
        self.assertEqual(result["registryAdmission"], "DEFERRED_PENPOT")

    def test_missing_solid_knob_pixel_fails(self):
        native = ROOT / "artifacts/task-069/figma/native.png"
        with Image.open(native) as image:
            changed = image.convert("RGBA")
        changed.putpixel((33, 11), (45, 140, 240, 255))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "tampered.png"
            changed.save(path)
            self.assertFalse(pixel_policy(compare(SOURCE, path)))

    def test_changed_native_text_fails_structure(self):
        observed = copy.deepcopy(read(ROOT / "artifacts/task-069/figma/native-read.json"))
        metadata = read(ROOT / "adapters/figma/metadata/switch-default-font-candidate-0.2.0.json")
        observed["label"]["text"] = "关"
        self.assertFalse(structure("figma", observed, metadata))


if __name__ == "__main__":
    unittest.main()
