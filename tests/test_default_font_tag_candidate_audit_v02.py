"""Regression: a changed non-text edge must not look like corner antialiasing."""
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.default_font_tag_candidate_audit_v02 import pixel_review
from validators.ui_ir import ROOT


class TagCandidatePixelReviewTests(unittest.TestCase):
    def test_changed_straight_edge_is_reported_outside_corners(self):
        source = ROOT / "artifacts/task-054/tag-source/data.tag.default.enabled.png"
        with Image.open(source) as image:
            changed = image.convert("RGBA")
        changed.putpixel((0, 10), (255, 0, 0, 255))
        with tempfile.TemporaryDirectory() as temporary:
            altered = Path(temporary) / "altered.png"
            changed.save(altered)
            result = pixel_review(source, altered)
        self.assertGreater(result["nonTextChangesOutsideFourCorners"], 0)


if __name__ == "__main__":
    unittest.main()
