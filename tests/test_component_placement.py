import copy
import importlib
from pathlib import Path
import unittest
from validators.ui_ir import load_json

placement = importlib.import_module('core.component-resolver.placement')
ROOT = Path(__file__).resolve().parents[1]


class SourcePlacementTests(unittest.TestCase):
    def setUp(self):
        self.registry = placement.registry_module.ComponentRegistry(
            load_json(ROOT/'registries/components/catalog.json'),
            load_json(ROOT/'registries/components/fidelity-reports.json'))
        self.bundle = load_json(ROOT/'adapters/figma/metadata/official-fixture-reference/component_ir.json')
        self.bundle['components'] = [c for c in self.bundle['components']
                                     if c['logicalComponentId']=='form.input.default.medium']
        self.geometry = placement.SourceGeometry(self.bundle, self.registry)
        self.instance = dict(id='input', type='ComponentInstance',
                             componentId='form.input.default.medium', variant='default')
        self.box = dict(x=24, y=80, width=336, height=32)

    def test_source_size_preserved_without_mutating_cell_or_instance(self):
        original = copy.deepcopy((self.instance, self.box))
        result = self.geometry.place(self.instance, self.box)
        self.assertEqual(result['instanceBox'], dict(x=24,y=80,width=240,height=32))
        self.assertEqual(result['cellBox'], self.box)
        self.assertEqual(result['instance']['layout']['width']['value'],240)
        self.assertEqual((self.instance,self.box),original)

    def test_source_tampering_duplicate_and_wrong_type_rejected(self):
        for change in ('size','duplicate','type'):
            bundle = copy.deepcopy(self.bundle)
            if change=='size': bundle['components'][0]['rootBounds']['width'] += 1
            if change=='duplicate': bundle['components'].append(copy.deepcopy(bundle['components'][0]))
            if change=='type': bundle['components'][0]['componentType']='Button'
            with self.assertRaises(ValueError): placement.SourceGeometry(bundle,self.registry)

    def test_overflow_missing_variant_and_nonfinite_box_rejected(self):
        for box in (dict(self.box,width=239),dict(self.box,height=31),dict(self.box,x=float('nan'))):
            with self.assertRaises(ValueError): self.geometry.place(self.instance,box)
        with self.assertRaises(ValueError):
            self.geometry.place(dict(self.instance,variant='unregistered'),self.box)

    def test_incomplete_geometry_cannot_emit_assembly_operations(self):
        from tests import test_component_assembly as fixture_module
        fixture = fixture_module.AssemblyTests()
        fixture.setUp()
        f = fixture.fixture.fixture
        result = fixture_module.assembly.assemble(
            f.analysis,f.page,fixture_module.BASE,f.review,f.plan,
            fixture.fixture.decisions,fixture.fixture.registry,f.registry,
            fixture.content,source_geometry=self.geometry,allow_test_fixtures=True)
        self.assertEqual(result['status'],'FAIL')
        self.assertEqual(result['operations'],[])
        self.assertFalse(result['sourcePlacementVerified'])
        self.assertFalse(result['readyForAdapter'])

    def test_complete_source_geometry_preserves_cells_and_section_local_changes(self):
        from tests import test_component_assembly as fixture_module
        fixture=fixture_module.AssemblyTests();fixture.setUp();f=fixture.fixture.fixture
        bundle=load_json(ROOT/'adapters/figma/metadata/official-fixture-reference/component_ir.json')
        bundle['components'].extend(load_json(ROOT/'adapters/figma/metadata/table-reference/component_ir.json')['components'])
        geometry=placement.SourceGeometry(bundle,fixture.fixture.registry)
        for row in fixture.fixture.run_mapping()['rows']:
            size=geometry.place(dict(componentId=row['componentId'],variant=row['variant']),dict(x=0,y=0,width=10000,height=10000))['instanceBox']
            f.plan['measurements'][row['sourceId']].update(width=size['width'],height=size['height'])
        tree,_=f.run_plan();fixture.fixture.decisions['layoutTreeSha256']=fixture_module.builder.fingerprint(tree)
        fixture.content['mappingSha256']=fixture_module.builder.fingerprint(fixture.fixture.run_mapping())
        def run(previous=None):
            return fixture_module.assembly.assemble(f.analysis,f.page,fixture_module.BASE,f.review,f.plan,
                fixture.fixture.decisions,fixture.fixture.registry,f.registry,fixture.content,
                source_geometry=geometry,previous=previous,allow_test_fixtures=True)
        baseline=run();self.assertEqual(baseline['status'],'PASS',baseline['issues'])
        self.assertTrue(baseline['sourcePlacementVerified']);self.assertFalse(baseline['readyForAdapter'])
        input_op=next(o for o in baseline['operations'] if o['sourceId']=='name')
        self.assertEqual(input_op['box']['width'],336)
        self.assertEqual(input_op['replacement']['id'],input_op['targetCellId'])
        self.assertEqual(input_op['replacement']['layout']['width']['value'],336)
        self.assertEqual(input_op['instance']['layout']['width']['value'],240)
        self.assertEqual(input_op['replacement']['children'][0]['id'],input_op['targetCellId']+'.instance')
        self.assertEqual(run(baseline)['operations'],[])
        next(i for i in fixture.content['items'] if i['sourceId']=='add')['slots']['label'][0]['claim']['text']='新增'
        changed=run(baseline);self.assertEqual(changed['changedSections'],['toolbar'])
        self.assertEqual(changed['sections']['filters'],baseline['sections']['filters'])
        entry=next(i for i in fixture.content['items'] if i['sourceId']=='name')
        entry['cellSlots']={'label':[{'id':'name-cell-label','type':'Text','sourceIds':['name'],
            'text':'姓名','style':{'typographyToken':{'token':'typography.body'},'colorToken':{'token':'color.text'}},
            'layout':{'width':{'mode':'fixed','value':28},'height':{'mode':'fixed','value':22}}}]}
        composed=run(changed)
        self.assertEqual(composed['status'],'PASS',composed['issues'])
        self.assertEqual(composed['changedSections'],['filters'])
        replacement=next(o for o in composed['operations'] if o['sourceId']=='name')['replacement']
        self.assertEqual([c['id'].split('.')[-1] for c in replacement['children']],['label','control'])
        self.assertEqual(replacement['children'][1]['children'][0]['componentId'],'form.input.default.medium')
        self.assertEqual(run(composed)['operations'],[])
        entry['cellSlots']['label'][0]['text']='伪造字段'
        rejected=run(composed)
        self.assertEqual(rejected['status'],'FAIL');self.assertEqual(rejected['operations'],[])
