from copy import deepcopy
import unittest
from adapters.figma.candidate_diagnostic import validate_text_box_evidence


class SupplementalTextEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.bundle={'components':[{'logicalComponentId':'fixture','environment':{'scale':1},'provenance':{'officialCssSha256':'css','rendererSha256':'original'}}]}
        self.evidence={'scope':'official_runtime_text_box_diagnostic','status':'PASS','referenceComponentIrSha256':'hash','admissionEligible':False,'environment':{'scale':1},'provenance':{'officialCssSha256':'css','rendererSha256':'observer'},'referenceMatches':[{'logicalId':'fixture','screenshotMatches':True,'environmentMatches':True}], 'observations':[{'logicalId':'fixture','surface':'user-agent-shadow','text':'placeholder','componentBounds':{'x':8,'y':8,'width':70,'height':16}}]}

    def test_explicit_actual_region_grouping_does_not_require_identical_observer_renderer(self):
        result=validate_text_box_evidence(self.bundle,self.evidence,'hash')
        self.assertEqual(result['fixture'][0]['componentBounds']['y'],8)
        self.assertFalse(self.evidence['admissionEligible'])

    def test_hash_environment_reproduction_and_source_drift_are_rejected(self):
        for key,value in [('referenceComponentIrSha256','other'),('environment',{'scale':2}),('provenance',{'officialCssSha256':'other'}),('referenceMatches',[])]:
            changed=deepcopy(self.evidence);changed[key]=value
            with self.assertRaises(ValueError):validate_text_box_evidence(self.bundle,changed,'hash')

    def test_invalid_identity_surface_and_bounds_do_not_enter_region_classification(self):
        for key,value in [('logicalId','foreign'),('surface','guessed'),('componentBounds',{'x':True,'y':0,'width':1,'height':1}),('componentBounds',{'x':0,'y':0,'width':float('inf'),'height':1})]:
            changed=deepcopy(self.evidence);changed['observations'][0][key]=value
            with self.assertRaises(ValueError):validate_text_box_evidence(self.bundle,changed,'hash')
