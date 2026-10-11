import base64
from copy import deepcopy
from io import BytesIO
import unittest
from PIL import Image
from adapters.figma.blend_mode_diagnostic import compare_experiment


def png(color):
    stream=BytesIO();Image.new('RGBA',(2,2),color).save(stream,format='PNG');return stream.getvalue()


class BlendModeDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.png=png((255,255,255,255))
        bounds={'x':0,'y':0,'width':2,'height':2}
        rows=[{'reference':ref,'type':kind,'absoluteBounds':bounds,
            'properties':{'blendMode':'PASS_THROUGH','opacity':1,'effects':[]}} for ref,kind in [('root','COMPONENT'),('text','TEXT')]]
        normal=deepcopy(rows);normal[1]['properties']['blendMode']='NORMAL'
        self.baseline={'pageReference':'page','nodes':deepcopy(rows)}
        self.manifest={'fileReference':'file','logicalId':'fixture','componentReference':'root','evidenceScope':'production'}
        self.experiment={'scope':'figma_text_blend_mode_experiment','status':'PASS','fileReference':'file','logicalId':'fixture','componentReference':'root',
            'pageReference':'page','admissionEligible':False,'fidelityGate':'NOT_RUN','createdNodeIds':[],'issues':[],
            'mutatedNodeIds':['text'],'restoredNodeIds':['text'],'originalObservedStateRestored':True,
            'observations':{'before':rows,'normal':normal,'restored':deepcopy(rows)},
            'rasters':{stage:{'format':'PNG','scale':1,'encoding':'base64','data':base64.b64encode(self.png).decode()} for stage in ('before','normal','restored')}}

    def compare(self):return compare_experiment(self.experiment,self.baseline,self.png,self.manifest)

    def test_equal_pixels_are_scoped_to_this_experiment_without_admission(self):
        report=self.compare();self.assertEqual(report['normalVsBeforeChangedPixels'],0)
        self.assertEqual(report['restoredVsBeforeChangedPixels'],0);self.assertFalse(report['admissionEligible'])

    def test_actual_changed_pixels_are_counted_and_failed_restoration_is_rejected(self):
        encoded=base64.b64encode(png((0,0,0,255))).decode()
        self.experiment['rasters']['normal']['data']=encoded
        self.assertEqual(self.compare()['normalVsBeforeChangedPixels'],4)
        self.experiment['rasters']['restored']['data']=encoded
        with self.assertRaisesRegex(ValueError,'pixels_not_restored'):self.compare()

    def test_unrelated_state_changes_or_wrong_file_cannot_certify_equivalence(self):
        self.experiment['observations']['normal'][1]['properties']['opacity']=.5
        with self.assertRaisesRegex(ValueError,'unrelated_state'):self.compare()
        self.experiment['observations']['normal'][1]['properties']['opacity']=1
        self.experiment['fileReference']='other'
        with self.assertRaisesRegex(ValueError,'identity_mismatch'):self.compare()

    def test_before_png_and_exact_mutation_restoration_inventory_are_required(self):
        self.png=png((0,0,0,255))
        with self.assertRaisesRegex(ValueError,'baseline_png_changed'):self.compare()
        self.png=png((255,255,255,255));self.experiment['restoredNodeIds']=[]
        with self.assertRaisesRegex(ValueError,'state_not_restored'):self.compare()
