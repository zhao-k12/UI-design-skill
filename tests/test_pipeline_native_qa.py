"""Real saved native readbacks plus corruption cases for end-to-end rejection."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from adapters.pipeline_qa import verify

ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_bytes())


class PipelineNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document=read('examples/end-to-end-acceptance/final_ui_ir.json')
        cls.content=read('examples/acceptance-prototype/content.json')
        cls.inputs={p:(read(f'examples/end-to-end-acceptance/{p}_preflight.json')['plan'],read(f'adapters/{p}/metadata/pipeline-acceptance/execution.json'),read(f'adapters/{p}/metadata/pipeline-acceptance/capture.json')) for p in ('figma','penpot')}
    def check(self,p,mutate=None):
        plan,e,c=deepcopy(self.inputs[p])
        if mutate:mutate(plan,e,c)
        return verify(self.document,plan,e,c,self.content,p)
    def test_both_actual_native_pages_pass(self):
        for p in self.inputs:self.assertEqual('PASS',self.check(p)['status'])
    def test_missing_field_button_section_and_icon_rejected(self):
        for p in self.inputs:
            for uid in ('field-name.label','layout.item.1.2.instance','pattern.table','header-title.icon'):
                def mutate(plan,e,c):
                    key='nodes' if p=='figma' else 'contentNodes';c[key]=[n for n in c[key] if n['id']!=e['nodeMap'][uid]]
                self.assertEqual('FAIL',self.check(p,mutate)['status'])
    def test_wrong_instance_variant_binding_and_flattening_rejected(self):
        for p in self.inputs:
            for field,value in (('component','unregistered-master'),('type','TEXT' if p=='figma' else 'text')):
                def mutate(plan,e,c):
                    n=next(n for n in c['nodes' if p=='figma' else 'contentNodes'] if n['id']==e['nodeMap']['layout.item.1.1.instance']);n[field]=value
                self.assertEqual('FAIL',self.check(p,mutate)['status'])
    def test_spacing_grid_size_and_text_overflow_rejected(self):
        for p in self.inputs:
            for uid,field,value in (('layout.item.1.0','width',329),('layout.item.1.1','x',0),('field-name.label','width',500)):
                def mutate(plan,e,c):
                    n=next(n for n in c['nodes' if p=='figma' else 'contentNodes'] if n['id']==e['nodeMap'][uid]);n[field]=value
                self.assertEqual('FAIL',self.check(p,mutate)['status'])
            def spacing(plan,e,c):
                if p=='figma':next(n for n in c['nodes'] if n['id']==e['nodeMap']['pattern.query'])['itemSpacing']=17
                else:next(n for n in c['evidence'] if n['uiIrId']=='pattern.query')['flex']['rowGap']=17
            self.assertEqual('FAIL',self.check(p,spacing)['status'])
    def test_old_hash_foreign_page_partial_png_and_content_rejected(self):
        for p in self.inputs:
            for mutation in (lambda plan,e,c:e.update(uiIrSha256='0'*64),lambda plan,e,c:c.update(pageReference='foreign-page'),lambda plan,e,c:c.update(nativePngBase64='invalid')):
                self.assertEqual('FAIL',self.check(p,mutation)['status'])
            def text(plan,e,c):
                next(n for n in c['nodes' if p=='figma' else 'contentNodes'] if n.get('characters')=='张三')['characters']='wrong'
            self.assertEqual('FAIL',self.check(p,text)['status'])
    def test_hidden_wrong_font_and_wrong_background_rejected(self):
        for p in self.inputs:
            for uid,key,value in (('header-title.icon','opacity',0),('layout.item.0.0.instance','fontSize',99),('pattern.page','fills',[])):
                def mutate(plan,e,c):
                    next(n for n in c['nodes' if p=='figma' else 'contentNodes'] if n['id']==e['nodeMap'][uid])[key]=value
                self.assertEqual('FAIL',self.check(p,mutate)['status'])
    def test_illegal_variant_and_unregistered_icon_rejected_even_with_new_hash(self):
        from validators.structure.gate import builder
        for p in self.inputs:
            for category in ('ComponentInstance','IconInstance'):
                document=deepcopy(self.document)
                def corrupt(n):
                    if n['type']==category:
                        n['variant' if category=='ComponentInstance' else 'iconId']='unregistered';return True
                    return any(corrupt(c) for c in n.get('children',[]))
                self.assertTrue(corrupt(document['pages'][0]))
                plan,e,c=deepcopy(self.inputs[p]);plan['uiIrSha256']=e['uiIrSha256']=builder.fingerprint(document)
                self.assertEqual('FAIL',verify(document,plan,e,c,self.content,p)['status'])


if __name__=='__main__':unittest.main()
