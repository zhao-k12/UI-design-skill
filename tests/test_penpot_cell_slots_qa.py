import unittest
from validators.ui_ir import ROOT,load_json
from adapters.penpot.cell_slots_qa import verify

BASE=ROOT/'adapters/penpot/metadata/cell-slots-acceptance'


class NativeCellSlotTests(unittest.TestCase):
    def qa(self,mutate=None):
        records=[load_json(BASE/(n+'.json'))['result'] for n in ('execution','before-capture','fill','after-capture')]
        request=load_json(BASE/'request.json')
        if mutate:mutate(*records,request)
        return verify(*records,request,visual_review=load_json(BASE/'visual-review.json'))

    def test_real_six_role_fill_keeps_all_existing_containers(self):
        result=self.qa();self.assertEqual(result['status'],'PASS',result['issues'])
        self.assertEqual(result['preservedContainerCount'],8);self.assertEqual(result['createdNodeCount'],16)
        self.assertFalse(result['fullTask015Acceptance'])

    def test_stale_snapshot_invented_source_and_incomplete_ledger_fail(self):
        for mutation in (
            lambda e,b,p,a,r:a.update(fileReference='foreign'),
            lambda e,b,p,a,r:p.update(createdNodeIds=[]),
            lambda e,b,p,a,r:a['nodes'][0].update(width=100),
            lambda e,b,p,a,r:r['items'][2]['children'][0].update(componentReference='foreign'),
            lambda e,b,p,a,r:r['items'][1]['children'][0].update(text='invented'),
        ):
            self.assertEqual(self.qa(mutation)['status'],'FAIL')
