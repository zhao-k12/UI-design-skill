from pathlib import Path
import tempfile
import unittest

from PIL import Image

from scripts import default_font_table_gate_v02 as gate
from validators.ui_ir import ROOT, load_json


class DefaultFontTableGateTests(unittest.TestCase):
    def test_fixed_native_table_passes_both_platforms(self):
        report = gate.run()
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["admissionEligible"])
        self.assertEqual(report["registryAdmission"], "NOT_RUN")
        self.assertFalse(report["readyForPageGeneration"])
        for platform, row in report["platforms"].items():
            self.assertTrue(all(row["checks"].values()), platform)
            self.assertEqual(row["pixelDiagnostics"]["nonTextDifferences"], 0)
            self.assertEqual(len(row["visibleInkByCharacter"]), 19)
            metadata = load_json(ROOT / f"adapters/{platform}/metadata/table-default-font-fidelity-0.2.5.json")
            self.assertEqual(metadata["componentId"], row["componentId"])
            self.assertFalse(metadata["readyForPageGeneration"])

    def test_wrong_svg_text_or_non_text_pixel_is_rejected(self):
        native_svg = ROOT / "artifacts/task-039/penpot/component-native.svg"
        svg_text = native_svg.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as folder:
            changed_svg = Path(folder) / "bad.svg"
            changed_svg.write_text(svg_text.replace("管理员", "审核员", 1), encoding="utf-8")
            self.assertFalse(gate.native_svg_check("penpot", changed_svg))

            changed_png = Path(folder) / "bad.png"
            image = Image.open(ROOT / "artifacts/task-039/figma/component-native.png").convert("RGB")
            image.putpixel((700, 46), (0, 0, 0))
            image.save(changed_png)
            self.assertGreater(gate.pixel_review(gate.REFERENCE, changed_png)["nonTextDifferences"], 0)


if __name__ == "__main__":
    unittest.main()
