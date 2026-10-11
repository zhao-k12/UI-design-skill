from fractions import Fraction
import unittest
from adapters.figma.configurable_font_calibration import ExactCubicPen, measure


class ExactQuadraticElevationTests(unittest.TestCase):
    def test_degree_elevation_preserves_curve_at_rational_parameters(self):
        pen=ExactCubicPen(None,0,Fraction(1))
        pen.moveTo((0,0));pen.qCurveTo((3,6),(9,0));pen.closePath()
        op,(a,b,end)=pen.commands[1]
        self.assertEqual(op,'curveTo')
        self.assertEqual((a,b,end),((Fraction(2),Fraction(-4)),(Fraction(5),Fraction(-4)),(Fraction(9),Fraction(0))))
        for t in (Fraction(0),Fraction(1,7),Fraction(1,2),Fraction(6,7),Fraction(1)):
            actual=tuple(3*(1-t)**2*t*a[i]+3*(1-t)*t*t*b[i]+t**3*end[i] for i in (0,1))
            expected=(2*(1-t)*t*3+t*t*9,-2*(1-t)*t*6)
            self.assertEqual(actual,expected)

    def test_implied_quadratic_midpoint_and_composite_translation_are_exact(self):
        pen=ExactCubicPen(None,10,Fraction(1,2))
        pen.moveTo((0,0));pen.qCurveTo((2,4),(6,4),(8,0));pen.closePath()
        self.assertEqual(len([op for op,_ in pen.commands if op=='curveTo']),2)
        self.assertEqual(pen.commands[1][1][-1],(Fraction(7),Fraction(-2)))
        self.assertEqual(pen.commands[2][1][-1],(Fraction(9),Fraction(0)))

    def test_open_contours_and_unsupported_text_are_rejected(self):
        pen=ExactCubicPen(None,0,Fraction(1));pen.moveTo((0,0))
        with self.assertRaisesRegex(ValueError,'open_font_contour'):pen.endPath()
        with self.assertRaisesRegex(ValueError,'unsupported_calibration_text'):measure('missing','0','a b',14)


if __name__=='__main__':unittest.main()
