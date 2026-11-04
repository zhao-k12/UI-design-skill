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
    def test_uploaded_value_preview_requires_explicit_valid_state(self):
        self.content['root']={'id':'value','kind':'container','designRole':'uploaded-value',
            'sourceIds':['action'],'previewState':{'bind':'row.preview'},'hoverPreview':True}
        self.assertEqual(self.run_compile()['ui_ir']['root']['previewState'],{'bind':'row.preview'})
        self.content['root']['previewState']='unknown'
        with self.assertRaisesRegex(ValueError,'invalid_preview_state'):self.run_compile()
        self.content['root']['previewState']='default'
        self.content['root']['hoverPreview']='yes'
        with self.assertRaisesRegex(ValueError,'invalid_hover_preview'):self.run_compile()
        self.content['root']['hoverPreview']=True
        self.content['root']['designRole']='form-section'
        with self.assertRaisesRegex(ValueError,'preview_state_requires_uploaded_value'):self.run_compile()
    def test_viewport_shell_and_fill_are_content_independent(self):
        child=self.content['root'];child['sourceIds']=[]
        self.content['root']={'id':'shell','kind':'container','sourceIds':['action'],
            'layout':{'minHeight':'viewport','fill':True},'children':[child]}
        result=self.run_compile()
        self.assertEqual(result['layout_tree']['nodes']['shell']['minHeight'],'viewport')

    def test_navigation_landmark_accepts_only_official_link_current(self):
        self.content['root']={'id':'nav','kind':'container','semantic':'navigation','ariaLabel':'快捷导航',
            'sourceIds':['action'],'children':[{'id':'link','kind':'component','component':'Link',
            'current':True,'props':{'strong':True},'children':[{'id':'text','kind':'text','value':'首页'}]}]}
        result=self.run_compile()
        self.assertEqual(result['ui_ir']['root']['semantic'],'navigation')
        self.assertTrue(result['ui_ir']['root']['children'][0]['current'])
        self.content['root']['children'][0]['component']='Button'
        with self.assertRaisesRegex(ValueError,'invalid_current_link'):self.run_compile()
        self.content['root']['children'][0]['component']='Link'
        self.content['root']['ariaLabel']=''
        with self.assertRaisesRegex(ValueError,'invalid_navigation_label'):self.run_compile()

    def test_minimum_gap_requires_valid_axis_and_spacing_token(self):
        self.content['layoutRelations']=[{'id':'gap','kind':'minimum-gap','first':'page','second':'label',
            'axis':'vertical','minimum':'xs','sourceEvidence':'操作区与表头留白'}]
        self.assertEqual(self.run_compile()['ui_ir']['layoutRelations'][0]['minimum'],'xs')
        self.content['layoutRelations'][0]['minimum']=8
        with self.assertRaisesRegex(ValueError,'layout_relation_minimum_gap_invalid'):self.run_compile()

    def test_shell_cannot_skip_surface_and_boundary_contracts(self):
        self.content['root']={'id':'page','kind':'component','component':'Layout','sourceIds':['action'],'children':[
            {'id':'header','kind':'component','component':'Header','children':[
                {'id':'nav','kind':'component','component':'Menu','props':{'mode':'horizontal'}}]},
            {'id':'side','kind':'component','component':'Menu'},
            {'id':'main','kind':'component','component':'Content'}]}
        with self.assertRaisesRegex(ValueError,'shell_surface_and_boundary'):self.run_compile()
        relations=[{'id':'paint','kind':'surface-cover','surface':'side','extent':'main','axis':'vertical','sourceEvidence':'侧栏背景延续到主区底部'},
                   {'id':'edge','kind':'edge-align','first':'nav','second':'side','firstEdge':'left','secondEdge':'right','sourceEvidence':'顶部导航从侧栏右边界开始'},
                   {'id':'center','kind':'vertical-center','first':'nav','second':'header','sourceEvidence':'顶栏导航在头部垂直居中'}]
        self.content['layoutRelations']=relations
        self.assertEqual(self.run_compile()['ui_ir']['layoutRelations'],relations)
        self.content['layoutRelations']=relations[:2]
        self.assertEqual(self.run_compile()['ui_ir']['layoutRelations'],relations[:2])
        self.content['layoutRelations']=relations
        relations[1]['second']='missing'
        with self.assertRaisesRegex(ValueError,'layout_relation_node_missing'):self.run_compile()

if __name__=='__main__':unittest.main()
