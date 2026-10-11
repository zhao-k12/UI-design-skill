from decimal import Decimal as D
import unittest
from adapters.figma.font_outline_comparison import compare_six_digit_serialization


class SvgSerializationTests(unittest.TestCase):
    def setUp(self):
        self.source=[('moveTo',((D('3.513671875'),D('-8.75')),)),('lineTo',((D('10.486328125'),D('-8.75')),)),('lineTo',((D('7'),D('-3.5')),)),('closePath',())]
        self.native=[('moveTo',((D('3.51367'),D('4.25')),)),('lineTo',((D('10.4863'),D('4.25')),)),('lineTo',((D('7'),D('9.5')),)),('closePath',())]
        # An exact extremum anchors x translation as in the actual icon.
        self.source[0]=('moveTo',((D('2.625'),D('-8.75')),));self.native[0]=('moveTo',((D('2.625'),D('4.25')),))

    def test_fixed_formatter_matches_all_points(self):
        self.assertEqual(compare_six_digit_serialization(self.source,self.native)['status'],'PASS')

    def test_even_tiny_unexplained_change_is_rejected(self):
        self.native[1]=('lineTo',((D('10.48631'),D('4.25')),))
        self.assertEqual(compare_six_digit_serialization(self.source,self.native)['status'],'REVIEW')

    def test_unsupported_fill_and_curves_are_not_approved(self):
        self.assertEqual(compare_six_digit_serialization(self.source,self.native,native_fill_rule='evenodd')['status'],'REVIEW')
        self.assertEqual(compare_six_digit_serialization(self.source,self.native,native_path_count=2)['status'],'REVIEW')
