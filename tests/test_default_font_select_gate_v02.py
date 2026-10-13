from pathlib import Path
import tempfile
import unittest

from PIL import Image

from scripts import default_font_select_gate_v02 as gate
from validators.ui_ir import ROOT, load_json


class DefaultFontSelectGateTests(unittest.TestCase):
    def test_native_gate_passes_both_platforms_but_does_not_admit_registry(self):
        report = gate.run()
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["admissionEligible"])
        self.assertEqual(report["registryAdmission"], "NOT_RUN")
        self.assertEqual(report["contentScopeProposal"]["selectedText"], "启用")
        for platform, row in report["platforms"].items():
            self.assertTrue(all(row["checks"].values()))
            self.assertLessEqual(row["maxCornerPaletteResidual"], 2)
            metadata = load_json(ROOT / f"adapters/{platform}/metadata/select-default-font-fidelity-0.2.4.json")
            self.assertEqual(metadata["componentId"], row["componentId"])
            self.assertFalse(metadata["readyForPageGeneration"])

    def test_mutated_text_or_corner_fails(self):
        penpot = ROOT / "artifacts/task-036/penpot/component-native.svg"
        with tempfile.TemporaryDirectory() as folder:
            changed = Path(folder) / "changed.svg"
            changed.write_text(penpot.read_text(encoding="utf-8").replace("启用", "禁用"), encoding="utf-8")
            self.assertFalse(gate.svg_check("penpot", changed))
            native = ROOT / "artifacts/task-036/penpot/component-native.png"
            png = Path(folder) / "changed.png"
            image = Image.open(native).convert("RGBA")
            image.putpixel((0, 0), (255, 0, 0, 255))
            image.save(png)
            self.assertGreater(gate.corner_palette_residual(png), 2)


if __name__ == "__main__":
    unittest.main()
