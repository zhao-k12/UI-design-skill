import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'core/pipeline'))
from html_composition import compile_tree

class CompositionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.source=Path(self.temp.name)/'source';self.source.write_bytes(b'development fixture')
        digest=hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.content={'sourceSha256':digest,'root':{'id':'page','kind':'component','component':'Button',
            'props':{'type':'primary'},'sourceIds':['action'],'children':[{'id':'label','kind':'text','value':'操作'}]}}
        traits=dict(leading='none',trailing='none',surface='filled',shape='rect',role='action')
        self.observation={'sourceSha256':digest,'items':[dict(id='action',region='page',traits=traits,decision='include',sourceEvidence='操作',treeRef='root')]}
        self.scan={'sourceSha256':digest,'items':[dict(id='action',region='page',traits=copy.deepcopy(traits),visual='操作')]}
    def tearDown(self):self.temp.cleanup()
    def run_compile(self):return compile_tree(self.source,self.content,self.observation,self.scan)
    def test_official_component_is_available_without_page_admission(self):
        self.content['root']['component']='Alert';self.content['root']['props']={'type':'success'}
        result=self.run_compile()
        self.assertEqual(result['qa_report']['status'],'PASS')
        self.assertEqual(result['ui_ir']['usedComponents'],['Alert'])
    def test_unknown_official_component_is_distinguished(self):
        self.content['root']['component']='InventedComponent'
        with self.assertRaisesRegex(ValueError,'official_component_unavailable'):self.run_compile()
    def test_source_coverage_is_not_weakened_by_flexible_structure(self):
        self.content['root']['sourceIds']=[]
        with self.assertRaisesRegex(ValueError,'page_tree_source_coverage'):self.run_compile()
    def test_official_visual_override_is_still_rejected(self):
        self.content['root']['props']['style']={'color':'red'}
        with self.assertRaisesRegex(ValueError,'component_visual_or_event_override'):self.run_compile()

if __name__=='__main__':unittest.main()
