import unittest
from validators.ui_ir import ROOT,load_json
from adapters.figma.cell_slots_qa import verify

BASE=ROOT/'adapters/figma/metadata/cell-slots-acceptance'


class FigmaCellSlotTests(unittest.TestCase):
    def qa(self,mutate=None):
        records=[load_json(BASE/(n+'.json')) for n in ('execution','before-capture','fill')]
        records.append(load_json(BASE/'after-transport.json')['capture'])
        request=load_json(BASE/'request.json')
        if mutate:mutate(*records,request)
        return verify(*records,request,visual_review=load_json(BASE/'visual-review.json'))

    def test_independent_native_six_role_capture_keeps_existing_cell(self):
        result=self.qa();self.assertEqual(result['status'],'PASS',result['issues'])
        self.assertEqual(result['preservedContainerCount'],8);self.assertEqual(result['createdNodeCount'],12)
        self.assertFalse(result['fullTask015Acceptance'])

    def test_ledger_source_font_and_context_tampering_fail(self):
        for mutation in (
            lambda e,b,p,a,r:a.update(fileReference='foreign'),
            lambda e,b,p,a,r:p.update(afterSha256='0'*64),
            lambda e,b,p,a,r:p.update(createdNodeIds=[]),
            lambda e,b,p,a,r:r['items'][1]['children'][0]['fontName'].update(style='Bold'),
            lambda e,b,p,a,r:r['items'][2]['children'][0].update(componentReference='foreign'),
        ):
            self.assertEqual(self.qa(mutation)['status'],'FAIL')
