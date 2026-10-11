import unittest
from PIL import Image
from adapters.figma.corner_raster_diagnostic import diagnose_corners


class CornerRasterTests(unittest.TestCase):
    def setUp(self):
        self.reference={'logicalComponentId':'fixture','componentType':'Button','nodes':[{'visible':True,'path':'0',
            'bounds':{'x':0,'y':0,'width':8,'height':8},'computedStyle':{
                'border-'+corner+'-radius':'2px' for corner in ('top-left','top-right','bottom-left','bottom-right')}}]}
        self.left=Image.new('RGBA',(8,8),'white');self.right=self.left.copy()

    def test_mirrored_positions_match_without_inferred_radius_correction(self):
        for point in ((0,0),(7,0),(0,7),(7,7)):self.right.putpixel(point,(254,255,255,255))
        report=diagnose_corners(self.left,self.right,self.reference)
        self.assertEqual(report['cornerChangedPixels'],4);self.assertTrue(report['cornerDeltaPatternsExactlySymmetric'])
        self.assertEqual(report['corners'][0]['pixels'][0]['signedDeltaRgba'],[-1,0,0,0])
        self.assertEqual(report['cause'],'UNDETERMINED');self.assertFalse(report['admissionEligible'])

    def test_single_corner_alpha_change_is_retained_and_text_interior_is_excluded(self):
        self.right.putpixel((7,7),(255,255,255,254));self.right.putpixel((4,4),(0,0,0,255))
        report=diagnose_corners(self.left,self.right,self.reference)
        self.assertEqual(report['cornerChangedPixels'],1);self.assertFalse(report['nativeCornerPixelsExactlySymmetric'])
        self.assertEqual(report['corners'][-1]['maximumChannelDelta'],1)

    def test_fractional_grid_or_raster_size_is_not_resampled(self):
        self.reference['nodes'][0]['bounds']['x']=.5
        with self.assertRaisesRegex(ValueError,'integer_pixel_grid'):diagnose_corners(self.left,self.right,self.reference)
        with self.assertRaisesRegex(ValueError,'size_mismatch'):diagnose_corners(self.left,Image.new('RGBA',(9,8)),self.reference)
