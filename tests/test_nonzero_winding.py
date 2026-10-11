import unittest
from adapters.figma.font_outline_comparison import compare_nonzero_winding


def contour(points):return [('moveTo',(points[0],))]+[('lineTo',(point,)) for point in points[1:]]+[('closePath',())]


class NonzeroWindingTests(unittest.TestCase):
    def setUp(self):
        self.outer=[(0,0),(10,0),(10,10),(0,10)]
        self.hole=[(2,2),(2,8),(8,8),(8,2)]
        self.source=contour(self.outer)+contour(self.hole)

    def test_translation_reordering_and_global_reversal_preserve_nonzero_fill(self):
        native=contour([(x+20,y+5) for x,y in reversed(self.hole)])+contour([(x+20,y+5) for x,y in reversed(self.outer)])
        result=compare_nonzero_winding(self.source,native)
        self.assertTrue(result['nonzeroPathFilledRegionEquivalent'])
        self.assertEqual(result['directionRelationship'],'ALL_CONTOURS_REVERSED')
        self.assertFalse(result['admissionEligible'])

    def test_reversing_only_the_hole_cannot_get_geometric_fill_pass(self):
        result=compare_nonzero_winding(self.source,contour(self.outer)+contour(list(reversed(self.hole))))
        self.assertEqual(result['status'],'REVIEW');self.assertFalse(result['nonzeroPathFilledRegionEquivalent'])

    def test_cubic_reversal_preserves_controls_and_rejects_tiny_difference(self):
        source=[('moveTo',((0,0),)),('curveTo',((1,0),(2,1),(3,1))),('lineTo',((0,0),)),('closePath',())]
        reverse=[('moveTo',((0,0),)),('lineTo',((3,1),)),('curveTo',((2,1),(1,0),(0,0))),('closePath',())]
        self.assertEqual(compare_nonzero_winding(source,reverse)['status'],'PASS')
        reverse[2]=('curveTo',((2,1),(1.000001,0),(0,0)))
        self.assertEqual(compare_nonzero_winding(source,reverse)['status'],'REVIEW')

    def test_evenodd_or_multiple_separately_filled_paths_do_not_get_inferred_equivalence(self):
        for options in ({'native_fill_rule':'evenodd'},{'native_path_count':2}):
            self.assertEqual(compare_nonzero_winding(self.source,self.source,**options)['status'],'REVIEW')
