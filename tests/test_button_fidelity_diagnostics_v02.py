import unittest

from PIL import Image

from scripts.button_fidelity_diagnostics_v02 import inspect


class ButtonFidelityDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.source = Image.new("RGBA", (60, 32), (45, 140, 240, 255))
        self.span = {"x": 16, "y": 5.5, "width": 28, "height": 21}

    def test_glyph_coverage_is_per_half(self):
        native = self.source.copy()
        native.putpixel((20, 15), (255, 255, 255, 255))
        native.putpixel((38, 15), (255, 255, 255, 255))
        report = inspect(native, self.source, self.span)
        self.assertEqual(report["textZone"]["brightInkPixelsByHalf"], [1, 1])
        self.assertEqual(report["nonTextInterior"]["different"], 0)

    def test_nontext_interior_change_is_separate(self):
        native = self.source.copy()
        native.putpixel((10, 16), (0, 0, 0, 255))
        self.assertEqual(inspect(native, self.source, self.span)["nonTextInterior"]["different"], 1)

    def test_off_palette_corner_is_reported(self):
        native = self.source.copy()
        native.putpixel((0, 0), (255, 0, 0, 255))
        edge = inspect(native, self.source, self.span)["cornerEdge"]
        self.assertEqual(edge["different"], 1)
        self.assertEqual(edge["outOfPalettePixels"], 1)


if __name__ == "__main__":
    unittest.main()
