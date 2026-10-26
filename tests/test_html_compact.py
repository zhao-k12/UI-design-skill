import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from html_compact import require_full_tree, delta_review, merge_patch
from html_fast_workflow import review_plan


class CompactTests(unittest.TestCase):
    def test_business_kind_and_id_are_not_treated_as_nodes(self):
        observed={'_groupIds':{'rows':['row']},'items':[{'id':'row','decision':'include','treeRef':'records','traits':{}}]}
        content={'root':{'id':'records','kind':'component','component':'Table','sourceIds':['row'],
                         'props':{'data':[{'id':'business-id','kind':'record','sourceIds':['row']}]}}}
        rendered={'stages':{stage:{'geometrySha256':'same','nodeSignatures':{'records':'same'}} for stage in ('skeleton','component','delivery')}}
        self.assertEqual(review_plan(observed,content,rendered)['groups']['rows']['bindings'],['records'])

    def test_full_tree_preserves_hierarchy_text_states_and_cells(self):
        content={'root':{'id':'page','kind':'container','layout':{'direction':'vertical'},'children':[
            {'id':'records','kind':'component','component':'Table','sourceIds':['row-0','row-1'],
             'props':{'data':[{'name':'甲','locked':False},{'name':'乙','locked':True}],
                      'columns':[{'key':'name','cell':{'id':'action','kind':'component','component':'Button',
                         'props':{'disabled':{'bind':'row.locked'}},
                         'children':[{'id':'label','kind':'text','value':{'bind':'row.name'}}]}}]}}]}}
        result=require_full_tree(content)
        table=result['root']['children'][0]
        self.assertEqual(result,content)
        self.assertIsNot(result,content)
        self.assertEqual(table['sourceIds'],['row-0','row-1'])
        cell=table['props']['columns'][0]['cell']
        self.assertEqual(cell['props']['disabled'],{'bind':'row.locked'})
        self.assertEqual(cell['children'][0]['value'],{'bind':'row.name'})

    def test_shorthand_and_implicit_ids_are_rejected(self):
        for content in ({'definitions':{},'root':{'id':'page','kind':'text','value':'正文'}},
                        {'root':{'ref':'fragment'}},
                        {'root':{'id':'button','kind':'component','use':'Button'}},
                        {'root':{'kind':'text','value':'missing id'}},
                        {'root':{'id':'page','kind':'container','children':['implicit text']}},
                        {'root':{'id':'records','kind':'component','component':'Table','props':{'data':{'$repeat':{'count':2,'value':{}}}}}}):
            with self.assertRaisesRegex(ValueError,'full_tree_required'):require_full_tree(content)

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
