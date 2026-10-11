from copy import deepcopy
import unittest
from unittest.mock import patch
from adapters.figma.baseline_alignment import compare_baseline_alignment


class BaselineAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.source={'scope':'official_runtime_baseline_diagnostic','status':'PASS','referenceComponentIrSha256':'a'*64,'referenceMatches':[{'logicalId':'fixture','screenshotMatches':True,'environmentMatches':True}], 'observations':[{'logicalId':'fixture','status':'OBSERVED','baselineComponentY':20.5,'originalGeometryAndMarkupRestored':True}]}
        self.identity={'referenceComponentIrSha256':'a'*64}
        self.native={'fileReference':'fixture-file','createdNodeIds':[],'mutatedNodeIds':[],'admissionEligible':False,'observations':[{'textReference':'text','fontName':{'family':'Fixture'}}], 'coordinateContext':[{'textReference':'text','componentReference':'root','textAbsoluteTransform':[[1,0,10],[0,1,4.5]],'componentAbsoluteTransform':[[1,0,0],[0,1,0]]}]}
        self.inventory={'fileReference':'fixture-file','components':[{'logicalId':'fixture','componentReference':'root'}]}
        self.comparison={'observations':[{'textReference':'text','dimensionEqual':True,'source':{'unshapedInkBoundsBaselineCoordinates':{'y':-12}},'nativeSvg':{'pathBoundsSvgCoordinates':{'y':4}},'contourComparison':{'unorientedGeometry':{'exactCoordinatesEqual':True}}}]}

    @patch('adapters.figma.baseline_alignment.compare_font_files')
    def test_actual_identity_transforms_and_font_ink_translation_define_baseline(self,mock):
        mock.return_value=self.comparison
        report=compare_baseline_alignment(self.source,self.native,self.identity,self.inventory)
        self.assertEqual(report['observations'][0]['deltaY'],0)
        self.assertFalse(report['admissionEligible']);self.assertEqual(report['status'],'REVIEW')

    @patch('adapters.figma.baseline_alignment.compare_font_files')
    def test_coordinate_scaling_and_unrestored_probe_are_rejected(self,mock):
        mock.return_value=self.comparison
        changed=deepcopy(self.native);changed['coordinateContext'][0]['textAbsoluteTransform'][0][0]=2
        with self.assertRaises(ValueError):compare_baseline_alignment(self.source,changed,self.identity,self.inventory)
        self.source['observations'][0]['originalGeometryAndMarkupRestored']=False
        with self.assertRaises(ValueError):compare_baseline_alignment(self.source,self.native,self.identity,self.inventory)

    @patch('adapters.figma.baseline_alignment.compare_font_files')
    def test_missing_and_ambiguous_native_roles_cannot_produce_alignment(self,mock):
        mock.return_value=self.comparison
        self.native['observations']*=2
        with self.assertRaises(ValueError):compare_baseline_alignment(self.source,self.native,self.identity,self.inventory)
