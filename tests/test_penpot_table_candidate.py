"""Source plan and write-host guards, not native Table acceptance."""
from copy import deepcopy
import unittest
from validators.ui_ir import ROOT
from adapters.penpot.table_candidate import prepare_table_candidate
from adapters.penpot.host.server import candidate_assets


class TablePlanTests(unittest.TestCase):
    def test_source_fractional_columns_and_independent_bottom_pseudo_preserved(self):
        plan=prepare_table_candidate(ROOT/'adapters/figma/metadata/table-reference','file','page')
        self.assertEqual(plan['rootBounds'],{'width':1392,'height':144})
        self.assertEqual([c['bounds']['width'] for c in plan['rows'][0]['cells']],[464.328125,464.328125,464.34375])
        self.assertEqual(plan['rows'][0]['bounds']['width'],1393)
        self.assertEqual(plan['rows'][0]['bottomBorder']['fill'],'#e8eaec')
        self.assertEqual(plan['bottomPseudo']['fill'],'#dcdee2')
        self.assertEqual(plan['fidelityGate'],'NOT_RUN')
        self.assertNotIn('calibrationBaselineOffset',plan)

    def test_changed_column_or_text_cannot_be_hosted(self):
        plan=prepare_table_candidate(ROOT/'adapters/figma/metadata/table-reference','file','page')
        hosted=candidate_assets('http://127.0.0.1:60000','file','nonce',plan)
        self.assertIn('await buildPenpotTableCandidate(penpot,candidateSpec)',hosted['/plugin.js'][1])
        self.assertIn('unsupported_table_action',hosted['/plugin.js'][1])
        for key in ('bounds','text'):
            changed=deepcopy(plan)
            if key=='bounds':changed['rows'][0]['cells'][0]['bounds']['width']=464
            else:changed['rows'][0]['cells'][0]['text']['characters']='错误'
            with self.assertRaises(ValueError):candidate_assets('http://127.0.0.1:60000','file','nonce',changed)
