import copy
import unittest
import json
from adapters.headed_table import prepare_source
from adapters.headed_table_policy import header_background_union
from validators.ui_ir import ROOT

class HeadedTablePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plans = [prepare_source(ROOT/'component-builder/runtime-renderer/metadata/headed-table-source'/case)
                     for case in ('two-column-typography', 'four-column-typography')]

    def test_both_exact_unions_without_source_mutation(self):
        for plan in self.plans:
            before = copy.deepcopy(plan)
            union = header_background_union(plan)
            self.assertEqual(union['bounds'], plan['rows'][0]['bounds'])
            self.assertEqual(union['bounds']['width'], plan['rootBounds']['width'] + 1)
            self.assertEqual(plan, before)
            self.assertFalse(union['productionAdmission'])

    def test_gap_overlap_wrong_color_and_body_rejected(self):
        for mutation in ('gap', 'overlap', 'color', 'body'):
            plan = copy.deepcopy(self.plans[0])
            cell = plan['rows'][0]['cells'][1]
            if mutation == 'gap': cell['bounds']['x'] += 1
            if mutation == 'overlap': cell['bounds']['x'] -= 1
            if mutation == 'color': cell['fill'] = '#ffffff'
            if mutation == 'body': cell['text']['role'] = 'body'
            with self.assertRaisesRegex(ValueError, 'headed_union_not_contiguous'):
                header_background_union(plan)

    def test_new_identity_or_source_digest_cannot_reuse_approval(self):
        for key in ('logicalId', 'componentIrSha256'):
            plan = copy.deepcopy(self.plans[0]); plan[key] = 'changed'
            with self.assertRaisesRegex(ValueError, 'headed_approval_scope_mismatch'):
                header_background_union(plan)

    def test_actual_repair_changes_only_one_fill_per_component(self):
        evidence=ROOT/'adapters/penpot/metadata/headed-table-native'
        repair=evidence/'header-union'
        for before_number,after_number in ((6,2),(5,3)):
            before=json.loads((evidence/f'font-recovery-discovery-{before_number}.json').read_text(encoding='utf8'))['result']
            after=json.loads((repair/f'discovery-{after_number}.json').read_text(encoding='utf8'))['result']
            self.assertEqual(after['status'],'CAPTURED')
            self.assertEqual(after['createdNodeIds'],[])
            self.assertEqual(after['mutatedNodeIds'],[])
            self.assertEqual([n['reference'] for n in before['nodes']],[n['reference'] for n in after['nodes']])
            changed=[(a,b) for a,b in zip(before['nodes'],after['nodes']) if a!=b]
            self.assertEqual(len(changed),1)
            a,b=changed[0]
            self.assertEqual([key for key in a if a[key]!=b[key]],['fills'])
            self.assertEqual(a['fills'],[])
            self.assertEqual(b['fills'],[{'fillColor':'#f8f8f9','fillOpacity':1,
                'fillColorGradient':None,'fillColorRefFile':None,'fillColorRefId':None,'fillImage':None}])

    def test_independent_raw_png_and_geometry_after_repair(self):
        from adapters.penpot.headed_table_repair_diagnostic import diagnose
        evidence=ROOT/'adapters/penpot/metadata/headed-table-native/header-union'
        for number,case in ((2,'two-column-typography'),(3,'four-column-typography')):
            report,raw=diagnose(evidence/f'discovery-{number}.json',ROOT/'component-builder/runtime-renderer/metadata/headed-table-source'/case)
            self.assertEqual(report['geometry']['status'],'PASS')
            self.assertEqual(report['outsideTextAndExactHorizontalRegions'],0)
            self.assertFalse(report['productionAdmission'])
            self.assertGreater(len(raw),0)
