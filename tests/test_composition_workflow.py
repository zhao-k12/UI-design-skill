import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('composition_workflow',Path(__file__).resolve().parents[1]/'scripts/composition_workflow.py')
workflow=importlib.util.module_from_spec(spec);spec.loader.exec_module(workflow)

class WorkflowTests(unittest.TestCase):
    def test_group_expands_instances_and_exceptions(self):
        data={'groups':[{'id':'row-{i}','sourceEvidence':'第{n}行','count':3,'traits':{'role':'avatar'},'overrides':{'1':{'sourceEvidence':'第二行例外'}}}]}
        expanded=workflow.expand(data)['items']
        self.assertEqual([x['id'] for x in expanded],['row-0','row-1','row-2'])
        self.assertEqual(expanded[1]['sourceEvidence'],'第二行例外')
        self.assertEqual(expanded[2]['sourceEvidence'],'第3行')
    def test_duplicate_instances_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'expanded_id_duplicate'):
            workflow.expand({'groups':[{'id':'same','count':2}]})
    def test_pending_review_cannot_be_auto_passed(self):
        with self.assertRaisesRegex(ValueError,'visual_group_not_reviewed'):
            workflow.expand_review({'items':[{'id':'one','decision':'include'}]}, {'groups':[{'id':'g','status':'PENDING'}]})
    def test_review_group_preserves_instance_coverage_and_exclusions(self):
        observation={'items':[{'id':'a','decision':'include'},{'id':'b','decision':'include'},{'id':'mark','decision':'exclude'}]}
        decisions={'sourceSha256':'source','reviewMode':'batched-v2','screenshotSha256':{},'stageChecks':{},'relationChecks':[],
            'excludedIdsReviewed':['mark'],'groups':[{'id':'shared','sourceIds':['a','b'],'status':'PASS',
            'renderedTraits':{'role':'avatar'},'component':'Avatar','variantReason':'circle','officialEvidence':'official/avatar.vue'}]}
        result=workflow.expand_review(observation,decisions)
        self.assertEqual({item['id'] for item in result['items']},{'a','b','mark'})
        self.assertEqual(len(result['variantRules']),1)

if __name__=='__main__':unittest.main()
