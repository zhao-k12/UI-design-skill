import unittest
from adapters.figma.font_outline_comparison import compare_unoriented_contours,minimum_rotation


class ContourComparisonTests(unittest.TestCase):
    def test_translation_cyclic_start_and_direction_are_normalized_without_admission(self):
        a=[('moveTo',((0,0),)),('lineTo',((4,0),)),('lineTo',((4,3),)),('lineTo',((0,3),)),('closePath',())]
        b=[('moveTo',((14,13),)),('lineTo',((14,10),)),('lineTo',((10,10),)),('lineTo',((10,13),)),('lineTo',((14,13),)),('closePath',())]
        report=compare_unoriented_contours(a,b)
        self.assertTrue(report['exactCoordinatesEqual']);self.assertFalse(report['admissionEligible'])

    def test_reversed_cubic_controls_match_but_real_coordinate_difference_remains(self):
        a=[('moveTo',((0,0),)),('curveTo',((0,4),(4,4),(4,0))),('closePath',())]
        b=[('moveTo',((4,0),)),('curveTo',((4,4),(0,4),(0,0))),('closePath',())]
        self.assertTrue(compare_unoriented_contours(a,b)['exactCoordinatesEqual'])
        b[1]=('curveTo',((4,4),(0,4.00001),(0,0)))
        self.assertFalse(compare_unoriented_contours(a,b)['exactCoordinatesEqual'])

    def test_linear_rotation_matches_exhaustive_result_for_repeating_sequences(self):
        for sequence in ([3,1,2,1],[2,2,2],[4],[2,1,2,1,0],[0,1,0,1]):
            expected=min(tuple(sequence[i:]+sequence[:i]) for i in range(len(sequence)))
            self.assertEqual(minimum_rotation(sequence),expected)
