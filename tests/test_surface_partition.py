import unittest
from PIL import Image
from adapters.figma.candidate_diagnostic import partition_surface_differences


class SurfacePartitionTests(unittest.TestCase):
    def setUp(self):
        self.reference={'componentType':'Button','nodes':[{'visible':True,'path':'0','bounds':{'x':0,'y':0,'width':8,'height':8},'computedStyle':{'border-'+corner+'-radius':'2px' for corner in ('top-left','top-right','bottom-left','bottom-right')}}]}
        self.left=Image.new('RGBA',(8,8),'white');self.right=self.left.copy()

    def test_disjoint_counts_and_text_priority_do_not_grant_admission(self):
        for point in [(0,0),(1,1),(3,3)]:self.right.putpixel(point,(0,0,0,255))
        report=partition_surface_differences(self.left,self.right,self.reference,[{'componentBounds':{'x':0,'y':0,'width':1,'height':1}}])
        self.assertEqual([report['categories'][name]['changedPixels'] for name in ('observedText','sourceCornerRectangles','unclassified')],[1,1,1])
        self.assertFalse(report['admissionEligible']);self.assertEqual(report['cause'],'UNDETERMINED')

    def test_nonuniform_or_css_normalized_radius_is_not_guessed(self):
        for value in ('3px','50%','20px'):
            self.reference['nodes'][0]['computedStyle']['border-top-left-radius']=value
            with self.assertRaises(ValueError):partition_surface_differences(self.left,self.right,self.reference,[])

    def test_alpha_changes_are_included_and_empty_regions_remain_unclassified(self):
        self.right.putpixel((4,4),(255,255,255,254))
        report=partition_surface_differences(self.left,self.right,self.reference,[])
        self.assertEqual(report['categories']['unclassified'],{'changedPixels':1,'maximumChannelDelta':1})
