"""The Tag gate rejects changed content and limits Penpot SVG normalization."""
from copy import deepcopy
import tempfile
import unittest
from pathlib import Path

from scripts.default_font_tag_gate_v02 import CANDIDATE, TASK, canonical_penpot_svg, native_structure, read_json, svg_check


class TagGateTests(unittest.TestCase):
    def test_native_text_change_fails_structure(self):
        candidate = read_json(CANDIDATE / "candidate-audit.json")["platforms"]["figma"]
        observed = read_json(TASK / "figma/native-read.json")
        self.assertTrue(native_structure("figma", observed, candidate))
        changed = deepcopy(observed)
        changed["label"]["characters"] = "停用"
        self.assertFalse(native_structure("figma", changed, candidate))

    def test_penpot_export_uuid_is_only_ignored_difference(self):
        main_id = "f1153c87-a7fc-80d8-8008-c9a7f325f8b1"
        previous = CANDIDATE / "penpot/component-native.svg"
        current = TASK / "penpot/native-gate.svg"
        self.assertEqual(canonical_penpot_svg(previous, main_id), canonical_penpot_svg(current, main_id))
        with tempfile.TemporaryDirectory() as temporary:
            changed = Path(temporary) / "changed.svg"
            changed.write_text(current.read_text(encoding="utf-8").replace("rgb(81, 90, 110)", "rgb(255, 0, 0)"), encoding="utf-8")
            self.assertNotEqual(canonical_penpot_svg(previous, main_id), canonical_penpot_svg(changed, main_id))

    def test_figma_svg_requires_visible_glyph_outline(self):
        original = TASK / "figma/native-gate.svg"
        self.assertTrue(svg_check("figma", original))
        with tempfile.TemporaryDirectory() as temporary:
            changed = Path(temporary) / "missing-glyph.svg"
            changed.write_text(original.read_text(encoding="utf-8").replace('fill="#515A6E"', 'fill="#FFFFFF"'), encoding="utf-8")
            self.assertFalse(svg_check("figma", changed))


if __name__ == "__main__":
    unittest.main()
