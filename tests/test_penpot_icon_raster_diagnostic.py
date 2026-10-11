import unittest
from pathlib import Path
from PIL import Image
from adapters.penpot.icon_raster_diagnostic import run,observe_pixels


class IconRasterDiagnosticTests(unittest.TestCase):
    def test_actual_differences_are_observations_without_admission(self):
        base=Path(__file__).resolve().parents[1]/'adapters/penpot/metadata/icons-native-v1'
        report=run(base)
        self.assertEqual(report['rasterPolicy'],'PENDING_DECISION');self.assertFalse(report['admissionEligible'])
        self.assertEqual([r['changedPixels'] for r in report['results']],[138,42])
        for row in report['results']:
            self.assertEqual(row['changedPixelsOutsideVerifiedEdgeBand'],0)
            self.assertTrue(row['proposedEvidenceConditionsMet']);self.assertFalse(row['repeatCaptureComplete'])

    def test_blank_colored_outside_pixels_and_missing_region_fail_conditions(self):
        base=Path(__file__).resolve().parents[1]/'adapters/penpot/metadata/icons-native-v1'
        with Image.open(base/'remix.download-line.source.png') as source,Image.open(base/'remix.download-line.native.png') as vector,Image.open(base/'latest.remix.download-line.png') as im:
            native=im.convert('RGBA')
            bad=Image.new('RGBA',(24,24),(0,0,0,0))
            self.assertFalse(observe_pixels(source,bad,vector)['proposedEvidenceConditionsMet'])
            bad=native.copy();bad.putpixel((0,0),(0,0,0,255))
            self.assertGreater(observe_pixels(source,bad,vector)['changedPixelsOutsideVerifiedEdgeBand'],0)
            bad=native.copy();bad.putpixel((12,2),(255,0,0,255))
            self.assertFalse(observe_pixels(source,bad,vector)['proposedEvidenceConditionsMet'])
            bad=native.copy()
            for y in range(19,21):
                for x in range(3,21):bad.putpixel((x,y),(0,0,0,0))
            self.assertFalse(observe_pixels(source,bad,vector)['inkAndVoidRegionCountsExact'])
            with self.assertRaises(ValueError):observe_pixels(source,native,Image.new('RGBA',(24,24),'white'))
