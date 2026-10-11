import unittest
from validators.ui_ir import ROOT, load_json
from adapters.penpot.primitive_content_qa import verify

BASE = ROOT / 'adapters/penpot/metadata/primitive-content-acceptance'


class PenpotPrimitiveContentTests(unittest.TestCase):
    def qa(self, mutate=None, visual=True):
        records = [load_json(BASE / (name+'.json')) for name in
                   ('execution','patch','before-capture','after-capture','request')]
        records = [record['result'] if 'result' in record else record for record in records]
        if mutate:
            mutate(*records)
        return verify(*records, visual_review=load_json(BASE/'visual-review.json') if visual else None)

    def test_five_content_categories_preserve_other_native_nodes(self):
        result = self.qa()
        self.assertEqual(result['status'], 'PASS', result['issues'])
        self.assertEqual(result['unchangedNativeNodeCount'], 72)
        self.assertFalse(result['fullTask015Acceptance'])

    def test_context_revision_request_and_unrelated_geometry_are_guarded(self):
        for mutate in (
            lambda e,p,b,a,r: a.update(fileReference='foreign'),
            lambda e,p,b,a,r: p.update(beforeRevision=-1),
            lambda e,p,b,a,r: p.update(mutatedNodeIds=[]),
            lambda e,p,b,a,r: a['nodes'][0].update(width=1),
            lambda e,p,b,a,r: r['targets'][0].update(text='invented'),
        ):
            self.assertEqual(self.qa(mutate)['status'], 'FAIL')
        self.assertEqual(self.qa(visual=False)['status'], 'Review')
