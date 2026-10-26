"""Source/mapping failure regressions for the flat role composition."""
import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core/pipeline'))
from html_role_page_v1 import compile_page


class RolePageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.source = Path(self.temp.name) / 'source.png'
        self.source.write_bytes(b'isolated-source-fixture')
        digest = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.content = dict(sourceSha256=digest, pattern='role-permissions-v1',
                            sidebar=[dict(key='role', label='职务权限')], activeMenu='role',
                            columns=[dict(key=k, span=s) for k,s in [('name',3),('memberCount',2),('description',4),('updatedAt',4),('actions',11)]],
                            rows=[dict(name='职务A', memberCount='3', description='说明', updatedAt='2026-10-26', actions=[dict(label='编辑职务')])])
        values = [('menu-0','sidebar[0]','职务权限','navigation.child')]
        values += [(f'row-0-{k}',f'rows[0].{k}',v,'data.table') for k,v in [('name','职务A'),('memberCount','3'),('description','说明'),('updatedAt','2026-10-26')]]
        values += [('row-0-action-0','rows[0].actions[0]','编辑职务','action.button-text')]
        self.content['leaves'] = [dict(id=i,ref=ref,roles=[role]) for i,ref,_,role in values]
        self.observation = dict(sourceSha256=digest, items=[dict(id=i,region='test',treeRef=ref,decision='include',sourceEvidence=text,
            traits=dict(leading='icon',trailing='none',surface='plain',shape='inline',role='item')) for i,ref,text,_ in values])
        self.scan = dict(sourceSha256=digest,items=[dict(id=i,region='test',visual=text,traits=copy.deepcopy(self.observation['items'][index]['traits'])) for index,(i,_,text,_) in enumerate(values)])

    def tearDown(self):
        self.temp.cleanup()

    def test_compiles_flat_official_table(self):
        result = compile_page(self.source,self.content,self.observation,self.scan)
        self.assertEqual(result['qa_report']['status'],'PASS')
        self.assertEqual(result['ui_ir']['registryVersion'],'html-role-v1.0')
        self.assertEqual(result['ui_ir']['layout']['table']['columnSpans'],[3,2,4,4,11])

    def test_missing_operation_in_rescan_is_rejected(self):
        self.scan['items'][-1]['visual']='其他操作'
        with self.assertRaisesRegex(ValueError,'row_action_not_source_bound'):
            compile_page(self.source,self.content,self.observation,self.scan)

    def test_unregistered_component_is_rejected(self):
        self.content['leaves'][0]['roles']=['unregistered.custom-menu']
        with self.assertRaisesRegex(ValueError,'unregistered_component'):
            compile_page(self.source,self.content,self.observation,self.scan)

    def test_added_arrow_is_rejected_even_if_both_scans_claim_it(self):
        self.observation['items'][0]['traits']['trailing']='chevron-down'
        self.scan['items'][0]['traits']['trailing']='chevron-down'
        with self.assertRaisesRegex(ValueError,'flat_menu_has_unobserved_chevron'):
            compile_page(self.source,self.content,self.observation,self.scan)


if __name__ == '__main__':
    unittest.main()
