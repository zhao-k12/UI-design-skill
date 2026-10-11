import copy
import unittest
from adapters.penpot.content import prepare_content
from validators.ui_ir import ROOT, load_json


class NativeContentTests(unittest.TestCase):
    def setUp(self):
        self.proofs=load_json(ROOT/'adapters/penpot/metadata/native-fidelity.json')

    def test_maps_unique_admitted_button_and_placeholder_texts(self):
        for proof in self.proofs.values():
            logical=proof['logicalId']
            if logical=='data.table.default':continue
            node={'componentId':logical}
            if logical.startswith('action.'):
                node['slots']={'label':[{'id':'label','type':'Text','text':'导出'}]}
            else:node['props']={'value' if logical=='form.select.default.medium' else 'placeholder':'姓名'}
            before=copy.deepcopy(proof)
            result=prepare_content(node,proof)
            self.assertEqual(len(result),1)
            self.assertIn('fontId',result[0]['style'])
            self.assertEqual(proof,before)

    def test_unsupported_content_is_not_guessed(self):
        nodes=[{'componentId':'data.table.default','props':{'headers':['姓名']}},
               {'componentId':'form.input.default.medium','props':{'value':'姓名'}},
               {'componentId':'action.button.primary.medium','slots':{'label':[{'id':'a','type':'Text','text':'导出','style':{'fill':'#ff0000'}}]}}]
        for node in nodes:
            proof=next(p for p in self.proofs.values() if p['logicalId']==node['componentId'])
            with self.assertRaises(ValueError):prepare_content(node,proof)

    def test_ambiguous_or_missing_native_text_fails(self):
        proof=next(p for p in self.proofs.values() if p['logicalId']=='action.button.primary.medium')
        node={'componentId':proof['logicalId'],'slots':{'label':[{'id':'a','type':'Text','text':'导出'}]}}
        for nodes in ([],proof['nativeEvidence']['nodes']*2):
            changed=copy.deepcopy(proof);changed['nativeEvidence']['nodes']=nodes
            with self.assertRaises(ValueError):prepare_content(node,changed)
