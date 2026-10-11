import copy
import importlib
import unittest
from tests import test_component_assembly as fixture_module
from core.prototype.parser import parse
from validators.ui_ir import load_json

materialize=importlib.import_module('core.component-resolver.materialize')
placement=importlib.import_module('core.component-resolver.placement')


class MaterializationTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture_module.AssemblyTests();self.fixture.setUp();f=self.fixture.fixture.fixture
        observations=load_json(fixture_module.BASE/'observations.json');observations['unknowns']=[]
        for block in observations['page']['blocks']:block['staticContent']=[]
        observations['page']['blocks']=[b for b in observations['page']['blocks'] if b['id']!='note']
        f.analysis=parse(observations,fixture_module.BASE);f.page=fixture_module.builder.build(f.analysis)
        f.review['analysisSha256']=fixture_module.builder.fingerprint(f.analysis)
        f.plan['pageTreeSha256']=fixture_module.builder.fingerprint(f.page);f.plan['sectionRegions'].pop('note')
        bundle=load_json(fixture_module.ROOT/'adapters/figma/metadata/official-fixture-reference/component_ir.json')
        bundle['components'].extend(load_json(fixture_module.ROOT/'adapters/figma/metadata/table-reference/component_ir.json')['components'])
        self.geometry=placement.SourceGeometry(bundle,self.fixture.fixture.registry)
        for entry in self.fixture.fixture.decisions['items']:
            logical={'name':'form.input.default.medium','status':'form.select.default.medium','users':'data.table.default'}.get(entry['sourceId'],'action.button.primary.medium')
            size=self.geometry.place(dict(componentId=logical,variant='default'),dict(x=0,y=0,width=10000,height=10000))['instanceBox']
            f.plan['measurements'][entry['sourceId']].update(width=size['width'],height=size['height'])
        self.tree,_=f.run_plan();self.fixture.fixture.decisions['layoutTreeSha256']=fixture_module.builder.fingerprint(self.tree)
        self.fixture.content['mappingSha256']=fixture_module.builder.fingerprint(self.fixture.fixture.run_mapping())
        self.assembly=fixture_module.assembly.assemble(f.analysis,f.page,fixture_module.BASE,f.review,f.plan,
            self.fixture.fixture.decisions,self.fixture.fixture.registry,f.registry,self.fixture.content,
            source_geometry=self.geometry,allow_test_fixtures=True)

    def run_materialize(self):
        return materialize.materialize(self.assembly,self.tree,self.fixture.fixture.fixture.registry,document_id='assembly-contract')

    def test_preserves_all_containers_and_cell_envelopes_with_source_sized_instances(self):
        before=copy.deepcopy((self.tree,self.assembly));result=self.run_materialize()
        self.assertEqual(result['status'],'PASS');self.assertFalse(result['readyForAdapter'])
        nodes={}
        def walk(n):
            nodes[n['id']]=n
            for c in n.get('children',[]):walk(c)
        walk(result['document']['pages'][0])
        for operations in self.assembly['sections'].values():
            for op in operations:
                self.assertEqual(nodes[op['targetCellId']]['type'],'Frame')
                self.assertEqual(nodes[op['targetCellId']]['layout']['width']['value'],op['box']['width'])
                self.assertEqual(nodes[op['instance']['id']]['layout'],op['instance']['layout'])
        self.assertEqual((self.tree,self.assembly),before)

    def test_modified_tree_checkpoint_and_unverified_source_rejected(self):
        for mutate in (lambda:self.tree['page'].update(id='changed'),lambda:self.assembly.update(stateSha256='0'*64),lambda:self.assembly.update(sourcePlacementVerified=False)):
            self.setUp();mutate()
            with self.assertRaises(ValueError):self.run_materialize()
