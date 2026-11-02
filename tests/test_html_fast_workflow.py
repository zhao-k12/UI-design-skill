import copy
from pathlib import Path
import sys
import json
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from html_fast_workflow import expand_observations,bind_groups,expand_review,record_timing_event,start,complete_timing,require_flat_table_coverage

class TimingEventTests(unittest.TestCase):
    def test_explicit_events_append_without_changing_existing_timing(self):
        with tempfile.TemporaryDirectory() as directory:
            task=Path(directory)
            with patch('html_fast_workflow.now',side_effect=['2026-01-01T00:00:00+00:00',
                    '2026-01-01T00:00:03+00:00','2026-01-01T00:00:10+00:00']):
                start(task)
                record_timing_event(task,'观察完成')
                record_timing_event(task,'Tree 完成')
            data=json.loads((task/'timing.json').read_text(encoding='utf8'))
            self.assertEqual(data['startedAt'],'2026-01-01T00:00:00+00:00')
            self.assertEqual(data['scope'],'timer-start; request start not verified')
            self.assertEqual(data['runs'],[])
            self.assertEqual(data['events'],[
                {'name':'观察完成','at':'2026-01-01T00:00:03+00:00'},
                {'name':'Tree 完成','at':'2026-01-01T00:00:10+00:00'}])
            self.assertNotIn('elapsedSeconds',data)

    def test_rejects_missing_timer_and_empty_event_without_creating_it(self):
        with tempfile.TemporaryDirectory() as directory:
            task=Path(directory)
            with self.assertRaisesRegex(ValueError,'timing_not_started'):
                record_timing_event(task,'观察完成')
            self.assertFalse((task/'timing.json').exists())
            with self.assertRaisesRegex(ValueError,'timing_event_name_required'):
                record_timing_event(task,'  ')

    def test_short_unverified_timer_cannot_claim_goal_met_even_with_legacy_label(self):
        for scope in ('timer-start; request start not verified','request-start',
                      'render-start; analysis time not measured'):
            with self.subTest(scope=scope):
                timing={'startedAt':'2026-01-01T00:02:00+00:00','scope':scope,
                        'targetSeconds':300,'runs':[]}
                completed=complete_timing(timing,'2026-01-01T00:06:00+00:00',
                                          '2026-01-01T00:05:00+00:00')
                self.assertEqual(completed['elapsedSeconds'],240)
                self.assertEqual(completed['reviewAndToolWaitSeconds'],60)
                self.assertEqual(completed['scope'],scope)
                self.assertFalse(completed['scopeVerified'])
                self.assertIsNone(completed['targetMet'])

    def test_lower_bound_over_target_cannot_meet_goal(self):
        timing={'startedAt':'2026-01-01T00:00:00+00:00','scope':'request-start',
                'targetSeconds':300,'runs':[]}
        completed=complete_timing(timing,'2026-01-01T00:05:01+00:00',
                                  '2026-01-01T00:04:30+00:00')
        self.assertEqual(completed['elapsedSeconds'],301)
        self.assertIs(completed['targetMet'],False)

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

class FlatTablePublicationTests(unittest.TestCase):
    def setUp(self):
        self.strict={'tableColumnReviewPolicy':'flat-titled-v1'}
        self.table={'id':'table','kind':'component','component':'Table','props':{
            'columns':[{'type':'selection'},{'title':'编号','key':'id'},{'title':'状态','key':'status'}]}}
        self.obs={'tableColumns':{'table':['编号','状态']}}
        self.scan={'tableColumns':{'table':['编号','状态']}}

    def test_new_flat_table_requires_both_matching_source_inventories(self):
        with self.assertRaisesRegex(ValueError,'flat_table_source_columns_unchecked:table'):
            require_flat_table_coverage(self.strict,self.table,{}, {})
        with self.assertRaisesRegex(ValueError,'table_columns_both_observations_required'):
            require_flat_table_coverage(self.strict,self.table,self.obs,{})
        with self.assertRaisesRegex(ValueError,'table_columns_observation_disagrees'):
            require_flat_table_coverage(self.strict,self.table,self.obs,{'tableColumns':{'table':['状态','编号']}})
        require_flat_table_coverage(self.strict,self.table,self.obs,self.scan)

    def test_legacy_task_remains_compatible(self):
        require_flat_table_coverage({},self.table,{}, {})

    def test_untitled_and_grouped_tables_are_not_falsely_checked(self):
        for columns in ([{'type':'selection'}],
                        [{'title':'组','children':[{'title':'编号','key':'id'}]}]):
            with self.subTest(columns=columns):
                table=copy.deepcopy(self.table);table['props']['columns']=columns
                require_flat_table_coverage(self.strict,table,{}, {})

    def test_mixed_tables_require_only_eligible_flat_table(self):
        grouped={'id':'grouped','kind':'component','component':'Table','props':{
            'columns':[{'title':'组','children':[{'title':'值','key':'v'}]}]}}
        root={'id':'page','kind':'container','children':[self.table,grouped]}
        with self.assertRaisesRegex(ValueError,'flat_table_source_columns_unchecked:table'):
            require_flat_table_coverage(self.strict,root,{}, {})
        require_flat_table_coverage(self.strict,root,self.obs,self.scan)

if __name__=='__main__':unittest.main()
