import base64
import copy
from io import BytesIO
from pathlib import Path
import unittest
from PIL import Image
from validators.ui_ir import load_json
from adapters.penpot.section_swap_qa import verify

BASE=Path(__file__).resolve().parents[1]/'adapters/penpot/metadata/section-swap-acceptance'


class NativeSwapQATests(unittest.TestCase):
    def setUp(self):
        self.execution=load_json(BASE/'execution.json')
        self.swap=load_json(BASE/'swap.json')['result']
        self.before=load_json(BASE/'before-capture.json')['result']
        self.after=load_json(BASE/'after-capture.json')['result']
        self.visual=load_json(BASE/'visual-review.json')

    def run_qa(self,visual=True):
        return verify(self.execution,self.swap,self.before,self.after,
                      expected_reference='b17404b9-592b-8074-8008-c0d00dc30929',
                      reference_copy_id=self.execution['nodeMap']['select.status'],
                      visual_review=self.visual if visual else None)

    def test_real_independent_native_evidence_and_visual_receipt_pass(self):
        result=self.run_qa();self.assertEqual(result['status'],'PASS',result['issues'])
        self.assertEqual(result['unchangedNativeNodeCount'],74)
        self.assertFalse(result['fullTask015Acceptance'])
        self.assertEqual(self.run_qa(False)['status'],'Review')

    def test_mismatched_context_snapshot_and_recovery_ledger_rejected(self):
        for mutate in (lambda:self.after.update(fileReference='foreign'),
                       lambda:self.swap.update(createdNodeIds=[]),
                       lambda:self.after.update(fileRevision=0),
                       lambda:self.swap.update(status='FAIL')):
            self.setUp();mutate();self.assertEqual(self.run_qa()['status'],'FAIL')

    def test_changed_font_or_unrelated_node_cannot_pass_matching_execution_snapshot(self):
        for kind in ('font','unrelated'):
            self.setUp()
            if kind=='font':
                ids=set(self.swap['createdNodeIds'])
                target=next(n for n in self.after['nodes'] if n['id'] in ids and n.get('type')=='text')
                target['fontSize']='15'
            else:self.after['nodes'][0]['width']+=1
            self.swap['after']=copy.deepcopy(self.after['nodes'])
            self.assertEqual(self.run_qa()['status'],'FAIL')

    def test_png_difference_outside_instance_rejected(self):
        im=Image.open(BytesIO(base64.b64decode(self.after['nativePngBase64']))).convert('RGB')
        im.putpixel((0,0),(255,0,0));buffer=BytesIO();im.save(buffer,format='PNG')
        self.after['nativePngBase64']=base64.b64encode(buffer.getvalue()).decode()
        self.assertIn('PNG changed outside swapped instance',self.run_qa()['issues'])

    def test_source_master_modification_and_wrong_visual_hash_rejected(self):
        self.swap['sourceMasterAfter'][0]['name']='changed'
        self.assertEqual(self.run_qa()['status'],'FAIL')
        self.setUp();self.visual['nativePngSha256']='0'*64
        self.assertEqual(self.run_qa()['status'],'Review')
