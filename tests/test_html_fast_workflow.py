import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from html_fast_workflow import expand_observations,bind_groups,expand_review

class CompactWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.traits=dict(leading='avatar',trailing='actions',surface='plain',shape='rect',role='record')
        self.doc={'sourceSha256':'fixture','groups':[dict(id='rows',prefix='row-',count=13,region='table',
            traits=self.traits,decision='include',sourceEvidence='原图13条记录',treeRef='table')]}
    def test_expands_ids_and_preserves_per_instance_exception(self):
        self.doc['groups'][0]['exceptions']={'row-12':{'traits':{**self.traits,'surface':'selected'}}}
        result=expand_observations(self.doc)
        self.assertEqual(len(result['items']),13)
        self.assertEqual(result['items'][-1]['traits']['surface'],'selected')
        self.assertEqual(result['items'][0]['traits']['surface'],'plain')
    def test_scan_requires_its_own_material_not_first_scan_copy(self):
        scan={'groups':[dict(id='rows',prefix='row-',count=12,region='table',traits=self.traits,visual='独立看见12行')]}
        self.assertNotEqual(len(expand_observations(scan,scan=True)['items']),len(expand_observations(self.doc)['items']))
        self.assertNotIn('sourceEvidence',expand_observations(scan,scan=True)['items'][0])
    def test_duplicate_ids_are_rejected(self):
        self.doc['items']=[dict(id='row-0')]
        with self.assertRaisesRegex(ValueError,'duplicate_observation_id'):expand_observations(self.doc)
    def test_unknown_exception_is_not_silently_discarded(self):
        self.doc['groups'][0]['exceptions']={'row-14':{'traits':self.traits}}
        with self.assertRaisesRegex(ValueError,'group_exception_unknown'):expand_observations(self.doc)
    def test_tree_group_binding_covers_all_instances(self):
        result=bind_groups(dict(id='table',kind='component',sourceGroups=['rows']),expand_observations(self.doc)['_groupIds'])
        self.assertEqual(len(result['sourceIds']),13)
        self.assertNotIn('sourceGroups',result)
    def test_review_cannot_infer_pass_from_source_group(self):
        with self.assertRaisesRegex(ValueError,'group_visual_review_required'):
            expand_review({'groups':[dict(sourceGroups=['rows'],variantRef='table')]},expand_observations(self.doc),{})
    def test_repeated_source_data_preserves_count_and_exception(self):
        result=bind_groups({'$repeat':{'count':13,'value':{'name':'李小明','online':'在线'},'exceptions':{'12':{'name':'赵六'}}}}, {})
        self.assertEqual(len(result),13)
        self.assertEqual(result[-1],{'name':'赵六','online':'在线'})
        self.assertEqual(result[0]['name'],'李小明')
    def test_data_repeat_exception_cannot_be_lost(self):
        with self.assertRaisesRegex(ValueError,'data_repeat_exception_unknown'):
            bind_groups({'$repeat':{'count':2,'value':{},'exceptions':{'2':{'name':'extra'}}}}, {})

if __name__=='__main__':unittest.main()
