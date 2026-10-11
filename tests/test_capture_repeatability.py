from copy import deepcopy
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from tests import test_native_capture as fixtures
from adapters.figma.native_capture import save_capture
from adapters.figma.capture_repeatability import evaluate_repeatability
from validators.ui_ir import ROOT


class CaptureRepeatabilityTests(unittest.TestCase):
    def setUp(self):
        fixtures.NativeCaptureTests.setUp(self)
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'artifacts');self.addCleanup(self.temp.cleanup)

    def captures(self,*,pixel_change=False,state_change=False,duplicate_ids=False):
        paths=[]
        for index in range(3):
            result=deepcopy(self.result);result['captureId']='duplicate' if duplicate_ids else f'fixture-{index}'
            if index==2 and pixel_change:
                stream=BytesIO();Image.new('RGBA',(2,2),'black').save(stream,format='PNG')
                result['raster']['bytes']=list(stream.getvalue())
            if index==2 and state_change:result['nativeEvidence']['nodes'][0]['properties']['opacity']=.5
            directory=Path(self.temp.name)/str(index);save_capture(result,directory,**self.expected);paths.append(directory)
        return paths

    def test_independent_fixture_exports_are_stable_without_admission(self):
        report=evaluate_repeatability(self.captures(),scope='test-fixture')
        self.assertEqual(report['status'],'PASS');self.assertFalse(report['admissionEligible'])
        self.assertTrue(all(row['changedPixels']==0 and row['nativeObservationEqual'] for row in report['comparisons']))

    def test_pixel_changes_remain_review_even_if_native_properties_match(self):
        report=evaluate_repeatability(self.captures(pixel_change=True),scope='test-fixture')
        self.assertEqual(report['status'],'REVIEW');self.assertEqual(report['comparisons'][-1]['changedPixels'],4)

    def test_equal_pixels_do_not_hide_changed_native_state(self):
        report=evaluate_repeatability(self.captures(state_change=True),scope='test-fixture')
        self.assertEqual(report['status'],'REVIEW');self.assertEqual(report['comparisons'][-1]['changedPixels'],0)

    def test_duplicate_capture_ids_or_test_scope_do_not_certify_production(self):
        directories=self.captures(duplicate_ids=True)
        with self.assertRaisesRegex(ValueError,'not_independent'):evaluate_repeatability(directories,scope='test-fixture')
        with self.assertRaisesRegex(ValueError,'scope_mismatch'):evaluate_repeatability(directories)
