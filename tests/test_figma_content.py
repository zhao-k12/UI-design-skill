import copy
import unittest
from tests import test_figma_adapter as fixtures
from validators.ui_ir import ROOT,load_json
from adapters.figma.content_compiler import prepare
from adapters.figma.section_content_qa import verify

BASE=ROOT/'adapters/figma/metadata/section-content-acceptance'


class FigmaContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.FigmaCompilerTests.setUpClass()
        cls.fixture=fixtures.FigmaCompilerTests()

    def test_declared_source_mappings_compile_without_modifying_historical_compiler(self):
        doc=load_json(ROOT/'examples/adapter-fidelity-acceptance.ui-ir.json')
        def walk(n):
            if n['id']=='input.name':n['props']={'placeholder':'姓名'}
            if n['id']=='select.status':n['props']={'value':'停用'}
            if n['id']=='button.query':n['slots']={'label':[{'id':'button.query.label','type':'Text','text':'导出'}]}
            for c in n.get('children',[]):walk(c)
        walk(doc['pages'][0]);before=copy.deepcopy(doc)
        f=self.fixture
        result=prepare(doc,f.tokens,f.components,f.bindings,f.icons,
            load_json(ROOT/'adapters/figma/metadata/icon-bindings.json'),load_json(ROOT/'adapters/figma/metadata/font-bindings.json'),file_reference='0vGWSRoLxBiVPXiZ8xJAX9')
        self.assertEqual(result['status'],'PASS',result['issues']);self.assertEqual(doc,before)
        self.assertEqual(result['plan']['adapterVersion'],'0.1.1-content')
        mappings=[]
        def collect(n):
            mappings.extend(n.get('nativeContent',[]))
            for c in n.get('children',[]):collect(c)
        collect(result['plan']['pages'][0]);self.assertEqual(len(mappings),3)

    def test_table_body_header_override_remains_explicitly_unsupported(self):
        doc=load_json(ROOT/'examples/adapter-fidelity-acceptance.ui-ir.json')
        def walk(n):
            if n['id']=='table.body':n['props']={'headers':['姓名']}
            for c in n.get('children',[]):walk(c)
        walk(doc['pages'][0]);f=self.fixture
        result=prepare(doc,f.tokens,f.components,f.bindings,f.icons,file_reference='0vGWSRoLxBiVPXiZ8xJAX9')
        self.assertEqual(result['status'],'FAIL');self.assertIsNone(result['plan'])

    def test_independent_real_native_content_evidence_passes(self):
        result=self.native_qa();self.assertEqual(result['status'],'PASS',result['issues'])
        self.assertEqual(result['unchangedNativeNodeCount'],70)
        self.assertFalse(result['fullTask015Acceptance'])

    def native_qa(self,mutate=None,visual=True):
        execution=load_json(BASE/'execution.json');patch=load_json(BASE/'patch.json')
        before=load_json(BASE/'before-transport.json')['capture'];after=load_json(BASE/'after-transport.json')['capture']
        request=load_json(BASE/'request.json');review=load_json(BASE/'visual-review.json')
        if mutate:mutate(execution,patch,before,after,request)
        return verify(execution,patch,before,after,request,visual_review=review if visual else None)

    def test_native_snapshot_or_ledger_tampering_cannot_pass(self):
        for mutate in (lambda e,p,b,a,r:a.update(fileReference='foreign'),lambda e,p,b,a,r:p.update(mutatedNodeIds=[]),
                       lambda e,p,b,a,r:a['nodes'][0].update(width=1),lambda e,p,b,a,r:r['targets'][0].update(text='invented')):
            self.assertEqual(self.native_qa(mutate)['status'],'FAIL')
        self.assertEqual(self.native_qa(visual=False)['status'],'Review')
