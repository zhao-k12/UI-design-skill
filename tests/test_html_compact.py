import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from html_compact import expand_tree, delta_review, merge_patch
from html_fast_workflow import review_plan


class CompactTests(unittest.TestCase):
    def test_business_kind_and_id_are_not_treated_as_nodes(self):
        observed={'_groupIds':{'rows':['row']},'items':[{'id':'row','decision':'include','treeRef':'records','traits':{}}]}
        content={'root':{'id':'records','kind':'component','component':'Table','sourceIds':['row'],
                         'props':{'data':[{'id':'business-id','kind':'record','sourceIds':['row']}]}}}
        rendered={'stages':{stage:{'geometrySha256':'same','nodeSignatures':{'records':'same'}} for stage in ('skeleton','component','delivery')}}
        self.assertEqual(review_plan(observed,content,rendered)['groups']['rows']['bindings'],['records'])

    def test_shorthand_preserves_text_states_and_cells(self):
        compact={'definitions':{'action':{'use':'Button','p':{'disabled':{'bind':'row.locked'}},'text':{'bind':'row.name'}}},
                 'root':{'stack':'vertical','gap':'md','children':[{'use':'Table','from':['records'],
                    'p':{'data':[{'name':'甲','locked':False},{'name':'乙','locked':True}],
                         'columns':[{'key':'name','cell':{'ref':'action'}}]}}]}}
        result=expand_tree(compact)
        table=result['root']['children'][0]
        self.assertEqual(table['sourceGroups'],['records'])
        self.assertEqual(table['props']['data'],compact['root']['children'][0]['p']['data'])
        cell=table['props']['columns'][0]['cell']
        self.assertEqual(cell['props']['disabled'],{'bind':'row.locked'})
        self.assertEqual(cell['children'][0]['value'],{'bind':'row.name'})
        self.assertEqual(expand_tree(result),result)
        self.assertNotIn('definitions',result)

    def test_reference_cycle_and_ambiguous_values_rejected(self):
        for content in ({'definitions':{'a':{'ref':'a'}},'root':{'ref':'a'}},
                        {'root':{'ref':'missing'}},
                        {'root':{'use':'Button','p':{},'props':{}}}):
            with self.assertRaises(ValueError):expand_tree(content)

    def test_patch_keeps_unaffected_rows_and_false(self):
        job={'content':{'rows':[{'name':'甲','disabled':False}]},'viewport':{'width':1440,'height':1000}}
        patched=merge_patch(job,{'viewport':{'width':1600}})
        self.assertEqual(patched['content'],job['content'])
        self.assertEqual(patched['viewport'],{'width':1600,'height':1000})
        self.assertEqual(job['viewport']['width'],1440)

    def test_difference_review_requires_explicit_complete_confirmation(self):
        traits={'surface':'tint'}
        plan={'groups':{'records':{'items':[{'id':'row-0','decision':'include','traits':traits},
                          {'id':'row-1','decision':'exclude'}],
                          'rules':{'row-0':{'id':'r','component':'Tag'}}}},'reusableGroups':[]}
        review={'reviewMode':'delta-v1','issues':[], 'checkedStages':['tree','skeleton','component','delivery']}
        with self.assertRaises(ValueError):delta_review(review,plan)
        review['confirmedGroups']=['records'];expanded=delta_review(review,plan)
        self.assertEqual(expanded['items'][0]['renderedTraits'],traits)
        self.assertEqual(expanded['items'][1]['exclusionStatus'],'PASS')
        review['issues']=['wrong variant']
        with self.assertRaises(ValueError):delta_review(review,plan)
        review['issues']=[];review['confirmedGroups']=[];plan['reusableGroups']=['records']
        self.assertEqual(len(delta_review(review,plan)['items']),2)


if __name__=='__main__':unittest.main()
