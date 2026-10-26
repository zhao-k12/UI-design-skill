import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from html_tree_editor import FullTreeEditor


class FullTreeEditorTests(unittest.TestCase):
    def editor(self):
        return FullTreeEditor('source-hash', '示例', {'id':'page','kind':'container','layout':{'direction':'horizontal'}})

    def test_explicit_region_ownership_and_move_preserve_facts(self):
        editor=self.editor()
        sidebar=editor.add('page','container',id='sidebar',layout={'direction':'vertical'})
        main=editor.add('page','container',id='main',layout={'direction':'vertical'})
        brand=editor.add(sidebar,'component',component='Avatar',props={'shape':'square'},sourceIds=['brand'])
        header=editor.add(main,'component',id='header',component='Card',props={'padding':16})
        self.assertEqual(editor.content()['root']['children'][0]['children'][0]['id'],brand)
        editor.move(brand,header)
        tree=editor.content()
        self.assertEqual(tree['root']['children'][0]['children'],[])
        self.assertEqual(tree['root']['children'][1]['children'][0]['children'][0]['sourceIds'],['brand'])
        with self.assertRaisesRegex(ValueError,'descendant'):editor.move(main,header)

    def test_rows_false_null_and_business_ids_are_not_inferred_or_modified(self):
        editor=self.editor()
        table=editor.add('page','component',component='Table',props={'columns':[{'title':'姓名','key':'name'}]})
        rows=[{'id':'same','name':'甲','enabled':False,'required':None}, {'id':'same','name':'乙','enabled':True,'required':False}]
        editor.set_rows(table,rows);rows[0]['name']='外部修改'
        saved=editor.content()['root']['children'][0]['props']['data']
        self.assertEqual(saved,[{'id':'same','name':'甲','enabled':False,'required':None}, {'id':'same','name':'乙','enabled':True,'required':False}])

    def test_nested_slots_and_cells_receive_unique_explicit_ids(self):
        editor=self.editor()
        table=editor.add('page','component',component='Table',props={'columns':[{'key':'name','cell':{'kind':'component','component':'Button','children':[{'kind':'text','value':{'bind':'row.name'}}]}}]})
        editor.add('page','component',id='input',component='Input',props={'placeholder':'姓名'})
        icon=editor.add('input','icon',slot='suffix',name='user-line')
        tree=editor.content();cell=tree['root']['children'][0]['props']['columns'][0]['cell']
        self.assertEqual(len({table,cell['id'],cell['children'][0]['id'],icon}),4)
        self.assertEqual(cell['children'][0]['value'],{'bind':'row.name'})
        with self.assertRaisesRegex(ValueError,'duplicate'):editor.add('page','text',id=icon,value='重复')

    def test_shorthand_rejection_and_failed_mutation_leave_tree_unchanged(self):
        editor=self.editor();before=editor.content()
        with self.assertRaisesRegex(ValueError,'full_tree_required'):editor.add('page','component',use='Button')
        self.assertEqual(editor.content(),before)
        table=editor.add('page','component',component='Table',props={})
        with self.assertRaises(ValueError):editor.set_rows(table,{'$repeat':{'count':2}})
        before=editor.content()
        with self.assertRaises(ValueError):editor.move(table,'page',index=8)
        self.assertEqual(editor.content(),before)

    def test_write_job_saves_canonical_tree_and_separate_source_material(self):
        editor=self.editor();editor.add('page','text',value='原文',sourceIds=['title'])
        observation={'sourceSha256':'source-hash','items':[{'id':'title','sourceEvidence':'初读'}]}
        scan={'sourceSha256':'source-hash','items':[{'id':'title','visual':'独立复扫'}]}
        relations=[{'id':'center','kind':'vertical-center','first':'page','second':'node-0001','sourceEvidence':'测试关系'}]
        editor.set_layout_relations(relations)
        with tempfile.TemporaryDirectory() as folder:
            path=editor.write_job(Path(folder)/'job.json',source='prototype.png',observation=observation,scan=scan)
            saved=json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(saved['content'],editor.content())
        self.assertEqual(saved['content']['layoutRelations'],relations)
        self.assertEqual(saved['observation'],observation)
        self.assertEqual(saved['scan'],scan)
        self.assertEqual(saved['content']['root']['children'][0]['kind'],'text')


if __name__=='__main__':unittest.main()
