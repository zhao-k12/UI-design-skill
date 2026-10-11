import unittest
from adapters.figma.outline_geometry import path_bounds, inspect_svg, inspect_capture


class OutlineGeometryTests(unittest.TestCase):
    def test_exact_polygon_bounds_include_implicit_line_and_multiple_subpaths(self):
        box=path_bounds('M1 2 4 6H8V-1ZM-3 0L2 3Z')
        self.assertEqual(box,{'x':-3,'y':-1,'width':11,'height':7})

    def test_curves_relative_coordinates_and_malformed_tokens_are_rejected(self):
        for path in ('M0 0Q1 2 3 4','m0 0l1 1','M0','M1e999 0','M0 0@L1 1','Z','H3'):
            with self.assertRaises(ValueError):path_bounds(path)

    def test_cubic_bounds_use_actual_extrema_instead_of_control_point_extents(self):
        box=path_bounds('M0 0C0 10 10 10 10 0')
        self.assertEqual(box,{'x':0,'y':0,'width':10,'height':7.5})
        box=path_bounds('M0 0C3 0 6 0 9 0')
        self.assertEqual(box['width'],9);self.assertEqual(box['height'],0)

    def test_transforms_strokes_scripts_and_entity_declarations_are_rejected(self):
        for content in ('<path d="M0 0L1 1" transform="scale(2)"/>','<path d="M0 0L1 1" stroke="black"/>','<script/>'):
            with self.assertRaises(ValueError):inspect_svg('<svg xmlns="http://www.w3.org/2000/svg">'+content+'</svg>')
        with self.assertRaises(ValueError):inspect_svg('<!DOCTYPE svg><svg/>')

    def test_capture_hashes_actual_export_and_never_admits_geometry(self):
        capture={'scope':'figma_native_text_outline_diagnostic','status':'PASS','fileReference':'fixture','admissionEligible':False,'createdNodeIds':[],'mutatedNodeIds':[],'observations':[{'textReference':'text','characters':'x','svg':'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2 2"><path d="M0 0L1 1"/></svg>'}]}
        result=inspect_capture(capture);self.assertFalse(result['admissionEligible'])
        self.assertEqual(len(result['observations'][0]['svgSha256']),64)
        capture['observations']*=2
        with self.assertRaises(ValueError):inspect_capture(capture)
