import unittest
from PIL import Image
from adapters.figma.candidate_diagnostic import locate_raster_differences


class RasterLocationTests(unittest.TestCase):
    def test_overlapping_regions_count_union_once_and_preserve_exact_rgba(self):
        left=Image.new('RGBA',(4,3),'white');right=left.copy()
        right.putpixel((1,1),(240,255,255,255));right.putpixel((3,2),(255,255,255,254))
        box={'x':1,'y':1,'width':1,'height':1}
        reference={'nodes':[{'visible':True,'path':'0','textRuns':[{'bounds':box},{'bounds':box}]}]}
        report=locate_raster_differences(left,right,reference)
        self.assertEqual(report['changedPixels'],2)
        self.assertEqual(report['insideObservedTextRunUnion'],1)
        self.assertEqual(report['outsideObservedTextRunUnion'],1)
        self.assertEqual([r['changedPixels'] for r in report['observedTextRegions']],[1,1])
        self.assertEqual(report['maximumChannelDelta'],15)
        self.assertEqual(report['changedPixelBounds'],[1,1,4,3])
        self.assertFalse(report['admissionEligible'])

    def test_missing_regions_and_unchanged_images_do_not_infer_text_or_cause(self):
        image=Image.new('RGBA',(2,2),'white')
        report=locate_raster_differences(image,image,{'nodes':[]})
        self.assertEqual(report['changedPixels'],0)
        self.assertIsNone(report['changedPixelBounds'])
        self.assertEqual(report['cause'],'UNDETERMINED')
        report=locate_raster_differences(image,image,{'nodes':[{'visible':True,'path':'0','textRuns':[{'text':'unknown'}]}]})
        self.assertEqual(report['unresolvedTextRegions'][0]['reason'],'missing_observed_text_bounds')

    def test_nonfinite_bounds_and_size_mismatch_rejected(self):
        image=Image.new('RGBA',(2,2),'white')
        with self.assertRaises(ValueError):
            locate_raster_differences(image,Image.new('RGBA',(1,2)),{'nodes':[]})
        with self.assertRaises(ValueError):
            locate_raster_differences(image,image,{'nodes':[{'path':'0','visible':True,'textRuns':[{'bounds':{'x':float('nan'),'y':0,'width':1,'height':1}}]}]})
