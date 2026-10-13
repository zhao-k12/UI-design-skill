from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from scripts import default_font_input_gate_v02 as gate


class DefaultFontInputGateTests(unittest.TestCase):
    def test_native_gate_pass_is_fixture_scoped_and_unadmitted(self):
        report = gate.run()
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["admissionEligible"])
        self.assertEqual(report["registryAdmission"], "NOT_RUN")
        self.assertFalse(report["readyForPageGeneration"])
        self.assertEqual(report["contentScopeProposal"], {
            "kind": "fixed-native-content", "placeholder": "请输入姓名",
            "value": "", "width": 240, "height": 32})
        for platform in ("figma", "penpot"):
            self.assertTrue(all(report["platforms"][platform]["checks"].values()))
            self.assertLessEqual(report["platforms"][platform]["maxCornerPaletteResidual"], 2)

    def test_wrong_svg_placeholder_cannot_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            altered = Path(folder) / "wrong.svg"
            original = gate.SVG["penpot"].read_text(encoding="utf-8")
            altered.write_text(original.replace("请输入姓名", "搜索姓名"), encoding="utf-8")
            with patch.dict(gate.SVG, {"penpot": altered}):
                report = gate.run()
            self.assertEqual(report["status"], "FAIL")
            self.assertFalse(report["admissionEligible"])
            self.assertFalse(report["platforms"]["penpot"]["checks"]["independentNativeSvg"])

    def test_corner_palette_rejects_unrelated_color(self):
        source = gate.SOURCE.parent / "form.input.default.medium.png"
        image = Image.open(gate.ROOT / "artifacts/task-033/figma/component-native.png").convert("RGBA")
        with tempfile.TemporaryDirectory() as folder:
            altered = Path(folder) / "bad-corner.png"
            image.putpixel((1, 1), (255, 0, 0, 255))
            image.save(altered)
            self.assertGreater(gate.corner_check(source, altered), 2)


if __name__ == "__main__":
    unittest.main()
