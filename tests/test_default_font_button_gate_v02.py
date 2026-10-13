from copy import deepcopy
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from scripts.default_font_button_gate_v02 import evaluate_platform, svg_checks


def fixture(directory):
    source = {"content": {"text": "查询"}, "rootBounds": {"width": 60, "height": 32},
              "nodes": [{"path": "0", "computedStyle": {"font-size": "14px", "line-height": "21px",
                         "padding-left": "15px", "padding-right": "15px", "padding-top": "0px",
                         "padding-bottom": "0px", "border-top-left-radius": "4px",
                         "border-top-width": "1px"}}]}
    candidate = {"status": "CANDIDATE_REVIEW", "fileReference": "file", "componentId": "component",
                 "instanceId": "instance", "nativeAdmission": "NOT_RUN"}
    target = {"defaultFont": {"family": "Inter"}}
    prior = {"status": "CANDIDATE_REVIEW", "checks": {str(i): True for i in range(11)},
             "nativeAdmission": "NOT_RUN"}
    current = {"fileReference": "file", "componentId": "component", "instanceId": "instance",
               "instanceMainComponentId": "component", "nativeAdmission": "NOT_RUN",
               "componentBounds": {"width": 60, "height": 32},
               "padding": {"left": 15, "right": 15, "top": 0, "bottom": 0},
               "radius": 4, "strokeWeight": 1,
               "label": {"characters": "查询", "fontName": {"family": "Inter", "style": "Regular"},
                         "fontWeight": 400, "fontSize": 14, "lineHeight": {"unit": "PIXELS", "value": 21},
                         "hasMissingFont": False}}
    source_png = Image.new("RGBA", (60, 32), (45, 140, 240, 255))
    native = source_png.copy()
    for x in (20, 38):
        for xx, yy in ((x, 14), (x-1, 15), (x, 15), (x+1, 15), (x, 16)):
            native.putpixel((xx, yy), (255, 255, 255, 255))
    native_path = Path(directory) / "native.png"
    repeated = Path(directory) / "repeated.png"
    native.save(native_path)
    native.save(repeated)
    svg = b'<svg width="60" height="32"><path fill="white" d="M20 14L21 15"/></svg>'
    visual = {"legibleText": "查询", "glyphsComplete": True, "tofuOrMissingGlyph": False,
              "clippedText": False, "nativePngSha256": hashlib.sha256(native_path.read_bytes()).hexdigest(),
              "nativeSvgSha256": hashlib.sha256(svg).hexdigest()}
    span = {"x": 16, "y": 5.5, "width": 28, "height": 21}
    return ["figma", source, candidate, target, prior, current, visual,
            native_path, repeated, svg, span, source_png]


class DefaultFontButtonGateTests(unittest.TestCase):
    def test_penpot_svg_keeps_unicode_and_font(self):
        good = (b'<svg width="60" height="32"><text style="font-family: sourcesanspro; '
                b'font-weight: 400">\xe6\x9f\xa5\xe8\xaf\xa2</text></svg>')
        self.assertTrue(svg_checks("penpot", good, "查询"))
        self.assertFalse(svg_checks("penpot", good.replace(b"sourcesanspro", b"other"), "查询"))

    def test_bound_candidate_passes_but_changes_fail(self):
        with TemporaryDirectory() as directory:
            inputs = fixture(directory)
            self.assertEqual(evaluate_platform(*inputs)["status"], "PASS")
            modified = list(inputs)
            modified[5] = deepcopy(modified[5])
            modified[5]["label"]["fontName"]["family"] = "Other"
            self.assertFalse(evaluate_platform(*modified)["checks"]["currentNativeTextAndFont"])
            modified = list(inputs)
            modified[6] = {**modified[6], "glyphsComplete": False}
            self.assertFalse(evaluate_platform(*modified)["checks"]["hashBoundVisualReview"])

    def test_repeat_drift_and_straight_edge_fail(self):
        with TemporaryDirectory() as directory:
            inputs = fixture(directory)
            repeated = Image.open(inputs[8]).convert("RGBA")
            repeated.putpixel((30, 0), (255, 255, 255, 255))
            repeated.save(inputs[8])
            self.assertFalse(evaluate_platform(*inputs)["checks"]["stableIndependentNativePng"])
            inputs = fixture(directory)
            native = Image.open(inputs[7]).convert("RGBA")
            native.putpixel((30, 0), (255, 255, 255, 255))
            native.save(inputs[7])
            self.assertFalse(evaluate_platform(*inputs)["checks"]["nonTextPixelsExact"])

    def test_erased_glyph_and_off_palette_corner_fail(self):
        with TemporaryDirectory() as directory:
            inputs = fixture(directory)
            native = Image.open(inputs[7]).convert("RGBA")
            for x in range(16, 30):
                for y in range(5, 27):
                    native.putpixel((x, y), (45, 140, 240, 255))
            native.save(inputs[7])
            self.assertFalse(evaluate_platform(*inputs)["checks"]["separateVisibleUnclippedGlyphs"])
            inputs = fixture(directory)
            native = Image.open(inputs[7]).convert("RGBA")
            native.putpixel((0, 0), (255, 0, 0, 255))
            native.save(inputs[7])
            self.assertFalse(evaluate_platform(*inputs)["checks"]["roundedCornerPaintBound"])


if __name__ == "__main__":
    unittest.main()
