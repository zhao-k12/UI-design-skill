import base64
import copy
from io import BytesIO
import unittest
from PIL import Image
from adapters.penpot.section_patch_qa import verify
from validators.ui_ir import ROOT, load_json

BASE=ROOT/'adapters/penpot/metadata/section-content-acceptance'


class SectionPatchQATests(unittest.TestCase):
    def setUp(self):
        self.execution=load_json(BASE/'execution.json')['result']
        self.patch=load_json(BASE/'patch.json')['result']
        self.before=load_json(BASE/'before-capture.json')['result']
        self.after=load_json(BASE/'after-capture.json')['result']
        self.content=load_json(BASE/'expected-content.json')
        self.review=load_json(BASE/'visual-review.json')

    def run_qa(self,review=True):
        return verify(self.execution,self.patch,self.before,self.after,
                      expected_content=self.content,visual_review=self.review if review else None)

    def test_real_readback_pass_and_preserved_native_nodes(self):
        result=self.run_qa()
        self.assertEqual(result['status'],'PASS',result['issues'])
        self.assertEqual(len(result['changedTextIds']),1)
        self.assertEqual(result['unchangedNativeNodeCount'],76)
        self.assertFalse(result['fullTask015Acceptance'])

    def test_missing_visual_or_expected_content_cannot_pass(self):
        self.assertEqual(self.run_qa(review=False)['status'],'Review')
        self.content=None
        self.assertEqual(self.run_qa()['status'],'FAIL')

    def test_wrong_expected_text_and_component_binding_rejected(self):
        self.content['button.query']['nativeContent'][0]['text']='wrong'
        self.assertEqual(self.run_qa()['status'],'FAIL')
        self.setUp();self.content['button.query']['componentReference']='wrong'
        self.assertEqual(self.run_qa()['status'],'FAIL')

    def test_foreign_capture_changed_style_and_topology_rejected(self):
        self.after['fileReference']='foreign'
        self.assertEqual(self.run_qa()['status'],'FAIL')
        self.setUp();self.after['nodes'][0]['width']+=1
        self.assertEqual(self.run_qa()['status'],'FAIL')
        self.setUp();self.after['nodes'].pop()
        self.assertEqual(self.run_qa()['status'],'FAIL')

    def test_pixel_change_outside_copy_is_rejected(self):
        with Image.open(BytesIO(base64.b64decode(self.after['nativePngBase64']))) as source:
            image=source.convert('RGBA');image.putpixel((0,0),(255,0,255,255));buf=BytesIO();image.save(buf,format='PNG')
        self.after['nativePngBase64']=base64.b64encode(buf.getvalue()).decode()
        result=self.run_qa()
        self.assertEqual(result['status'],'FAIL')
        self.assertIn('native PNG changed outside patched copy bounds',result['issues'])

    def test_missing_png_and_stale_revision_rejected(self):
        self.after['nativePngBase64']=''
        self.assertEqual(self.run_qa()['status'],'FAIL')
        self.setUp();self.after['fileRevision']=0
        self.assertEqual(self.run_qa()['status'],'FAIL')
