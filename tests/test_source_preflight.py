import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from html_fast_workflow import require_source_preflight

class SourcePreflightTests(unittest.TestCase):
    def setUp(self):
        self.policy={'sourceEvidencePolicy':'complete-traits-v1'}
        self.root={'id':'menu','component':'Menu','sourceIds':['a'],'children':[{'id':'entry','component':'MenuItem','sourceIds':['a']}]}
        self.item={'id':'a','decision':'include','treeRef':'entry','traits':dict(leading='none',trailing='none',surface='plain',shape='rect',role='navigation')}
    def check(self):
        require_source_preflight(self.policy,self.root,{'items':[self.item]},{'items':[self.item]})
    def test_complete(self): self.check()
    def test_role_only_rejected(self):
        self.item['traits']={'role':'navigation'}
        with self.assertRaisesRegex(ValueError,'source_traits_incomplete'): self.check()
    def test_blank_and_nonstring_rejected(self):
        for value in (' ',None,False):
            self.item['traits']['shape']=value
            with self.assertRaisesRegex(ValueError,'source_traits_incomplete'): self.check()
    def test_whole_menu_binding_insufficient(self):
        self.item['treeRef']='menu';self.root['children'][0]['sourceIds']=[]
        with self.assertRaisesRegex(ValueError,'menu_instance_source_missing'): self.check()
    def test_invalid_tree_reference(self):
        self.item['treeRef']='missing'
        with self.assertRaisesRegex(ValueError,'source_binding_missing'): self.check()
    def test_icon_requires_bound_icon(self):
        self.item['traits']['leading']='icon: home'
        with self.assertRaisesRegex(ValueError,'source_icon_binding_missing'): self.check()
        self.root['children'][0]['icon']='home-line';self.check()
    def test_legacy(self):
        self.policy={};self.item['traits']={};self.check()
    def test_module_icon_child_is_valid_without_duplicate_source_ids(self):
        self.item['traits']['leading']='home-outline'
        with self.assertRaisesRegex(ValueError,'source_icon_binding_missing'): self.check()
        self.root['children'][0]['children']=[{'id':'home','kind':'icon','name':'home-line'}]
        self.check()
    def test_two_menu_entries_cannot_share_only_one_observation(self):
        self.root['children'].append({'id':'second','component':'MenuItem','sourceIds':['a']})
        with self.assertRaisesRegex(ValueError,'menu_instance_source_not_distinct'): self.check()
    def test_unrelated_sibling_icon_cannot_satisfy_entry_evidence(self):
        self.item['traits']['leading']='icon: home'
        self.root['children'].append({'id':'unrelated','kind':'container','children':[{'id':'other-icon','kind':'icon','name':'settings-line'}]})
        with self.assertRaisesRegex(ValueError,'source_icon_binding_missing'): self.check()

if __name__=='__main__': unittest.main()
