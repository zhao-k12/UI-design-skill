"""PNG transport fixtures are explicitly test-fixture, never native acceptance."""
from copy import deepcopy
import hashlib
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image
from adapters.figma.native_capture import package_capture, save_capture, verify_saved_capture
from validators.ui_ir import ROOT


class NativeCaptureTests(unittest.TestCase):
    def setUp(self):
        image=Image.new('RGBA',(2,2),(255,0,0,128))
        buffer=BytesIO();image.save(buffer,format='PNG')
        self.raw=buffer.getvalue()
        self.expected={'file_reference':'fixture','component_reference':'component','logical_id':'fixture.button','scope':'test-fixture'}
        self.result={'scope':'figma_native_component_capture','status':'PASS','evidenceKind':'native-platform-export',
            'evidenceScope':'test-fixture','fileReference':'fixture','componentReference':'component','logicalId':'fixture.button',
            'captureId':'fixture-capture','exporterVersion':'fixture-exporter','admissionEligible':False,'fidelityGate':'NOT_RUN',
            'createdNodeIds':[],'mutatedNodeIds':[],'issues':[],
            'nativeEvidence':{'pageReference':'page','rootReference':'component','nodes':[{'reference':'component',
                'type':'COMPONENT','parentReference':None,'properties':{},
                'localBounds':{'x':80,'y':80,'width':2,'height':2},
                'absoluteBounds':{'x':80,'y':80,'width':2,'height':2}}]},
            'raster':{'format':'PNG','scale':1,'background':'native-transparent','bytes':list(self.raw)}}

    def test_original_png_preserved_and_white_composite_never_resized(self):
        manifest,files=package_capture(self.result,**self.expected)
        self.assertEqual(files['native.png'],self.raw)
        self.assertEqual(manifest['pixelSize'],[2,2])
        with Image.open(BytesIO(files['comparison-white.png'])) as image:
            self.assertEqual(image.size,(2,2));self.assertEqual(image.getpixel((0,0)),(255,127,127,255))
        self.assertEqual(manifest['nativeEvidenceSha256'],hashlib.sha256(files['native-evidence.json']).hexdigest())
        self.assertFalse(manifest['admissionEligible']);self.assertEqual(manifest['fidelityGate'],'NOT_RUN')

    def test_fixture_cannot_be_imported_as_production(self):
        expected=dict(self.expected,scope='production')
        with self.assertRaisesRegex(ValueError,'identity'): package_capture(self.result,**expected)

    def test_combined_builder_output_is_bound_to_its_created_component(self):
        combined={'scope':'figma_button_candidate','status':'PASS','admissionEligible':False,
            'fidelityGate':'NOT_RUN','issues':[],'createdNodeIds':['component'],
            'nativeObservation':{'componentReference':'component'},'nativeCapture':self.result}
        self.assertEqual(package_capture(combined,**self.expected)[0]['logicalId'],'fixture.button')
        combined['nativeObservation']['componentReference']='other'
        with self.assertRaisesRegex(ValueError,'reference_mismatch'):package_capture(combined,**self.expected)
        combined['status']='FAIL'
        with self.assertRaisesRegex(ValueError,'not_successful'):package_capture(combined,**self.expected)

    def test_scope_identity_status_and_mutation_guards(self):
        for key,value in [('fileReference','other'),('componentReference','other'),('logicalId','other'),('status','FAIL'),('mutatedNodeIds',['node'])]:
            changed=deepcopy(self.result);changed[key]=value
            with self.assertRaises(ValueError):package_capture(changed,**self.expected)

    def test_png_invalid_bytes_or_dimensions_fail(self):
        for values in ([True],[256],[-1],[],[137,80,78,71]):
            changed=deepcopy(self.result);changed['raster']['bytes']=values
            with self.assertRaises((ValueError,OSError)):package_capture(changed,**self.expected)
        changed=deepcopy(self.result);changed['nativeEvidence']['nodes'][0]['localBounds']['width']=3
        with self.assertRaisesRegex(ValueError,'size'):package_capture(changed,**self.expected)

    def test_duplicate_references_unknown_parents_and_nonfinite_bounds_fail(self):
        changed=deepcopy(self.result);changed['nativeEvidence']['nodes'].append(deepcopy(changed['nativeEvidence']['nodes'][0]))
        with self.assertRaisesRegex(ValueError,'tree'):package_capture(changed,**self.expected)
        changed['nativeEvidence']['nodes'][-1].update(reference='text',parentReference='unknown')
        with self.assertRaisesRegex(ValueError,'tree'):package_capture(changed,**self.expected)
        changed=deepcopy(self.result);changed['nativeEvidence']['nodes'][0]['localBounds']['width']=float('nan')
        with self.assertRaisesRegex(ValueError,'bounds'):package_capture(changed,**self.expected)

    def test_immutable_artifacts_and_hashes(self):
        with tempfile.TemporaryDirectory(prefix='capture-tests-',dir=ROOT/'artifacts') as directory:
            output=Path(directory)/'capture';manifest=save_capture(self.result,output,**self.expected)
            for name,expected in manifest['files'].items():
                self.assertEqual(hashlib.sha256((output/name).read_bytes()).hexdigest(),expected)
            with self.assertRaisesRegex(ValueError,'exists'):save_capture(self.result,output,**self.expected)
            self.assertEqual(json.loads((output/'capture_manifest.json').read_text())['status'],'PASS')
            self.assertEqual(verify_saved_capture(output)['status'],'PASS')
            (output/'native.png').write_bytes(self.raw+b'tamper')
            self.assertEqual(verify_saved_capture(output)['status'],'FAIL')

    def test_manifest_hash_and_normalization_claims_cannot_drift(self):
        with tempfile.TemporaryDirectory(prefix='capture-tests-',dir=ROOT/'artifacts') as directory:
            output=Path(directory)/'capture';manifest=save_capture(self.result,output,**self.expected)
            manifest['normalization']['resize']=True
            (output/'capture_manifest.json').write_text(json.dumps(manifest))
            self.assertEqual(verify_saved_capture(output)['status'],'FAIL')
